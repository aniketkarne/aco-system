# Changelog

All notable changes to ACO System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Fixed
- Quick Start (`python run_all_agents_final.py`) referenced a non-existent entry point; every doc + script + Makefile now points to the actual `run_agents.py`. The README's six-step install now actually starts the pipeline.
- `make db-reset` called `init_db()` which doesn't exist; now calls the real `init_database()` and creates the `data/` directory first.
- `init_story.py` had a hardcoded absolute path (`/home/ubuntu/.openclaw/workspace/aco-system`) that crashed for every non-developer-machine user; replaced with a `__file__`-relative `sys.path.insert` so the script runs from any cwd.
- `pip install playwright==1.40.0` is in `requirements.txt` but never imported anywhere; removed the unused dependency.

### Added
- `tests/` directory with a `conftest.py` (adds repo root to `sys.path`) and three smoke-test files: `test_database.py` (ORM CRUD, enum values, cascade), `test_settings.py` (required GitHub fields, default values, singleton), `test_validation_hooks.py` (secrets-detection gate is the headline Architect feature — covers positive + negative case).
- `.github/workflows/tests.yml` running `pytest` on Python 3.10 / 3.11 / 3.12 plus a `ruff check` advisory job. CI now fails a PR that breaks the database / settings / hooks smoke tests.

## [0.1.0] - 2025-03-30

### Added
- **Phase 1: Agent Markdown Prompts & Model Tiering** — Agents defined in `agent_prompts/*.md` with YAML frontmatter; Opus for complex reasoning, Sonnet for implementation, None for human routing
- **Phase 2: Rules Injection** — `rules/common/` with mandatory standards (security, coding-standards, git-workflow, testing) injected into agent context
- **Phase 3: Validation Hooks** — Pre/post transition validation via deterministic JSON configs (no LLM for hard gates like secret detection and schema compliance)
- **Phase 4: Skills & Contexts** — Domain knowledge in `skills/`, project context in `contexts/`, and context trimming for long-running stories
- **Six-Agent Pipeline** — PM → Planner → Architect → Dev → QA → Human Reviewer
- **Next.js Dashboard** — Real-time Kanban board with live agent status, story timelines, task details, and event feed
- **GitHub Integration** — Stories sync with GitHub issues and pull requests
- **Multi-LLM Support** — OpenAI, Anthropic, xAI, and OpenRouter providers configurable via environment variables
- **PostgreSQL + SQLite** — Works with SQLite for local dev, PostgreSQL for production

### Removed
- Experimental test scripts (moved to `experiments/` or deleted prior to open source release)
- Legacy `.venv` virtual environment directory

[0.1.0]: https://github.com/aniketkarne/aco-system/releases/tag/v0.1.0
