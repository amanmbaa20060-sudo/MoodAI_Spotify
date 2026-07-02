# Mood-First Discovery Gateway — Problem Statement & Proposed Solution

**Document purpose:** Product and technical foundation for detailed system architecture design.  
**Context:** Growth Team, Spotify — increasing meaningful music discovery and reducing repetitive listening.  
**Version:** 1.0  
**Status:** Draft for architecture planning

---

## 1. Executive Summary

Spotify has achieved massive scale and operates one of the world's most sophisticated music recommendation systems. Despite this, a significant share of listening still comes from **repeat playlists, familiar artists, and previously discovered tracks**. Users open the app without a clear path to fresh music that matches how they feel in the moment.

This document defines the problem, user and business constraints, and a proposed solution: the **Mood-First Discovery Gateway** — a contextual entry point that replaces the overwhelming default homepage experience with emotion-led discovery as the default behavior, not the exception.

**Core thesis:** Meet users where they are emotionally first; deliver curated novelty second. Reduce decision friction, increase trust in recommendations, and make daily discovery a habit rather than a weekly event.

---

## 2. Problem Statement

### 2.1 Business Context

| Dimension | Current State |
|-----------|---------------|
| **Scale** | Millions of acquired users; mature recommendation infrastructure |
| **Listening behavior** | High proportion of repetitive consumption (saved playlists, repeat artists, known catalog) |
| **Strategic goal** | Increase *meaningful* music discovery; reduce repetitive listening |
| **Growth team mandate** | Improve activation of discovery surfaces and deepen engagement with unfamiliar content |

### 2.2 Core Problem

> **Users who want to discover new music are blocked by cognitive overload, lack of emotional context, and low trust in opaque recommendations — so they default to what they already know.**

The homepage and primary discovery surfaces are optimized for breadth and recency, not for the **"I just opened Spotify — what do I want right now?"** moment. That moment currently fails users because:

1. **No emotional entry point** — The app does not ask or infer *how* the user wants to feel; it presents a firehose of content.
2. **Discovery is episodic, not habitual** — Discover Weekly (weekly cadence) is too infrequent to compete with the comfort of familiar libraries.
3. **Familiar content leaks into discovery** — Users encounter tracks they have already heard, eroding the sense of novelty.
4. **Browse and search feel like work** — Text-heavy lists increase decision friction; visual recognition is underused.
5. **Recommendations lack explainability** — Users cannot tell *why* something was suggested, which reduces trust (survey avg transparency importance: **3.6/5**; power users up to **5/5**).

### 2.3 Who Is Affected

| Persona | Behavior | Pain |
|---------|----------|------|
| **Routine listener** | Opens app daily; plays same playlists | Wants variety but won't search for it |
| **Mood-driven listener** | Listens based on activity/emotion | Homepage doesn't reflect current intent |
| **Discovery-curious user** | Uses Discover Weekly sporadically | Weekly cadence feels stale; familiar tracks appear |
| **Visual browser** (e.g. Anupriya) | Searches or browses by artist recognition | Text lists slow recognition and increase friction |
| **Trust-sensitive user** (e.g. Rukma) | Engages when recommendations feel intentional | Opaque algo feels random; wants one-line rationale |

### 2.4 Problem in One Sentence

**Spotify's recommendation strength is undermined at the front door: users arrive without context, face too many undifferentiated choices, and retreat to repetitive listening because discovery feels effortful and untrustworthy.**

---

## 3. Research & Evidence (Inputs to Solution)

| Finding | Implication |
|---------|-------------|
| Significant listening from repeat/saved content | Discovery must be *easier than* reopening old playlists |
| Survey: transparency importance avg 3.6/5 | Every recommendation surface should carry lightweight explanation |
| Anupriya: visual recognition unmet need | Artist-first visual grids for browse/search paths |
| Rukma: 5/5 on transparency | High-trust users are a design anchor for explainability |
| Discover Weekly engagement exists but is weekly | Daily, shorter ritual can increase frequency without fatigue |

---

## 4. Goals & Success Metrics

### 4.1 Product Goals

