# QuoteCopilot Architecture Design

**Date:** 2026-06-17
**Status:** Approved

## Overview

QuoteCopilot is a multi-agent insurance underwriting review system for HO3 homeowner submissions. It converts a raw quote application into a cited `ACCEPT`, `REFER`, or `DECLINE` decision packet using a LangGraph hierarchical subgraph pipeline, hybrid RAG retrieval, deterministic underwriting rules, and human-in-the-loop review via a FastAPI backend and Streamlit frontend.

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Agent orchestration | LangGraph hierarchical subgraphs | Demonstrates graph composition, nested state, and multi-level interrupt handling |
| LLM assignment | Multiple / switchable via `llm/factory.py` | Cheaper models for routing, stronger models for assessment and packaging |
| Retrieval | Hybrid BM25 + semantic + RRF + cross-encoder re-ranking | Exact rule term matching + paraphrase coverage; fully local |
| State persistence | SqliteSaver (checkpoints) + separate SQLite (business data) | Clean separation between LangGraph internals and domain schema |
| Demo surface | Streamlit → FastAPI (HTTP) | API is independently testable; Streamlit is a pure rendering layer |

---

## 1. Project Structure

```
QuoteCopilot/
├── app/
│   ├── api/
│   │   ├── main.py             # App factory, router registration
│   │   ├── routes/
│   │   │   ├── quotes.py       # POST /quote/ho3, /quote/run
│   │   │   ├── runs.py         # GET /runs, /runs/{id}, /runs/{id}/audit
│   │   │   ├── answers.py      # POST /runs/{id}/answers
│   │   │   └── reviews.py      # GET+POST /reviews/*
│   │   └── deps.py             # Shared FastAPI dependencies (DB, graph runner)
│   ├── graph/
│   │   ├── state.py            # RunState TypedDict (shared schema)
│   │   ├── orchestrator.py     # Parent StateGraph composing 4 subgraphs
│   │   ├── subgraphs/
│   │   │   ├── intake.py       # Normalizer → Router → interrupt
│   │   │   ├── enrichment.py   # Enrichment → Retrieval → interrupt
│   │   │   ├── assessment.py   # Assessor → Verifier → Rating
│   │   │   └── packaging.py    # Packager → Critic → Review routing
│   │   └── runner.py           # Graph invocation, resume, checkpoint wiring
│   ├── agents/
│   │   ├── normalizer.py
│   │   ├── router.py
│   │   ├── enrichment.py
│   │   ├── retrieval.py
│   │   ├── assessor.py
│   │   ├── verifier.py
│   │   ├── packager.py
│   │   └── critic.py
│   ├── tools/
│   │   ├── rating.py           # Deterministic premium indication calculator
│   │   ├── rules.py            # Deterministic HO3 eligibility rule engine
│   │   └── rag.py              # Hybrid retrieval (BM25 + semantic + RRF + re-rank)
│   ├── models/
│   │   ├── submission.py       # HO3CanonicalSubmission, LegacyQuotePayload
│   │   ├── decision.py         # DecisionPacket, ReasonCode, Citation
│   │   └── review.py           # ReviewTask, ReviewAction
│   ├── db/
│   │   ├── connection.py       # SQLite connection + migrations
│   │   └── schema.sql          # runs, audit_events, decision_packets, review_tasks
│   └── llm/
│       └── factory.py          # Returns correct LLM client by agent role
├── corpus/                     # Synthetic guideline markdown files
├── streamlit_app.py            # Streamlit UI (calls FastAPI via httpx)
├── evals/
│   ├── dataset.json            # Labeled synthetic cases
│   └── run_evals.py            # Decision accuracy, recall, faithfulness scoring
└── tests/
    ├── unit/                   # Rules engine, rating tool, state schema
    └── integration/            # Full graph runs against synthetic cases
```

**Structural invariants:**
- `graph/` and `agents/` are separate — LangGraph wiring is never mixed into agent logic, so agents are testable without a graph runner.
- `llm/factory.py` is the single place where model selection happens.
- `tools/` contains only deterministic code — no LLM calls, ensuring rules cannot be overridden by model output.

---

## 2. LangGraph Graph Architecture

### Shared State Schema

One `RunState` TypedDict flows through the parent graph and all subgraphs. Subgraphs read from and write back to the same schema — no mapping layer needed. `thread_id` maps 1:1 to `run_id`.

```python
class RunState(TypedDict):
    run_id: str
    quote_id: str
    status: str                  # processing|waiting_for_info|pending_review|completed|failed
    current_node: str
    submission_raw: dict
    submission_canonical: dict
    missing_info: list[str]
    required_questions: list[dict]
    additional_answers: dict
    enrichment: dict             # property_profile, hazard_profile, retrieval_plan
    retrieval: dict              # chunks, source_metadata, retrieval_metrics
    assessment: dict             # rule_findings, preliminary_decision, reason_codes, confidence
    verification: dict           # grounding_result, review_flags, forced_decision
    rating: dict                 # premium_indication, rating_factors
    decision_packet: dict        # recommendation, confidence, citations, next_steps, review_status
    events: list[dict]           # ordered audit events
```

