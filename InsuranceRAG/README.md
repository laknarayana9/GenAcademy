# Insurance RAG — Gen Academy Week 2 Project

> **One-liner:** My RAG app helps underwriters answer HO3 coverage, eligibility, rating, and referral questions from 5 HO3/HO5 underwriting guideline documents in a Python CLI with 95%+ answer relevance, 95%+ source recall, and sub-15-second single-question latency.

## What this is

A RAG pipeline over real HO3/HO5 insurance underwriting guidelines. Ask any coverage or eligibility question and get a grounded, cited answer backed by the actual policy documents.

Built for Gen Academy Week 2 — Track 2 (LangChain + Pinecone, code-heavy).

**Project type:** Project 2 — Financial / Regulated Document Intelligence  
**Retrieval pattern:** Hybrid (BM25 + dense) → Reciprocal Rank Fusion → **LLM reranking**  
**Chunking:** Fixed-size vs. paragraph-based — both indexed, recall compared in `comparison_report.md`  
**Models:** OpenAI embeddings (1536-dim) + **Nebius Token Factory** for generation *and* reranking

---

## Architecture

```
data/guidelines/*.md
       |
       v
  chunking.py ──── fixed / paragraph (shared by ingest + retriever)
       |
  ingest.py  ──── OpenAI text-embedding-3-small
             └──── Pinecone (namespace per strategy)
                            |
                    retriever.py  ──── dense (Pinecone)
                                  ──── sparse (BM25, per-strategy)
                                  ──── RRF merge → candidate pool
                                  ──── reranker.py (Nebius LLM) → top-5
                                            |
                                   rag.py  ──── Nebius (Llama-3.3-70B) generation
                                           ──── cited answer
                                           ──── "I don't know" when top
                                                relevance < threshold
                                                    |
                                          eval.py  ──── chunking × rerank matrix
                                                   ──── + unanswerable questions
                                                   ──── comparison_report.md
```

---

## Corpus

5 synthetic HO3/HO5 insurance guideline documents:

| File | Contents |
|---|---|
| `uw_guidelines_homeowners.md` | Eligibility, declines, referrals, loss history |
| `hazards_guidance.md` | Wildfire, flood, wind/hail signals and actions |
| `endorsements_manual.md` | Water backup, flood, wildfire deductible, ORD-01, SPP-01 |
| `rating_rules.md` | Base premium formula, surcharges, deductible factors |
| `uw_workflow_playbook.md` | Triage workflow, missing-info loop, evidence policy |

---

## RAG Framework

| Field | Decision |
|---|---|
| Use case | Underwriters ask HO3/HO5 homeowners eligibility, coverage, rating, referral, and endorsement questions through a Python CLI. The assistant returns concise answers grounded only in retrieved guideline excerpts. |
| Corpus | 5 Markdown insurance guideline documents owned by the demo underwriting knowledge base: eligibility guidelines, hazard guidance, endorsements manual, rating rules, and workflow playbook. |
| Ingestion + cleaning | Markdown files are loaded from `data/guidelines`; section text and filenames are preserved as metadata, with chunking performed consistently across ingestion and BM25 retrieval. |
| Ingestion + freshness | The demo corpus is manually refreshed by updating Markdown files and rerunning `python ingest.py`; a production version would rerun ingestion whenever source guidelines change. |
| Chunking + embedding | Two strategies are compared: fixed-size 512-character chunks with overlap and paragraph/section-based chunks. Dense embeddings use OpenAI `text-embedding-3-small` with 1536 dimensions. |
| Retrieve | Pinecone stores dense vectors in separate namespaces per chunking strategy. Retrieval combines Pinecone dense search and local BM25 sparse search with Reciprocal Rank Fusion, then optionally reranks with Nebius. |
| Generation + fallback | Nebius `meta-llama/Llama-3.3-70B-Instruct` generates cited answers. If the best reranked passage is below the relevance threshold, the system refuses instead of hallucinating. |
| Evaluation target | Target is 95%+ source recall and answer relevance on answerable questions, plus correct refusal on out-of-corpus questions. The latest `comparison_report.md` run achieved 100% on all three. |

---

## Setup

