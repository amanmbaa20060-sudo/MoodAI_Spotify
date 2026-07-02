-- Phase 1 schema extension for Discovery Drop MVP.

CREATE TABLE IF NOT EXISTS discovery_drop (
    drop_id             UUID PRIMARY KEY,
    user_id             VARCHAR(64) NOT NULL,
    drop_date           DATE NOT NULL,
    mood_at_generation  VARCHAR(32) NOT NULL,
    drop_header         VARCHAR(120) NOT NULL,
    header_method       VARCHAR(16) NOT NULL,
    track_count         SMALLINT NOT NULL DEFAULT 0,
    status              VARCHAR(16) NOT NULL DEFAULT 'READY',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, drop_date)
);

CREATE INDEX IF NOT EXISTS idx_discovery_drop_user_date
    ON discovery_drop (user_id, drop_date DESC);

CREATE TABLE IF NOT EXISTS drop_track (
    drop_id             UUID NOT NULL REFERENCES discovery_drop(drop_id) ON DELETE CASCADE,
    position            SMALLINT NOT NULL,
    track_id            VARCHAR(128) NOT NULL REFERENCES tracks(track_id) ON DELETE CASCADE,
    reason_text         VARCHAR(80) NOT NULL,
    reason_feature_id   VARCHAR(64) NOT NULL,
    reason_method       VARCHAR(16) NOT NULL,
    base_score          DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (drop_id, position)
);

CREATE INDEX IF NOT EXISTS idx_drop_track_track_id
    ON drop_track (track_id);

CREATE TABLE IF NOT EXISTS explanation_audit_log (
    recommendation_id   UUID PRIMARY KEY,
    user_id             VARCHAR(64) NOT NULL,
    track_id            VARCHAR(128) NOT NULL REFERENCES tracks(track_id) ON DELETE CASCADE,
    feature_id          VARCHAR(64) NOT NULL,
    rendered_text       VARCHAR(120) NOT NULL,
    generation_method   VARCHAR(16) NOT NULL,
    model_id            VARCHAR(128) NOT NULL,
    prompt_hash         VARCHAR(128) NOT NULL,
    grounding_passed    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_explanation_audit_user_created
    ON explanation_audit_log (user_id, created_at DESC);
