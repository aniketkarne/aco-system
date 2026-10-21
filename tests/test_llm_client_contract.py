"""
Regression tests for the shared LLM client contract.

Background
----------
``LoggingProxyLLMClient`` wraps whichever provider client is configured and
forwards a per-agent ``model`` to it. Several provider clients declared
``chat(self, messages, temperature=0.7)`` with no ``model`` parameter and no
``**kwargs``, so the proxy raised::

    TypeError: MockLLMClient.chat() got an unexpected keyword argument 'model'

before any request was sent. This affected every agent that resolves a
per-agent model (architect, planner, dev, QA, PM).

The same file also pinned model IDs several generations behind the providers'
current catalogs, and the sampling parameters it sent were rejected outright
by some of the current models.

This module is deliberately self-contained (no conftest.py) so it can land
alongside the other test files without colliding with them.
"""
import importlib
import os
import sys
from pathlib import Path

import pytest

# --- Bootstrap ---------------------------------------------------------------
# Must happen before config.settings is imported: Settings() is constructed at
# import time and requires the GitHub fields to be present.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

for _key, _value in {
    "GITHUB_TOKEN": "test-token",
    "GITHUB_OWNER": "test-owner",
    "GITHUB_REPO": "test-repo",
}.items():
    os.environ.setdefault(_key, _value)


@pytest.fixture(autouse=True)
def reload_settings():
    """Reload config.settings around every test.

    Settings are read from the environment at import time and cached in a
    module-level singleton, so a test that sets an env var has to reload the
    module for the change to take effect. The reload propagates to modules
    that did ``from config.settings import get_settings`` because
    importlib.reload reuses the same module namespace and re-binds the
    module-level ``settings`` object in place.
    """
    import config.settings as settings_mod

    def _reload():
        importlib.reload(settings_mod)
        return settings_mod

    _reload()
    yield _reload
    _reload()


@pytest.fixture
def reset_client_cache():
    """Clear the per-(agent, model) client cache between tests."""
    from integrations.llm_client import reset_client

    reset_client()
    yield
    reset_client()


# --- Helpers -----------------------------------------------------------------


def _capture_post(monkeypatch, response_payload):
    """Patch httpx.Client.post to capture the outgoing request body.

    Returns the list that the captured bodies are appended to.
    """
    import httpx

    captured = []

    def fake_post(self, url, **kwargs):
        body = kwargs.get("json") or {}
        captured.append({"url": url, "body": body})
        request = httpx.Request("POST", url)
        return httpx.Response(200, json=response_payload, request=request)

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    return captured


# --- 1. The contract ---------------------------------------------------------


def test_every_provider_accepts_model_kwarg(monkeypatch):
    """No provider may reject the ``model`` kwarg the proxy injects.

    This is the regression that broke every agent: the proxy passed
    ``model=`` to a client whose signature did not accept it.
    """
    from integrations.llm_client import (
        AnthropicClient,
        LoggingProxyLLMClient,
        MinimaxClient,
        MockLLMClient,
        OpenAIClient,
        OpenRouterClient,
        XAIClient,
    )

    _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}],
                                "content": [{"text": "OK"}]})

    providers = [
        MockLLMClient(),
        XAIClient("test-key"),
        OpenAIClient("test-key"),
        AnthropicClient("test-key"),
        MinimaxClient("test-key"),
        OpenRouterClient("test-key"),
    ]

    for provider in providers:
        proxy = LoggingProxyLLMClient(
            provider, agent_name="architect", agent_model="claude-opus-5-5"
        )
        proxy.chat([{"role": "user", "content": "hi"}])


def test_every_provider_accepts_max_tokens_kwarg(monkeypatch):
    """``agents/developer.py`` passes ``max_tokens=`` on every call.

    That is a second TypeError waiting to happen on any provider whose
    signature lacks the parameter.
    """
    from integrations.llm_client import (
        AnthropicClient,
        LoggingProxyLLMClient,
        MinimaxClient,
        MockLLMClient,
        OpenAIClient,
        OpenRouterClient,
        XAIClient,
    )

    _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}],
                                "content": [{"text": "OK"}]})

    providers = [
        MockLLMClient(),
        XAIClient("test-key"),
        OpenAIClient("test-key"),
        AnthropicClient("test-key"),
        MinimaxClient("test-key"),
        OpenRouterClient("test-key"),
    ]

    for provider in providers:
        proxy = LoggingProxyLLMClient(
            provider, agent_name="architect", agent_model="claude-opus-5-5"
        )
        proxy.chat([{"role": "user", "content": "hi"}], max_tokens=8192)


