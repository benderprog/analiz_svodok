# Руководство администратора

Документ описывает настройку окружения, запросов к порталу и эксплуатационные операции.

## Переменные окружения (.env)

Минимальные параметры (см. `.env.example`):
- `DJANGO_SECRET_KEY` — секретный ключ Django.
- `DJANGO_DEBUG` — режим отладки (`true/false`).
- `DJANGO_ALLOWED_HOSTS` — разрешённые хосты.
- `TAG` — тег релизных образов (`analiz_svodok_web:<TAG>` и `analiz_svodok_celery:<TAG>`).

**База приложения (app_db):**
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.

**База портала (portal_db):**
- `PORTAL_DB`, `PORTAL_USER`, `PORTAL_PASSWORD`, `PORTAL_HOST`, `PORTAL_PORT`.

**Redis/Celery:**
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`.

**Пользователь администратора:**
- `APP_ADMIN_LOGIN`, `APP_ADMIN_PASSWORD`.

**Результаты и NLP:**
- `RESULT_TTL_SECONDS` — TTL результатов в Redis (по умолчанию 1800 секунд).
- `SEMANTIC_MODEL_NAME` — имя модели SentenceTransformer.
- `SEMANTIC_MODEL_CACHE_DIR`, `SEMANTIC_MODEL_LOCAL_ONLY` — локальный кэш/офлайн-режим.

**SQL-контракт:**
- `PORTAL_QUERY_CONFIG_PATH` — путь к `configs/portal_queries.yaml`.

## Порог семантики и окно времени
Порог семантики и окно времени хранятся в таблице настроек приложения:
- `semantic_threshold_subdivision` — порог совпадения подразделения (по умолчанию 0.8).
- `time_window_minutes` — окно сравнения по времени (по умолчанию 30).

Чтобы изменить значения (пример через Django shell):
```bash
docker compose -f docker-compose.offline.yml run --rm web \
  python manage.py shell -c "from apps.core.models import Setting; Setting.objects.update_or_create(key='semantic_threshold_subdivision', defaults={'value': 0.85}); Setting.objects.update_or_create(key='time_window_minutes', defaults={'value': 45});"
```

## Конфиг SQL-запросов к порталу
Файл: `configs/portal_queries.yaml`.

Структура:
- `find_candidates` — поиск событий по интервалу времени (используются параметры `ts_from`, `ts_to`, `ts_exact`, `limit`).
- `fetch_subdivision` — выборка подразделения по `id`.
- `fetch_offenders` — выборка нарушителей по `event_id`.

### Адаптация под другую схему БД
1) Замените имена таблиц и полей в SQL.
2) Сохраните параметры `%(...)s` (иначе нарушится безопасная подстановка).
3) Перезапустите сервисы после изменения.

### Проверка запросов через psql (тестовый портал)
```bash
docker compose -f docker-compose.offline.yml exec -T portal-postgres \
  psql -U "$PORTAL_USER" -d "$PORTAL_DB"
```
Пример запроса:
```sql
SELECT id, date_detection
FROM events
ORDER BY date_detection DESC
LIMIT 5;
```

## Seed-данные
- `seed/*.sql` — схема и тестовые данные для **тестовой** БД портала.
- Для изменения тестовых данных редактируйте SQL-файлы и запускайте:
  ```bash
  ./scripts/closed/seed.sh
  ```

## Логи и healthcheck
- Проверка статуса сервисов и `/help`:
  ```bash
  ./scripts/closed/verify.sh
  ```
- Логи всех сервисов:
  ```bash
  ./scripts/closed/logs.sh
  ```
- Логи конкретного сервиса:
  ```bash
  ./scripts/closed/logs.sh web
  ```

## Резервное копирование и сброс данных
- Бэкап БД приложения:
  ```bash
  ./scripts/closed/backup_app_db.sh
  ```
- Восстановление:
  ```bash
  ./scripts/closed/restore_app_db.sh <путь_к_бэкапу>
  ```
- Полный сброс тестовых томов:
  ```bash
  docker compose -f docker-compose.offline.yml down -v
  ```