### Parent Orchestrator

```
START → intake_subgraph → enrichment_subgraph → assessment_subgraph → packaging_subgraph → END
```

Each subgraph is compiled and added as a node. The parent has no conditional edges — all branching lives inside the subgraphs. This keeps the top-level graph readable as a straight sequence of phases.

### Subgraph Internals

**`intake_subgraph`**
```
normalize → route → [conditional]
  status == waiting_for_info       → interrupt_before(normalize)  # resumes on /answers
  status == hard_decline_candidate → END (proceeds to enrichment+assessment to confirm)
  else                             → END (proceed to enrichment)
```

**`enrichment_subgraph`**
```
enrich → [conditional]
  contextual_gaps → interrupt_before(enrich)  # wildfire mitigation follow-up
  else            → retrieve → END
```

**`assessment_subgraph`**
```
assess → verify → rate → END
# No interrupts — fully autonomous; verify sets review_flags if grounding insufficient
```

**`packaging_subgraph`**

`CRITIC_ENABLED` is a boolean env var (default `false`). It is not a state field — it is read once at graph compile time and baked into the conditional edge as a static branch.

```
package → [conditional]
  CRITIC_ENABLED=true → critic → [conditional]
    critique_passed → route_decision
    retry_budget_remaining → package   # retry loop, capped at 2
    else → route_decision (with review flag)
  CRITIC_ENABLED=false → route_decision

route_decision → [conditional]
  review_needed → create_review_task → END
  else          → END
```

### Checkpointing and Resume

`SqliteSaver` attaches to the parent orchestrator at compile time. On `POST /runs/{run_id}/answers`, the runner calls:

```python
graph.invoke(
    {"additional_answers": answers},
    config={"configurable": {"thread_id": run_id}}
)
```

LangGraph replays from the last checkpoint with answers merged into state. No custom resume logic needed.

### LLM Assignment

| Agent | Model | Reason |
|---|---|---|
| Normalizer, Router | claude-haiku-4-5 / gpt-4o-mini | Fast, cheap, structured output |
| Enrichment, Retrieval | claude-haiku-4-5 / gpt-4o-mini | Deterministic-heavy, LLM assist is light |
| Assessor, Verifier | claude-sonnet-4-6 / gpt-4o | Governed reasoning, needs reliability |
| Packager, Critic | claude-sonnet-4-6 / gpt-4o | Rationale quality matters |

`AGENT_MODEL_MAP` env var overrides defaults per role without code changes.

---

## 3. Retrieval Pipeline

### Corpus Ingestion (offline)

Synthetic guideline markdown files in `corpus/` are chunked at ~400 tokens with 50-token overlap, preserving section headers as metadata. Each chunk stores: `chunk_id`, `doc_id`, `section`, `text`, `source_file`.

Two indexes built from the same chunks:
- **BM25 index** — `rank_bm25`, serialized to disk. Catches exact rule terms.
- **Semantic index** — `sentence-transformers` embeddings stored in ChromaDB. Catches paraphrases.

### Retrieval Agent Flow

The Enrichment agent produces a **retrieval plan** — a structured list of query intents:

```json
{
  "queries": [
    {"intent": "wildfire band eligibility", "keywords": ["wildfire", "band A", "mitigation"]},
    {"intent": "roof age referral threshold", "keywords": ["roof age", "refer", "years"]},
    {"intent": "occupancy eligibility", "keywords": ["occupancy", "rental", "eligible"]}
  ]
}
```

For each query intent, `tools/rag.py` runs:
1. BM25 retrieval → top-10 by BM25 score
2. Semantic retrieval → top-10 by cosine similarity
3. Reciprocal Rank Fusion (RRF) to merge both lists
4. Cross-encoder re-ranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`) → return top-5

The Retrieval agent deduplicates by `chunk_id` across intents and writes the final set into `RunState.retrieval`.

### Citation Traceability

The Verifier checks that every `chunk_id` cited in the decision packet exists in `RunState.retrieval.chunks`. Any citation not in the retrieved set triggers a grounding failure and forces the review route.

---

## 4. Persistence Layer

### Two SQLite Databases

- `checkpoints.db` — owned by LangGraph's `SqliteSaver`. Never queried directly by application code.
- `quotecopilot.db` — owned by the application. All business reads and writes go here.

### `quotecopilot.db` Schema

```sql
CREATE TABLE runs (
    run_id        TEXT PRIMARY KEY,
    quote_id      TEXT NOT NULL,
    status        TEXT NOT NULL,
    current_node  TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE TABLE decision_packets (
    run_id             TEXT PRIMARY KEY REFERENCES runs(run_id),
    recommendation     TEXT NOT NULL,
    confidence         REAL,
    reason_codes       TEXT,   -- JSON array
    citations          TEXT,   -- JSON array of {chunk_id, source, text}
    facts_used         TEXT,   -- JSON
    premium_indication REAL,
    next_steps         TEXT,
    created_at         TEXT NOT NULL
);

CREATE TABLE audit_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL REFERENCES runs(run_id),
    node       TEXT NOT NULL,
    event_type TEXT NOT NULL,   -- started|completed|paused|resumed|failed
    payload    TEXT,            -- JSON snapshot of relevant state slice
    created_at TEXT NOT NULL
);

