from fastapi import Request                         # Для получения реквестов
import time                                         # Будем время измерять
from collections import defaultdict                 # Для словаря с хранением времени
from fastapi.responses import JSONResponse          # Для ответа json-ом

class RateLimiter:
    def __init__(self, max_calls=3, period=1.0):
        self.calls = defaultdict(list)                      # Словарь для хранения времени запросов по IP-адресам
        self.max_calls = max_calls                          # Максимальное число запросов за период
        self.period = period                                # Период времени (в секундах), за который считаются запросы

    async def check_limit(self, request: Request):
        if request.client:
            client_ip = request.client.host                             # Получаем IP-адрес клиента
        else:
            raise Exception("Пустой request.client")                    # Если по каким-то причинам IP не доступен, выбрасываем исключение или обрабатываем иначе
        
        now = time.time()                                   # Текущее время
        
        self.calls[client_ip] = [                                                       # Удаляем из списка все запросы, сделанные раньше, чем текущий момент минус период
            t for t in self.calls[client_ip] if now - t < self.period
        ]
        
        if len(self.calls[client_ip]) >= self.max_calls:                                        # Проверяем, не превышает ли количество запросов за период лимит
            return JSONResponse(                                                                            # Возвращаем ответ с ошибкой 429 Too Many Requests
                status_code=429,
                content={"detail": f"Rate limit: {self.max_calls} requests per {self.period} sec"},
                headers={"Retry-After": str(self.period)}                                                   # Подсказка, когда можно повторить
            )
        
        self.calls[client_ip].append(now)                                   # Добавляем текущий запрос в список
        return None                                                         # Возвращаем None, если лимит не превышен

rate_limiter = RateLimiter(max_calls=3, period=1.0)         # Создаем экземпляр лимитера с лимитом 3 запроса в 1 секунду