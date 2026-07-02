# Production Runbook — MoodAI on Railway

Deploy the **Phase 3** API (includes Phase 1 + 2 features) with your `Music_Data.csv` catalog seeded into managed Postgres.

## Architecture on Railway

| Service | Role | Config |
|---------|------|--------|
| **Postgres** | Managed PostgreSQL — catalog + drops | Add from **+ New → Database → PostgreSQL** |
| **Redis** | Cache + prewarm | Add from **+ New → Database → Redis** |
| **moodai-api** | Web service — `phases/phase-3` FastAPI | Root `railway.toml` |
| **moodai-daily-drop** | Cron — discovery drops (06:00 UTC) | `railway/cron-daily-drop.toml` |
| **moodai-llm-prewarm** | Cron — LLM cache (every 6h) | `railway/cron-llm-prewarm.toml` |
| **moodai-candidate-prewarm** | Cron — candidate cache (every 6h) | `railway/cron-candidate-prewarm.toml` |

**Important:** The API never reads `Music_Data.csv` at request time. You seed Postgres once from your laptop; production serves from the database.

## Prerequisites

- GitHub repo pushed (e.g. `MoodAI_Spotify`)
- [Railway](https://railway.com) account
- [Groq API key](https://console.groq.com/)
- Your catalog locally: `data/source/Music_Data.csv` (~114k tracks)

`Music_Data.csv` is **gitignored**. Load it from your machine into Railway Postgres after the database is created.

---

## Step 1 — Create the Railway project

1. Go to [railway.com/new](https://railway.com/new) → **Deploy from GitHub repo**.
2. Select `MoodAI_Spotify` (or your fork).
3. Railway creates a service from the repo. Rename it to **`moodai-api`**.

### Add Postgres and Redis

In the same project:

1. **+ New → Database → PostgreSQL**
2. **+ New → Database → Redis**

Railway provisions both automatically.

---

## Step 2 — Configure the API service (`moodai-api`)

### Build & start (auto from `railway.toml`)

| Setting | Value |
|---------|--------|
| Config file | `railway.toml` (default) |
| Build command | `pip install -r requirements-prod.txt` |
| Start command | `cd phases/phase-3 && uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT` |
| Health check | `/healthz` |

### Environment variables

In **moodai-api → Variables**, add:

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `GROQ_API_KEY` | Your Groq key (secret) |
| `LLM_PROVIDER` | `groq` |
| `GROQ_MODEL` | `llama-3.1-8b-instant` |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` |
| `DATASET_VERSION` | `v1.1.0` |
| `MOOD_GATEWAY_ENABLED` | `true` |
| `VISUAL_SEARCH_ENABLED` | `true` |
| `PUSH_NOTIFICATIONS_ENABLED` | `false` |
| `SMART_MOOD_DEFAULT_ENABLED` | `true` |
| `HOME_CACHE_TTL_SECONDS` | `60` |
| `ADAPTIVE_DROP_SIZE` | `10` |
| `DROP_PARTITIONS` | `4` |
| `LLM_TOKEN_BUDGET_PER_DAY` | `5000` |

Use **Add Reference** for `DATABASE_URL` and `REDIS_URL` so Railway injects the live connection strings. If your database services have different names, pick the matching reference (e.g. `${{Postgres.DATABASE_URL}}`).

### Public URL

**moodai-api → Settings → Networking → Generate Domain**

---

## Step 3 — Add cron services

Create **three more services** from the **same GitHub repo** (each is a separate Railway service in the same project).

### Daily drop

1. **+ New → GitHub Repo** → same repo → name: `moodai-daily-drop`
2. **Settings → Config file path:** `railway/cron-daily-drop.toml`
3. Variables:

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `GROQ_API_KEY` | (same secret as API) |
| `LLM_PROVIDER` | `groq` |
| `GROQ_MODEL` | `llama-3.1-8b-instant` |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` |

### LLM prewarm

1. New service: `moodai-llm-prewarm`
2. Config file: `railway/cron-llm-prewarm.toml`
3. Variables: `DATABASE_URL`, `REDIS_URL`, `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL`

### Candidate prewarm

1. New service: `moodai-candidate-prewarm`
2. Config file: `railway/cron-candidate-prewarm.toml`
3. Variables: `DATABASE_URL`, `REDIS_URL`

Cron schedules are defined in each TOML file. Railway runs the start command on schedule; the process must **exit** when done (our scripts do).

---

## Step 4 — Apply database schemas

From your **local machine** (repo cloned, venv active):

```bash
pip install -r requirements-prod.txt
```

Copy the **public** Postgres URL from Railway → **Postgres → Connect → Public URL**.

```powershell
$env:DATABASE_URL = "postgresql://..."
python scripts/apply_schemas.py
```

This applies, in order:

- `sql/schema.sql` (tracks, mood tags, play history)
- `phases/phase-1/sql/schema.sql` (discovery drops)
- `phases/phase-2/sql/schema.sql` (heard-before, push)
- `phases/phase-3/sql/schema.sql` (experiments, token budget)

---

## Step 5 — Seed your catalog

Still using the **public** `DATABASE_URL` from your laptop:

```bash
python scripts/seed_all.py --source data/source/Music_Data.csv
```

Expected outcome:

- ~114,000 tracks loaded
- ~31,329 mood-tagged
- All 5 dataset moods ≥ 200 tracks
- Synthetic `play_history` for demo users

**Duration:** ~5–15 minutes depending on network.

### Smaller demo (no full CSV)

```bash
python scripts/seed_all.py --generate
```

Uses the bundled sample catalog (~1,319 tracks).

---

## Step 6 — Deploy and verify

1. Push latest code to GitHub (Railway auto-deploys on push if enabled).
2. Wait for **moodai-api** deploy to finish (green).
3. Open your Railway domain.

| Check | URL / command |
|-------|----------------|
| Health | `GET /healthz` → `{"status":"ok","phase":"3"}` |
| Web UI | `GET /` |
| Home | `GET /v1/home` with header `X-User-Id: demo-user` |
| Mood | `PUT /v1/users/me/mood` |
| Drop | `GET /v1/discovery-drop` |
| Smart mood | `GET /v1/mood/suggestion` |
| Artist search | `GET /v1/search/artists?q=beatles` |

```bash
curl -s https://YOUR-DOMAIN.up.railway.app/healthz
curl -s -H "X-User-Id: demo-user" https://YOUR-DOMAIN.up.railway.app/v1/home
```

### Test crons manually

Railway → each cron service → **Deployments → Deploy** (or wait for schedule). Check logs for success.

---

## Re-seeding / updates

```powershell
$env:DATABASE_URL = "postgresql://..."   # public URL from Railway Postgres
python scripts/seed_all.py --source data/source/Music_Data.csv
```

Schema only:

```bash
python scripts/apply_schemas.py
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Build fails on Railway | Confirm `requirements-prod.txt` exists; check build logs |
| `connection refused` on API | Verify `DATABASE_URL` reference on moodai-api |
| Empty home / no tracks | Run Step 5 seed against **public** Postgres URL |
| All explanations `TEMPLATE` | Set `GROQ_API_KEY` on API + daily-drop + llm-prewarm |
| Redis errors | API falls back to in-memory cache; verify `REDIS_URL` reference |
| Cron skipped | Previous run still active — ensure script exits; check logs |
| SSL errors seeding locally | Use Railway **public** URL; psycopg handles `postgres://` |

---

## Security notes

- Do **not** commit `.env` or `GROQ_API_KEY`.
- Use **private** `DATABASE_URL` references inside Railway services.
- Use the **public** Postgres URL only from your laptop for seeding.
- Rotate Groq keys if exposed.

---

## Data flow

```
Music_Data.csv  ──seed (once)──►  Railway Postgres
                                      │
                                      ├── tracks (114k)
                                      ├── track_mood_tags (31k+)
                                      ├── play_history (demo users)
                                      └── discovery_drop (cron-generated)
                                              │
                                              ▼
                                    moodai-api + Groq explanations
```

Your CSV `Mood` column is **not** used; moods are computed from audio features per `docs/architecture.md` §6.5.

---

## Related docs

- [phasewiseimplementation.md](./phasewiseimplementation.md) — phase exit criteria
- [phase0-setup.md](./phase0-setup.md) — local pipeline
- [phases/README.md](../phases/README.md) — phase folders
- [railway.toml](../railway.toml) — API service config
