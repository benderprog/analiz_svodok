CREATE TABLE IF NOT EXISTS subdivision (
    id INTEGER PRIMARY KEY,
    fullname TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    date_detection TIMESTAMP NOT NULL,
    find_subdivision_unit_id INTEGER REFERENCES subdivision(id)
);

CREATE TABLE IF NOT EXISTS offenders (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    last_name TEXT NOT NULL,
    date_of_birth DATE,
    UNIQUE (event_id, first_name, middle_name, last_name, date_of_birth)
);
