# Развёртывание в закрытом контуре (Docker)

## Предварительные требования
- Docker Engine и Docker Compose plugin (команда `docker compose`).
- Сетевой доступ к внешней БД портала: `PORTAL_HOST:PORTAL_PORT`.
- Доступ к хосту, где будет размещён каталог проекта (рекомендуется `/opt/analiz_svodok`).

## Структура папок на хосте
Рекомендуемая структура:

```
/opt/analiz_svodok/
  .env
  docker-compose.closed.yml
  fixtures/
    text/
    sql/
  artifacts/
  scripts/
    closed/
```

## Настройка .env для закрытого контура
Минимально обязательные переменные:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- `DJANGO_ALLOWED_HOSTS` (например `*` или домен/подсеть)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `PORTAL_HOST`, `PORTAL_PORT`, `PORTAL_DB`, `PORTAL_USER`, `PORTAL_PASSWORD`

Дополнительно (если нужно явно переопределить):
- `APP_ADMIN_LOGIN`, `APP_ADMIN_PASSWORD` — суперпользователь создаётся автоматически при миграциях.
- `SEMANTIC_MODEL_NAME` — модель SentenceTransformer, запечённая в образ.

> В compose-файле для закрытого контура параметры подключения к `app-postgres` и Redis
> задаются напрямую (через `service name`), поэтому `POSTGRES_HOST` и `REDIS_URL`
> в `.env` можно не указывать.

## Первый запуск
1. **Загрузка образов** (если пришли в виде tar):
   ```bash
   docker load -i dist/analiz_svodok_images_<version>.tar
   ```
2. **Запуск стека**:
   ```bash
   ./scripts/closed/up.sh
   ```
3. **Миграции**:
   ```bash
   ./scripts/closed/migrate.sh
   ```
4. **Администратор**: создаётся автоматически при миграциях,
   если заданы `APP_ADMIN_LOGIN` и `APP_ADMIN_PASSWORD`.
5. **Проверка**:
   ```bash
   curl -s http://localhost:8000/health
   ```

## Подключение к порталу
- Приложение подключается к портальной БД по TCP `PORTAL_HOST:PORTAL_PORT`.
- Пользователь БД портала должен иметь права только на чтение таблиц `events`, `offenders`, `subdivision`.
- Сетевые правила должны разрешать соединение контейнеров `web/celery` с порталом.

## Прогон тестовой сводки
### Через UI
1. Откройте `/upload`.
2. Загрузите DOCX, который хранится вне репозитория (например, в `dist/` или на хосте).

### Через smoke_docx
```bash
docker compose -f docker-compose.closed.yml exec -T web \
  python manage.py smoke_docx --path /data/fixtures/text/sample_01.txt
```
TXT фикстуры расположены в `fixtures/text/` (маунтятся в `/data/fixtures/text`).
Результат сохраняется в `/data/artifacts/smoke_result.json` (на хосте `./artifacts`).

## Логи и диагностика
- Все логи: `./scripts/closed/logs.sh`
- Только web: `./scripts/closed/logs.sh web`
- Только celery: `./scripts/closed/logs.sh celery`
- Только БД приложения: `./scripts/closed/logs.sh app-postgres`

## Обновление (патч)
1. Бэкап БД приложения:
   ```bash
   ./scripts/closed/backup_app_db.sh
   ```
2. Загрузка нового образа:
   ```bash
   docker load -i dist/analiz_svodok_images_<version>.tar
   ```
3. Поднять контейнеры:
   ```bash
   ./scripts/closed/up.sh
   ```
4. Миграции:
   ```bash
   ./scripts/closed/migrate.sh
   ```
5. Smoke test:
   ```bash
   docker compose -f docker-compose.closed.yml exec -T web \
     python manage.py smoke_docx --path /data/fixtures/text/sample_01.txt
   ```

## Откат
1. Остановить текущий стек:
   ```bash
   ./scripts/closed/down.sh
   ```
2. Загрузить прошлый образ:
   ```bash
   docker load -i dist/analiz_svodok_images_<version>.tar
   ```
3. Поднять контейнеры:
   ```bash
   ./scripts/closed/up.sh
   ```
4. Восстановить БД приложения:
   ```bash
   ./scripts/closed/restore_app_db.sh ./artifacts/app_db_backup_<timestamp>.dump
   ```

## Offline модель
- Кэш модели встроен в образ на этапе сборки и находится в `/models/hf`.
- В рантайме включён офлайн-режим (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`).
- Чтобы заменить модель, пересоберите образ в открытой среде с другим
  `SEMANTIC_MODEL_NAME` и передайте новый tar в закрытый контур.

## Release bundle (пакет для переноса)
Скрипт `scripts/release/make_release_bundle.sh` собирает bundle:
- образы `analiz_svodok_web` и `analiz_svodok_celery`;
- `docker-compose.closed.yml`, `.env.example`, документацию и скрипты.

Пример:
```bash
APP_VERSION=1.2.3 SEMANTIC_MODEL_NAME=intfloat/multilingual-e5-large \
  ./scripts/release/make_release_bundle.sh
```

В `dist/` будут:
- `analiz_svodok_images_<version>.tar`
- `docker-compose.closed.yml`
- `.env.example`
- `CLOSED_CONTOUR_DEPLOY.md`
- `scripts/closed/*`
- `SHA256SUMS`
