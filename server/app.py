from fastapi import FastAPI, Request, HTTPException, responses
import httpx
import redis
from urllib.parse import parse_qs
import logging                                  # Модуль для логирования (ведения журнала событий)
import os
from cryptography.fernet import Fernet
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime
from pathlib import Path

from app.db import get_session, init_db
from app.models import VKToken, User

logging.basicConfig(level=logging.INFO)     # Настройка логов
logger = logging.getLogger(__name__)

FERNET_KEY = os.getenv("FERNET_KEY")  # Ключ для шифрования
if FERNET_KEY:
    cipher = Fernet(FERNET_KEY.encode())
else:
    raise Exception("FERNET_KEY не считан")

app = FastAPI()

redis_client = redis.Redis(             # Подключение к Redis
    host="redis",                       # Имя сервиса в docker-compose
    port=6379,
    db=0,
    decode_responses=True
)

init_db(os.getenv("DATABASE_URL"))      # Подключение к Postgre

@app.get("/vk-callback")
async def vk_callback(request: Request):
    logger.info("Запрос получен")
    params = parse_qs(str(request.url.query))
    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]
    device_id = params.get("device_id", [None])[0]                              # Получаем device_id из параметров callback URL
    if not device_id:
        raise HTTPException(status_code=400, detail="Не получен device_id")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Не хватает code или state")

    redis_key = f"vk_auth:{state}"
    try:
        data = redis_client.hgetall(redis_key)  # Добавлен await
        if not data:
            raise HTTPException(status_code=400, detail="Неверный или устаревший state")

        logger.info("Все считано, приступаю к обмену на токен...")
        # Обмен кода на токен
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://id.vk.com/oauth2/auth",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": os.getenv("VK_APP_ID"),
                    "redirect_uri": os.getenv("VK_CALLBACK_URL"),
                    "code_verifier": data["code_verifier"], # type: ignore
                    "device_id": device_id
                }
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Ошибка VK ID: {response.text}")

            token_data = response.json()

            # Проверяем наличие токена
            if 'access_token' not in token_data:
                logger.error(f"VK не вернул токен. Полный ответ: {token_data}")
                raise HTTPException(
                    status_code=400,
                    detail="VK не вернул access_token"
                )
            
            try:
                # Шифруем токен перед сохранением
                encrypted_token = cipher.encrypt(token_data['access_token'].encode())
                
                async with get_session() as session:
                    # Явно преобразуем telegram_id к int
                    telegram_id = int(data['telegram_id']) # type: ignore
                    
                    # Проверяем существование пользователя
                    user = await session.get(User, telegram_id)
                    if not user:
                        logger.error(f"Пользователь с telegram_id={telegram_id} не найден")
                        raise HTTPException(status_code=404, detail="User not found")
                    
                    stmt = insert(VKToken).values(
                        id=telegram_id,
                        encrypted_token=encrypted_token,
                        created_at=datetime.utcnow()
                    ).on_conflict_do_update(
                        index_elements=['id'],
                        set_={
                            'encrypted_token': encrypted_token,
                            'created_at': datetime.utcnow()
                        }
                    )
                    
                    await session.execute(stmt)
                    await session.commit()
            except Exception as e:
                raise Exception(f"Не удалось записать токен в БД: {e}")

            # Удаляем временные данные из Redis
            redis_client.delete(redis_key)

            # Читаем файл и возвращаем его содержимое
            html_file = Path(__file__).parent / "success.html"
            html_content = html_file.read_text(encoding="utf-8")

            return responses.HTMLResponse(content=html_content, status_code=200)
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка подключения к VK")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")