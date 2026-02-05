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
- `SEMANTIC_MODEL_PATH` — путь к локальному снапшоту модели (если нужен явный путь).
- `SEMANTIC_MODEL_CACHE_DIR`, `SEMANTIC_MODEL_LOCAL_ONLY` — локальный кэш/офлайн-режим.
- `MODEL_CACHE_MODE` — режим подготовки кэша (`download`/`local`).
- `SEMANTIC_MODEL_LOCK_FILE` — путь к lock-файлу ревизии модели.
- `EVENT_TYPE_MATCH_THRESHOLD` — порог определения типа события (по умолчанию 0.78).

**SQL-контракт:**
- `PORTAL_QUERY_CONFIG_PATH` — путь к `configs/portal_queries.yaml`.
- `PORTAL_ADMIN_ENABLED` — включение тестового CRUD для портальной БД (только при `DJANGO_DEBUG=true`).

## Portal admin (TEST)
**Временная тестовая функция. По умолчанию выключена.**

Чтобы включить:
```bash
export DJANGO_DEBUG=true
export PORTAL_ADMIN_ENABLED=1
```
В админке появится раздел **TEST/PORTAL: события** (CRUD тестовых записей).
Чтобы отключить — уберите `PORTAL_ADMIN_ENABLED` или выключите `DJANGO_DEBUG`.

## Порог семантики и окно времени
Порог семантики и окно времени хранятся в таблице настроек приложения:
- `semantic_threshold_subdivision` — порог совпадения подразделения (по умолчанию 0.8).
- `time_window_minutes` — окно сравнения по времени (по умолчанию 30).

Чтобы изменить значения (пример через Django shell):
```bash
docker compose -f docker-compose.offline.yml run --rm web \
  python manage.py shell -c "from apps.core.models import Setting; Setting.objects.update_or_create(key='semantic_threshold_subdivision', defaults={'value': 0.85}); Setting.objects.update_or_create(key='time_window_minutes', defaults={'value': 45});"
```

## Типы событий и паттерны событий
Справочник хранится в БД приложения и используется при семантическом сопоставлении текста.

### Формат XLSX
Колонки:
1. **Тип события** (строка, обязательна для строки).
2. **Паттерн события** (текстовый фрагмент, необязателен).
3. **Статья КоАП** (строка «номер + часть», необязателен).

Примеры строк:
```
Выявление | выявлены | 12.1
Задержание | задержан | 18.8
Задержание | задержаны |
Проверка | на посту |
Опрос | опрошен |
Осмотр | осмотр проведен | 27.3
Выявление | обнаружены |
```

### Импорт через админку
1) Откройте **Типы событий**.
2) Нажмите **Импорт XLSX**.
3) Загрузите файл и проверьте отчёт по созданным/обновлённым строкам.

### Импорт через команду
```bash
python manage.py import_event_types_xlsx --path /path/to/file.xlsx
```
Для проверки без сохранения:
```bash
python manage.py import_event_types_xlsx --path /path/to/file.xlsx --dry-run
```

### Troubleshooting
- **Ошибка “row N: пустой тип события при заполненных данных”** —
  в строке указан паттерн или статья КоАП без типа события.
- **Ничего не импортируется** —
  убедитесь, что файл именно `.xlsx`, и в нём заполнены первые три колонки.

## Конфиг SQL-запросов к порталу
Файл: `configs/portal_queries.yaml`.

Структура:
- `find_candidates` — поиск событий по интервалу времени (используются параметры `ts_from`, `ts_to`, `ts_exact`, `limit`).

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
SELECT id, detected_at
FROM portal_events
ORDER BY detected_at DESC
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
