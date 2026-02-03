# Офлайн развёртывание в закрытом контуре

Этот документ описывает запуск переносимого релиза без доступа к интернету.

## Состав релиза
- `images/images_<TAG>.tar` — контейнерные образы.
- `docker-compose.offline.yml` — compose без секций `build`.
- `configs/portal_queries.yaml` — SQL-запросы к портальной БД.
- `scripts/closed/*.sh` — утилиты загрузки образов, запуска и проверки.
- `seed/*.sql` — SQL для тестовой портальной БД.
- `fixtures/` — тестовые файлы (docx/текстовые шаблоны).

## Быстрый старт
1. Разархивируйте релиз в отдельный каталог.
2. Загрузите образы:
   ```bash
   ./scripts/closed/load_images.sh
   ```
3. Создайте `.env` и настройте параметры:
   ```bash
   cp .env.example .env
   ```
   Минимально проверьте:
   - `TAG` — тег релизных образов `analiz_svodok_web`/`analiz_svodok_celery`.
   - `POSTGRES_*` — параметры БД приложения.
   - `PORTAL_*` — параметры тестовой портальной БД (по умолчанию работает `portal-postgres`).
   - `APP_ADMIN_LOGIN` / `APP_ADMIN_PASSWORD` — учётные данные администратора.
   - `PORTAL_QUERY_CONFIG_PATH` — путь к `configs/portal_queries.yaml`.
4. Заполните БД тестовыми данными:
   ```bash
   ./scripts/closed/seed.sh
   ```
5. Запустите сервисы:
   ```bash
   ./scripts/closed/up.sh
   ```
6. Проверьте доступность:
   ```bash
   ./scripts/closed/verify.sh
   ```
   Либо откройте в браузере `http://localhost:8000/help`.

## Где лежат тестовые DOCX
Тестовые документы для сравнения лежат в каталоге `fixtures/`. При необходимости
их можно сгенерировать командой внутри контейнера:
```bash
docker compose -f docker-compose.offline.yml run --rm web python manage.py make_test_docx
```

## Логи
- Просмотр логов web/celery:
  ```bash
  ./scripts/closed/logs.sh
  ```
- Полное отключение:
  ```bash
  ./scripts/closed/down.sh
  ```

## Подключение к боевой портальной БД
1. Остановите сервис `portal-postgres` (или весь compose) и отключите локальную БД.
2. В `.env` замените `PORTAL_HOST`/`PORTAL_PORT` на параметры боевой БД.
3. Отредактируйте `configs/portal_queries.yaml` под боевую схему:
   - обновите имена таблиц/полей;
   - сохраните параметры `%(...)s` для безопасной подстановки.
4. Перезапустите сервисы (`./scripts/closed/up.sh`).

## Режим офлайн для NLP
`docker-compose.offline.yml` включает `HF_HUB_OFFLINE=1` и `TRANSFORMERS_OFFLINE=1`.
Это гарантирует, что при старте не будет попыток скачать модели из интернета.
Если нужна предзагрузка модели, выполняйте `build_closed.sh --prewarm` в открытом контуре
и включайте результат в релизный образ.
