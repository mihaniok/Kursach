#!/bin/sh

echo "Waiting for Postgres..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Postgres is up!"

python manage.py migrate --noinput

# Загружаем группы
python manage.py loaddata fixtures/groups.json || echo "No groups fixture"

# Создаём суперпользователя
python manage.py shell < create_superuser.py

# Запуск Django
exec python manage.py runserver 0.0.0.0:8000
