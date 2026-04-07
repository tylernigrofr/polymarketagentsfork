# Polymarket Trading Agent Framework (2026) — Repo Design + Agent-Driven Plan

This document proposes a clean, maintainable architecture for building Polymarket trading “agents” with:

- **Quant-first candidate generation** (find markets worth researching).
- **LLM committee review** (multiple specialized reviewers + consensus).
- **Human-in-the-loop execution** (hands-on understanding first; automation later).

The central idea is to treat every potential trade as a **reproducible artifact** (“Trade Brief”) that can be reviewed, replayed, and evaluated.

---

## Goals and constraints

- **Human-in-loop by default**: no live order placement without explicit approval.
- **Single-source-of-truth per decision**: every recommendation is derived from a `TradeBrief` and its attached evidence.
- **Hard boundaries**:
  - Data collection/normalization must not depend on LLMs.
  - Execution is the only place that touches signing/credentials.
  - Risk checks gate all proposed orders (even in “suggest-only” mode).
- **Reproducible + auditable**: store raw snapshots and hashes; support deterministic replay.
- **Measurable learning**: log predictions, confidence, reviewer votes, and outcomes for calibration analysis.

Non-goals (initially):
- Fully autonomous trading.
- Complex forecasting models. Start simple and iterate based on logged performance.

---

## Key artifact: the Trade Brief

Every candidate market you consider produces a **Trade Brief**: a structured JSON record plus a readable Markdown render.

The Trade Brief contains:
- **Market snapshot**: question, outcomes, rules, current implied prices/probabilities, time-to-resolution.
- **Microstructure snapshot**: spread, depth, basic slippage estimate.
- **Features/signals**: a small curated vector (pricing, movement, liquidity, quality flags, cross-market consistency checks).
- **External evidence** (optional): curated sources (news/official data) with extracted claims and timestamps.
- **Fair value estimate**: a distribution or mean+interval with uncertainty notes.
- **Edge + risk analysis**: what creates the edge, what could invalidate it, and key risks.
- **Draft intents**: bounded “what I would do” suggestions (not executable orders yet).

The LLM committee is only allowed to reason over this artifact (and attached evidence). Execution consumes only structured `OrderIntent`s derived from it.

---

## Repository layout (proposed)

This assumes the existing `agents/` package remains the root python package, but introduces a cleaner internal split:

```
agents/
  __init__.py

  # 1) Connectors (raw I/O)
  connectors/
    __init__.py
    polymarket_gamma.py        # events/markets metadata
    polymarket_clob.py         # quotes/orderbook/trades; later order placement
    news/
      __init__.py              # optional retrieval adapters (NewsAPI, etc.)

  # 2) Domain models (typed contracts)
  domain/
    __init__.py
    models.py                  # pydantic models: snapshots, briefs, intents, reviews
    ids.py                     # stable identifiers, idempotency keys

  # 3) Market data normalization + feature extraction
  research/
    __init__.py
    normalize.py               # raw -> canonical snapshots
    features.py                # FeatureVector computation
    candidates.py              # scoring + ranking
    brief_builder.py           # build TradeBrief from snapshots + evidence
    render.py                  # TradeBrief -> markdown report (for humans/PRs)

  # 4) Committee + consensus (LLM-optional, contract-first)
  committee/
    __init__.py
    roles.py                   # role registry + schemas
    prompts/                   # role prompts (grounded, citation required)
      news_analyst.md
      quant_reviewer.md
      microstructure.md
      skeptic.md
      risk_officer.md
    review_runner.py           # run all reviewers on a TradeBrief
    consensus.py               # reducer -> Recommendation

  # 5) Risk + sizing (deterministic)
  risk/
    __init__.py
    limits.py                  # exposure, size caps, market filters
    checks.py                  # resolution ambiguity, liquidity gates, slippage bounds
    sizing.py                  # transform edge+uncertainty into size bounds

  # 6) Execution gateway (human approval first)
  execution/
    __init__.py
    intents.py                 # OrderIntent -> executable request mapping
    approval.py                # approval gate (CLI/UI)
    broker_polymarket.py       # live connector (later); paper broker now
    reconciliation.py          # fills -> ledger; idempotency handling

  # 7) Ledger + evaluation + replay
  ledger/
    __init__.py
    store.py                   # sqlite/jsonl store for briefs/reviews/intents/fills
    schema.py                  # storage schema migrations if using sqlite
    metrics.py                 # calibration + pnl + slippage error
    replay.py                  # deterministic replay from stored snapshots

scripts/
  python/
    cli.py                     # user-facing commands, thin wrapper over modules

docs/
  TRADING_AGENT_FRAMEWORK_SPEC.md
```

