# Phase 0 — Local setup

## Without Docker (tagging & validation only)

If Docker is not installed locally, you can still complete the data pipeline:

```bash
pip install -r requirements.txt
python scripts/seed_all.py --generate --dry-run
python scripts/validate_coverage.py --csv data/seed/v1/track_mood_tags.csv
pytest tests/ -v
```

For **database load**, use either:

- **Docker Desktop** + `docker compose up -d`, then `python scripts/seed_all.py --generate`
- **Railway Postgres** — set `DATABASE_URL` in `.env`, run `python scripts/apply_schemas.py`, then `seed_all.py`

### Windows ARM note

`psycopg[binary]` may not install on Windows ARM. The project falls back to `pg8000` automatically via `scripts/db.py`.

## One-command pipeline

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env

docker compose up -d
python scripts/seed_all.py --generate
```

This will:

1. Generate `data/source/tracks.xlsx` (1,350+ tracks, 250 per mood)
2. Load tracks + mood tags into Postgres
3. Seed 10 synthetic users + play history
4. Run `validate_coverage.py` and `verify_mood_pools.py`

## Replace with your Excel file

Place your file at `data/source/tracks.xlsx`, then:

```bash
python scripts/seed_all.py --source data/source/tracks.xlsx
```

## Railway Postgres (optional)

1. Create a **PostgreSQL** database in a [Railway](https://railway.com) project.
2. Copy the **public** connection string into `.env` as `DATABASE_URL`.
3. Run: `python scripts/apply_schemas.py`
4. Run: `python scripts/seed_all.py --source data/source/tracks.xlsx`

Use Railway **reference variables** (`${{Postgres.DATABASE_URL}}`) for services in the same project.

## Verify

```bash
python scripts/validate_coverage.py
python scripts/verify_mood_pools.py
pytest tests/ -v
```

## Phase 0 exit criteria

- [x] ≥1,000 tracks loaded
- [x] ≥200 tracks per dataset mood
- [x] Zero ADVENTUROUS tags in dataset
- [x] Same seed script works locally (and Railway with `DATABASE_URL`)
