# Phase 3 — Optimization & Scale

Extends [Phase 2](../phase-2/) with smart mood defaults, edge caching, candidate prewarm, adaptive drop sizing, token budgets, and sharded drop workers.

## New capabilities

| Feature | Endpoint / job |
|---------|----------------|
| Smart mood default | `GET /v1/mood/suggestion` |
| Home edge cache (60s, mood-keyed) | automatic on `GET /v1/home` |
| Candidate prewarm | `POST /internal/candidate-prewarm`, `scripts/candidate_prewarm.py` |
| LLM token budget | `GET /internal/token-budget` |
| Drop sharding | `GET /internal/drop-shard/{partition}`, `scripts/drop_shard_worker.py` |
| Adaptive drop size experiment | `ADAPTIVE_DROP_SIZE` env + `experiment_assignments` table |

## Setup

```bash
pip install -r phases/phase-3/requirements.txt
psql $DATABASE_URL -f sql/schema.sql
psql $DATABASE_URL -f phases/phase-1/sql/schema.sql
psql $DATABASE_URL -f phases/phase-2/sql/schema.sql
psql $DATABASE_URL -f phases/phase-3/sql/schema.sql
```

## Run (local UI)

**Use port 8010** — port `8000` is often taken by other projects (e.g. AI Travel Planner).

```bash
# From repo root (recommended)
python scripts/run_dev.py

# Or manually
cd phases/phase-3
uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8010
```

Open **http://127.0.0.1:8010/** (not `:8000`). Verify: `GET /healthz` → `"product": "MoodAI Spotify"`.

## Jobs

```bash
python phases/phase-3/scripts/candidate_prewarm.py
python phases/phase-3/scripts/drop_shard_worker.py --partition 0
python phases/phase-2/scripts/llm_prewarm.py
```

## Tests

```bash
pytest phases/phase-1/tests phases/phase-2/tests phases/phase-3/tests -q
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `SMART_MOOD_DEFAULT_ENABLED` | `false` | Enable listening/time mood suggestion |
| `HOME_CACHE_TTL_SECONDS` | `60` | BFF edge cache TTL |
| `ADAPTIVE_DROP_SIZE` | `10` | Drop size (10 or 15 experiment) |
| `DROP_PARTITIONS` | `4` | Horizontal drop worker shards |
| `LLM_TOKEN_BUDGET_PER_DAY` | `5000` | Per-user LLM token cap |
