from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx
from urllib.parse import parse_qs
import logging                                              # Модуль для логирования (ведения журнала событий)
import os                                                   # Для чтения переменных окружения
from cryptography.fernet import Fernet                      # Для шифрования
from sqlalchemy.dialects.postgresql import insert           # Для вставки в БД
from datetime import datetime
from pathlib import Path                                    # Нужен только для отправки сервером html-файла

from app.db import get_session, init_db
from app.models import VKToken, User


logging.basicConfig(level=logging.INFO)                     # Настройка логов
logger = logging.getLogger(__name__)

#logger.info("Все переменные окружения: %s", dict(os.environ))  # Была проблема со считыванием

FERNET_KEY = os.getenv("FERNET_KEY")                        # Ключ для шифрования
if FERNET_KEY:
    cipher = Fernet(FERNET_KEY.encode())
else:
    raise Exception("FERNET_KEY не считан")

app = FastAPI()

init_db(os.getenv("DATABASE_URL"))      # Подключение к Postgre

# ОТЛАЖИВАЛ ПРОБЛЕМУ С .ENV :)
@app.get("/debug")
async def debug():
    return {
        "VK_CALLBACK_URL": os.getenv("VK_CALLBACK_URL"),
    }

# Обрабатываем запрос на авторизацию и строим ссылку
@app.get("/vk/login")
async def vk_login(request: Request):
    # Получаем telegram_user_id из параметров запроса
    telegram_user_id = request.query_params.get("telegram_user_id")
    if not telegram_user_id:
        raise HTTPException(status_code=400, detail="Telegram user ID is missing")

    client_id = os.getenv("VK_APP_ID")                              # ID приложения
    redirect_uri = f"{os.getenv('VK_CALLBACK_URL')}?telegram_user_id={telegram_user_id}"                     # URL для callback
    scope = 6                                                       # Запрашиваемые права

    logger.info(redirect_uri)
    # Формируем VK URL для авторизации
    url = f'https://oauth.vk.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code'
    
    logger.info(url)
    return RedirectResponse(url)

@app.get("/vk/callback")
async def vk_callback(request: Request):
    logger.info("Ответ получен")
    params = parse_qs(str(request.url.query))                                   # Получаем параметры из ответа ВК. Здесь все необходимые
    logger.info(f"Полученные параметры: {params}")
    
    code = params.get("code", [None])[0]
    telegram_user_id = params.get("telegram_user_id", [None])[0]
    client_id = os.getenv("VK_APP_ID")
    client_secret = os.getenv("VK_SECRET")
    redirect_uri = f"{os.getenv('VK_CALLBACK_URL')}?telegram_user_id={telegram_user_id}" 
    
    
    if not code or not telegram_user_id:                                                           # Проверка параметров
        raise HTTPException(status_code=400, detail="Не хватает code или telegram_user_id")
    
    try:
        logger.info("Все считано, приступаю к обмену на токен...")
        # Обмен кода на токен
        urltoken = f'https://oauth.vk.com/access_token?client_id={client_id}&client_secret={client_secret}&redirect_uri={redirect_uri}&code={code}'
        async with httpx.AsyncClient() as client:
            response = await client.get(urltoken)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Ошибка VK ID: {response.text}")

            token_data = response.json()

            # Пытаемся получить токен
            if 'error' in token_data:
                raise HTTPException(status_code=400, detail={'error': 'Failed to obtain access token', 'details': token_data})
            
            access_token = token_data.get("access_token")
            
            try:
                telegram_id=int(telegram_user_id)                                      # Переводим в число для БД
                encrypted_token = cipher.encrypt(access_token.encode())                # Шифруем токен перед сохранением
                
                async with get_session() as session:
                    # Проверяем существование пользователя
                    user = await session.get(User, telegram_id)
                    if not user:
                        logger.error(f"Пользователь с telegram_id={telegram_id} не найден")
                        raise HTTPException(status_code=404, detail="User not found")
                    
                    now = datetime.utcnow()
                    stmt = insert(VKToken).values(
                        id=telegram_id,
                        encrypted_token=encrypted_token,
                        created_at=now
                    ).on_conflict_do_update(
                        index_elements=['id'],
                        set_={
                            'encrypted_token': encrypted_token,
                            'created_at': now
                        }
                    )
                    
                    await session.execute(stmt)
                    await session.commit()
                    
                    # Проверка: получаем сохранённый токен из БД и расшифровываем
                    saved_token_obj = await session.get(VKToken, telegram_id)
                    if saved_token_obj and saved_token_obj.encrypted_token:
                        decrypted_token = cipher.decrypt(saved_token_obj.encrypted_token).decode()
                        if decrypted_token != access_token:
                            logger.warning("Внимание! Дешифрованный токен не совпадает с исходным!")
                            
                            
                    # Читаем файл и возвращаем его содержимое
                    html_file = Path(__file__).parent / "success.html"
                    html_content = html_file.read_text(encoding="utf-8")
                            
                    return HTMLResponse(content=html_content, status_code=200)
            except Exception as e:
                raise Exception(f"Не удалось записать токен в БД: {e}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Ошибка HTTP: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка подключения к VK")
    except HTTPException as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")