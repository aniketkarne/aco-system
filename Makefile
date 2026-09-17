.PHONY: help install install-frontend dev dev-agents test lint format clean db-reset

help:
	@echo "ACO System — available commands:"
	@echo ""
	@echo "  make install          Install Python dependencies"
	@echo "  make install-frontend Install frontend dependencies"
	@echo "  make dev             Run frontend dashboard (http://localhost:3001)"
	@echo "  make dev-agents      Run all agents"
	@echo "  make test            Run tests"
	@echo "  make lint            Lint Python code"
	@echo "  make format          Format Python code"
	@echo "  make clean           Remove build artifacts and caches"
	@echo "  make db-reset        Reset SQLite database (delete + recreate)"
	@echo ""

install:
	python -m venv .venv
	(. .venv/bin/activate && pip install -r requirements.txt)

install-frontend:
	cd frontend && npm install && cd ..

dev:
	cd frontend && npm run dev

dev-agents:
	python run_agents.py

test:
	pytest -v

lint:
	ruff check agents/ core/ config/ integrations/

format:
	ruff format agents/ core/ config/ integrations/

clean:
	rm -rf __pycache__ agents/__pycache__ core/__pycache__ config/__pycache__
	rm -rf .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

db-reset:
	@mkdir -p data
	rm -f data/aco.db && python -c "from core.database import init_database; from config.settings import get_settings; init_database(get_settings().DATABASE_URL)"
