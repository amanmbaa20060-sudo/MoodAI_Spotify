# Production Runbook — MoodAI on Render

Deploy the **Phase 3** API (includes Phase 1 + 2 features) with your `Music_Data.csv` catalog seeded into managed Postgres.

## Architecture on Render

| Service | Role |
|---------|------|
| `moodai-db` | Managed PostgreSQL — runtime catalog + drops |
| `moodai-redis` | Key Value (Redis) — edge cache + prewarm |
| `moodai-api` | Web service — `phases/phase-3` FastAPI BFF |
| `moodai-daily-drop` | Cron — generate discovery drops (06:00 UTC daily) |
| `moodai-llm-prewarm` | Cron — LLM reason cache (every 6h) |
| `moodai-candidate-prewarm` | Cron — candidate pool cache (every 6h) |

**Important:** The API never reads `Music_Data.csv` at request time. You seed Postgres once; production serves from the database.

## Prerequisites

- GitHub repo pushed (e.g. `MoodAI_Spotify`)
- [Render](https://render.com) account
- [Groq API key](https://console.groq.com/)
- Your catalog file locally: `data/source/Music_Data.csv` (~114k tracks)

`Music_Data.csv` is **gitignored** (too large). You load it from your machine into Render Postgres after the database is created.

## Step 1 — Deploy infrastructure

### Option A: Blueprint (recommended)

1. In Render Dashboard → **New** → **Blueprint**.
2. Connect this repository.
3. Render reads root `render.yaml` and creates DB, Redis, web service, and crons.
4. When prompted, set **`GROQ_API_KEY`** (marked `sync: false` in the blueprint).

### Option B: Manual

Create the same resources as listed in `render.yaml` and wire `DATABASE_URL` / `REDIS_URL` from the database and Key Value instances.

| Service | Build command | Start command |
|---------|---------------|---------------|
| `moodai-api` | `pip install --upgrade pip && pip install -r requirements-prod.txt` | `bash scripts/render_start.sh` |
| `moodai-daily-drop` | `pip install -r requirements-prod.txt` | `python phases/phase-1/scripts/generate_drop.py` |
| `moodai-llm-prewarm` | `pip install -r requirements-prod.txt` | `python phases/phase-2/scripts/llm_prewarm.py` |
| `moodai-candidate-prewarm` | `pip install -r requirements-prod.txt` | `python phases/phase-3/scripts/candidate_prewarm.py` |

Health check path for the web service: `/healthz`

## Step 2 — Apply database schemas

From your **local machine** (with repo cloned and venv active):

```bash
pip install -r requirements-prod.txt
```

Copy the **External Database URL** from Render → `moodai-db` → Connect.

```powershell
$env:DATABASE_URL = "postgresql://..."
python scripts/apply_schemas.py
```

This applies, in order:

- `sql/schema.sql` (tracks, mood tags, play history)
- `phases/phase-1/sql/schema.sql` (discovery drops)
- `phases/phase-2/sql/schema.sql` (heard-before, push)
- `phases/phase-3/sql/schema.sql` (experiments, token budget)

## Step 3 — Seed your catalog

Still using the **external** `DATABASE_URL` from your laptop:

```bash
python scripts/seed_all.py --source data/source/Music_Data.csv
```

Expected outcome (from your manifest):

- ~114,000 tracks loaded
- ~31,329 mood-tagged
- All 5 dataset moods ≥ 200 tracks
- Synthetic `play_history` for demo users

**Duration:** ~5–15 minutes depending on network (114k rows).

### Smaller demo (no full CSV)

```bash
python scripts/seed_all.py --generate
```

Uses the bundled sample catalog (~1,319 tracks) for a quick demo only.

## Step 4 — Verify production API

Open your Render web service URL (e.g. `https://moodai-api.onrender.com`).

| Check | URL / command |
|-------|----------------|
| Health | `GET /healthz` → `{"status":"ok","phase":"3","product":"MoodAI Spotify"}` |
| Web UI | `GET /` |
| Home | `GET /v1/home` with header `X-User-Id: demo-user` |
| Mood | `PUT /v1/users/me/mood` |
| Drop | `GET /v1/discovery-drop` |
| Smart mood | `GET /v1/mood/suggestion` |
| Artist search | `GET /v1/search/artists?q=beatles` |

Example:

```bash
curl -s https://YOUR-SERVICE.onrender.com/healthz
curl -s -H "X-User-Id: demo-user" https://YOUR-SERVICE.onrender.com/v1/home
```

## Step 5 — Deploy frontend on Vercel (production UI)

The Vercel site is **static only**. It calls your **Render API** at runtime via `config.js`.

### Vercel project settings

| Setting | Value |
|---------|--------|
| Root Directory | *(empty — repo root)* |
| Framework Preset | **Other** |
| Build Command | `node build.mjs` |
| Output Directory | `public` |

### Required Vercel environment variable

| Name | Value | Environments |
|------|--------|--------------|
| **`MOODAI_API_URL`** | `https://YOUR-SERVICE.onrender.com` | Production, Preview, Development |

No trailing slash. Example: `https://moodai-api.onrender.com`

The build writes this into `public/config.js`:

```js
window.__MOODAI_CONFIG__ = { apiBaseUrl: "https://YOUR-SERVICE.onrender.com" };
```

If `MOODAI_API_URL` is missing, the Vercel build **fails** (by design) so you never deploy a broken frontend.

### Required Render environment variables (for Vercel)

On **`moodai-api`** in Render:

| Variable | Value |
|----------|--------|
| **`CORS_ALLOW_VERCEL`** | `true` |
| **`GROQ_API_KEY`** | your Groq key (for LLM explanations) |
| **`DATABASE_URL`** | linked Postgres (catalog must be seeded) |

Optional — custom Vercel domain (not `*.vercel.app`):

| Variable | Example |
|----------|---------|
| **`CORS_ORIGINS`** | `https://moodai.yourdomain.com` |

You can set both `CORS_ALLOW_VERCEL=true` and `CORS_ORIGINS` (comma-separated).

### Verify end-to-end

1. Browser: `https://YOUR-SERVICE.onrender.com/healthz` → JSON with `"product":"MoodAI Spotify"`
2. Vercel → **Deployments** → latest build log shows `API=https://YOUR-SERVICE.onrender.com`
3. Open your Vercel URL → home feed loads (not “Production API not connected”)

### Vercel troubleshooting

| Symptom | Fix |
|---------|-----|
| “Could not verify MoodAI API” / “Production API not connected” | Set `MOODAI_API_URL` on Vercel → **Redeploy** |
| Build fails: `MOODAI_API_URL is required` | Add env var in Vercel → Settings → Environment Variables |
| UI loads but API calls fail (browser console CORS error) | Set `CORS_ALLOW_VERCEL=true` on Render; redeploy API |
| API works on Render `/` but Vercel UI empty | Seed Postgres (Step 3); check Render logs |
| `mode: demo` in `/healthz` | Do **not** set `MOODAI_DEMO_MODE=true` on Render; ensure `DATABASE_URL` is set |

## Step 6 — Environment variables (Render dashboard)

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | Auto from `moodai-db` |
| `REDIS_URL` | Yes | Auto from `moodai-redis` |
| `GROQ_API_KEY` | Yes | Set manually; never commit |
| `GROQ_MODEL` | No | Default `llama-3.1-8b-instant` |
| `DATASET_VERSION` | No | `v1.1.0` |
| `SMART_MOOD_DEFAULT_ENABLED` | No | `true` in blueprint |
| `HOME_CACHE_TTL_SECONDS` | No | `60` |
| `LLM_TOKEN_BUDGET_PER_DAY` | No | `5000` |
| `CORS_ALLOW_VERCEL` | Yes (if using Vercel UI) | `true` |
| `CORS_ORIGINS` | No | Custom Vercel domain, comma-separated |

## Cron jobs

| Job | Schedule (UTC) | Script |
|-----|----------------|--------|
| Daily drop | `0 6 * * *` | `phases/phase-1/scripts/generate_drop.py` |
| LLM prewarm | `0 */6 * * *` | `phases/phase-2/scripts/llm_prewarm.py` |
| Candidate prewarm | `30 */6 * * *` | `phases/phase-3/scripts/candidate_prewarm.py` |

Trigger manually from Render → Cron → **Trigger Run** after first seed to validate.

## Re-seeding / updates

To reload catalog after CSV changes:

```bash
$env:DATABASE_URL = "postgresql://..."   # external URL
python scripts/seed_all.py --source data/source/Music_Data.csv
```

Schema changes only:

```bash
python scripts/apply_schemas.py
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `connection refused` on API | Wait for deploy; check `DATABASE_URL` on web service |
| Empty home / no tracks | Run Step 3 seed against external DB URL |
| All explanations `TEMPLATE` | Check `GROQ_API_KEY` on web service + cron jobs |
| Redis errors | API falls back to in-memory cache; verify `moodai-redis` is running |
| Slow first request | Render free/starter cold start; hit `/healthz` to warm |

## Security notes

- Do **not** commit `.env` or `GROQ_API_KEY` to git.
- Use Render **internal** `DATABASE_URL` for services in the same region; use **external** URL only from your laptop for seeding.
- Rotate Groq keys if exposed.

## What production uses from your data

```
Music_Data.csv  ──seed (once)──►  Render Postgres
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

## Related docs

- [phasewiseimplementation.md](./phasewiseimplementation.md) — phase exit criteria
- [phase0-setup.md](./phase0-setup.md) — local pipeline
- [phases/README.md](../phases/README.md) — phase folders
- [render.yaml](../render.yaml) — Render Blueprint
