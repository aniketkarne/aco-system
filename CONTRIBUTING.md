# Contributing to ACO System

ACO System is an open-source multi-agent development framework. Contributions are welcome.

## Ways to Contribute

- Report bugs and request features via GitHub Issues
- Submit pull requests to fix bugs or add capabilities
- Improve documentation
- Share your use cases and integrations

## Development Setup

```bash
# Clone the repo
git clone https://github.com/aniketkarne/aco-system.git
cd aco-system

# Set up Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up frontend
cd frontend
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# Run the dashboard
cd frontend && npm run dev

# In another terminal, run the agents
python run_agents.py
```

## Project Structure

```
aco-system/
├── agents/              # Agent implementations (Python)
│   ├── base_agent.py   # Base class all agents inherit
│   ├── project_manager.py   # PM agent
│   ├── planner.py            # Planner agent
│   ├── architect.py          # Architect agent
│   ├── developer.py           # Developer agent
│   ├── qa.py                  # QA agent
│   └── human_reviewer.py      # Human routing agent
├── agent_prompts/       # Markdown prompts for each agent
│   ├── pm.md
│   ├── planner.md
│   ├── architect.md
│   ├── dev.md
│   ├── qa.md
│   └── human.md
├── core/                # Core system
│   ├── database.py      # SQLite/PostgreSQL interface
│   ├── event_bus.py    # Agent event bus
│   ├── prompt_loader.py # Loads agent prompts from markdown
│   ├── rule_loader.py   # Loads rules for agents
│   ├── context_trimmer.py # Trims context for long stories
│   └── validation_hooks.py # Pre/post transition validators
├── config/
│   └── settings.py     # Configuration loader
├── hooks/               # Transition validation configs (JSON)
│   ├── pre-architect-approval.json
│   ├── post-dev-complete.json
│   └── ...
├── rules/common/        # Mandatory rules injected into agents
│   ├── security.md
│   ├── coding-standards.md
│   ├── git-workflow.md
│   └── testing.md
├── skills/              # Domain knowledge for agents
│   ├── python-patterns.md
│   ├── fastapi-patterns.md
│   └── ...
├── contexts/            # Project-specific context
│   └── project-overview.md
├── frontend/            # Dashboard (Next.js 15 + Tailwind)
│   ├── app/            # Next.js App Router pages
│   ├── components/     # UI components
│   └── lib/            # Database queries + types
├── integrations/        # GitHub sync and other integrations
└── run_agents.py          # Main entry point
```

## Adding a New Agent

1. **Create the prompt file** at `agent_prompts/<name>.md`:

```markdown
---
name: aco-newagent
description: What this agent does
model: sonnet  # opus, sonnet, haiku, or none
tools: []      # tools this agent can use
---

You are [role description]...
```

2. **Create the Python class** at `agents/<name>.py`:

```python
from agents.base_agent import BaseAgent
from core.database import StoryStatus

class NewAgent(BaseAgent):
    AGENT_NAME = "newagent"
    HANDLES_STATUSES = [StoryStatus.READY_DEV]
    
    def process_story(self, story):
        # Implementation
        pass
```

3. **Register the agent** in `run_agents.py`.

## Adding Rules

Drop a `.md` file in `rules/common/`. Each agent loads rules relevant to its role. Rules are injected as mandatory constraints in the agent's LLM context.

## Adding Validation Hooks

Add a JSON file to `hooks/`:

```json
{
  "name": "pre-my-transition",
  "description": "Validates something before transition",
  "validators": [
    {
      "type": "schema",
      "params": { "required": ["field"] }
    }
  ]
}
```

## Coding Standards

- Python: type hints, async/await for I/O, Pydantic models for data validation
- Format Python with `ruff` or `black`
- All agents log via `structlog`
- Database: use `get_session()` context manager

## Testing

Add unit tests alongside modules (e.g., `test_workflow.py`). Use `pytest`:

```bash
pytest agents/ -v
```

## Commit Messages

Format: `type: short description`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Pull Request Process

1. Fork the repo and create a feature branch
2. Make your changes
3. Ensure tests pass
4. Update CHANGELOG.md if relevant
5. Open a PR with a clear description

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
