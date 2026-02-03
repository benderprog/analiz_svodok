# Контракт с портальной БД

## Схема (read-only)

Минимальная схема для локальной разработки создаётся командой `bootstrap_local_portal`.

- `subdivision(id int, fullname varchar, is_test bool)`
- `events(id int, date_detection timestamp, find_subdivision_unit_id int -> subdivision.id, is_test bool)`
- `offenders(id int, event_id int -> events.id, first_name, middle_name, last_name, date_of_birth date, is_test bool)`

> В боевом контуре типы идентификаторов могут отличаться (например, UUID), но используются те же
> имена колонок (`fullname`, `date_detection`, `find_subdivision_unit_id`, `event_id`).

## Что делает bootstrap_local_portal
- Создаёт таблицы (если их ещё нет).
- Добавляет колонку `is_test` для безопасной очистки тестовых данных.
- Заполняет набор кейсов:
  1) 3/3 совпало
  2) 2/3 совпало (подразделение отличается)
  3) время в окне ±30 минут
  4) нарушитель отличается
  5) не найдено
  6) дубликаты

## Запросы
1. Получение кандидатов по времени:
   - выборка из `events` с `date_detection BETWEEN timestamp - N AND timestamp + N`;
   - джойн на `subdivision` для получения `fullname`.
2. Подгрузка нарушителей:
   - выборка из `offenders` по `event_id IN (...)`.

## Логика матчинга
- Событие считается найденным, если совпали любые 2 из 3:
  - время (точное совпадение по `timestamp`);
  - подразделение (по `fullname`);
  - нарушители (по множеству с нормализацией).
- Если найдены несколько совпадающих записей по этой логике — показываем K записей как дубликаты.

## Как править `portal_queries.yaml` под боевую БД
1. Откройте `configs/portal_queries.yaml` и убедитесь, что в секции `queries` есть ключи:
   - `find_candidates`
   - `fetch_subdivision`
   - `fetch_offenders`
2. Сопоставьте реальные таблицы/колонки боевой БД с ожидаемыми полями:
   - `find_candidates` должен возвращать `id`, `date_detection` и идентификатор подразделения,
     который дальше используется в `fetch_subdivision`.
   - `fetch_subdivision` должен вернуть `id` и `fullname` (или совместимое поле, которое
     используется для сравнения подразделений).
   - `fetch_offenders` должен вернуть ФИО и дату рождения нарушителя по `event_id`.
3. Используйте безопасные параметры `%(...)s`, чтобы избежать SQL-инъекций:
   - `%(ts_from)s`, `%(ts_to)s`, `%(ts_exact)s`, `%(limit)s`
   - `%(id)s` для подразделения
   - `%(event_id)s` для нарушителей
4. После правок проверьте доступность файла через `PORTAL_QUERY_CONFIG_PATH`
   (переменная окружения указывает путь к yaml).
