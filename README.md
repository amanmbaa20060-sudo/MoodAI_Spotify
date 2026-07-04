# MoodAI Spotify

Mood-First Discovery Gateway — grad project implementing mood-led music discovery on top of a catalog dataset.

**Repository:** [github.com/amanmbaa20060-sudo/MoodAI_Spotify](https://github.com/amanmbaa20060-sudo/MoodAI_Spotify)

## Production (Render)

Deploy with the root [`render.yaml`](render.yaml) blueprint and follow **[docs/production-runbook.md](docs/production-runbook.md)**:

1. Connect repo to Render Blueprint → creates Postgres, Redis, API, crons.
2. Set `GROQ_API_KEY` in the dashboard.
3. From your laptop (with `Music_Data.csv`):
   ```bash
   set DATABASE_URL=<Render external database URL>
   python scripts/apply_schemas.py
   python scripts/seed_all.py --source data/source/Music_Data.csv
   ```
4. Open `https://<your-service>.onrender.com/` and test with `X-User-Id: demo-user`.

The API serves from **Postgres**, not the CSV file, at runtime.

## Quick start (local UI)

```bash
python scripts/run_dev.py
```

Opens **http://127.0.0.1:8010/** (not port 8000 — often used by other apps).

## Phase 0 status

Phase 0 (data pipeline) is implemented. See **[docs/phase0-setup.md](docs/phase0-setup.md)** for the full runbook.

```bash
pip install -r requirements-api.txt
copy .env.example .env
docker compose up -d
python scripts/seed_all.py --generate
```

## Documentation

| Doc | Description |
|-----|-------------|
| [docs/problemstatement.md](docs/problemstatement.md) | Product problem & solution |
| [docs/architecture.md](docs/architecture.md) | System architecture, LLM layer, dataset mood rules (§6.5) |
| [docs/phasewiseimplementation.md](docs/phasewiseimplementation.md) | Phase-wise build plan (0–3) |
| [docs/phase0-setup.md](docs/phase0-setup.md) | Phase 0 local + hosted DB setup |
| [docs/production-runbook.md](docs/production-runbook.md) | **Production deploy on Render** |
| [phases/README.md](phases/README.md) | Phase 1–3 API implementations |

## Quick start (Excel → database → model)

### 1. Clone & setup

```bash
git clone https://github.com/amanmbaa20060-sudo/MoodAI_Spotify.git
cd MoodAI_Spotify
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-api.txt
copy .env.example .env
```

### 2. Add your Excel dataset

Place your file at:

```
data/source/tracks.xlsx
```

Required numeric columns: `energy`, `valence`, `tempo`, `instrumentalness`  
See [data/source/README.md](data/source/README.md) for column name aliases.

### 3. Start PostgreSQL + Redis

```bash
docker compose up -d
```

### 4. Load Excel into the database

```bash
python scripts/excel_to_db.py --source data/source/tracks.xlsx
python scripts/validate_coverage.py
```

### 5. Connect your model

Services read from the database — **not** from Excel directly:

```env
DATABASE_URL=postgresql://app:app@localhost:5432/discovery
REDIS_URL=redis://localhost:6379
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

Example query (mood = FOCUSED):

```sql
SELECT t.* FROM tracks t
JOIN track_mood_tags m ON t.track_id = m.track_id
WHERE 'FOCUSED' = ANY(m.mood_tags)
LIMIT 500;
```

## Project structure

```
MoodAI_Spotify/
├── data/source/tracks.xlsx    ← your Excel (local, gitignored)
├── scripts/
│   ├── excel_to_db.py         ← Excel → Postgres
│   ├── build_mood_buckets.py  ← mood tagging (§6.5)
│   ├── mood_rules.py          ← threshold definitions
│   └── validate_coverage.py   ← coverage checks
├── sql/schema.sql             ← Postgres tables
├── docker-compose.yml
└── docs/
```

## Data flow

```
Excel (.xlsx)  →  excel_to_db.py  →  PostgreSQL (tracks, track_mood_tags)
                                              ↓
                                    Mood Ranker / Discovery API
```

## Production

- Host **Excel** in private blob storage (S3/Azure) — source only, not runtime
- Host **PostgreSQL** + **Redis** on Render / RDS / similar
- Run the same `excel_to_db.py` against production `DATABASE_URL`
- Pin `DATASET_VERSION` in env (see architecture §6.5)

## License

Academic / grad project use.
