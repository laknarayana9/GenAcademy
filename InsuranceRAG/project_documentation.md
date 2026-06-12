# Insurance RAG Project Documentation

## Project Overview

This project builds a retrieval-augmented generation application for homeowners insurance underwriting guidelines. It helps underwriters answer HO3/HO5 eligibility, coverage, rating, referral, and endorsement questions from a small guideline corpus through a Python command-line interface.

The system retrieves relevant guideline chunks, reranks the candidate passages, generates a concise cited answer, and refuses when the retrieved context does not support an answer.

## Dataset Used

The corpus lives in `data/guidelines` and contains 5 Markdown guideline documents:

| File | Purpose |
|---|---|
| `uw_guidelines_homeowners.md` | HO3/HO5 eligibility, decline, referral, protection class, wiring, occupancy, and loss rules |
| `hazards_guidance.md` | Wildfire, flood, wind/hail, and earthquake guidance |
| `endorsements_manual.md` | Water backup, flood acknowledgement, wildfire deductible, ordinance/law, and scheduled property endorsements |
| `rating_rules.md` | Base premium formula, surcharge rules, deductible factors, and rating adjustments |
| `uw_workflow_playbook.md` | Minimum required fields, missing-information workflow, evidence policy, and decision flow |

The evaluation set is `data/eval_questions.json`, with 15 answerable questions and 3 deliberately unanswerable questions.

## RAG Design

The pipeline compares two chunking strategies:

| Strategy | Description |
|---|---|
| `fixed` | Recursive 512-character chunks with 50-character overlap |
| `paragraph` | Markdown paragraph/section chunks split on blank lines |

Retrieval is hybrid:

| Layer | Implementation |
|---|---|
| Dense retrieval | OpenAI `text-embedding-3-small` embeddings stored in Pinecone |
| Sparse retrieval | Local BM25 over the same chunking strategy |
| Fusion | Reciprocal Rank Fusion |
| Reranking | Nebius-hosted LLM relevance scoring |
| Generation | Nebius `meta-llama/Llama-3.3-70B-Instruct` |
| Fallback | Refuse when the top rerank score is below `MIN_RELEVANCE_SCORE` |

## Evaluation Summary

The latest run generated `comparison_report.md`.

| Metric | Result |
|---|---:|
| Paragraph recall@5, rerank off | 100% |
| Paragraph recall@5, rerank on | 100% |
| Fixed recall@5, rerank off | 100% |
| Fixed recall@5, rerank on | 100% |
| End-to-end answer relevance | 15/15 |
| End-to-end source recall | 15/15 |
| Refusal correctness | 3/3 |

The report also includes detailed answers, retrieved sources, top reranker scores, and pass/fail marks for each question.

## Prompts Used During AI Coding

Representative prompts used while building and testing the project:

| Prompt | Purpose |
|---|---|
| Build a code-heavy RAG pipeline for insurance underwriting guidelines using LangChain, Pinecone, hybrid retrieval, reranking, citations, and a refusal path. | Initial architecture and implementation direction |
| Add two chunking strategies and compare fixed-size chunks against paragraph/section chunks on the same evaluation questions. | Chunking comparison requirement |
| Use Nebius Token Factory for at least one model call, preferably generation and reranking. | Cohort requirement compliance |
| Create an evaluation script with 15 answerable questions and unanswerable edge cases, then generate a comparison report. | Evaluation deliverable |
| Test the full stack with Pinecone, OpenAI embeddings, Nebius generation, and Nebius reranking. | Final integration verification |

## Iterations Tried

| Iteration | Outcome |
|---|---|
| Dense-only retrieval design | Replaced with hybrid BM25 + dense retrieval to catch exact terms such as endorsement codes, section references, and underwriting triggers. |
| Single chunking strategy | Expanded to fixed and paragraph chunking so retrieval quality could be compared directly. |
| RRF-only ordering | Added Nebius LLM reranking to score candidate passages against each question. |
| Answer-only generation | Added explicit source citations and a relevance-threshold refusal path. |
| Initial Pinecone configuration | Corrected to use a standard dense vector index named `insurance-rag`, with separate namespaces for `fixed` and `paragraph`. |

## Learnings and Observations

Hybrid retrieval performed well on this corpus because underwriting questions mix semantic intent with exact terms like `ORD-01`, `WBK-01`, `SFHA`, deductible factors, and decline/referral triggers.

Paragraph-based chunks were easier to inspect and cite because they preserved section-level context. Fixed chunks also performed well on the evaluation set, but paragraph chunks are the preferred default for this corpus because the source documents are already organized into compact policy sections.

The refusal path is important. The system correctly refused questions about whole-life cash surrender value, auto collision claims, and CEO contact details because those facts are outside the homeowners underwriting guideline corpus.

## Submission Notes

For submission, include:

- GitHub repository or zip file containing this codebase.
- `comparison_report.md` as the evaluation/comparison report.
- This `project_documentation.md` file, or copy its contents into the required Google Doc.
- A demo recording of 5 minutes or less.