def test_base_class_declares_the_shared_contract():
    """The abstract base must advertise the same signature."""
    import inspect

    from integrations.llm_client import LLMClient

    params = inspect.signature(LLMClient.chat).parameters
    for name in ("messages", "temperature", "model", "max_tokens"):
        assert name in params, f"LLMClient.chat is missing {name!r}"
    assert params["model"].default is None
    assert params["max_tokens"].default is None


# --- 2. The proxy injects the per-agent model --------------------------------


def test_proxy_injects_per_agent_model_into_request(monkeypatch):
    """The agent's model must actually reach the provider request."""
    from integrations.llm_client import AnthropicClient, LoggingProxyLLMClient

    captured = _capture_post(monkeypatch, {"content": [{"text": "OK"}]})

    proxy = LoggingProxyLLMClient(
        AnthropicClient("test-key"), agent_name="architect",
        agent_model="claude-opus-5-5",
    )
    proxy.chat([{"role": "user", "content": "hi"}])

    assert captured[0]["body"]["model"] == "claude-opus-5-5"


def test_proxy_does_not_override_caller_model(monkeypatch):
    """An explicit per-call model wins over the agent's configured model."""
    from integrations.llm_client import AnthropicClient, LoggingProxyLLMClient

    captured = _capture_post(monkeypatch, {"content": [{"text": "OK"}]})

    proxy = LoggingProxyLLMClient(
        AnthropicClient("test-key"), agent_name="architect",
        agent_model="claude-opus-5-5",
    )
    proxy.chat([{"role": "user", "content": "hi"}], model="claude-haiku-5-5")

    assert captured[0]["body"]["model"] == "claude-haiku-5-5"


def test_proxy_without_agent_model_sends_no_model_override(monkeypatch):
    """``get_client()`` with no agent name must not inject a model."""
    from integrations.llm_client import AnthropicClient, LoggingProxyLLMClient

    captured = _capture_post(monkeypatch, {"content": [{"text": "OK"}]})

    proxy = LoggingProxyLLMClient(AnthropicClient("test-key"), agent_name="agent")
    proxy.chat([{"role": "user", "content": "hi"}])

    # The client's own default is used, not an injected override.
    assert captured[0]["body"]["model"] == "claude-sonnet-5-5"


# --- 3. Model IDs are current ------------------------------------------------


def test_anthropic_default_model_is_not_retired():
    """The Anthropic default must not be a retired model ID.

    claude-3-sonnet-20240229 was retired on 2026-01-05.
    """
    from integrations.llm_client import AnthropicClient

    assert AnthropicClient("test-key").model == "claude-sonnet-5-5"


def test_openai_default_model_is_not_deprecated():
    """gpt-4-turbo-preview is deprecated and no longer current."""
    from integrations.llm_client import OpenAIClient

    assert OpenAIClient("test-key").model == "gpt-6.1-sol"


def test_xai_default_model_is_published():
    """grok-beta is absent from the xAI model catalog."""
    from integrations.llm_client import XAIClient

    assert XAIClient("test-key").model == "grok-4.7"


def test_minimax_default_model_is_current():
    """MiniMax-M2.7 has been superseded by MiniMax-M3."""
    from integrations.llm_client import MinimaxClient

    assert MinimaxClient("test-key").model == "MiniMax-M3"


