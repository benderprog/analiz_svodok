CREATE TABLE IF NOT EXISTS subdivision (
    id UUID PRIMARY KEY,
    fullname TEXT NOT NULL,
    is_test BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY,
    date_detection TIMESTAMP NOT NULL,
    find_subdivision_unit_id UUID NOT NULL REFERENCES subdivision(id),
    event_type_name TEXT
);

CREATE TABLE IF NOT EXISTS offenders (
    id UUID PRIMARY KEY,
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    first_name TEXT NOT NULL,
    middle_name TEXT NOT NULL DEFAULT '',
    last_name TEXT NOT NULL,
    date_of_birth DATE,
    CONSTRAINT uq_offenders_key UNIQUE (event_id, first_name, middle_name, last_name, date_of_birth)
);
