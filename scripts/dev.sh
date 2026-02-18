#!/usr/bin/env bash
# Start backend (port 8080) and frontend dev server (port 3000) together.
# The frontend's api.ts already routes dev traffic from :3000 to :8080.

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cleanup() {
  echo "Stopping servers..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
}
trap cleanup EXIT

# Backend
echo "Starting backend on :8080..."
cd "$REPO_ROOT"
python -m paperbanana.api.server &
BACKEND_PID=$!

# Frontend
echo "Starting frontend on :3000..."
cd "$REPO_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo "Backend PID=$BACKEND_PID  Frontend PID=$FRONTEND_PID"
echo "Open http://localhost:3000"

wait
