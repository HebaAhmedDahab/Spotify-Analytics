CREATE TABLE IF NOT EXISTS recent_tracks (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    track_id TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT NOT NULL,
    played_at TIMESTAMP NOT NULL,
    track TEXT NOT NULL,
    played_date DATE NOT NULL,
    played_hour INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,
    duration_minutes NUMERIC(10,2) NOT NULL,
    image_url TEXT,
    CONSTRAINT recent_tracks_track_played_at_key
        UNIQUE (track_id, played_at)
);

CREATE TABLE IF NOT EXISTS recent_tracks_import (
    track_id TEXT NOT NULL,
    track TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT NOT NULL,
    played_at TIMESTAMP NOT NULL,
    played_date DATE NOT NULL,
    played_hour INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,
    duration_minutes NUMERIC(10,2) NOT NULL,
    image_url TEXT
);

CREATE TABLE IF NOT EXISTS loaded_files (
    file_name TEXT PRIMARY KEY,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);