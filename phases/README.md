# Phased Implementations

Each folder contains a **self-contained implementation** for that project phase. See [`docs/phasewiseimplementation.md`](../docs/phasewiseimplementation.md) for the full plan.

| Folder | Scope | Run |
|--------|-------|-----|
| [phase-0](./phase-0/) | Data pipeline (Excel/CSV → Postgres, mood tagging) | `python phases/phase-0/scripts/run_seed.py` |
| [phase-1](./phase-1/) | MVP: Mood Gateway, Discovery Drop, Groq LLM, home API | `cd phases/phase-1 && uvicorn app.main:create_app --factory --reload` |
| [phase-2](./phase-2/) | Phase 1 + visual search, heard-before, push, LLM prewarm | `cd phases/phase-2 && uvicorn app.main:create_app --factory --reload` |
| [phase-3](./phase-3/) | Phase 2 + smart mood default, caching, scale hooks | `cd phases/phase-3 && uvicorn app.main:create_app --factory --reload` |

Shared library: [`common/`](./common/) — mood rules, DB helpers, config.

## Prerequisites

```bash
pip install -r requirements.txt
copy .env.example .env   # from repo root
docker compose up -d     # Postgres + Redis (repo root)
python phases/phase-0/scripts/seed_all.py --source data/source/Music_Data.csv
```

## Phase progression

```
Phase 0  →  catalog in Postgres
Phase 1  →  mood + drop + Groq explanations (API + web UI)
Phase 2  →  artist grid search + heard-before feedback
Phase 3  →  smart defaults + edge cache + optimization jobs
```

**Production:** deploy Phase 3 via root [`railway.toml`](../railway.toml) — see [docs/production-runbook.md](../docs/production-runbook.md).
