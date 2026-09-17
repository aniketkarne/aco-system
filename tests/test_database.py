"""
Smoke tests for the database layer.

These exercise the public ORM surface (init, CRUD, enum values, to_dict shape)
without ever hitting the network or the real .env. Each test gets a fresh
in-process SQLite database via the `fresh_db` fixture.
"""
import pytest


@pytest.fixture
def fresh_db(monkeypatch):
    """Yield a freshly initialized SQLite-backed database, then clean up.

    Uses an in-process SQLite URL so tests don't touch the project's `data/`
    directory and don't need to import `config.settings` (whose `str | None`
    annotations require Python 3.10+).
    """
    db_url = "sqlite:///:memory:"

    from core.database import init_database, engine
    init_database(db_url)
    yield db_url

    try:
        engine.dispose()
    except Exception:
        pass


def test_init_creates_tables(fresh_db):
    """init_database() must create the four documented tables."""
    from core.database import Base
    expected = {"stories", "tasks", "story_comments", "agent_logs", "channel_messages"}
    assert expected.issubset(set(Base.metadata.tables.keys()))


def test_story_status_enum_values():
    """The pipeline labels in the README must match the enum exactly."""
    from core.database import StoryStatus
    values = {s.value for s in StoryStatus}
    assert values == {
        "pm-review",
        "ready-planner",
        "ready-architect",
        "approved",
        "dev",
        "qa",
        "human-review",
        "done",
    }


def test_task_status_enum_values():
    from core.database import TaskStatus
    assert {s.value for s in TaskStatus} == {"todo", "in_progress", "done", "blocked"}


def test_story_crud_round_trip(fresh_db):
    """Create -> query -> to_dict must round-trip with the expected shape."""
    from core.database import get_session, Story, StoryStatus
    from datetime import datetime

    db = get_session()
    story = Story(
        title="Smoke test story",
        description="Round-trip the ORM.",
        status=StoryStatus.PM_REVIEW,
        priority="high",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        acceptance_criteria=["a", "b"],
        context_json={"k": "v"},
    )
    db.add(story)
    db.commit()
    story_id = story.id

    fetched = db.query(Story).filter(Story.id == story_id).first()
    assert fetched is not None
    assert fetched.title == "Smoke test story"
    assert fetched.status == StoryStatus.PM_REVIEW
    assert fetched.priority == "high"
    assert fetched.acceptance_criteria == ["a", "b"]
    assert fetched.context_json == {"k": "v"}

    d = fetched.to_dict()
    assert d["id"] == story_id
    assert d["title"] == "Smoke test story"
    assert d["status"] == "pm-review"
    assert d["priority"] == "high"
    assert d["acceptance_criteria"] == ["a", "b"]
    assert d["context"] == {"k": "v"}
    assert d["tasks"] == []


def test_task_relationship_and_cascade(fresh_db):
    """Deleting a story must cascade-delete its tasks and comments."""
    from core.database import (
        get_session, Story, Task, TaskStatus, StoryStatus,
        StoryComment, Story,
    )
    db = get_session()
    story = Story(
        title="Parent",
        description="Has children.",
        status=StoryStatus.READY_PLANNER,
    )
    db.add(story)
    db.flush()
    db.add(Task(story_id=story.id, title="t1", description="d", status=TaskStatus.TODO))
    db.add(StoryComment(story_id=story.id, author="aco-pm", content="hi"))
    db.commit()

    story_id = story.id
    db.delete(story)
    db.commit()

    assert db.query(Story).filter(Story.id == story_id).first() is None
    assert db.query(Task).filter(Task.story_id == story_id).count() == 0
    assert db.query(StoryComment).filter(StoryComment.story_id == story_id).count() == 0


def test_get_session_requires_init(monkeypatch):
    """Calling get_session() before init_database() must raise a clear error."""
    import importlib
    import core.database as db_mod
    importlib.reload(db_mod)
    # After reload, engine/SessionLocal are None until init.
    monkeypatch.setattr(db_mod, "SessionLocal", None)
    with pytest.raises(RuntimeError, match="Database not initialized"):
        db_mod.get_session()