1. **Increase novel listening** — More streams from tracks the user has never played before.
2. **Reduce repetitive listening share** — Lower proportion of sessions dominated by saved/repeat catalog.
3. **Make discovery habitual** — Daily return to a dedicated discovery ritual.
4. **Improve trust and satisfaction** — Higher perceived relevance and transparency of recommendations.
5. **Lower time-to-first-play** — Faster path from app open to meaningful playback.

### 4.2 North-Star & Supporting Metrics

| Metric | Definition | Target Direction |
|--------|------------|------------------|
| **Novel stream rate** | % of streams from never-before-played tracks | ↑ |
| **Discovery Drop completion rate** | Users who play ≥3 of 10 daily tracks | ↑ |
| **Mood selector usage rate** | % of home sessions with mood tap | ↑ |
| **Repeat listening index** | Share of listening from top 50 repeated tracks | ↓ |
| **Save rate from discovery** | Tracks saved from Drop / mood feed | ↑ |
| **Recommendation trust score** | In-product survey / thumbs feedback | ↑ |
| **Time to first play** | Seconds from app open to playback | ↓ |

### 4.3 Non-Goals (Explicit Scope Boundaries)

- Replacing Spotify's full recommendation engine or collaborative filtering stack.
- Full mood inference from passive signals only (mood *selection* is explicit in v1).
- Social/sharing features for discovery drops.
- Podcast or audiobook discovery (music-only in v1).

---

## 5. Proposed Solution: Mood-First Discovery Gateway

### 5.1 Solution Overview

Replace the overwhelming default homepage with a **contextual entry point** that:

1. Captures **emotional intent** in one tap (Mood Gateway).
2. **Recalibrates** home feed, mixes, and discovery surfaces in real time around mood + taste.
3. Delivers a **daily 10-track Discovery Drop** of never-heard music.
4. Uses **visual-first artist anchors** in browse/search paths.
5. Shows a **one-line recommendation reason** on every suggested track.