def test_settings_default_models_are_current():
    """No setting may default to a retired or deprecated model ID."""
    from config.settings import Settings

    settings = Settings()
    for name in ("MODEL_OPU", "MODEL_SONNET", "MODEL_HAIKU",
                 "ANTHROPIC_MODEL", "OPENAI_MODEL", "XAI_MODEL",
                 "OPENROUTER_MODEL", "MINIMAX_MODEL"):
        value = getattr(settings, name)
        assert value, f"{name} is empty"
        # Retired/deprecated IDs that must not come back.
        for retired in ("claude-3-sonnet-20240229", "claude-opus-4-20250514",
                        "claude-sonnet-4-20250514", "claude-haiku-4-20250514",
                        "gpt-4-turbo-preview", "grok-beta", "MiniMax-M2.7",
                        "minimax/minimax-m2.5"):
            assert retired not in value, f"{name}={value!r} uses a retired ID"


# --- 4. Sampling parameters the current models reject ------------------------


def test_anthropic_omits_temperature_for_claude_4_7_and_newer(monkeypatch):
    """Claude 4.7+ returns HTTP 400 for a non-default temperature."""
    from integrations.llm_client import AnthropicClient

    captured = _capture_post(monkeypatch, {"content": [{"text": "OK"}]})

    AnthropicClient("test-key").chat(
        [{"role": "user", "content": "hi"}], temperature=0.3,
        model="claude-opus-5-5",
    )

    assert "temperature" not in captured[0]["body"]


def test_anthropic_sends_temperature_for_older_models(monkeypatch):
    """Models before 4.7 still accept temperature."""
    from integrations.llm_client import AnthropicClient

    captured = _capture_post(monkeypatch, {"content": [{"text": "OK"}]})

    AnthropicClient("test-key").chat(
        [{"role": "user", "content": "hi"}], temperature=0.3,
        model="claude-sonnet-4-6",
    )

    assert captured[0]["body"]["temperature"] == 0.3


def test_openai_reasoning_model_omits_temperature(monkeypatch):
    """gpt-5+/gpt-6/o-series reject temperature unless effort is "none"."""
    from integrations.llm_client import OpenAIClient

    captured = _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}]})

    OpenAIClient("test-key").chat(
        [{"role": "user", "content": "hi"}], temperature=0.3, model="gpt-6.1-sol",
    )

    assert "temperature" not in captured[0]["body"]


def test_openai_reasoning_model_uses_max_completion_tokens(monkeypatch):
    """Reasoning models take max_completion_tokens, not max_tokens."""
    from integrations.llm_client import OpenAIClient

    captured = _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}]})

    OpenAIClient("test-key").chat(
        [{"role": "user", "content": "hi"}], model="gpt-6.1-sol", max_tokens=4096,
    )

    assert captured[0]["body"]["max_completion_tokens"] == 4096
    assert "max_tokens" not in captured[0]["body"]


def test_openai_legacy_model_keeps_temperature_and_max_tokens(monkeypatch):
    """Non-reasoning models keep the classic parameters."""
    from integrations.llm_client import OpenAIClient

    captured = _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}]})

    OpenAIClient("test-key").chat(
        [{"role": "user", "content": "hi"}], temperature=0.3, model="gpt-4o",
        max_tokens=4096,
    )

    assert captured[0]["body"]["temperature"] == 0.3
    assert captured[0]["body"]["max_tokens"] == 4096
    assert "max_completion_tokens" not in captured[0]["body"]


def test_openai_does_not_force_reasoning_effort_none(monkeypatch):
    """gpt-6.1-sol rejects effort="none" outright.

    Sending it unasked would turn a working request into a 400.
    """
    from integrations.llm_client import OpenAIClient

    captured = _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}]})

    OpenAIClient("test-key").chat(
        [{"role": "user", "content": "hi"}], model="gpt-6.1-sol",
    )

    assert "reasoning_effort" not in captured[0]["body"]


def test_minimax_omits_temperature(monkeypatch):
    """MiniMax-M3 always uses temperature 1 and ignores the parameter."""
    from integrations.llm_client import MinimaxClient

    captured = _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}]})

    MinimaxClient("test-key").chat(
        [{"role": "user", "content": "hi"}], temperature=0.3,
    )

    assert "temperature" not in captured[0]["body"]
    assert captured[0]["body"]["max_completion_tokens"] > 0


# --- 5. Per-agent env overrides ----------------------------------------------


