-- Phase 3 schema extension — engagement signals, experiments, LLM budgets.

CREATE TABLE IF NOT EXISTS user_engagement_signals (
    user_id           VARCHAR(64) NOT NULL,
    signal_date       DATE NOT NULL,
    dominant_mood     VARCHAR(32),
    session_count     INT NOT NULL DEFAULT 0,
    drop_completions  INT NOT NULL DEFAULT 0,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, signal_date)
);

CREATE TABLE IF NOT EXISTS experiment_assignments (
    user_id      VARCHAR(64) NOT NULL,
    flag_name    VARCHAR(64) NOT NULL,
    variant      VARCHAR(32) NOT NULL,
    assigned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, flag_name)
);

CREATE TABLE IF NOT EXISTS llm_token_usage (
    user_id     VARCHAR(64) NOT NULL,
    usage_date  DATE NOT NULL,
    tokens_used INT NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, usage_date)
);