```
┌─────────────────────────────────────────────────────────────────┐
│                        APP OPEN (HOME)                          │
├─────────────────────────────────────────────────────────────────┤
│  [ Mood Gateway: Energised | Focused | Low-key | Adventurous   │
│                  | Nostalgic | Sad ]          ← persistent      │
├─────────────────────────────────────────────────────────────────┤
│  Discovery Drop (10 tracks, daily)                              │
│  + one-line "why" per track + heard-before filter               │
├─────────────────────────────────────────────────────────────────┤
│  Mood-recalibrated feeds: mixes, fresh picks, artist grids      │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Design Principles

| Principle | Application |
|-----------|-------------|
| **Mood before catalog** | Emotional state is the first input, not search or library |
| **Fresh by default** | Discovery surfaces exclude previously played tracks |
| **Low friction** | One tap to set context; no forms or onboarding gates |
| **Transparent by default** | One short sentence explains every pick |
| **Visual recognition** | Artists and albums as images, not text walls |
| **Daily ritual** | Short, predictable cadence (10 tracks, consistent refresh time) |

---

## 6. Feature Specification

### 6.1 Feature A: Mood Gateway on Home (Persistent)

**What it is:** A full-width, always-visible emotional state selector above the fold on the home screen. Not a one-time onboarding question — a persistent 1-tap control.

**Mood states (v1):**

| Mood | User intent (examples) | Discovery bias |
|------|------------------------|----------------|
| **Energised** | Workout, party prep, morning commute | Higher tempo, upbeat, rhythmic |
| **Focused** | Work, study, deep work | Instrumental, steady, minimal lyrics |
| **Low-key** | Relaxing evening, background | Mellow, acoustic, ambient |
| **Adventurous** | Open to genre stretch | Adjacent genres, higher novelty score |
| **Nostalgic** | Memory, comfort with twist | Era/decade affinity + unfamiliar artists in that vein |
| **Sad** | Reflective, cathartic | Emotional valence match; avoid jarring picks |

**Behavior:**

- One tap sets active mood for the session (and optionally persists until changed).
- Home feed, mixes, radio seeds, and Discovery Drop **immediately recalibrate** — no page reload required.
- Default mood: last selected, or system default (e.g. **Low-key**) for first-time users.
- Mood is an **explicit signal** fed to ranking; it does not replace taste profile.

**User story:**  
*As a user who just opened Spotify, I want to tell the app how I feel in one tap so that everything shown fits my current moment without searching.*

**Acceptance criteria:**

- [ ] Mood selector visible on home without scroll (above the fold).
- [ ] Mood change updates feed content within &lt;2s perceived latency.
- [ ] Mood selection persists across sessions (user-configurable reset optional).
- [ ] All downstream discovery modules receive mood context in ranking request.

---

### 6.2 Feature B: Daily Discovery Drop (10 Tracks)

**What it is:** A daily curated playlist of **10 tracks the user has never heard**, refreshed at a **consistent time** (user-local morning default, e.g. 6:00 AM). Replaces or supplements Discover Weekly as the primary daily discovery ritual.

**Behavior:**

| Attribute | Specification |
|-----------|---------------|
| **Size** | 10 tracks |
| **Cadence** | Daily refresh |
| **Novelty rule** | Exclude any track with prior play history for user |
| **Selection logic** | Genres adjacent to taste profile + active mood |
| **Presentation** | Play in-session or save individual tracks / full drop |
| **Explanation** | One sentence per track ("Because you love …") |
| **Familiarity flag** | "Heard it before" guard — if false positive detected, allow dismiss/report |

**User story:**  
*As a discovery-curious listener, I want a short daily set of genuinely new music matched to my mood so that discovery becomes a habit I can trust.*

**Acceptance criteria:**

- [ ] Exactly 10 tracks per drop; no duplicates within drop or vs. prior 7 days (configurable).
- [ ] Zero tracks with confirmed prior user play (hard filter).
- [ ] Refresh at consistent local time; UI shows countdown / "next drop" when empty.
- [ ] Each track displays one-line reason and supports play + save.
- [ ] Drop playable as a queue (continuous session).

---

### 6.3 Feature C: Visual-First Artist Anchors

**What it is:** For users entering via **search or browse**, replace text-list-heavy results with a **visual grid of artist images** (and optionally album art), enabling recognition before reading.

**Behavior:**

- Search results surface **artist tiles** prominently when query matches artist intent.
- Browse categories lead with **image grids** rather than numbered text lists.
- Tap artist → artist page; long-press or secondary affordance for quick play / radio.
- Complements Mood Gateway for users who do not start on home.

**User story:**  
*As a visual browser, I want to recognize artists by their image so that I can decide faster without reading long lists.*

**Acceptance criteria:**

- [ ] Artist search returns visual grid as primary layout on mobile.
- [ ] Image assets meet CDN/cache performance budgets.
- [ ] Grid accessible (alt text, screen reader artist name).

---

### 6.4 Feature D: One-Line Recommendation Reason

**What it is:** Every recommended track (Discovery Drop, mood feed, mixes) shows **one short explanation** of why it was picked.

**Example copy patterns:**

- "Because you love **[Artist/Genre]**"
- "Trending in **[Genre]** this week"
- "Fans of **[Artist]** are listening to this"
- "Matches your **[Mood]** vibe"
- "New release near your taste"

**Constraints:**

- Max ~60 characters or one line on mobile.
- Template-based generation (not free-form LLM in v1) for consistency and latency.
- Reasons must map to **actual ranking features** (auditable).

**User story:**  
*As a trust-sensitive listener, I want to know why a song was recommended so that I can decide whether to give it a chance.*

**Acceptance criteria:**

- [ ] 100% of Discovery Drop tracks show a reason.
- [ ] ≥90% of mood-recalibrated feed items show a reason in v1.
- [ ] Reason maps to logged ranking feature for debugging and compliance.

---

## 7. User Flows

### 7.1 Primary Flow: Mood-Led Discovery

```
Open App → Home
    → Tap Mood (e.g. "Adventurous")
        → Discovery Drop loads (10 new tracks + reasons)
        → Home feed refreshes (mood-weighted mixes & picks)
    → Play track / Save track / Play full Drop
    → Optional: Change mood → surfaces re-rank in real time
```

### 7.2 Secondary Flow: Search / Browse (Visual Path)

```
Open App → Search or Browse
    → See artist image grid
    → Tap artist → play top track or start radio
    → Optional: Navigate to Home → set mood for deeper discovery
```

### 7.3 Daily Ritual Flow

```
Morning (drop refresh time)
    → Push notification (optional): "Your Discovery Drop is ready"
    → Open Drop → scan reasons → play 1–3 tracks
    → Save favorites → return next day