def test_per_agent_override_is_read_from_env(monkeypatch, reload_settings,
                                              reset_client_cache):
    """ACO_ARCHITECT_MODEL must actually override the tier default.

    The variable is documented in .env.example and the README, but nothing
    read it.
    """
    monkeypatch.setenv("ACO_ARCHITECT_MODEL", "claude-haiku-5-5")
    reload_settings()

    from core.prompt_loader import get_agent_model

    assert get_agent_model("aco-architect") == "claude-haiku-5-5"


def test_per_agent_override_accepts_hyphenated_env_name(monkeypatch,
                                                        reload_settings):
    """.env.example documents the hyphenated spelling; it must work too."""
    monkeypatch.setenv("ACO-ARCHITECT-MODEL", "claude-haiku-5-5")
    reload_settings()

    from core.prompt_loader import get_agent_model

    assert get_agent_model("aco-architect") == "claude-haiku-5-5"


def test_per_agent_override_beats_tier_default(monkeypatch, reload_settings):
    """An override wins over MODEL_OPU / MODEL_SONNET."""
    monkeypatch.setenv("ACO_PLANNER_MODEL", "claude-haiku-5-5")
    reload_settings()

    from core.prompt_loader import get_agent_model

    assert get_agent_model("aco-planner") == "claude-haiku-5-5"


def test_agent_without_override_uses_tier_default(reload_settings):
    """Without an override the tier default still applies."""
    from core.prompt_loader import get_agent_model

    assert get_agent_model("aco-architect") == "claude-opus-5-5"
    assert get_agent_model("aco-pm") == "claude-sonnet-5-5"
    assert get_agent_model("aco-human") == "none"


def test_per_agent_override_reaches_the_provider_request(monkeypatch,
                                                         reload_settings,
                                                         reset_client_cache):
    """End to end: env var -> get_client() -> provider request body."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("ACO_ARCHITECT_MODEL", "claude-haiku-5-5")
    reload_settings()

    captured = _capture_post(monkeypatch, {"content": [{"text": "OK"}]})

    from integrations.llm_client import get_client

    client = get_client("aco-architect")
    client.chat([{"role": "user", "content": "hi"}])

    assert captured[0]["body"]["model"] == "claude-haiku-5-5"


def test_tier_defaults_are_not_injected_into_other_providers(monkeypatch,
                                                              reload_settings,
                                                              reset_client_cache):
    """MODEL_OPU is an Anthropic ID; OpenAI must not receive it.

    The previous code only special-cased minimax, so an OpenAI or xAI
    deployment would have been sent "claude-opus-4-20250514".
    """
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    reload_settings()

    captured = _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}]})

    from integrations.llm_client import get_client

    client = get_client("aco-architect")
    client.chat([{"role": "user", "content": "hi"}])

    assert captured[0]["body"]["model"] == "gpt-6.1-sol"


def test_explicit_override_is_used_for_non_anthropic_providers(monkeypatch,
                                                               reload_settings,
                                                               reset_client_cache):
    """An explicit override is deliberate, so it applies to any provider."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ACO_ARCHITECT_MODEL", "gpt-6-luna")
    reload_settings()

    captured = _capture_post(monkeypatch, {"choices": [{"message": {"content": "OK"}}]})

    from integrations.llm_client import get_client

    client = get_client("aco-architect")
    client.chat([{"role": "user", "content": "hi"}])

    assert captured[0]["body"]["model"] == "gpt-6-luna"


# --- 6. Settings layer -------------------------------------------------------


def test_max_tokens_default_is_generous():
    """A small cap truncates reasoning models' visible answer to empty."""
    from config.settings import Settings

    assert Settings().MAX_TOKENS >= 8192


def test_settings_still_loads_with_required_fields(monkeypatch, reload_settings):
    """The migration to model_config must not break the existing contract."""
    from config.settings import Settings

    settings = Settings()
    assert settings.LLM_PROVIDER == "anthropic"
    assert settings.DATABASE_URL == "sqlite:///./data/aco.db"
    assert settings.AGENT_POLL_INTERVAL_SECONDS == 30
