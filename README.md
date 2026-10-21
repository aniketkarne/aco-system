# ACO System — Autonomous Company Operating System
<img width="2814" height="1536" alt="aco-system" src="https://raw.githubusercontent.com/aniketkarne/aco-system/refs/heads/main/docs/597115327-b7155ff7-059f-44d1-b255-f78ba4f95269.png" />


A framework for running a multi-agent software development team — autonomously or semi-autonomously. Six specialized agents collaborate through a shared database pipeline: **requirements → planning → architecture → implementation → QA → human review**. Works with GitHub Issues, ships real PRs.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Next.js](https://img.shields.io/badge/next.js-15-black.svg)

---

## The Problem

Shipping software is a coordination problem. PMs write requirements, architects validate feasibility, developers write code, QA tests it, and a human reviews everything — each step a handoff that introduces delays, miscommunication, and dropped context.

Traditional project management tools automate the *tracking* of this process. ACO automates the *execution* of it.

---

## How It Works

```
 GitHub Issue
     │
     ▼
┌─────────┐   writes    ┌─────────┐   breaks down   ┌───────────┐   validates   ┌───────────┐
│   PM    │ ──────────► │ Planner │ ─────────────► │ Architect │ ────────────► │ Developer │
│ (Sonnet)│  user story │  (Opus) │   into tasks    │  (Opus)   │  feasibility  │  (Sonnet) │
└─────────┘             └─────────┘                 └───────────┘  & security    └───────────┘
                                                                    (hard gate)           │
                                                                                           │ creates
                                                                                           │ branch + PR
                                                                                           ▼
                                                                                      ┌─────────┐
                                                                                      │   QA    │
                                                                                      │(Sonnet) │──► runs tests
                                                                                      └─────────┘
                                                                                           │
                                                                                           ▼
                                                                                      ┌──────────┐
                                                                                      │  Human   │
                                                                                      │ Reviewer │──► escalation / merge
                                                                                      └──────────┘
```

Every agent runs independently, polls for work, and writes results to a shared database. No message passing. No shared context window. No degradation as stories get complex.

---

## Why ACO Over Other Frameworks?

| | ACO System | LangChain Agents | AutoGen | CrewAI |
|--|--|--|--|--|
| **Structured pipeline** | ✅ 6-agent gate chain | ❌ | ❌ | ⚠️ Sequential only |
| **Deterministic security gate** | ✅ Hard pre-commit checks | ❌ | ❌ | ❌ |
| **Real-time dashboard** | ✅ Kanban + live feed + alerts | ❌ | ❌ | ❌ |
| **Human escalation** | ✅ Configurable at any stage | ⚠️ | ⚠️ | ⚠️ |
| **Multi-LLM support** | ✅ Per-agent model override | ⚠️ | ⚠️ | ⚠️ |
| **File-based extensibility** | ✅ Prompts, rules, hooks, skills | ⚠️ | ❌ | ❌ |

The Architect agent is the key difference. Before any code is written, it runs **deterministic validation** — no LLM involved, no hallucination risk:

- ✅ No hardcoded secrets (`api_key`, `password`, `token`, `secret` scanned)
- ✅ Story has `tech_stack` and `acceptance_criteria`
- ✅ All tasks are assigned and estimated

If these fail, the story is **rejected at the gate** — it never reaches the developer. No bad PRs, no leaked credentials, no incomplete features.

---

## 🎯 Who It's For

- **Engineering teams** that want to automate repetitive development workflows
- **AI/agent researchers** building on a proven multi-agent collaboration pattern
- **Solo developers** who want a "virtual team" handling the boilerplate
- **Platform builders** who need extensible agent primitives

---

## ⚡ Quick Start

```bash
# 1. Clone
git clone https://github.com/aniketkarne/aco-system.git
cd aco-system

# 2. Python dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Frontend dependencies
cd frontend && npm install && cd ..

# 4. Configure
cp .env.example .env
# Edit .env: add your GITHUB_TOKEN, LLM provider key, and repo details

# 5. Run dashboard
cd frontend && npm run dev
# → http://localhost:3001

# 6. Run the agent pipeline
python run_all_agents_final.py
```

That's it. The dashboard shows the live pipeline — Kanban board, agent status, story timeline, and a streaming event feed.

---

## 🏗️ Architecture

### Six Agents, Each Doing One Thing Well

| Agent | Model | Role |
|-------|-------|------|
| **PM** | Sonnet | Writes user stories from GitHub Issues, does web research |
| **Planner** | Opus | Breaks stories into tasks, estimates effort, maps dependencies |
| **Architect** | Opus | Hard gate: validates feasibility, security, schema — blocks bad stories |
| **Developer** | Sonnet | Writes code, creates branches and PRs, follows coding standards |
| **QA** | Sonnet | Reviews PRs, writes and runs tests, validates acceptance criteria |
| **Human** | — | Escalation point for edge cases, final merge sign-off |

### State-Driven, Not Message-Passing

All agents communicate through a shared **SQLite** (dev) or **PostgreSQL** (prod) database. Each agent polls for work, acquires a story lock, executes its step, writes results, and releases the lock. No shared context window. No agent-to-agent API calls. Complexity stays in the database schema, not in the agent logic.

---

## GitHub as the Workflow Layer

ACO System does not replace GitHub — it builds on top of it. Every story in the pipeline automatically creates or links to a GitHub Issue, giving you full history, labels, and search without any additional tooling.

### How it works

| Pipeline Stage | GitHub Action |
|---|---|
| PM creates story | GitHub Issue opened with full description, acceptance criteria, and CEO/Founder analysis |
| Planner breaks down tasks | Issue body updated with task checklist |
| Architect approves | Issue labeled `approved`, ready for development |
| Developer starts | Feature branch created, issue assigned, work begins |
| Developer finishes | Pull Request opened against `main`, linked to the issue |
| QA reviews | PR checks run, QA feedback posted as PR review comments |
| Human approves | PR merged or manual merge requested |

### Labels

Each pipeline stage has a corresponding label. The dashboard Kanban board mirrors these labels — the board and GitHub Issues always stay in sync:

```
pm-review → ready-planner → ready-architect → approved → dev → qa → human-review → done
```

### What gets created

- **Branches** — `feat/story-42-stripe-payments`, `fix/story-15-email-verification`
- **Issues** — One per story, with full context in the body, updated as the story moves through the pipeline
- **Pull Requests** — One per story, with linked tasks, description from acceptance criteria, and test instructions

### Why GitHub Issues?

Using GitHub as the collaboration layer means:

- **No lock-in** — The data is yours. Close the dashboard, the agents still work through the GitHub API alone
- **Your existing tools** — Search, filter, and triage using GitHub's UI. Get notifications through GitHub's settings
- **Full audit trail** — Every agent action is in the issue comments. Every decision is timestamped and attributable
- **CI/CD ready** — GitHub Actions triggers on PR creation, running your test suite automatically before QA reviews

---

## Dashboard

A real-time Next.js dashboard provides visual oversight of the entire pipeline. It is not a static tracker — it reflects live agent activity as it happens.

**Kanban Board** — Stories move through columns representing each pipeline stage. Each card shows the story title, priority badge (critical / high / medium / low), time since last update, and rejection count. Columns include PM Review, Planner, Architect, Dev, QA, Human Review, Done, and Blocked.

![Kanban Board](docs/screenshots/kanban-board.png)

**Agent Activity Panel** — Each of the six agents shows as a live card: current status (idle / working / blocked), the story it is handling, and which LLM model it is using. A streaming event log below shows timestamped agent actions in real time — "aco-pm: New story created", "aco-architect: Approved story #12", "aco-dev: PR opened for task #4". An alert panel surfaces rejections, escalations, and failures immediately.

![Agent Activity](docs/screenshots/agent-activity.png)

**Story Detail** — Clicking any card opens a side panel with the full story context: description, acceptance criteria, task list with status, conversation history, and linked GitHub issue. The human reviewer uses this view for final sign-off.

---

## 🔧 Extension Points

Everything is file-based and hot-reloadable. No code changes needed to influence agent behavior:

| Extension | Format | What It Changes |
|-----------|--------|-----------------|
| Agent prompts | Markdown + YAML frontmatter | How each agent thinks and decides |
| Coding rules | Markdown in `rules/common/` | Mandatory standards (security, git workflow, testing) |
| Validation hooks | JSON in `hooks/` | Deterministic pre/post transition checks |
| Domain skills | Markdown in `skills/` | Python patterns, FastAPI, React, etc. |
| Project context | Markdown in `contexts/` | Project-specific background knowledge |

---

## 📁 Project Layout

```
aco-system/
├── agents/                  # Agent Python implementations
│   └── base_agent.py       # Inherit to add new agents
├── agent_prompts/          # Markdown prompts (hot-reloadable)
│   ├── pm.md / planner.md / architect.md / developer.md / qa.md / human.md
├── core/
│   ├── database.py         # SQLite/PostgreSQL ORM layer
│   ├── event_bus.py        # Agent event pub/sub
│   ├── prompt_loader.py    # Runtime prompt loading
│   ├── rule_loader.py      # Rule injection into agent context
│   ├── context_trimmer.py  # Token budget management
│   └── validation_hooks.py # Deterministic gate validators
├── hooks/                  # JSON configs for hard validation gates
├── rules/common/           # Mandatory rules for all agents
│   ├── security.md
│   ├── coding-standards.md
│   ├── git-workflow.md
│   └── testing.md
├── skills/                 # Domain knowledge
├── contexts/              # Project-specific context
├── integrations/          # GitHub sync, external APIs
├── frontend/              # Dashboard (Next.js 15 + Tailwind CSS)
│   ├── app/api/           # API routes (stories, agents, feed, alerts)
│   └── components/        # Kanban, timeline, live feed, alerts
└── run_all_agents_final.py  # Main entry point
```

---

## 🚀 Production Use

```bash
# PostgreSQL for multi-instance deployments
DATABASE_URL=postgresql://user:password@host:5432/aco

# Optional Redis for distributed task queue
REDIS_URL=redis://localhost:6379/0

# Per-agent model override
# The value is used verbatim, so it must be a model ID your configured
# provider accepts. Both ACO_ARCHITECT_MODEL and ACO-ARCHITECT-MODEL work.
ACO-ARCHITECT_MODEL=claude-opus-5-5
ACO-DEV_MODEL=claude-sonnet-5-5
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

Built by [Aniket Karne](https://github.com/aniketkarne)
