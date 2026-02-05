# Офлайн-развёртывание в закрытом контуре

Документ для оператора. Описывает запуск **без интернета**, без `docker build` и без загрузки образов из DockerHub.

## Что получает оператор
Папка релиза `release_<TAG>/` (или архив), внутри:
- `images/images_<TAG>.tar` — контейнерные образы.
- `docker-compose.offline.yml` — compose **без** секций `build`.
- `.env.example` — шаблон окружения.
- `configs/portal_queries.yaml` — SQL-запросы к БД портала.
- `docs/INSTALL_CLOSED.md` — эта инструкция.
- `docs/USAGE.md` — инструкция оператора.
- `scripts/closed/*.sh` — запуск/проверка/логи.
- `seed/*.sql` — SQL для тестовой БД портала.
- `fixtures/*` — тестовые файлы.
- `models/model_lock.json` — lock-файл модели.
- `models/hf/` — локальный кэш модели (если сборка в режиме `MODEL_CACHE_MODE=local`).
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
- `SEMANTIC_MODEL_PATH` — путь к локальному снапшоту (если нужен явный путь).
- `PORTAL_QUERY_CONFIG_PATH` — путь к `configs/portal_queries.yaml`.
- `SEMANTIC_MODEL_CACHE_DIR` — путь к кэшу модели (по умолчанию `/models/hf`).
- `SEMANTIC_MODEL_LOCAL_ONLY` — принудительно использовать локальный кэш.
- `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` — офлайн-режим Hugging Face/Transformers.
- `MODEL_CACHE_MODE` — режим подготовки кэша (`local` в закрытом контуре).

### 2.1) Режим модели
В закрытом контуре интернета нет, поэтому используйте локальный режим:

1) В `.env` установите:
   ```bash
   MODEL_CACHE_MODE=local
   SEMANTIC_MODEL_LOCAL_ONLY=true
   HF_HUB_OFFLINE=1
   TRANSFORMERS_OFFLINE=1
   ```
2) Убедитесь, что в каталоге релиза есть `models/hf/`.
3) Выполните `./scripts/closed/seed.sh` — он скопирует модель в volume `hf_cache`.

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
- при наличии `models/hf` копирует кэш в volume `hf_cache`;
- применяет `seed/*.sql` для тестовой БД портала.

#### Seed портальной БД из DOCX
Если в `fixtures/` есть `test_svodka_semantic3.docx` (или любой `*.docx`), `seed.sh` сначала сгенерирует SQL из DOCX:
- входной файл: `fixtures/test_svodka_semantic3.docx` (приоритет) или любой `fixtures/*.docx`;
- выходной файл: `seed/portal_data_generated.sql`;
- каждый абзац DOCX = одно событие (максимум 15).

Классы событий задаются детерминированно по индексу абзаца `i` (1..N):
- **OK** — по умолчанию (данные как в DOCX).
- **PARTIAL** если `i % 3 == 0`: в БД либо теряется один нарушитель, либо у нарушителя проставляется `NULL` вместо `date_of_birth`.
- **BAD** если `i % 5 == 0`: в БД либо время события сдвигается на +60 минут, либо подставляется другое подразделение.

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

Пример проверки запросов через `psql` в тестовом окружении:
```bash
docker compose -f docker-compose.offline.yml exec -T portal-postgres \
  psql -U "$PORTAL_USER" -d "$PORTAL_DB"
```
Внутри `psql` можно выполнить:
```sql
SELECT e.id, e.detected_at, e.subdivision_id
FROM portal_events e
WHERE e.detected_at BETWEEN NOW() - INTERVAL '30 minutes' AND NOW() + INTERVAL '30 minutes'
ORDER BY e.detected_at DESC
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
  - Проверьте, что `models/hf/` есть в каталоге релиза и скрипт `seed.sh` был выполнен.
  - Либо подготовьте кэш в открытом контуре через `MODEL_CACHE_MODE=download` и пересоберите релиз.
- **Если модель не найдена локально**
  1) В открытом контуре выполните:
     ```bash
     MODEL_CACHE_MODE=download bash scripts/models/ensure_model_cache.sh
     ```
  2) Пересоберите релиз с `MODEL_CACHE_MODE=local`, чтобы кэш попал в `release_<TAG>/models/hf`.
- **В релизе отсутствуют стили/шаблоны** — проверьте исходную сборку образа: если build context был **десятки KB**, значит `.dockerignore` исключил почти всё. Нормальный build context — **десятки/сотни MB**.
  - Внутри образа должны быть каталоги:
    ```bash
    docker run --rm <image> ls -la /app/templates /app/static
    ```
