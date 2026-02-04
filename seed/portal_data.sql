INSERT INTO subdivision (id, fullname, is_test)
VALUES
    (1101, 'ПОГЗ №2 (с. Васильки)', true),
    (1102, 'ОПК «Центральное» (г. Южный)', true),
    (1103, 'ПОГК «Лесная» (пгт Лесной)', true),
    (1104, 'ПОГО «Южное» (г. Южный)', true),
    (1105, 'ОПК «Заречное» (г. Заречный)', true),
    (1106, 'ПОГК «Речная» (пгт Речной)', true),
    (1201, 'ПОГЗ №1 (с. Полярное)', true),
    (1202, 'ПОГК «Северная» (пгт Северный)', true),
    (1203, 'ОПК «Северное» (г. Северск)', true),
    (1204, 'ПОГО «Тундровое» (с. Тундра)', true),
    (1205, 'ПОГК «Озерная» (пгт Озерный)', true),
    (1206, 'ОПК «Горное» (г. Горный)', true),
    (1301, 'ПОГЗ №3 (с. Южные Ключи)', true),
    (1302, 'ОПК «Южное» (г. Южногорск)', true),
    (1303, 'ПОГК «Прибрежная» (пгт Береговой)', true),
    (1304, 'ПОГО «Степное» (с. Степное)', true),
    (1305, 'ОПК «Цветочное» (г. Цветочный)', true),
    (1306, 'ПОГК «Солнечная» (пгт Солнечный)', true)
ON CONFLICT (id) DO UPDATE
SET fullname = EXCLUDED.fullname,
    is_test = EXCLUDED.is_test;

INSERT INTO events (id, date_detection, find_subdivision_unit_id, is_test)
VALUES
    (2001, '2024-01-10 12:00:00', 1101, true),
    (2002, '2024-01-11 09:30:00', 1102, true),
    (2003, '2024-01-12 14:20:00', 1202, true),
    (2004, '2024-01-13 16:45:00', 1201, true),
    (2005, '2024-01-14 10:15:00', 1301, true),
    (2006, '2024-01-14 10:15:00', 1101, true)
ON CONFLICT (id) DO UPDATE
SET date_detection = EXCLUDED.date_detection,
    find_subdivision_unit_id = EXCLUDED.find_subdivision_unit_id,
    is_test = EXCLUDED.is_test;

INSERT INTO offenders (event_id, first_name, middle_name, last_name, date_of_birth, is_test)
VALUES
    (2001, 'Иван', 'Иванович', 'Иванов', '1990-05-05', true),
    (2002, 'Петр', 'Петрович', 'Петров', '1985-03-12', true),
    (2003, 'Анна', 'Сергеевна', 'Сидорова', '1992-07-01', true),
    (2004, 'Алексей', 'Николаевич', 'Кузнецов', '1978-09-09', true),
    (2005, 'Роман', 'Романович', 'Романов', '1995-12-30', true),
    (2006, 'Роман', 'Романович', 'Романов', '1995-12-30', true)
ON CONFLICT (event_id, first_name, middle_name, last_name, date_of_birth)
DO NOTHING;
