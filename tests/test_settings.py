"""
Smoke tests for the settings/config layer.

Asserts the env-driven config loads with sensible defaults and that the GitHub
auth fields are mandatory (the README's quick start fails without them).
"""
import importlib
import sys

import pytest


# config.settings uses `str | None` PEP 604 syntax; CI runs 3.10+ so these
# pass there, but on Python 3.9 (the venv on some dev machines) the import
# itself raises.
_py310_required = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="config.settings uses PEP 604 union syntax (str | None)",
)


def _reload_settings(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import config.settings as settings_mod
    importlib.reload(settings_mod)
    return settings_mod


@_py310_required
def test_required_github_fields_must_be_set(monkeypatch):
    """GITHUB_TOKEN/OWNER/REPO are declared required in Settings()."""
    for k in ("GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_REPO"):
        monkeypatch.delenv(k, raising=False)

    import config.settings as settings_mod
    importlib.reload(settings_mod)

    with pytest.raises(Exception):
        # Pydantic ValidationError surfaces as a generic Exception on import
        # because the `settings` module-level instance is constructed at import.
        _ = settings_mod.settings  # noqa


@_py310_required
def test_defaults_load_when_required_fields_present(monkeypatch):
    """With the three required fields set, defaults populate cleanly."""
    settings_mod = _reload_settings(
        monkeypatch,
        GITHUB_TOKEN="t",
        GITHUB_OWNER="o",
        GITHUB_REPO="r",
    )
    s = settings_mod.settings
    assert s.GITHUB_TOKEN == "t"
    assert s.DATABASE_URL == "sqlite:///./data/aco.db"
    assert s.LLM_PROVIDER == "anthropic"
    assert s.AGENT_POLL_INTERVAL_SECONDS == 30


@_py310_required
def test_get_settings_returns_singleton(monkeypatch):
    settings_mod = _reload_settings(
        monkeypatch,
        GITHUB_TOKEN="t",
        GITHUB_OWNER="o",
        GITHUB_REPO="r",
    )
    assert settings_mod.get_settings() is settings_mod.settings