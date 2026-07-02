# Phase 1 MVP

Phase 1 implements the mood-first Discovery Gateway MVP described in `docs/phasewiseimplementation.md`.

## What is included

- FastAPI BFF with `GET /v1/home`, `PUT /v1/users/me/mood`, and `GET /v1/discovery-drop`
- Mood State Service backed by `user_mood_preferences`
- Mood-Aware Ranker using `track_mood_tags` audio features and weight vectors
- Novelty Filter excluding `play_history` and recent 7-day drop repeats
- Discovery Orchestrator for the `GenerateDrop` pipeline
- Explanation Service with Groq LLM gateway and deterministic template fallback
- Home Feed Composer with `mood_gateway`, `discovery_drop`, and `fresh_picks`
- Daily drop worker script
- Static web UI at `/`
- SQL schema extension for `discovery_drop`, `drop_track`, and `explanation_audit_log`

## Layout

```text
phases/
  common/
    config.py
    db.py
    mood_rules.py
  phase-1/
    app/
    scripts/
    sql/
    static/
    tests/
```

## Setup

```bash
pip install -r phases/phase-1/requirements.txt
copy phases\phase-1\.env.example .env
docker compose up -d
python scripts/excel_to_db.py --source data/source/tracks.xlsx
```

Apply the schema extension after the base schema:

```bash
psql postgresql://app:app@localhost:5432/discovery -f sql/schema.sql
psql postgresql://app:app@localhost:5432/discovery -f phases/phase-1/sql/schema.sql
```

## Run the API

From `phases/phase-1`:

```bash
uvicorn app.main:create_app --factory --reload
```

The demo UI will be available at [http://localhost:8000](http://localhost:8000). Demo auth uses the `X-User-Id` header and defaults to `demo-user`.

## Run the worker

```bash
python phases/phase-1/scripts/generate_drop.py
python phases/phase-1/scripts/generate_drop.py --user-id demo-user
```

## Run tests

```bash
pytest phases/phase-1/tests -q
```