### 1. Prerequisites
- Python 3.12+
- [Pinecone account](https://app.pinecone.io) — free tier is sufficient
- OpenAI API key (embeddings)
- [Nebius Token Factory](https://studio.nebius.com) API key (generation + reranking)

### 2. Create a Pinecone index
In the Pinecone console, create an index with:
- **Dimensions:** 1536
- **Metric:** cosine
- **Name:** `insurance-rag` (or your own — update `.env`)

### 3. Install dependencies
```bash
pip install -e .
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your keys
```

---

## Usage

### Step 1 — Ingest guidelines
```bash
# Ingest with both chunking strategies (recommended)
python ingest.py

# Ingest with one strategy only
python ingest.py --strategy fixed
python ingest.py --strategy paragraph

# Preview chunk counts without upserting
python ingest.py --verify
```

### Step 2 — Ask a question
```bash
python rag.py "Is a property with knob-and-tube wiring eligible for HO3?"
python rag.py "What wildfire score triggers a decline?"
python rag.py "What endorsement is recommended for a property with a basement?"
```

**Sample output:**
```
Question: Is a property with knob-and-tube wiring eligible for HO3?

Answer:
No. Per the HO3 guidelines, a property with knob-and-tube wiring that has not
been remediated MUST BE DECLINED [uw_guidelines_homeowners.md §1.2].

Sources:
  - uw_guidelines_homeowners.md
  - hazards_guidance.md
```

### Step 3 — Run evaluation
```bash
python eval.py
# Produces comparison_report.md
```

You can also inspect a single retrieval with and without reranking:
```bash
python retriever.py "What roof age triggers a referral?"
python retriever.py --no-rerank "What roof age triggers a referral?"
```

### Optional — Web UI (Streamlit)
A chat UI over the same pipeline, handy for demos:
```bash
streamlit run app.py
```
Shows the cited answer, the retrieved chunks with their rerank relevance scores,
and the refusal state. The sidebar toggles chunking strategy (paragraph/fixed)
and reranking on/off. Requires the index to be populated first (`python ingest.py`).

---

## Evaluation

`eval.py` produces **`comparison_report.md`** with three parts:

1. **Retrieval quality matrix** — recall@5 for every *(chunking strategy × rerank on/off)* combination. This is both the **chunking-strategy comparison** and the **reranking-impact analysis**.
2. **End-to-end answers** — full pipeline (Nebius generation) on the best config, scoring answer relevance (keyword match) on the 15 answerable questions.
3. **Refusal path** — 3 deliberately unanswerable / out-of-corpus questions; the run is correct only if the system refuses ("I don't know") rather than hallucinating. Refusal fires when the reranker's top relevance score falls below `MIN_RELEVANCE_SCORE`.

---

## Key Design Decisions

| Decision | Choice | Why |
|---|---|---|
| Chunking | Fixed-size + paragraph (shared by dense & BM25) | Compare boundary preservation vs. uniform size, apples-to-apples |
| Retrieval | Hybrid BM25 + dense + RRF | BM25 catches exact terms (section numbers, codes); dense catches semantic intent |
| Reranking | LLM reranker over fused pool (Nebius) | RRF only knows rank position; the reranker reads the query against each passage and scores relevance 0–10 |
| Vector DB | Pinecone (namespaced per strategy) | Simple, hosted, no local setup |
| Generation | Nebius `Llama-3.3-70B-Instruct`, temp=0 | Required Nebius Token Factory call; deterministic graded answers |
| Fallback | Refuse when top rerank score < threshold | Real "I don't know" signal — never hallucinate on missing evidence |

---

## Project Structure

```
InsuranceRAG/
├── data/
│   ├── guidelines/          # 5 .md insurance guideline documents
│   └── eval_questions.json  # 15 answerable + 3 unanswerable questions
├── chunking.py              # Shared chunking strategies (fixed / paragraph)
├── nebius.py                # Nebius Token Factory client factory
├── ingest.py                # Chunk + embed + upsert to Pinecone
├── retriever.py             # Hybrid BM25 + dense + RRF (+ optional rerank)
├── reranker.py              # LLM reranker via Nebius + refusal threshold
├── rag.py                   # Full Q&A pipeline with citations and fallback
├── app.py                   # Streamlit chat UI over the pipeline
├── eval.py                  # Chunking × rerank matrix → comparison_report.md
├── .env.example             # Environment variable template
├── pyproject.toml           # Dependencies
└── README.md
```
