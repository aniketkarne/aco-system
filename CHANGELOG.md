# Changelog

All notable changes to ACO System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased - LLM client contract] - 2026-10-21

### Fixed
- **CRITICAL:** `LoggingProxyLLMClient` injected a per-agent `model=` into the
  wrapped provider client, but `MockLLMClient`, `XAIClient`, `OpenAIClient`
  and `AnthropicClient` declared `chat(self, messages, temperature=0.7)` with
  no `model` parameter and no `**kwargs`. Every agent that resolves a
  per-agent model crashed with `TypeError: ... got an unexpected keyword
  argument 'model'` before any request was sent. All providers now share one
  signature: `chat(messages, temperature=0.7, model=None, max_tokens=None,
  **kwargs)`.
- `agents/developer.py` passes `max_tokens=` on every call, which raised the
  same `TypeError` on the Anthropic, OpenAI, xAI and mock providers — only
  MiniMax and OpenRouter happened to accept it.
- `get_client()` special-cased only the MiniMax provider, so an OpenAI or xAI
  deployment was sent the Anthropic tier IDs (`claude-opus-4-20250514`) to a
  provider that does not know them. The shared tiers are now applied to
  Anthropic only; other providers fall back to their own configured model.
- The per-agent model overrides documented in `.env.example` and the README
  (`ACO-PM_MODEL`, `ACO-ARCHITECT_MODEL`, ...) were never read by any code.
  They now resolve, and both the hyphenated and underscored spellings work.
- `AnthropicClient` hard-coded `max_tokens: 4096`. Current reasoning models
  spend part of that budget on thinking tokens, so the visible answer was
  truncated to empty. The cap is now `MAX_TOKENS` (default 16384) and is
  overridable per call.

### Changed
- Refreshed every pinned model ID, which were several generations stale and
  now point at retired or unpublished models: `claude-3-sonnet-20240229`
  (retired), `claude-*-4-20250514` (retired 2026-06-15), `gpt-4-turbo-preview`
  (deprecated), `grok-beta` (no longer published), `MiniMax-M2.7` and
  `minimax/minimax-m2.5`. Defaults are now `claude-sonnet-5-5`,
  `gpt-6.1-sol`, `grok-4.7`, `MiniMax-M3` and `minimax/minimax-m3`, and each
  provider's model is configurable via `ANTHROPIC_MODEL` / `OPENAI_MODEL` /
  `XAI_MODEL` / `OPENROUTER_MODEL` / `MINIMAX_MODEL`.
- Sampling parameters that the current models reject are no longer sent:
  Claude 4.7+ (including the 5.x family) returns HTTP 400 for a non-default
  `temperature`, and the OpenAI reasoning models (`gpt-5+`, `gpt-6`, o-series)
  reject `temperature`/`top_p` and expect `max_completion_tokens`. MiniMax-M3
  always uses temperature 1. Each client now omits the parameters its model
  cannot accept.
- Migrated `Settings.Config` to `SettingsConfigDict` (pydantic-settings v2
  no longer deprecates the class-based form) and added `AliasChoices` so the
  documented hyphenated env-var spellings resolve.

### Added
- `tests/test_llm_client_contract.py` — 27 regression tests covering the
  shared `chat()` contract across every provider, the proxy's model
  injection, the per-agent env overrides, and the request payloads the
  current models accept. 26 of the 27 fail against the pre-fix code.

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
