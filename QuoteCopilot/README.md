# QuoteCopilot

A multi-agent insurance underwriting review system for **HO3 homeowner submissions**.
QuoteCopilot turns a raw quote application into a cited `ACCEPT`, `REFER`, or
`DECLINE` decision packet using a LangGraph hierarchical subgraph pipeline,
hybrid RAG retrieval, deterministic underwriting rules, and human-in-the-loop
review.

## Architecture

See [`docs/superpowers/specs/2026-06-17-quoteCopilot-architecture-design.md`](docs/superpowers/specs/2026-06-17-quoteCopilot-architecture-design.md)
for the full design. High level:

- **FastAPI** backend exposing quote intake, run polling, answer resume, and review endpoints.
- **LangGraph** orchestrator composing four subgraphs: intake -> enrichment -> assessment -> packaging.
- **Hybrid retrieval** (BM25 + semantic + RRF + cross-encoder re-rank) over a synthetic guideline corpus.
- **Two SQLite stores**: LangGraph checkpoints (`checkpoints.db`) and business data (`quotecopilot.db`).
- **Streamlit** frontend as a pure rendering + `httpx` client layer.

## Project layout

```
app/        # api, graph, agents, tools, models, db, llm
corpus/     # synthetic HO3 guideline markdown
evals/      # labeled cases + scoring
tests/      # unit + integration
streamlit_app.py
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY or OPENAI_API_KEY and LLM_PROVIDER
```

> **API keys:** QuoteCopilot calls a hosted LLM provider. Set the key for your
> chosen provider in `.env`. Never commit `.env`.

## Running (available after later phases)

```bash
# 1. Build retrieval indexes from the corpus
python scripts/ingest_corpus.py

# 2. Start the API
uvicorn app.api.main:app --reload

# 3. Start the UI
streamlit run streamlit_app.py
```

## Tests

```bash
pytest
```

## Status

Built in phases. Used superpowers (claude code) framework to build this.