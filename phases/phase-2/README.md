# Phase 2 — Trust & Browse

Extends [Phase 1](../phase-1/) with visual artist search, heard-before feedback, push notifications, and LLM prewarm.

## New endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/search/artists` | GET | Visual artist grid (`?q=`) |
| `/v1/discovery-drop/tracks/{id}/heard-before` | POST | Report track as already heard |
| `/v1/users/me/push-subscription` | POST | Register push endpoint |
| `/internal/explanation-audit` | GET | Internal audit trail |
| `/internal/llm-prewarm` | POST | Trigger LLM cache prewarm |

## Setup

```bash
pip install -r phases/phase-2/requirements.txt
psql $DATABASE_URL -f sql/schema.sql
psql $DATABASE_URL -f phases/phase-1/sql/schema.sql
psql $DATABASE_URL -f phases/phase-2/sql/schema.sql
```

## Run

```bash
cd phases/phase-2
uvicorn app.main:create_app --factory --reload
```

## Jobs

```bash
python phases/phase-2/scripts/llm_prewarm.py
python phases/phase-2/scripts/llm_prewarm.py --user-id demo-user
```

## Tests

```bash
pytest phases/phase-2/tests -q
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `VISUAL_SEARCH_ENABLED` | `true` | Artist grid feature flag |
| `PUSH_NOTIFICATIONS_ENABLED` | `false` | Queue DiscoveryDropReady push |
| `REDIS_URL` | `redis://localhost:6379` | LLM prewarm cache |
