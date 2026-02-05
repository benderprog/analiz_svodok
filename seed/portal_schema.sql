DROP VIEW IF EXISTS portal_subdivisions CASCADE;
DROP TABLE IF EXISTS portal_events CASCADE;

CREATE TABLE portal_events (
    id UUID PRIMARY KEY,
    detected_at TIMESTAMP NOT NULL,
    subdivision_id UUID NOT NULL,
    subdivision_fullname TEXT NOT NULL,
    event_type_id UUID NULL,
    event_type_name TEXT NULL,
    raw_text TEXT NOT NULL,
    offenders JSONB NOT NULL DEFAULT '[]',
    is_test BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_portal_events_detected_at ON portal_events (detected_at);
CREATE INDEX idx_portal_events_subdivision_id ON portal_events (subdivision_id);

CREATE OR REPLACE VIEW portal_subdivisions AS
SELECT DISTINCT subdivision_id, subdivision_fullname
FROM portal_events;
