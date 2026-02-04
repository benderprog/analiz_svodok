INSERT INTO subdivision (id, fullname)
VALUES
    (101, 'ПУ-1 Центральное'),
    (102, 'ПУ-2 Северное'),
    (103, 'ПУ-3 Южное')
ON CONFLICT (id) DO NOTHING;

INSERT INTO events (id, date_detection, find_subdivision_unit_id)
VALUES
    (1001, '2024-01-10 12:00:00', 101),
    (1002, '2024-01-11 09:30:00', 102),
    (1003, '2024-01-12 14:20:00', 101),
    (1004, '2024-01-13 16:45:00', 103),
    (1005, '2024-01-14 10:15:00', 101),
    (1006, '2024-01-14 10:15:00', 101)
ON CONFLICT (id) DO NOTHING;

INSERT INTO offenders (event_id, first_name, middle_name, last_name, date_of_birth)
VALUES
    (1001, 'Иван', 'Иванович', 'Иванов', '1990-05-05'),
    (1002, 'Петр', 'Петрович', 'Петров', '1985-03-12'),
    (1003, 'Анна', 'Сергеевна', 'Сидорова', '1992-07-01'),
    (1004, 'Алексей', 'Николаевич', 'Кузнецов', '1978-09-09'),
    (1005, 'Роман', 'Романович', 'Романов', '1995-12-30'),
    (1006, 'Роман', 'Романович', 'Романов', '1995-12-30')
ON CONFLICT (event_id, first_name, middle_name, last_name, date_of_birth)
DO NOTHING;
