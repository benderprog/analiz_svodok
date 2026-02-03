# Сборка релиза в открытом контуре

Документ описывает, как собрать релизный бандл в открытой среде с доступом к интернету и подготовить его к переносу в закрытый контур.

## Требования
- Docker Engine
- Docker Compose v2 (команда `docker compose`)
- Git
- Доступ к интернету (нужен **только** в открытом контуре для сборки образов)

## Подготовка релиза

### 1) Обновить код и определить тег
```bash
git pull
TAG=$(git rev-parse --short HEAD)
# альтернативно можно задать APP_VERSION вручную
```
Дальше при проверке релиза в каталоге `release_<TAG>` тег должен быть записан в `.env`.

### 2) Собрать релизный бандл
**Без прогрева модели (по умолчанию):**
```bash
APP_VERSION="$TAG" bash scripts/docker/make_release_bundle.sh --no-prewarm
```

**С прогревом модели (офлайн-готовый NLP):**
```bash
APP_VERSION="$TAG" bash scripts/docker/make_release_bundle.sh --prewarm
```

### 3) Где появляется релиз
Результат появится в каталоге:
```
dist/release_<TAG>/
```

### 4) Что внутри релиза
Структура бандла (пример):
```
release_<TAG>/
  images/
    images_<TAG>.tar
  docker-compose.offline.yml
  .env.example
  configs/
    portal_queries.yaml
  docs/
    INSTALL_CLOSED.md
  scripts/
    closed/*.sh
  seed/*.sql
  fixtures/*
  SHA256SUMS
```

## Локальная проверка релиза (в открытом контуре)

> Эти шаги выполняются **перед** переносом, чтобы убедиться, что офлайн-стек поднимается без сборки и без доступа в интернет.

1) Перейдите в каталог релиза:
```bash
cd dist/release_<TAG>
```

2) Подготовьте `.env`:
```bash
cp .env.example .env
```
Убедитесь, что `TAG` **обязательно** записан в `.env` **до запуска любых офлайн-скриптов**.

3) Импортируйте образы:
```bash
./scripts/closed/load_images.sh
```

4) Подготовьте базы и данные:
```bash
./scripts/closed/seed.sh
```

5) Запустите сервисы:
```bash
./scripts/closed/up.sh
```

6) Проверьте доступность:
```bash
./scripts/closed/verify.sh
```

7) Проверка UI:
- Откройте `http://127.0.0.1:8000/login`.
- Войдите под `APP_ADMIN_LOGIN`/`APP_ADMIN_PASSWORD`.
- Загрузите тестовый DOCX (см. ниже) и выполните анализ.

### Где взять тестовый DOCX
В релизе есть каталог `fixtures/` с текстовыми примерами. Для UI нужен `.docx`, его можно сгенерировать прямо в контейнере:
```bash
docker compose -f docker-compose.offline.yml run --rm web \
  python manage.py make_test_docx --out /data/fixtures/test.docx
```
После этого файл появится на хосте в `fixtures/test.docx`.

## Прогрев модели (prewarm)
- По умолчанию `make_release_bundle.sh` использует `--no-prewarm`.
- `--prewarm` увеличивает размер образа, но гарантирует, что модель уже включена и **не требует интернета** в закрытом контуре.

**Важно**
- В релизном контуре нельзя выполнять `docker build` и нельзя тянуть образы из DockerHub. Проверку релиза выполняйте **только** через `docker load` и `docker compose up`.

## Типовые ошибки/диагностика
- **Слишком маленький build context (десятки KB) при `docker build`** — почти весь репозиторий исключён через `.dockerignore`, в образ не попадают `templates/` и `static/`. Нормальный build context для этого проекта — **десятки/сотни MB**, а не KB.
  - Проверьте в логе сборки строку `Sending build context to Docker daemon ...`.
  - После сборки убедитесь, что внутри образа есть каталоги:
    ```bash
    docker run --rm <image> ls -la /app/templates /app/static
    ```
- **`docker compose` пытается скачать `python:3.11-slim` или другие базовые образы** — значит где-то используется `build`. В офлайн-релизе должна быть только загрузка через `./scripts/closed/load_images.sh` и запуск `./scripts/closed/up.sh`.
- **`Missing image: analiz_svodok_web:<TAG>`** при запуске — не загружены образы. Запустите `./scripts/closed/load_images.sh` в каталоге релиза.
- **`rg: command not found`** — в закрытом контуре нет ripgrep. Используйте актуальные офлайн-скрипты из релиза (они не зависят от `rg`).
- **`unknown flag: --pull`** — используйте актуальные офлайн-скрипты без `--pull`.
- **`Missing image :local`** — тег не задан. Добавьте `TAG=<тег>` в `.env` перед запуском офлайн-скриптов.
- **`SEMANTIC_MODEL_LOCAL_ONLY` ошибки при старте** — образ собран без прогрева, а в окружении включён офлайн-режим. Пересоберите релиз с `--prewarm`.
