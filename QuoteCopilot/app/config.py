"""Central configuration for QuoteCopilot.

All runtime settings load from environment variables (optionally via a local
.env file). This is the single source of truth for paths, model selection, and
feature flags; no other module should read os.environ directly.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Strongly typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM provider + model selection ---
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    nebius_api_key: str | None = None
    # Nebius Token Factory / AI Studio exposes an OpenAI-compatible endpoint.
    nebius_base_url: str = "https://api.studio.nebius.com/v1"
    fast_model: str = "claude-haiku-4-5"
    strong_model: str = "claude-sonnet-4-6"
    agent_model_map: dict[str, str] = {}

    # --- Packaging critic loop ---
    critic_enabled: bool = False
    critic_retry_budget: int = 2

    # --- Storage paths ---
    business_db_path: Path = PROJECT_ROOT / "data" / "quotecopilot.db"
    checkpoint_db_path: Path = PROJECT_ROOT / "data" / "checkpoints.db"
    chroma_dir: Path = PROJECT_ROOT / "data" / "chroma"
    bm25_index_path: Path = PROJECT_ROOT / "data" / "bm25_index.pkl"
    corpus_dir: Path = PROJECT_ROOT / "corpus"

    # --- Retrieval tuning ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieval_top_k: int = 5

    # --- API client ---
    api_base_url: str = "http://localhost:8000"

    @field_validator("agent_model_map", mode="before")
    @classmethod
    def _parse_model_map(cls, value: object) -> object:
        """Allow AGENT_MODEL_MAP to be supplied as a JSON string."""
        if value in (None, ""):
            return {}
        if isinstance(value, str):
            return json.loads(value)
        return value

    def ensure_data_dirs(self) -> None:
        """Create on-disk directories required for persistence and indexes."""
        for path in (
            self.business_db_path.parent,
            self.checkpoint_db_path.parent,
            self.chroma_dir,
            self.bm25_index_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance for the process lifetime."""
    return Settings()
