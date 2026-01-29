# Запуск локально и в Docker

## Локально
1. Создайте виртуальное окружение и установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Подготовьте переменные окружения (см. `.env.example`).
3. Примените миграции и запустите сервер:
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
4. Запустите Celery:
   ```bash
   celery -A config.celery worker -l info
   ```

## Docker
```bash
cp .env.example .env

docker compose up --build
```
