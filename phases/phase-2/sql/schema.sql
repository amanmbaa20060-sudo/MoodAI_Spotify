-- Phase 2 schema extension — visual search, heard-before, push subscriptions.

ALTER TABLE tracks ADD COLUMN IF NOT EXISTS artist_image_url VARCHAR(512);

CREATE TABLE IF NOT EXISTS heard_before_reports (
    report_id    UUID PRIMARY KEY,
    user_id      VARCHAR(64) NOT NULL,
    track_id     VARCHAR(128) NOT NULL REFERENCES tracks(track_id) ON DELETE CASCADE,
    drop_id      UUID REFERENCES discovery_drop(drop_id) ON DELETE SET NULL,
    reported_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, track_id)
);

CREATE INDEX IF NOT EXISTS idx_heard_before_user
    ON heard_before_reports (user_id, reported_at DESC);

CREATE TABLE IF NOT EXISTS push_subscriptions (
    user_id       VARCHAR(64) PRIMARY KEY,
    endpoint      VARCHAR(512) NOT NULL,
    enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    subscribed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS push_notification_log (
    notification_id UUID PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL,
    event_type      VARCHAR(64) NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
