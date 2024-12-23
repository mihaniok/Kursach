# Dockerfile

# Используем официальный образ Python в качестве базового
FROM python:3.12-slim

# Установим рабочую директорию внутри контейнера
WORKDIR /app

# Установим переменные окружения для предотвращения создания .pyc файлов и буферизации вывода
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Установим системные зависимости для psycopg2
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Указываем команду для запуска приложения с помощью gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
