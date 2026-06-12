"""
nebius.py — Nebius Token Factory client.

Nebius Token Factory exposes an OpenAI-compatible API, so we reuse the OpenAI
SDK and just point it at the Nebius base URL with a Nebius API key. Both the
answer generation (rag.py) and the reranking step (reranker.py) route their
model calls through here, satisfying the cohort requirement that at least one
model call go through Nebius Token Factory.

Required env vars:
    NEBIUS_API_KEY            your Nebius Token Factory key
Optional env vars:
    NEBIUS_BASE_URL           default: https://api.studio.nebius.com/v1/
    NEBIUS_GENERATION_MODEL   default: meta-llama/Llama-3.3-70B-Instruct
    NEBIUS_RERANK_MODEL       default: meta-llama/Llama-3.3-70B-Instruct
"""

import os

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.studio.nebius.com/v1/"
DEFAULT_GENERATION_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
DEFAULT_RERANK_MODEL = "meta-llama/Llama-3.3-70B-Instruct"


def get_nebius_client() -> OpenAI:
    """Return an OpenAI-compatible client pointed at Nebius Token Factory."""
    return OpenAI(
        base_url=os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL),
        api_key=os.environ["NEBIUS_API_KEY"],
    )


def generation_model() -> str:
    return os.environ.get("NEBIUS_GENERATION_MODEL", DEFAULT_GENERATION_MODEL)


def rerank_model() -> str:
    return os.environ.get("NEBIUS_RERANK_MODEL", DEFAULT_RERANK_MODEL)
