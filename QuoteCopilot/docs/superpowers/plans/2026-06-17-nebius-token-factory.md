# Nebius Token Factory LLM Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Nebius Token Factory as a third LLM provider option so that any agent role can route its LLM call through Nebius's OpenAI-compatible API endpoint.

**Architecture:** Nebius exposes an OpenAI-compatible REST API, so `langchain-openai`'s `ChatOpenAI` is reused with a custom `base_url` and `NEBIUS_API_KEY`. The only files that change are `app/config.py` (two new settings) and `app/llm/factory.py` (one new provider branch). All agents that call `complete_text()` or `get_llm()` automatically pick up Nebius when `LLM_PROVIDER=nebius`.

**Tech Stack:** Python 3.13, `langchain-openai` (already installed), `pydantic-settings`, `pytest`

## Global Constraints

- Do not break the existing `anthropic` and `openai` provider paths.
- `langchain-openai` is already in `requirements.txt`; do not add new packages.
- All new settings must have safe defaults so existing `.env` files continue to work unchanged.
- The Nebius base URL default is `https://api.studio.nebius.ai/v1`.
- Tests must be runnable without a real Nebius key (mock the HTTP call).
- Keep `_build_client` LRU-cached; the cache key is `role` only — callers never pass provider explicitly.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `app/config.py` | Modify | Add `nebius_api_key` and `nebius_base_url` fields |
| `app/llm/factory.py` | Modify | Add `"nebius"` branch in `_provider_key_present` and `_build_client` |
| `.env.example` | Modify | Document the two new Nebius env vars |
| `tests/unit/test_factory.py` | Create | Unit tests for all three provider paths |

---

### Task 1: Add Nebius Settings to `app/config.py`

**Files:**
- Modify: `app/config.py`

**Interfaces:**
- Produces: `Settings.nebius_api_key: str | None` and `Settings.nebius_base_url: str` — consumed by Task 2

- [ ] **Step 1: Read the current file**

Open `app/config.py` and locate the `# --- LLM provider + model selection ---` block (lines 29–35). Confirm the last field in that block is `agent_model_map`.

- [ ] **Step 2: Write the failing test**

Create `tests/unit/test_factory.py`:

```python
"""Unit tests for app/llm/factory.py — all three provider paths."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _settings(**overrides):
    """Return a minimal Settings-like object."""
    from app.config import Settings
    defaults = dict(
        llm_provider="anthropic",
        anthropic_api_key=None,
        openai_api_key=None,
        nebius_api_key=None,
        nebius_base_url="https://api.studio.nebius.ai/v1",
        fast_model="claude-haiku-4-5",
        strong_model="claude-sonnet-4-6",
        agent_model_map={},
    )
    defaults.update(overrides)
    return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# _provider_key_present
# ---------------------------------------------------------------------------

def test_provider_key_present_anthropic_with_key():
    from app.llm.factory import _provider_key_present
    s = _settings(llm_provider="anthropic", anthropic_api_key="sk-ant-test")
    assert _provider_key_present(s) is True


def test_provider_key_present_anthropic_without_key():
    from app.llm.factory import _provider_key_present
    s = _settings(llm_provider="anthropic", anthropic_api_key=None)
    assert _provider_key_present(s) is False


def test_provider_key_present_openai_with_key():
    from app.llm.factory import _provider_key_present
    s = _settings(llm_provider="openai", openai_api_key="sk-openai-test")
    assert _provider_key_present(s) is True


def test_provider_key_present_nebius_with_key():
    from app.llm.factory import _provider_key_present
    s = _settings(llm_provider="nebius", nebius_api_key="neb-test-key")
    assert _provider_key_present(s) is True


def test_provider_key_present_nebius_without_key():
    from app.llm.factory import _provider_key_present
    s = _settings(llm_provider="nebius", nebius_api_key=None)
    assert _provider_key_present(s) is False
```

- [ ] **Step 3: Run to confirm test fails (nebius fields not on Settings yet)**

```
cd /Users/sumedhtuttagunta/code/GenAcademy/QuoteCopilot
pytest tests/unit/test_factory.py::test_provider_key_present_nebius_with_key -v
```

Expected: `AttributeError` or `FAIL` because `nebius_api_key` does not exist on `Settings`.

- [ ] **Step 4: Add the two Nebius fields to `app/config.py`**

In `app/config.py`, find this block:

```python
    # --- LLM provider + model selection ---
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    fast_model: str = "claude-haiku-4-5"
    strong_model: str = "claude-sonnet-4-6"
    agent_model_map: dict[str, str] = {}
```

Replace it with:

```python
    # --- LLM provider + model selection ---
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    nebius_api_key: str | None = None
    nebius_base_url: str = "https://api.studio.nebius.ai/v1"
    fast_model: str = "claude-haiku-4-5"
    strong_model: str = "claude-sonnet-4-6"
    agent_model_map: dict[str, str] = {}
```

- [ ] **Step 5: Run the settings-related tests to confirm they pass**

```
pytest tests/unit/test_factory.py -v -k "settings or provider_key"
```

Expected: all `test_provider_key_present_*` tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/config.py tests/unit/test_factory.py
git commit -m "feat: add nebius_api_key and nebius_base_url settings"
```

---

### Task 2: Add Nebius Provider Branch to `app/llm/factory.py`

**Files:**
- Modify: `app/llm/factory.py`

**Interfaces:**
- Consumes: `Settings.nebius_api_key: str | None`, `Settings.nebius_base_url: str` (from Task 1)
- Produces: `_build_client(role)` returns `ChatOpenAI` pointed at Nebius when `llm_provider == "nebius"`

- [ ] **Step 1: Write the failing test for `_build_client` Nebius path**

Append to `tests/unit/test_factory.py`:

```python
# ---------------------------------------------------------------------------
# _build_client — Nebius path
# ---------------------------------------------------------------------------

