"""Single source of truth for LLM model selection.

`llm/factory.py` is the only place model selection happens. Each agent role maps
to a tier (fast vs strong) and an optional explicit override from
`AGENT_MODEL_MAP`. LLM usage is always optional: when no provider key is
configured (or the client library is unavailable), helpers fall back to
deterministic wording so the whole system remains runnable and testable offline.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings

# Sensible Nebius Token Factory defaults when the configured model names still
# point at the Anthropic defaults (so Nebius works out of the box).
NEBIUS_DEFAULT_FAST = "Qwen/Qwen3-30B-A3B-Instruct-2507"
NEBIUS_DEFAULT_STRONG = "meta-llama/Llama-3.3-70B-Instruct"

# Role -> default tier. Fast for routing/enrichment, strong for reasoning/wording.
ROLE_TIER = {
    "normalizer": "fast",
    "router": "fast",
    "enrichment": "fast",
    "retrieval": "fast",
    "assessor": "strong",
    "verifier": "strong",
    "packager": "strong",
    "critic": "strong",
}


def model_for_role(role: str) -> str:
    """Resolve the model name for an agent role."""
    settings = get_settings()
    tier = ROLE_TIER.get(role, "fast")
    if role in settings.agent_model_map:
        model = settings.agent_model_map[role]
    else:
        model = settings.fast_model if tier == "fast" else settings.strong_model
    # If running on Nebius but the resolved model still points at an Anthropic
    # model (tier default or AGENT_MODEL_MAP override), substitute a
    # Nebius-hosted model so the provider works without extra config.
    if settings.llm_provider == "nebius" and model.startswith("claude"):
        return NEBIUS_DEFAULT_FAST if tier == "fast" else NEBIUS_DEFAULT_STRONG
    return model


def _provider_key_present(settings) -> bool:
    if settings.llm_provider == "anthropic":
        return bool(settings.anthropic_api_key)
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key)
    if settings.llm_provider == "nebius":
        return bool(settings.nebius_api_key)
    return False


def llm_available() -> bool:
    """True only if a provider key is configured and the client imports."""
    settings = get_settings()
    if not _provider_key_present(settings):
        return False
    try:
        _build_client(role="router")
        return True
    except Exception:  # noqa: BLE001
        return False


@lru_cache(maxsize=8)
def _build_client(role: str):
    """Construct (and cache) a LangChain chat model for the role."""
    settings = get_settings()
    model = model_for_role(role)
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=0,
            max_tokens=1024,
        )
    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=settings.openai_api_key,
            temperature=0,
            max_tokens=1024,
        )
    if settings.llm_provider == "nebius":
        # Nebius Token Factory is OpenAI-compatible: reuse ChatOpenAI with the
        # Nebius base_url and Nebius API key.
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=settings.nebius_api_key,
            base_url=settings.nebius_base_url,
            temperature=0,
            max_tokens=1024,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


def get_llm(role: str):
    """Return a chat model for the role, or None when unavailable."""
    if not llm_available():
        return None
    try:
        return _build_client(role)
    except Exception:  # noqa: BLE001
        return None


def complete_text(role: str, system: str, user: str, fallback: str) -> str:
    """Generate text for a role, returning ``fallback`` if the LLM is unusable.

    This is the guardrailed entry point agents use for narrative wording. It
    never raises on LLM failure — it logs nothing and returns the deterministic
    fallback so decisions remain reproducible.
    """
    llm = get_llm(role)
    if llm is None:
        return fallback
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        response = llm.invoke(
            [SystemMessage(content=system), HumanMessage(content=user)]
        )
        text = getattr(response, "content", "")
        if isinstance(text, list):  # some providers return content blocks
            text = " ".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in text
            )
        text = (text or "").strip()
        return text or fallback
    except Exception:  # noqa: BLE001
        return fallback
