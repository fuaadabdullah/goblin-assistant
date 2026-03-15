#!/bin/bash
# Development server startup script for this Goblin Assistant workspace.

set -euo pipefail

echo "Starting Goblin Assistant development servers..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

if lsof -i :8004 > /dev/null 2>&1; then
    echo -e "${RED}Port 8004 already in use. Stopping existing backend...${NC}"
    pkill -f "uvicorn.*api.main:app" || true
    sleep 2
fi

if lsof -i :3000 > /dev/null 2>&1; then
    echo -e "${RED}Port 3000 already in use. Stopping existing frontend...${NC}"
    pkill -f "next dev" || true
    sleep 2
fi

echo -e "${BLUE}Starting FastAPI backend on port 8004...${NC}"
nohup "$SCRIPT_DIR/start_backend.sh" </dev/null > /tmp/goblin-backend.log 2>&1 &
BACKEND_PID=$!
disown
echo "Backend PID: $BACKEND_PID"

sleep 4

if ! lsof -i :8004 > /dev/null 2>&1; then
    echo -e "${RED}Failed to start backend. Check logs: tail -f /tmp/goblin-backend.log${NC}"
    exit 1
fi
echo -e "${GREEN}Backend running at http://localhost:8004${NC}"

echo -e "${BLUE}Starting Next.js frontend on port 3000...${NC}"
nohup npm run dev </dev/null > /tmp/goblin-frontend.log 2>&1 &
FRONTEND_PID=$!
disown
echo "Frontend PID: $FRONTEND_PID"

sleep 4

if ! lsof -i :3000 > /dev/null 2>&1; then
    echo -e "${RED}Failed to start frontend. Check logs: tail -f /tmp/goblin-frontend.log${NC}"
    exit 1
fi
echo -e "${GREEN}Frontend running at http://localhost:3000${NC}"

echo
echo -e "${GREEN}All servers running.${NC}"
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8004"
echo "API docs: http://localhost:8004/docs"
echo
echo "Logs:"
echo "  Backend:  tail -f /tmp/goblin-backend.log"
echo "  Frontend: tail -f /tmp/goblin-frontend.log"