CREATE TABLE review_tasks (
    run_id        TEXT PRIMARY KEY REFERENCES runs(run_id),
    status        TEXT NOT NULL,   -- pending|approved|rejected|info_requested|closed
    priority      TEXT NOT NULL,   -- high|medium|low
    trigger       TEXT NOT NULL,   -- missing_info|refer|decline|verification_failure
    review_packet TEXT,            -- JSON
    reviewer_note TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
```

### Write Discipline

Agents return updated `RunState` only. The graph runner writes audit events and syncs run status to `quotecopilot.db` as a post-node step. Agents are pure functions — persistence is a side effect of the runner, not the agent.

---

## 5. FastAPI + Streamlit Surface

### FastAPI Endpoints

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/health` | Service readiness |
| `POST` | `/quote/ho3` | Start canonical HO3 run; return `{run_id, status}` immediately; client polls |
| `POST` | `/quote/run` | Start legacy quote run |
| `GET` | `/runs` | List recent runs |
| `GET` | `/runs/{run_id}` | Run state + decision packet |
| `GET` | `/runs/{run_id}/audit` | Node-by-node audit events |
| `POST` | `/runs/{run_id}/answers` | Resume paused run with missing-info answers |
| `GET` | `/reviews/pending` | List open review tasks |
| `GET` | `/reviews/{run_id}` | Full review packet |
| `POST` | `/reviews/{run_id}/actions` | `approve|reject|request_info|close` with optional note |

**Graph interrupt handling:** When the graph pauses at an `interrupt_before` node, the runner catches `GraphInterrupt`, writes `status=waiting_for_info` and `required_questions` to the DB, and returns `{run_id, status: "waiting_for_info"}`.

**Error shapes:** `{error: str, field_errors: [...]}` for validation failures; `{error: str, run_id: str}` for run-level failures.

### Streamlit Pages

| Page | Purpose |
|---|---|
| **Submit Quote** | Paste JSON or pick a demo scenario → POST to `/quote/ho3` → poll status → render decision packet with citations and reason codes |
| **Answer Questions** | Shows `required_questions` for a paused run → submit answers → POST to `/runs/{id}/answers` |
| **Review Queue** | Lists pending review tasks → click into a task → approve / request info / close |
| **Audit Trail** | Select a run → node-by-node audit events rendered as a timeline |

The Submit Quote page preloads four demo scenario buttons. No business logic lives in `streamlit_app.py` — it is a pure rendering and `httpx` client layer.

---

## 6. Evaluation Design

### Dataset Structure (`evals/dataset.json`)

```json
{
  "case_id": "accept_001",
  "scenario": "straight_through_accept",
  "input": { },
  "expected": {
    "recommendation": "ACCEPT",
    "reason_codes": ["RC-001", "RC-007"],
    "missing_info_fields": [],
    "review_required": false
  }
}
```

Dataset covers: accept, refer, decline, missing roof age, missing occupancy, wildfire evidence required, flood-risk referral, liability referral, claims-history referral, invalid payload.

### Metrics

| Metric | How measured | Target |
|---|---|---|
| Decision accuracy | `recommendation == expected.recommendation` | ≥ 95% |
| Reason-code exact match | Set equality of `reason_codes` vs expected | ≥ 90% |
| Retrieval recall@5 | Expected `chunk_ids` present in top-5 retrieved | ≥ 90% |
| Citation faithfulness | Every cited `chunk_id` exists in `RunState.retrieval.chunks` | 100% |
| Missing-info detection | `missing_info_fields` set match vs expected | ≥ 95% |
| Resume correctness | Same `run_id` completes after answer injection | 100% |

### Output

`evals/results/YYYY-MM-DD.json` with per-case scores. `run_evals.py --report` prints the summary table to stdout for the README.

---

## Human-in-the-Loop Rules

Human review is mandatory when:
- Required intake facts are missing or uncertain
- Contextual wildfire mitigation evidence is required
- Preliminary decision is `REFER` or `DECLINE`
- Verifier blocks or downgrades the decision
- System cannot retrieve relevant evidence
- LLM output is invalid after retry/fallback

---

## Failure Handling

| Failure | Behavior |
|---|---|
| Missing required fields | Pause run, generate questions, preserve checkpoint |
| Invalid payload | Return validation error with field-level details |
| Retrieval returns no chunks | Continue only if deterministic rules support the decision; otherwise route to review |
| LLM structured output fails | Retry, then deterministic fallback wording |
| Critic rejects rationale | Revise if retry budget remains; otherwise route to review |
| Rating input incomplete | Use documented defaults only; otherwise route to review |
| Database write failure | Return failure status, log context for recovery |