```

---

## 8. Architecture Foundations (For Detailed Design)

*This section outlines logical components for a follow-on architecture document.*

### 8.1 Logical System Components

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Client Apps  │────▶│ API / BFF Layer  │────▶│ Discovery Orchestrator│
│ (Mobile/Web) │     │                  │     │                     │
└──────────────┘     └──────────────────┘     └──────────┬──────────┘
        │                       │                          │
        │                       ▼                          ▼
        │              ┌────────────────┐        ┌─────────────────────┐
        │              │ User Profile & │        │ Recommendation      │
        │              │ Mood State Svc │        │ Engine (existing +  │
        │              └────────────────┘        │ mood/novelty layers)│
        │                       │                  └──────────┬──────────┘
        │                       ▼                             │
        │              ┌────────────────┐                     ▼
        └─────────────▶│ Discovery Drop │        ┌─────────────────────┐
                       │ Generator      │        │ Listening History / │
                       │ (scheduled)    │        │ Novelty Filter        │
                       └────────────────┘        └─────────────────────┘
                                  │
                                  ▼
                       ┌─────────────────────┐
                       │ Explanation Service │
                       │ (template reasons)  │
                       └─────────────────────┘
```

### 8.2 Key Services (Candidate Bounded Contexts)

| Service | Responsibility |
|---------|----------------|
| **Mood State Service** | Store and expose active mood per user; session + persistent preference |
| **Discovery Orchestrator** | Aggregate mood, taste, history; route ranking requests |
| **Novelty Filter** | Hard exclude played tracks; maintain "heard before" bitmap/history |
| **Discovery Drop Generator** | Batch job: daily 10-track selection per user at local refresh time |
| **Mood-Aware Ranker** | Re-score candidates by mood features (tempo, energy, valence, genre) |
| **Explanation Service** | Map ranking features → one-line template copy |
| **Visual Catalog API** | Artist images, grid layouts for search/browse |
| **Home Feed Composer** | Assemble mood gateway UI + drop + recalibrated modules |

### 8.3 Data Inputs