def test_build_client_nebius_uses_openai_with_custom_base_url():
    """_build_client("router") with nebius provider returns ChatOpenAI pointed at Nebius."""
    from app.llm import factory

    nebius_settings = _settings(
        llm_provider="nebius",
        nebius_api_key="neb-fake-key",
        nebius_base_url="https://api.studio.nebius.ai/v1",
        fast_model="mistralai/Mistral-Nemo-Instruct-2407",
    )

    # Clear LRU cache so this test gets a fresh call.
    factory._build_client.cache_clear()

    with patch("app.llm.factory.get_settings", return_value=nebius_settings):
        with patch("langchain_openai.ChatOpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            factory._build_client.cache_clear()
            client = factory._build_client("router")

    mock_openai.assert_called_once_with(
        model="mistralai/Mistral-Nemo-Instruct-2407",
        api_key="neb-fake-key",
        base_url="https://api.studio.nebius.ai/v1",
        temperature=0,
        max_tokens=1024,
    )


def test_build_client_unknown_provider_raises():
    from app.llm import factory

    bad_settings = _settings(llm_provider="unknown_provider")
    factory._build_client.cache_clear()

    with patch("app.llm.factory.get_settings", return_value=bad_settings):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            factory._build_client.cache_clear()
            factory._build_client("router")
```

- [ ] **Step 2: Run to confirm the Nebius test fails**

```
pytest tests/unit/test_factory.py::test_build_client_nebius_uses_openai_with_custom_base_url -v
```

Expected: `FAIL` — no `"nebius"` branch exists in `_build_client` yet.

- [ ] **Step 3: Add `"nebius"` to `_provider_key_present` and `_build_client`**

In `app/llm/factory.py`, find this function:

```python
def _provider_key_present(settings) -> bool:
    if settings.llm_provider == "anthropic":
        return bool(settings.anthropic_api_key)
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key)
    return False
```

Replace it with:

```python
def _provider_key_present(settings) -> bool:
    if settings.llm_provider == "anthropic":
        return bool(settings.anthropic_api_key)
    if settings.llm_provider == "openai":
        return bool(settings.openai_api_key)
    if settings.llm_provider == "nebius":
        return bool(settings.nebius_api_key)
    return False
```

Then find `_build_client`:

```python
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
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

Replace it with:

```python
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
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            api_key=settings.nebius_api_key,
            base_url=settings.nebius_base_url,
            temperature=0,
            max_tokens=1024,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
```

- [ ] **Step 4: Run all factory tests**

```
pytest tests/unit/test_factory.py -v
```

Expected: all tests pass, including both Nebius tests.

- [ ] **Step 5: Run the full test suite to confirm no regressions**

```
pytest tests/ -v
```

Expected: all existing tests continue to pass.

- [ ] **Step 6: Commit**

```bash
git add app/llm/factory.py tests/unit/test_factory.py
git commit -m "feat: add Nebius Token Factory provider to LLM factory"
```

---

### Task 3: Document Nebius in `.env.example`

**Files:**
- Modify: `.env.example`

**Interfaces:**
- Consumes: `Settings.nebius_api_key`, `Settings.nebius_base_url` (from Task 1)

- [ ] **Step 1: Open `.env.example` and locate the LLM keys block**

Find this section (lines 3–6):

```
# --- LLM provider keys (set the one matching your chosen models) ---
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# --- Default LLM provider: anthropic | openai ---
LLM_PROVIDER=anthropic
```

- [ ] **Step 2: Add Nebius entries**

Replace that block with:

```
# --- LLM provider keys (set the one matching your chosen models) ---
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
NEBIUS_API_KEY=
NEBIUS_BASE_URL=https://api.studio.nebius.ai/v1

# --- Default LLM provider: anthropic | openai | nebius ---
LLM_PROVIDER=anthropic
```

- [ ] **Step 3: Confirm `.env.example` renders correctly**

```
cat .env.example
```

Expected: file shows the two new lines under LLM keys and the updated comment.

- [ ] **Step 4: Commit**

```bash
git add .env.example
git commit -m "docs: document NEBIUS_API_KEY and NEBIUS_BASE_URL in .env.example"
```

---

## Self-Review

### Spec Coverage

The request was "Add Nebius Token Factory support for at least one LLM call." This plan delivers:
- Settings for `NEBIUS_API_KEY` and `NEBIUS_BASE_URL` (Task 1)
- Factory branch that constructs a `ChatOpenAI` client pointed at Nebius for any role (Task 2)
- Because all agents call `complete_text()` → `get_llm()` → `_build_client()`, every LLM call in the system is automatically routed through Nebius when `LLM_PROVIDER=nebius` — satisfying "at least one LLM call"
- `.env.example` updated so engineers know how to activate it (Task 3)

### Placeholder Scan

No TBDs, no "similar to" references, no "add appropriate" hand-waves. All code blocks are complete and runnable.

### Type Consistency

- `Settings.nebius_api_key: str | None` — used as `settings.nebius_api_key` in factory (matches)
- `Settings.nebius_base_url: str` — used as `settings.nebius_base_url` in factory (matches)
- `ChatOpenAI(base_url=...)` — the `base_url` parameter name matches `langchain-openai`'s public API
