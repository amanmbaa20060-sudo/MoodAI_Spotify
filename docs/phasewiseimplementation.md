# Mood-First Discovery Gateway — Phase-Wise Implementation Plan

**Document purpose:** Actionable, phase-by-phase build plan for implementation and deployment.  
**Sources:** [`docs/problemstatement.md`](./problemstatement.md) · [`docs/architecture.md`](./architecture.md)  
**Repository:** [github.com/amanmbaa20060-sudo/MoodAI_Spotify](https://github.com/amanmbaa20060-sudo/MoodAI_Spotify)  
**Version:** 1.0  
**Status:** Active

---

## Table of Contents

1. [Overview](#1-overview)
2. [Phase Map](#2-phase-map)
3. [Phase 0 — Foundation & Data Pipeline](#phase-0--foundation--data-pipeline)
4. [Phase 1 — MVP (Habit + Novelty)](#phase-1--mvp-habit--novelty)
5. [Phase 2 — Trust & Browse](#phase-2--trust--browse)
6. [Phase 3 — Optimization & Scale](#phase-3--optimization--scale)
7. [Cross-Phase Concerns](#7-cross-phase-concerns)
8. [Milestone Timeline](#8-milestone-timeline)
9. [Traceability Matrix](#9-traceability-matrix)

---

## 1. Overview

### 1.1 North-star outcomes (from product brief)

| Goal | Primary metric |
|------|----------------|
| Increase novel listening | Novel stream rate ↑ |
| Make discovery habitual | Discovery Drop completion rate ↑ |
| Reduce repetitive listening | Repeat listening index ↓ |
| Build trust in recommendations | Recommendation trust score ↑ |
| Faster path to music | Time to first play ↓ |

### 1.2 Implementation principles

1. **Overlay, don't replace** — Reuse catalog DB + mood ranker; don't rebuild a full rec engine (ADR-001).
2. **Excel is source; Postgres is runtime** — Model never reads `.xlsx` in production.
3. **LLM off the critical path** — Batch/precompute explanations; template fallback always available (ADR-004).
4. **Novelty is a hard gate** — Played tracks never appear in Discovery Drop (ADR-005).
5. **Same mood logic everywhere** — Dataset tagging §6.5 identical in dev, staging, and prod.

### 1.3 Mood scope (dataset vs product)

| Context | Moods |
|---------|-------|
| **Product UI** | 6 moods: Energised, Focused, Low-key, Adventurous, Nostalgic, Sad |
| **Dataset catalog tagging** | 5 moods: Energised, Focused, Low-key, Nostalgic, Sad — **Adventurous excluded** (§6.5) |
| **Dataset features** | `energy`, `valence`, `tempo`, `instrumentalness` only |

---

## 2. Phase Map

```
Phase 0          Phase 1              Phase 2                 Phase 3
Foundation  →    MVP                  Trust & Browse    →     Optimization
(2–3 weeks)      (4–6 weeks)          (3–4 weeks)             (3–4 weeks)

Excel → DB       Mood Gateway         Visual artist search    Smart mood default
Schema           Discovery Drop       Heard-before feedback   Adaptive drop size
Seed scripts     Mood ranker          Push notifications      DW pool merge
Docker local     BFF + Home API       LLM on all modules      Edge caching
                 LLM explanations
                 Basic metrics
```

| Phase | Product theme | Architecture anchor |
|-------|---------------|---------------------|
| **0** | Data ready | §6, §6.5, `scripts/`, `sql/schema.sql` |
| **1** | Prove habit + novelty | §5, §8, §9, §16 Phase 1, problem §6.1–6.2 |
| **2** | Trust + visual browse | §5.9, §16 Phase 2, problem §6.3–6.4 |
| **3** | Personalization + scale | §16 Phase 3, §10, §11 |

---

## Phase 0 — Foundation & Data Pipeline

**Duration:** 2–3 weeks  
**Goal:** Catalog loaded, mood-tagged, validated, and queryable — ready for ranker and API work.

### 0.1 Objectives

- [x] Excel dataset ingested into PostgreSQL (script + schema ready; DB via Docker/Render)
- [x] All 5 dataset moods tagged per §6.5 rules
- [x] Coverage validation passes (≥200 tracks per mood)
- [x] Local dev environment reproducible (Docker Compose + no-Docker dry-run path)
- [ ] Render Postgres provisioned (optional — user action)

### 0.2 Deliverables

| Deliverable | Location / artifact |
|-------------|---------------------|
| Postgres schema | `sql/schema.sql` |
| Mood bucketing logic | `scripts/mood_rules.py`, `scripts/build_mood_buckets.py` |
| Excel → DB loader | `scripts/excel_to_db.py` |
| Coverage validator | `scripts/validate_coverage.py` |
| Golden dataset | `data/source/tracks.xlsx` (local) |
| Tagged export | `data/seed/v1/track_mood_tags.csv` |
| Environment template | `.env.example`, `docker-compose.yml` |

### 0.3 Tasks

#### Week 1 — Data prep

| # | Task | Owner | Done when |
|---|------|-------|-----------|
| 0.1 | Finalize Excel columns: `track_id`, `name`, `artist_name`, `energy`, `valence`, `tempo`, `instrumentalness` | Data | All rows have numeric audio features |
| 0.2 | Place file at `data/source/tracks.xlsx` | Data | File loads without parse errors |
| 0.3 | Run `python scripts/excel_to_db.py --dry-run` | Eng | Mood tag counts printed per mood |
| 0.4 | Fix column aliases in `build_mood_buckets.py` if headers differ | Eng | `normalize_columns()` succeeds |
| 0.5 | Document `dataset_version` (e.g. `v1.0.0`) | Eng | Version in env + DB rows |

#### Week 2 — Database & validation

| # | Task | Owner | Done when |
|---|------|-------|-----------|
| 0.6 | `docker compose up -d` — Postgres + Redis | Eng | `psql` connects |
| 0.7 | Run full load: `excel_to_db.py` | Eng | `tracks` + `track_mood_tags` populated |
| 0.8 | Run `validate_coverage.py` | Eng | All checks pass |
| 0.9 | Seed 5–10 synthetic `play_history` users for novelty testing | Eng | `play_history` table has sample rows |
| 0.10 | Create Render Postgres; run schema + seed | Eng | External `DATABASE_URL` works |

#### Week 3 — Baseline queries & docs

| # | Task | Owner | Done when |
|---|------|-------|-----------|
| 0.11 | Verify mood pool queries (e.g. FOCUSED ≥200 tracks) | Eng | SQL returns expected counts |
| 0.12 | Confirm 0 rows with `ADVENTUROUS` in `track_mood_tags` | Eng | Validator passes |
| 0.13 | Add CI step: dry-run + validate on sample CSV | Eng | GitHub Action green |
| 0.14 | Push Phase 0 code to [MoodAI_Spotify](https://github.com/amanmbaa20060-sudo/MoodAI_Spotify) | Eng | `main` branch up to date |

### 0.4 Exit criteria

- [ ] ≥1,000 tracks loaded (or 80% of catalog tagged)
- [ ] ≥200 tracks per dataset mood (ENERGISED, FOCUSED, LOW_KEY, NOSTALGIC, SAD)
- [ ] Zero `ADVENTUROUS` tags in dataset
- [ ] Same seed script works locally and against Render Postgres

### 0.5 Risks

| Risk | Mitigation |
|------|------------|
| Thin mood buckets after tagging | Expand source catalog; relax thresholds only with architecture review |
| Excel column name mismatch | `COLUMN_ALIASES` in `build_mood_buckets.py` |
| Render free DB expiry | Upgrade to Starter before demo deadline |

---

## Phase 1 — MVP (Habit + Novelty)

**Duration:** 4–6 weeks  
**Goal:** End-to-end mood-led home experience with daily Discovery Drop, mood recalibration, and LLM explanations.

### 1.1 Objectives (product)

- [ ] **Mood Gateway** — persistent 6-state selector on home (problem §6.1)
- [ ] **Discovery Drop** — 10 novel tracks daily with reasons (problem §6.2)
- [ ] **Mood recalibration** — home feed updates on mood tap (<2s perceived)
- [ ] **LLM explanations** — grounded one-liners + drop header (architecture §5.6, §5.10)
- [ ] **Metrics instrumentation** — mood tap, drop completion, novel streams

### 1.2 Services to build

| Service | Priority | Reference |
|---------|----------|-----------|
| Discovery Gateway BFF | P0 | architecture §5.1 |
| Mood State Service | P0 | architecture §5.2 |
| Mood-Aware Ranker | P0 | architecture §5.4 |
| Novelty Filter Service | P0 | architecture §5.5 |
| Discovery Orchestrator | P0 | architecture §5.3 |
| Discovery Drop Generator (batch) | P0 | architecture §5.7 |
| Explanation Service + LLM Gateway | P0 | architecture §5.6, §5.10 |
| Home Feed Composer | P0 | architecture §5.8 |

**Defer:** Visual Search Adapter, push notifications, heard-before endpoint (architecture §16).

### 1.3 Tasks by week

#### Weeks 1–2 — Core API + mood

| # | Task | Details |
|---|------|---------|
| 1.1 | Choose API stack (e.g. Python FastAPI or Node) | Single BFF to start |
| 1.2 | Implement `PUT /v1/users/me/mood` | Persist to `user_mood_preferences` + Redis `mood:{user_id}` |
| 1.3 | Implement `GET /v1/users/me/mood` | Default `LOW_KEY` if unset |
| 1.4 | Implement Mood-Aware Ranker | Weight vectors from §5.4; query `track_mood_tags` |
| 1.5 | Implement `GET /v1/home` (skeleton) | Return `mood_gateway` module + `active_mood` |
| 1.6 | Build mood selector UI (web or mobile) | 6 states, above the fold |

#### Weeks 3–4 — Discovery Drop pipeline

| # | Task | Details |
|---|------|---------|
| 1.7 | Implement Novelty Filter | Query `play_history`; exclude played `track_id`s |
| 1.8 | Implement Orchestrator `GenerateDrop` | Pipeline: candidates → mood rank → novelty → diversity → top 10 |
| 1.9 | Apply DROP_RULES diversity | Max 2/artist, min 4 genres, no 7-day dupes |
| 1.10 | Create `discovery_drop` + `drop_track` tables | Extend `sql/schema.sql` |
| 1.11 | Build Drop Generator (cron / script) | Daily batch per user; idempotent `(user_id, drop_date)` |
| 1.12 | Implement `GET /v1/discovery-drop` | Return today's drop or `next_refresh_at` |

#### Weeks 5–6 — LLM, home compose, deploy

| # | Task | Details |
|---|------|---------|
| 1.13 | Implement LLM Gateway | Batched `DROP_EXPLANATIONS` prompt via Groq; default model `llama-3.1-8b-instant` |
| 1.14 | Implement Explanation Service | Grounding validation + template fallback |
| 1.15 | Implement Home Feed Composer | Pin `mood_gateway` + `discovery_drop`; add `fresh_picks` |
| 1.16 | Mood tap → re-rank | Invalidate `home:{user}:{mood}`; re-score cached candidates <1.5s p95 |
| 1.17 | Add basic analytics events | `MoodChanged`, `DiscoveryDropReady`, `RecommendationServed` |
| 1.18 | Deploy BFF + worker to Render | Internal `DATABASE_URL`; optional Redis |
| 1.19 | End-to-end demo script | App open → mood tap → play drop → verify novel tracks |

### 1.4 API contracts (MVP)

| Endpoint | Method | Phase 1 |
|----------|--------|---------|
| `/v1/home` | GET | Yes |
| `/v1/users/me/mood` | PUT | Yes |
| `/v1/discovery-drop` | GET | Yes |
| `/v1/search/artists` | GET | No (Phase 2) |
| `/v1/discovery-drop/tracks/{id}/heard-before` | POST | No (Phase 2) |

### 1.5 NFR targets (MVP)

| Metric | Target |
|--------|--------|
| Home load p95 | ≤ 800 ms |
| Mood change → feed refresh p95 | ≤ 1.5 s |
| Discovery Drop read p95 | ≤ 200 ms (precomputed) |
| Explanation attach rate (drops) | ≥ 99% |
| LLM fallback rate | ≤ 5% |

### 1.6 Exit criteria

- [ ] User can select mood and see home recalibrate
- [ ] Daily drop returns exactly 10 never-played tracks
- [ ] Each drop track has LLM or template reason + optional header
- [ ] Mood tap updates feed without full page reload
- [ ] Deployed on Render with Render Postgres
- [ ] A/B flag `mood_gateway_enabled` stubbed for experiments

### 1.7 Experiments to prepare

| Experiment | Hypothesis | Metric |
|------------|------------|--------|
| Mood Gateway vs control | Mood increases novel streams | Novel stream rate |
| Daily Drop vs weekly only | Daily cadence increases sessions | Drop completion rate |
| LLM vs template explanations | LLM increases saves | Save rate |

---

## Phase 2 — Trust & Browse

**Duration:** 3–4 weeks  
**Goal:** Improve transparency feedback loops and visual browse for non-home entry paths.

### 2.1 Objectives (product)

- [ ] **Visual-first artist grids** in search/browse (problem §6.3 — Anupriya persona)
- [ ] **Expanded explanations** on all home module types (problem §6.4 — Rukma persona)
- [ ] **Push notification** when Discovery Drop is ready
- [ ] **"Heard it before"** report → novelty correction loop

### 2.2 Services to add

| Service | Priority | Reference |
|---------|----------|-----------|
| Visual Search Adapter | P0 | architecture §5.9 |
| Push notification consumer | P1 | architecture §16 Phase 2 |
| Heard-before feedback handler | P0 | architecture §7.1, §15 |
| LLM prewarm job (`llm-prewarm-reasons`) | P1 | architecture §11.1 |

### 2.3 Tasks

#### Weeks 1–2 — Visual search + feedback

| # | Task | Details |
|---|------|---------|
| 2.1 | Add artist `image_url` to catalog (column or CDN mapping) | Required for grid |
| 2.2 | Implement `GET /v1/search/artists?q=` | Visual grid DTO; p95 ≤ 500 ms |
| 2.3 | Build search UI — artist image grid | Alt text + screen reader names |
| 2.4 | Implement `POST .../heard-before` | Update novelty exclude list + bloom filter |
| 2.5 | Dashboard: heard-before reports per 1k drops | architecture §14.1 |

#### Weeks 3–4 — LLM expansion + notifications

| # | Task | Details |
|---|------|---------|
| 2.6 | LLM reasons on `fresh_picks` + `mood_mix` modules | Async prewarm; not on sync path |
| 2.7 | `llm-prewarm-reasons` job every 6h | Fill `llm:cache:{prompt_hash}` in Redis |
| 2.8 | Push on `DiscoveryDropReady` event | "Your Discovery Drop is ready" |
| 2.9 | Explanation audit log UI (internal) | `feature_id`, `prompt_hash`, `model_id` |
| 2.10 | Experiment: `visual_search_grid` on/off | Time to first play |

### 2.4 Exit criteria

- [ ] Artist search returns visual grid as primary layout
- [ ] ≥90% of home module items show a reason
- [ ] Heard-before report removes track from future drops for user
- [ ] Push notification fires on drop ready (opt-in)
- [ ] Trust survey stub or thumbs feedback captured

### 2.5 Personas addressed

| Persona | Phase 2 feature |
|---------|-----------------|
| Anupriya (visual browser) | Artist image grid search |
| Rukma (trust-sensitive) | Full explanation coverage + audit trail |

---

## Phase 3 — Optimization & Scale

**Duration:** 3–4 weeks  
**Goal:** Personalize defaults, tune discovery cadence, and harden performance for production scale.

### 3.1 Objectives

- [ ] **Smart mood default** — LLM + time-of-day / listening signals
- [ ] **Adaptive drop sizing** — experiment with 10 vs 15 tracks
- [ ] **Unified candidate pool** with Discover Weekly (deduplicated)
- [ ] **Edge caching** of home at BFF
- [ ] **Production hardening** — HA, monitoring, cost controls

### 3.2 Tasks

#### Personalization

| # | Task | Details |
|---|------|---------|
| 3.1 | Smart mood default service | Suggest mood on app open; user can override |
| 3.2 | Personalize drop refresh time | User-local optimal window from engagement data |
| 3.3 | Adaptive drop size flag | `drop_size`: 10 / 15 (architecture §14.3) |
| 3.4 | Merge Discover Weekly + Drop candidate pools | Phase 2/3 strategy §9.5 |

#### Performance & scale

| # | Task | Details |
|---|------|---------|
| 3.5 | BFF edge cache (mood-keyed, 60s) | architecture §10.1 |
| 3.6 | Candidate prewarm every 6h | `candidates:{user_id}` in Redis |
| 3.7 | Drop generator horizontal sharding | `hash(user_id) % partitions` |
| 3.8 | Connection pooling for Postgres | Respect Render connection limits |
| 3.9 | LLM token budget per user/day | architecture §5.10 |

#### Experimentation & tuning

| # | Task | Details |
|---|------|---------|
| 3.10 | Tune mood weight vectors offline | A/B per mood; architecture §9.1 |
| 3.11 | Run full experiment suite | problem §12 |
| 3.12 | Novel stream rate + repeat listening index report | North-star dashboard |

### 3.3 Exit criteria

- [ ] Smart mood default improves mood tap rate vs `LOW_KEY` default
- [ ] Home p95 ≤ 800 ms under load test
- [ ] 95% of users have READY drop within 5 min of refresh window
- [ ] LLM cost per user per day within budget
- [ ] Production runbook + on-call dashboards complete

---

## 7. Cross-Phase Concerns

### 7.1 Security & privacy (all phases)

| Requirement | Phase |
|-------------|-------|
| Mood data not used for ads | 1+ |
| LLM prompts exclude raw PII | 1+ |
| Explanation audit retention 90 days | 1+ |
| User can clear mood history | 2+ |
| GDPR export (mood + drop history) | 3 |

### 7.2 Resilience (implement early, harden later)

| Failure | MVP behavior | Phase |
|---------|----------------|-------|
| Groq API down | Template fallback | 1 |
| Drop not ready | Countdown + skeleton UI | 1 |
| Novelty uncertain | Fail closed (hide track) | 1 |
| Redis down | Direct Postgres reads | 1 |
| Multi-provider LLM failover | Queue + extend batch window | 3 |

### 7.3 Testing strategy

| Layer | Phase 0 | Phase 1 | Phase 2 | Phase 3 |
|-------|---------|---------|---------|---------|
| Unit | mood_rules, validators | ranker, novelty | search adapter | weight tuning |
| Integration | excel_to_db | drop pipeline | heard-before loop | prewarm jobs |
| E2E | SQL mood queries | home + mood + drop | search grid + push | load test |
| Data | coverage ≥200/mood | 0 played in drop | image URLs present | full catalog scale |

### 7.4 Render deployment by phase

| Phase | Render services |
|-------|-----------------|
| **0** | Postgres (managed) |
| **1** | Web Service (BFF) + Postgres; optional Cron (drop generator) |
| **2** | + Background worker (LLM prewarm); push via third-party or Render cron |
| **3** | + Redis (Key Value); autoscale workers; read replica if needed |

### 7.5 Repository structure (target)

```
MoodAI_Spotify/
├── data/source/tracks.xlsx
├── scripts/                    # Phase 0 ✓
├── sql/schema.sql              # Phase 0 ✓; extend in Phase 1
├── services/
│   ├── bff/                    # Phase 1
│   ├── ranker/                 # Phase 1
│   ├── orchestrator/           # Phase 1
│   ├── llm-gateway/            # Phase 1
│   └── drop-worker/            # Phase 1
├── apps/
│   └── web/                    # Phase 1 UI
├── docs/
│   ├── problemstatement.md
│   ├── architecture.md
│   └── phasewiseimplementation.md
├── docker-compose.yml
├── render.yaml                 # Phase 1
└── requirements.txt
```

---

## 8. Milestone Timeline

| Milestone | Target | Key demo |
|-----------|--------|----------|
| **M0: Data ready** | End of Phase 0 | Show mood-tagged catalog in DB; validation report |
| **M1: Mood + Drop** | Week 4 of Phase 1 | Select mood → see 10-track drop with reasons |
| **M2: MVP complete** | End of Phase 1 | Full home on Render; mood recalibration live |
| **M3: Trust & Browse** | End of Phase 2 | Visual search + heard-before + push |
| **M4: Production-ready** | End of Phase 3 | Smart defaults, load test, experiment results |

**Total estimated duration:** 12–17 weeks (grad project pace).

---

## 9. Traceability Matrix

| Product requirement | Phase | Architecture § |
|----------------------|-------|------------------|
| Mood Gateway (persistent) | 1 | §5.2, §8.2 |
| Discovery Drop (10 tracks, daily) | 1 | §5.7, §6.2 |
| Novelty / heard-before filter | 1 (filter), 2 (feedback) | §5.5 |
| One-line LLM reasons | 1 (drop), 2 (all modules) | §5.6, §5.10 |
| Mood recalibration <2s | 1 | §8.2, §10.3 |
| Visual artist anchors | 2 | §5.9, §8.4 |
| Dataset mood tagging (5 moods, numeric) | 0 | §6.5 |
| Excel → Postgres pipeline | 0 | §6.5, README |
| Smart mood default | 3 | §16 Phase 3 |
| Metrics & experiments | 1 (instrument), 3 (full) | §14, problem §12 |

---

## Appendix A — Phase 1 Definition of Done (checklist)

```
[ ] data/source/tracks.xlsx loaded; validate_coverage.py passes
[ ] GET /v1/home returns mood_gateway + discovery_drop modules
[ ] PUT /v1/users/me/mood persists and triggers feed update
[ ] GET /v1/discovery-drop returns 10 novel tracks with reasons
[ ] No played track appears in drop (novelty filter)
[ ] LLM explanation with template fallback on failure
[ ] Deployed on Render with managed Postgres
[ ] README updated with run instructions
```

---

## Appendix B — Open items to resolve during build

| Item | Suggested default | Decide by |
|------|-------------------|-----------|
| API language (Python vs Node) | Python FastAPI (matches scripts) | Phase 1 Week 1 |
| Frontend (web vs mobile) | React web MVP | Phase 1 Week 1 |
| LLM provider | Groq `llama-3.1-8b-instant` | Phase 1 Week 5 |
| Adventurous at runtime | Ranker novelty_score + genre stretch (no dataset tag) | Phase 1 Week 2 |
| Auth | Simple JWT / mock user for grad demo | Phase 1 Week 1 |

---

*This plan is the execution companion to the product brief and architecture. Update task checkboxes as phases complete.*