Notes:
- If you prefer a new top-level package (e.g. `framework/`), that’s fine too, but keeping under `agents/` minimizes churn.
- Existing modules (e.g. current `agents/polymarket/*`) can be progressively migrated to `connectors/`.

---

## Core data contracts (v0)

Implement these as Pydantic models in `agents/domain/models.py` so every subsystem shares the same types.

### `MarketSnapshot`
- `market_id`, `event_id`
- `question`, `description`
- `outcomes[]`
- `rules_text`, `resolution_source`
- `end_time`
- `implied`: `best_bid/ask/mid` per outcome, `implied_prob` per outcome
- `volume` / liquidity proxies (when available)
- `collected_at`

### `OrderBookSnapshot`
- `bids[]`, `asks[]` (price, size)
- derived: `spread`, `depth_by_band`, `slippage_estimates` (for standard sizes)

### `FeatureVector` (keep small)
- pricing: `mid`, `spread`, `vig_proxy`
- movement: `delta_1h`, `delta_24h` (if you store history)
- liquidity: `depth_0_50bps`, `depth_0_1pct`
- time: `time_to_resolution_hours`
- cross-market: `inconsistency_flags[]`
- quality: `ambiguity_flag`, `thin_book_flag`, `suspicious_move_flag`

### `ExternalEvidence`
- `sources[]`: `{type, url, title, published_at, extracted_claims[], reliability_score}`
- `retrieval_log`: `{queries[], collected_at}`

### `TradeBrief`
- ids: `brief_id`, `market_id`, `created_at`, `version`
- snapshots: `market`, `orderbook`
- `features`
- `external_evidence?`
- `fair_value`: `distribution_or_interval`, `method`, `uncertainty_notes`
- `edge`: `edge_summary`, `liquidity_adjusted_edge`, `drivers[]`
- `risks`: `resolution_ambiguity`, `tail_risks[]`, `correlations[]`
- `falsifiers[]`
- `draft_intents[]` (bounded)
- attachments: raw payload hashes + pointers in ledger storage

### `Review` (committee output)
- `role`
- `verdict`: approve/reject/needs_more_info
- `confidence` (0–1)
- `citations[]`: JSONPath-like references into `TradeBrief` or evidence entries
- `key_points[]`
- `missing_info[]`
- `suggested_intents[]` (bounded)

### `Recommendation` (consensus)
- `decision`
- `consensus_confidence`
- `rationale`
- `required_info[]`
- `order_intents[]` (bounded)
- `audit`: included roles, weights

### `OrderIntent` (risk-gated)
- `market_id`, `outcome`, `side`
- `order_type` (limit/market), `limit_price?`
- `size`: `{min, max}` + rationale
- `max_slippage_bps`
- `time_in_force`
- `idempotency_key`
- `explanation` + citations

---

## CLI commands (thin, stable surface)

Keep the CLI as a thin wrapper; put logic in modules above.

Suggested commands:

- `candidates`: list top markets by “research value”
- `brief <market_id>`: build and store a `TradeBrief`, render markdown
- `review <brief_id>`: run committee, store `Review`s + `Recommendation`
- `recommend <brief_id>`: run risk sizing + output `OrderIntent`s
- `approve <intent_id>`: interactive approval gate (human edits allowed within bounds)
- `paper-run <intent_id>`: simulate fills and log outcomes
- `replay <brief_id>`: reproduce brief + committee outputs from stored inputs
- `report`: calibration, reviewer performance, and postmortems

---

## Committee design (roles + grounded reviews)

### Roles (v0)
- News Analyst
- Quant Reviewer
- Microstructure Reviewer
- Adversarial Skeptic
- Risk Officer

### Grounding rules
- Reviewers only see the `TradeBrief` + curated `ExternalEvidence`.
- All non-trivial claims must include citations into the brief/evidence.
- Output strictly matches the `Review` schema.

### Consensus reducer (v0)
- Simple weighted aggregation:
  - Risk Officer can veto if hard limits/flags triggered.
  - Skeptic increases weight toward `needs_more_info` when ambiguity flags present.
- Produces a single `Recommendation` with required info checklist.

---

## Human-in-loop execution (initial posture)

Execution is a “gate” between recommendation and any live actions:

1. Generate brief
2. Committee reviews + consensus
3. Risk-gated `OrderIntent`s
4. Human approves/edits within bounds
5. Place order (later) or paper-simulate (now)
6. Ledger records everything for evaluation

Automation later becomes “auto-approve under strict constraints” without changing the underlying architecture.

---

## Storage / ledger (start simple)

Start with SQLite (or JSONL) to store:
- raw snapshots (or hashes + compressed blobs)
- `TradeBrief`s
- committee `Review`s + `Recommendation`s
- `OrderIntent`s + approvals
- simulated/live fills

The key requirement is **replay**: every decision is reconstructible from stored inputs.

---

## Step-by-step agent-driven development plan

This plan is designed so you can delegate each step to an engineering agent (or do it manually) with clear acceptance criteria and minimal coupling.

### Phase 0 — Scaffolding and contracts
**Deliverables**
- `agents/domain/models.py` with Pydantic models for all contracts (v0).
- `agents/ledger/store.py` stub with basic CRUD for `TradeBrief` + `Review`.
- A new CLI command skeleton wired into `scripts/python/cli.py` (or a new `agents/cli.py`).

**Acceptance criteria**
- You can create and validate a minimal `TradeBrief` object and persist it.
- `python -m compileall` passes.

**Agent prompt**
> Add Pydantic domain models for TradeBrief/Review/OrderIntent and a minimal SQLite (or JSONL) store. Keep it small and type-safe. No trading logic yet.

---

### Phase 1 — Read-only market data + normalization
**Deliverables**
- `agents/connectors/polymarket_gamma.py`: fetch markets/events (read-only).
- `agents/connectors/polymarket_clob.py`: fetch best bid/ask (and orderbook if available).
- `agents/research/normalize.py`: raw payloads → `MarketSnapshot` / `OrderBookSnapshot`.
- Snapshot caching in ledger (store raw payload hashes + blobs).

**Acceptance criteria**
- `candidates` can fetch at least N active markets and build snapshots for them.
- Snapshots are stored and replayable (same input → same snapshot).

**Agent prompt**
> Implement read-only Gamma + CLOB connectors and normalize to canonical snapshots. Store raw payloads and normalized snapshots in the ledger for replay.

---

### Phase 2 — Candidate generator (quant-first, heuristic)
**Deliverables**
- `agents/research/features.py`: compute `FeatureVector` from snapshots.
- `agents/research/candidates.py`: rank markets by research value and liquidity quality.
- CLI: `candidates` prints a table of top markets + key metrics/flags.

**Acceptance criteria**
- Candidate list is stable and explainable (each candidate shows why it ranked).
- Clear down-ranking for ambiguous/illiquid markets.

**Agent prompt**
> Build a heuristic candidate ranker with a small feature vector (spread, depth, time-to-resolution, movement if history exists, quality flags). Provide an explainable score breakdown.

