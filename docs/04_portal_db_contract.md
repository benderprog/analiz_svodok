# Контракт с портальной БД

## Схема (read-only)
- `subdivision(id uuid, name varchar, fullname varchar)`
- `events(id uuid, date_detection timestamp, find_subdivision_unit_id uuid -> subdivision.id)`
- `offenders(event_id uuid -> events.id, first_name, middle_name, last_name, date_of_birth date)`

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
