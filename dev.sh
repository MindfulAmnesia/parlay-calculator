#!/bin/bash
# dev.sh — start backend and frontend dev servers together.
# Ctrl+C stops both.

cd ~/Projects/parlay-calculator

# Kill all child processes when this script exits
trap 'kill 0 2>/dev/null' EXIT INT TERM

source .venv/bin/activate

echo "→ Starting backend on http://localhost:8000"
uvicorn main:app --reload &

sleep 1

echo "→ Starting frontend on http://localhost:3000"
cd frontend
npm run dev