---

### Phase 3 — Trade Brief builder + renderer
**Deliverables**
- `agents/research/brief_builder.py`: create a `TradeBrief` for a market_id.
- `agents/research/render.py`: render a brief to Markdown for human review.
- CLI: `brief <market_id>` generates/stores a brief + prints the markdown path.

**Acceptance criteria**
- The brief contains market rules text and a clear summary of microstructure + key flags.
- The markdown render is readable and consistent (good for reviewing diffs over time).

**Agent prompt**
> Implement TradeBrief builder that attaches snapshots, features, and an initial fair-value placeholder with uncertainty notes. Add a markdown renderer for human review.

---

### Phase 4 — LLM committee (contract-first, grounded)
**Deliverables**
- `agents/committee/roles.py` and prompt templates.
- `agents/committee/review_runner.py`: run role reviews → `Review`s.
- `agents/committee/consensus.py`: reduce to `Recommendation`.
- CLI: `review <brief_id>` stores reviews + recommendation.

**Acceptance criteria**
- Review outputs are valid `Review` objects (schema-validated).
- Reviews contain citations to brief fields (enforced).
- Consensus output is deterministic given the set of reviews.

**Agent prompt**
> Add committee review runner with 5 roles and strict schema validation + citation enforcement. Implement a simple consensus reducer with a risk veto.

---

### Phase 5 — Risk + sizing → OrderIntents (still no live trading)
**Deliverables**
- `agents/risk/limits.py`, `agents/risk/checks.py`, `agents/risk/sizing.py`.
- Convert `Recommendation` → bounded `OrderIntent`s.
- CLI: `recommend <brief_id>` prints intents and stores them.

**Acceptance criteria**
- Hard liquidity and ambiguity gates prevent unsafe suggestions.
- Sizing outputs a range (min/max) with rationale and slippage bounds.

**Agent prompt**
> Implement deterministic risk checks and bounded sizing that converts recommendations into OrderIntents with min/max size and max slippage. No execution yet.

---

### Phase 6 — Paper broker + replay + evaluation
**Deliverables**
- `agents/execution/broker_polymarket.py` paper mode (fill model).
- `agents/ledger/metrics.py`: calibration + slippage error + attribution basics.
- CLI: `paper-run <intent_id>` and `report`.

**Acceptance criteria**
- End-to-end loop runs: candidate → brief → committee → intent → paper fill → report.
- Replay produces the same brief/features when using stored snapshots.

**Agent prompt**
> Add a paper broker and evaluation metrics. Ensure every run is replayable from ledger inputs. Provide a simple report command for calibration and reviewer performance.

---

### Phase 7 — Live execution behind approval gate (later)
**Deliverables**
- `agents/execution/approval.py`: interactive approval gate (confirm/edit within bounds).
- `agents/execution/broker_polymarket.py`: live mode (key isolation, idempotency, retries).
- `agents/execution/reconciliation.py`: reconcile open orders/fills into the ledger.
- CLI: `approve <intent_id>` places a live order only after explicit confirmation.

**Acceptance criteria**
- Orders are never placed without an approval step (config-enforced).
- Idempotency keys prevent accidental double-submits.
- A reconciliation command can recover state after restarts.

**Agent prompt**
> Add a live execution path behind a strict approval gate, with idempotency keys and reconciliation into the ledger. Keep paper and live brokers behind the same interface.

---

## Migration strategy from the current repo

Keep the existing code working while migrating incrementally:

- **Step 1**: Introduce `agents/domain/` models and adapt current logic to emit/consume them.
- **Step 2**: Wrap existing Gamma/CLOB logic behind `agents/connectors/` without changing behavior.
- **Step 3**: Move ad-hoc prompting logic into `committee/` with schema-validated outputs.
- **Step 4**: Route all trade suggestions through `risk/` and `execution/approval.py`.

This avoids a “big bang” rewrite and ensures each phase yields a usable tool.
