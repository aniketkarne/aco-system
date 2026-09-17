"""
Smoke tests for the deterministic validation hooks.

The Architect gate is one of ACO's headline features — secrets detection must
work without any LLM involvement. These tests cover the path the README
advertises: a story with an obvious hardcoded API key is rejected before it
ever reaches the developer agent.
"""
import sys

import pytest


@pytest.fixture
def fresh_db():
    """Yield a fresh in-process SQLite-backed database."""
    from core.database import init_database
    init_database("sqlite:///:memory:")
    yield


# The hooks module imports config.settings at module top, whose `str | None`
# annotations require Python 3.10+. CI runs 3.10/3.11/3.12; on 3.9 the import
# itself raises, so skip the file's tests gracefully.
_requires_py310 = pytest.mark.skipif(
    sys.version_info < (3, 10),
    reason="config.settings uses PEP 604 union syntax (str | None)",
)


def _make_story(title="Smoke", description="ok", context=None, criteria=None):
    from core.database import Story, StoryStatus
    return Story(
        title=title,
        description=description,
        status=StoryStatus.READY_ARCHITECT,
        priority="medium",
        context_json=context or {},
        acceptance_criteria=criteria or ["works"],
    )


@_requires_py310
def test_secrets_in_description_block_transition(fresh_db):
    from core.database import get_session
    from core.validation_hooks import validate_story_transition

    db = get_session()
    story = _make_story(description="use api_key = '«redacted:sk-…»' in the config")
    db.add(story)
    db.commit()

    passed, messages = validate_story_transition(story, "ready-architect", "approved")
    assert passed is False
    assert any("secret" in m.lower() or "credential" in m.lower() for m in messages)


@_requires_py310
def test_clean_story_passes_secrets_gate(fresh_db):
    from core.database import get_session
    from core.validation_hooks import validate_story_transition

    db = get_session()
    story = _make_story(
        description="A clean story with no secrets.",
        criteria=["ships correctly"],
    )
    db.add(story)
    db.commit()

    passed, _ = validate_story_transition(story, "ready-architect", "approved")
    assert passed is True