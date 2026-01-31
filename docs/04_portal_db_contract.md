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
