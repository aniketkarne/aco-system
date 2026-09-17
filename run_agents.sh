#!/bin/bash
# Setup script for ACO System - runs the agent pipeline

echo "🚀 Starting ACO System agents"
echo ""

echo "Step 1: Install Python dependencies..."
python3 -m pip install -r requirements.txt 2>&1 | tail -5

echo ""
echo "Step 2: Initialize database (creates tables if needed)..."
python3 -c "from core.database import init_database; from config.settings import get_settings; init_database(get_settings().DATABASE_URL)" 2>/dev/null || echo "Database already initialized"

echo ""
echo "Step 3: Run the full agent pipeline..."
echo "Note: Agents poll for stories in status order and process them"
echo ""

# Run all agents (blocks - use in a separate terminal or with & for background)
python3 run_agents.py

echo ""
echo "✓ ACO agents started!"
echo ""
echo "In another terminal, run the dashboard:"
echo "  cd frontend && npm run dev"
echo ""
echo "Agent statuses will be visible at http://localhost:3001"
