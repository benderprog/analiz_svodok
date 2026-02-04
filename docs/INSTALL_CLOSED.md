# Офлайн-развёртывание в закрытом контуре

Документ для оператора. Описывает запуск **без интернета**, без `docker build` и без загрузки образов из DockerHub.

## Что получает оператор
Папка релиза `release_<TAG>/` (или архив), внутри:
- `images/images_<TAG>.tar` — контейнерные образы.
- `docker-compose.offline.yml` — compose **без** секций `build`.
- `.env.example` — шаблон окружения.
- `configs/portal_queries.yaml` — SQL-запросы к БД портала.
- `docs/INSTALL_CLOSED.md` — эта инструкция.
- `scripts/closed/*.sh` — запуск/проверка/логи.
- `seed/*.sql` — SQL для тестовой БД портала.
- `fixtures/*` — тестовые файлы.
- `SHA256SUMS` — контрольные суммы.

## Пошаговая установка

### 1) Проверка целостности
Перейдите в каталог релиза и проверьте контрольные суммы:
```bash
cd release_<TAG>
sha256sum -c SHA256SUMS
```

### 2) Подготовка `.env`
Создайте файл окружения:
```bash
cp .env.example .env
```

Минимально заполните/проверьте:
- `TAG` — тег релиза (должен совпадать с именем образов в `images_<TAG>.tar`). Тег **обязателен** и должен быть записан в `.env` **до запуска любых офлайн-скриптов**.
- `POSTGRES_*` — БД приложения.
- `PORTAL_*` — БД портала (в тестовом режиме используется контейнер `portal-postgres`).
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — Redis для Celery.
- `APP_ADMIN_LOGIN` / `APP_ADMIN_PASSWORD` — логин администратора.
- `SEMANTIC_MODEL_NAME` — имя модели, зашитой в образ.
- `PORTAL_QUERY_CONFIG_PATH` — путь к `configs/portal_queries.yaml`.
- `SEMANTIC_MODEL_CACHE_DIR` — путь к кэшу модели (по умолчанию `/models/hf`).
- `SEMANTIC_MODEL_LOCAL_ONLY` — принудительно использовать локальный кэш.
- `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` — офлайн-режим Hugging Face/Transformers.

### 3) Импорт образов
```bash
./scripts/closed/load_images.sh
```
Проверьте, что образы загружены:
```bash
docker images | grep analiz_svodok
```

### 4) Подготовка БД и тестовых данных
```bash
./scripts/closed/seed.sh
```
Скрипт:
- поднимает `postgres`, `portal-postgres`, `redis`;
- выполняет миграции Django;
- создаёт администратора;
- заполняет справочники приложения;
- применяет `seed/*.sql` для тестовой БД портала.

### 5) Запуск сервиса
```bash
./scripts/closed/up.sh
```

### 6) Проверка
```bash
./scripts/closed/verify.sh
```
Дополнительно можно открыть в браузере:
```
http://127.0.0.1:8000/help
```

### 7) Прогон тестовых сводок через UI
1) Откройте `http://127.0.0.1:8000/login`.
2) Войдите под `APP_ADMIN_LOGIN`/`APP_ADMIN_PASSWORD`.
3) На экране загрузки выберите DOCX и нажмите **«Анализировать справку»**.

Если нужен тестовый DOCX, создайте его в контейнере:
```bash
docker compose -f docker-compose.offline.yml run --rm web \
  python manage.py make_test_docx --out /data/fixtures/test.docx
```
После этого файл будет доступен на хосте как `fixtures/test.docx`.

## Остановка и очистка
- Остановить сервисы:
  ```bash
  ./scripts/closed/down.sh
  ```
- Полностью удалить тестовые тома (сброс БД):
  ```bash
  docker compose -f docker-compose.offline.yml down -v
  ```

## Настройка SQL под боевую БД портала (позже)
Запросы вынесены в `configs/portal_queries.yaml`. В нём можно менять **только** SQL-часть (таблицы/поля/джойны), не трогая код.

Что именно менять:
- `find_candidates` — выборка событий по времени (`ts_from`, `ts_to`, `ts_exact`, `limit`).
- `fetch_subdivision` — получение названия подразделения по `id`.
- `fetch_offenders` — получение ФИО/ДР нарушителей по `event_id`.

Пример проверки запросов через `psql` в тестовом окружении:
```bash
docker compose -f docker-compose.offline.yml exec -T portal-postgres \
  psql -U "$PORTAL_USER" -d "$PORTAL_DB"
```
Внутри `psql` можно выполнить:
```sql
SELECT e.id, e.date_detection, e.find_subdivision_unit_id
FROM events e
WHERE e.date_detection BETWEEN NOW() - INTERVAL '30 minutes' AND NOW() + INTERVAL '30 minutes'
ORDER BY e.date_detection DESC
LIMIT 5;
```

## Известные проблемы/диагностика
- **NumPy/torch несовместимы с NumPy 2.x** — в образах используются колёса torch 2.2, которые ожидают NumPy < 2. Поэтому в `requirements.txt` зафиксирован `numpy<2`. Если заменить на NumPy 2.x, возможны ошибки импорта в ML-части.
- **Ограничение длины имени в Postgres (63 символа)** — длинные имена constraint/index обрезаются и могут конфликтовать при повторном запуске seed. В seed используются короткие явные имена ограничений, а `ON CONFLICT` прописан по колонкам.

**Важно**
- В закрытом контуре запрещено использовать `docker build` и `docker pull`.
- Запускать стек нужно **только** через `docker load` + `docker compose up` (скрипты `scripts/closed/*.sh`).
- Образ уже содержит кэш модели в `/models/hf`, если он был подготовлен в открытом контуре.

## Типовые ошибки/диагностика
- **`Missing image`** при запуске — образы не загружены. Выполните `./scripts/closed/load_images.sh`.
- **`docker compose` пытается тянуть `postgres:15-alpine` или `redis:7-alpine`** — не загружены базовые образы из архива. Проверьте, что `images/images_<TAG>.tar` загружен полностью.
- **`rg: command not found`** — в закрытом контуре нет ripgrep. Используйте актуальные офлайн-скрипты из релиза (они не зависят от `rg`).
- **`unknown flag: --pull`** — используйте актуальные офлайн-скрипты без `--pull`.
- **`Missing image :local`** — тег не задан. Добавьте `TAG=<тег>` в `.env` перед запуском офлайн-скриптов.
- **Ошибки подключения к БД портала** — проверьте `PORTAL_HOST`, `PORTAL_PORT`, `PORTAL_DB`, `PORTAL_USER`, `PORTAL_PASSWORD` в `.env`.
- **`SEMANTIC_MODEL_LOCAL_ONLY` и ошибки модели** — релиз собран без подготовленного кэша модели. Нужен релиз с заполненным `models/hf/` в открытом контуре.
- **В релизе отсутствуют стили/шаблоны** — проверьте исходную сборку образа: если build context был **десятки KB**, значит `.dockerignore` исключил почти всё. Нормальный build context — **десятки/сотни MB**.
  - Внутри образа должны быть каталоги:
    ```bash
    docker run --rm <image> ls -la /app/templates /app/static
    ```
