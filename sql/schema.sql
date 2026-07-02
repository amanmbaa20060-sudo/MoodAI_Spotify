-- MoodAI Spotify — catalog schema (see docs/architecture.md §6)

CREATE TABLE IF NOT EXISTS tracks (
    track_id        VARCHAR(128) PRIMARY KEY,
    name            VARCHAR(512) NOT NULL,
    artist_name     VARCHAR(512),
    album_name      VARCHAR(512),
    genre           VARCHAR(256),
    energy          DOUBLE PRECISION NOT NULL,
    valence         DOUBLE PRECISION NOT NULL,
    tempo           DOUBLE PRECISION NOT NULL,
    instrumentalness DOUBLE PRECISION NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS track_mood_tags (
    track_id          VARCHAR(128) PRIMARY KEY REFERENCES tracks(track_id) ON DELETE CASCADE,
    primary_mood      VARCHAR(32),
    mood_tags         TEXT[] NOT NULL DEFAULT '{}',
    energy            DOUBLE PRECISION NOT NULL,
    valence           DOUBLE PRECISION NOT NULL,
    tempo             DOUBLE PRECISION NOT NULL,
    instrumentalness  DOUBLE PRECISION NOT NULL,
    tagged_at         TIMESTAMPTZ DEFAULT NOW(),
    dataset_version   VARCHAR(32) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_track_mood_tags_primary ON track_mood_tags(primary_mood);
CREATE INDEX IF NOT EXISTS idx_track_mood_tags_tags ON track_mood_tags USING GIN(mood_tags);

CREATE TABLE IF NOT EXISTS play_history (
    user_id    VARCHAR(64) NOT NULL,
    track_id   VARCHAR(128) NOT NULL REFERENCES tracks(track_id),
    played_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, track_id)
);

CREATE TABLE IF NOT EXISTS user_mood_preferences (
    user_id      VARCHAR(64) PRIMARY KEY,
    active_mood  VARCHAR(32) NOT NULL DEFAULT 'LOW_KEY',
    persist      BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