| Data Source | Use |
|-------------|-----|
| Listening history (plays, skips, saves) | Novelty filter; taste embedding |
| Taste profile / genre affinities | Adjacent genre selection |
| Active mood selection | Ranking feature; explanation copy |
| Track audio features (tempo, energy, valence) | Mood matching |
| Artist metadata + images | Visual grids; reason templates |
| Discover Weekly / existing rec models | Candidate pool generation (reuse, don't rebuild) |

### 8.4 Key APIs (Illustrative)

| Endpoint | Purpose |
|----------|---------|
| `PUT /v1/users/{id}/mood` | Set active mood |
| `GET /v1/home` | Mood gateway + composed feed |
| `GET /v1/discovery-drop` | Today's 10 tracks + reasons |
| `GET /v1/search/artists?q=` | Visual-first artist grid |
| `POST /v1/recommendations/explain` | Feature → reason string (internal) |

### 8.5 Scheduling & Freshness

- **Discovery Drop:** Per-user timezone batch; pre-compute candidates overnight; finalize at refresh window.
- **Mood recalibration:** Real-time re-rank from cached candidate pools (avoid full batch on each tap).
- **CDN:** Artist images cached at edge for grid performance.

### 8.6 Failure Modes & Degradation

| Failure | Degraded behavior |
|---------|-------------------|
| Mood service unavailable | Default mood; generic ranking |
| Drop not generated in time | Show previous drop + "refreshing" state; fallback to Discover Weekly pool |
| Explanation service down | Show track without reason; never block playback |
| Novelty filter uncertain | Prefer false negative (hide track) over false positive |

---

## 9. Ranking Logic (High-Level)

### 9.1 Discovery Drop Selection Pipeline

```
1. Candidate generation (from existing rec system — adjacent genres)
2. Mood filter / re-weight (audio features + genre tags)
3. Novelty filter (remove all previously played)
4. Diversity pass (artist spread, genre spread)
5. Top 10 selection
6. Attach primary explanation feature per track
7. Persist drop for user-day
```

### 9.2 Mood Recalibration (Real-Time)

On mood tap:

```
1. Load cached candidate pool for user (precomputed)
2. Apply mood weight vector to scores
3. Re-sort modules (mixes, picks, radios)
4. Push delta to client (partial update)
```

### 9.3 Mood → Feature Weights (Example)

| Mood | Energy | Valence | Tempo | Novelty | Vocal/instrumental |
|------|--------|---------|-------|---------|---------------------|
| Energised | High | High | High | Medium | — |
| Focused | Low–Med | Neutral | Low–Med | Low | Prefer instrumental |
| Low-key | Low | Neutral | Low | Low | — |
| Adventurous | — | — | — | **High** | Genre stretch |
| Nostalgic | — | — | Era match | Medium | Familiar timbres |
| Sad | Low | Low | Low | Low | Emotional match |

*Exact weights to be tuned offline and via experimentation.*

---

## 10. Phasing & MVP Scope

### Phase 1 — MVP (Prove habit + novelty)

- Mood Gateway (6 states, persistent on home)
- Daily Discovery Drop (10 tracks, novelty filter, one-line reasons)
- Basic mood recalibration of home modules
- Metrics instrumentation

### Phase 2 — Trust & Browse

- Visual-first artist grids in search
- Expanded explanation coverage on all feed types
- Push notification for daily drop
- "Heard it before" report/dismiss feedback loop

### Phase 3 — Optimization

- Personalize mood default from time-of-day / listening patterns
- Adaptive drop size and refresh time
- Deeper experimentation on mood weight vectors

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Mood selector ignored | Low engagement | Above-fold placement; A/B test default pre-selection |
| Drop feels repetitive | Churn from ritual | Diversity constraints; expand candidate pools |
| Over-aggressive novelty filter | Thin catalog for heavy listeners | Adjacent genre expansion; podcast exclusion only |
| Explanation feels generic | Trust not improved | Tie copy to real features; user testing on copy |
| Latency on mood change | Bad UX | Precomputed pools; edge caching |
| Privacy concerns on mood data | Trust / regulatory | Explicit opt-in storage; clear data policy |

---

## 12. Experimentation Plan

| Experiment | Hypothesis | Primary metric |
|------------|------------|----------------|
| Mood Gateway vs. control home | Mood increases novel streams | Novel stream rate |
| Daily Drop vs. Discover Weekly only | Daily cadence increases discovery sessions | Drop completion rate |
| With vs. without explanations | Reasons increase saves and listen-through | Save rate; trust score |
| Visual artist grid vs. text list | Visual search reduces time to play | Time to first play |

---

## 13. Open Questions for Architecture

1. **Mood persistence model:** Session-only vs. account-persistent vs. smart default?
2. **Candidate pool strategy:** Shared pool across users vs. per-user precompute at drop time?
3. **Integration point with existing Discover Weekly:** Replace, supplement, or merge pools?
4. **Real-time mood ranking SLA:** Target p95 latency for feed refresh?
5. **Explanation auditability:** Required retention of feature → copy mappings for compliance?
6. **Markets / licensing:** Any regional constraints on pre-generated daily drops?
7. **Offline / low-connectivity:** Cached drop behavior when offline?

---

## 14. Appendix: Glossary

| Term | Definition |
|------|------------|
| **Discovery Drop** | Daily 10-track novel playlist per user |
| **Mood Gateway** | Persistent home-screen mood selector |
| **Novelty filter** | Rule excluding any track already played by user |
| **Adjacent genre** | Genre near user's taste graph, not random |
| **One-line reason** | Single-sentence explanation of recommendation |
| **Novel stream** | Stream of a track never before played by user |

---

## 15. Document Traceability

| Source input | Reflected in |
|--------------|--------------|
| Repeat listening / discovery goal | §2, §4 |
| Mood-First Discovery Gateway concept | §5 |
| 6 mood states | §6.1 |
| Daily 10-track drop + heard-before flag | §6.2 |
| Visual artist anchors (Anupriya) | §6.3 |
| Transparency 3.6/5, Rukma 5/5 | §6.4, §3 |
| Persistent mood selector | §6.1, §7.1 |

---

*Next step: Use this document as the product brief for `docs/architecture.md` — detailed component diagrams, data models, sequence flows, and infrastructure choices.*
