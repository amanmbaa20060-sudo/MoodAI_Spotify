# Phase 0 — Data Pipeline

Phase 0 seeds the catalog from Excel/CSV into PostgreSQL with mood tagging per `docs/architecture.md` §6.5.

## What lives where

| Asset | Location |
|-------|----------|
| Mood bucketing rules | `phases/common/mood_rules.py` (also `scripts/mood_rules.py`) |
| Build + validate scripts | `scripts/` (repo root) |
| Base SQL schema | `sql/schema.sql` |
| Docker Postgres + Redis | `docker-compose.yml` |
| Sample / real data | `data/source/` |

Phase 0 scripts remain at the **repo root** (`scripts/`) so CI and one-command seeding stay unchanged. This folder documents and wraps them.

## Quick start

```bash
pip install -r requirements.txt
copy .env.example .env
docker compose up -d
```

### Full pipeline (recommended)

```bash
python phases/phase-0/scripts/run_seed.py --source data/source/Music_Data.csv
```

### Step by step

```bash
python scripts/build_mood_buckets.py --source data/source/Music_Data.csv
python scripts/validate_coverage.py
python scripts/excel_to_db.py --source data/source/Music_Data.csv
python scripts/seed_play_history.py
python scripts/verify_mood_pools.py
```

### Without Docker (dry-run only)

```bash
python scripts/build_mood_buckets.py --source data/source/Music_Data.csv
python scripts/validate_coverage.py
```

Outputs land in `data/seed/v1/` and `data/dataset_manifest.json`.

## Exit criteria

- [x] ≥200 tracks per dataset mood (ENERGISED, FOCUSED, LOW_KEY, NOSTALGIC, SAD)
- [x] ≥1000 mood-tagged tracks OR ≥80% of catalog tagged
- [x] `play_history` seeded for synthetic users
- [x] Mood pool SQL verification passes

## Next phase

Apply Phase 1 schema and start the API:

```bash
psql $DATABASE_URL -f sql/schema.sql
psql $DATABASE_URL -f phases/phase-1/sql/schema.sql
cd phases/phase-1 && uvicorn app.main:app --reload
```
