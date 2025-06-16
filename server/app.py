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

from .middleware import rate_limiter
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

@app.middleware("http")                                                     # Подключаем middleware к FastAPI приложению
async def rate_limit_middleware(request: Request, call_next):
    if request.client:

        logger.info(f"\n[Before] IP: {request.client.host} | Calls: {len(rate_limiter.calls.get(request.client.host, []))}")        # Логируем IP клиента и количество запросов, сделанных за период

        limit_response = await rate_limiter.check_limit(request)                    # Проверяем лимит для текущего IP
        if limit_response:                                                          # Если лимит превышен, логируем блокировку
            print(f"[Blocked] IP: {request.client.host}")
            return limit_response                                                   # Возвращаем ответ с ошибкой 429 и не пропускаем дальше

        response = await call_next(request)                                         # Если лимит не превышен, продолжаем обработку запроса

        logger.info(f"[After] IP: {request.client.host} | Calls: {len(rate_limiter.calls.get(request.client.host, []))}")        # После обработки запроса: логируем IP и обновленный уровень запросов
    else:
        response = await call_next(request)        # Если по каким-то причинам IP не получен, просто пропускаем запрос

    return response                                # Возвращаем ответ клиенту

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
    telegram_user_id = request.query_params.get("telegram_user_id")                         # Получаем telegram_user_id из параметров запроса
    if not telegram_user_id:
        raise HTTPException(status_code=400, detail="Telegram user ID is missing")

    client_id = os.getenv("VK_APP_ID")                                                      # ID приложения
    redirect_uri = f"{os.getenv('VK_CALLBACK_URL')}?telegram_user_id={telegram_user_id}"    # URL для callback
    scope = 6                                                                               # Запрашиваемые права

    # logger.info(redirect_uri)
    url = f'https://oauth.vk.com/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&response_type=code'        # Формируем VK URL для авторизации
    
    #logger.info(url)
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
        urltoken = f'https://oauth.vk.com/access_token?client_id={client_id}&client_secret={client_secret}&redirect_uri={redirect_uri}&code={code}'        # Обмен кода на токен
        async with httpx.AsyncClient() as client:
            response = await client.get(urltoken)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Ошибка VK ID: {response.text}")

            token_data = response.json()

            if 'error' in token_data:                                                                                                    # Пытаемся получить токен
                raise HTTPException(status_code=400, detail={'error': 'Failed to obtain access token', 'details': token_data})      
            
            access_token = token_data.get("access_token")
            
            try:
                telegram_id=int(telegram_user_id)                                      # Переводим в число для БД
                encrypted_token = cipher.encrypt(access_token.encode())                # Шифруем токен перед сохранением
                
                async with get_session() as session:
                    user = await session.get(User, telegram_id)                                        # Проверяем существование пользователя
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
                    
                    saved_token_obj = await session.get(VKToken, telegram_id)                               # Проверка: получаем сохранённый токен из БД и расшифровываем
                    if saved_token_obj and saved_token_obj.encrypted_token:
                        decrypted_token = cipher.decrypt(saved_token_obj.encrypted_token).decode()
                        if decrypted_token != access_token:
                            logger.warning("Внимание! Дешифрованный токен не совпадает с исходным!")
                            
                            
                    html_file = Path(__file__).parent / "success.html"                                      # Читаем файл и возвращаем его содержимое (Страничка успешной записи)
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