# Используем официальный образ Python
FROM python

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы
COPY app/ .

# Команда для запуска бота
CMD ["python", "main.py"]