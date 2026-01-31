# Запуск локально и в Docker

## Local run (без Docker)

### Предусловия
- Установленные PostgreSQL и Redis, запущенные локально.
- Созданное виртуальное окружение + зависимости проекта.

### Пошаговый запуск
1. Скопируйте локальный env-файл:
   ```bash
   cp .env.local.example .env
   ```
2. Создайте базы и роли (пример под значения из `.env`):
   ```bash
   psql -U postgres -f scripts/create_local_dbs.sql
   ```
   Либо вручную:
   ```sql
   CREATE USER app_user WITH PASSWORD 'app_password';
   CREATE DATABASE app_db OWNER app_user;

   CREATE USER portal_user WITH PASSWORD 'portal_password';
   CREATE DATABASE portal_db OWNER portal_user;
   ```
3. Примените миграции приложения:
   ```bash
   python manage.py migrate
   ```
4. Заполните тестовые данные приложения:
   ```bash
   python manage.py bootstrap_local_app --reset
   ```
5. Создайте таблицы и тестовые данные портала:
   ```bash
   python manage.py bootstrap_local_portal --reset
   ```
6. Сгенерируйте тестовый DOCX:
   ```bash
   python manage.py make_test_docx --out out/test.docx
   ```
7. Запустите Django:
   ```bash
   python manage.py runserver 127.0.0.1:8000
   ```
8. Запустите Celery worker:
   ```bash
   celery -A config worker -l info
   ```

### Тесты
- `bootstrap_local_portal` требует доступный PostgreSQL для `DATABASES['portal']`. В CI без Postgres тест будет пропущен.

## Docker (для закрытого контура, позже)
```bash
cp .env.example .env

docker compose up --build
```
