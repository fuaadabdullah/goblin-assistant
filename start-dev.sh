#!/bin/bash
# Development server startup script for GoblinOS Assistant

set -e

echo "🚀 Starting GoblinOS Assistant Development Servers..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if servers are already running
if lsof -i :8000 > /dev/null 2>&1; then
    echo -e "${RED}❌ Port 8000 already in use. Stopping existing backend...${NC}"
    pkill -f "uvicorn.*main:app" || true
    sleep 2
fi

if lsof -i :3000 > /dev/null 2>&1; then
    echo -e "${RED}❌ Port 3000 already in use. Stopping existing frontend...${NC}"
    pkill -f "next" || true
    sleep 2
fi

# Start backend
echo -e "${BLUE}📡 Starting FastAPI backend on port 8000...${NC}"
cd "$SCRIPT_DIR/backend"
nohup ../venv/bin/python -m uvicorn main:app --reload --port 8000 </dev/null > /tmp/goblin-backend.log 2>&1 &
BACKEND_PID=$!
disown
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Check if backend is running
if ! lsof -i :8000 > /dev/null 2>&1; then
    echo -e "${RED}❌ Failed to start backend. Check logs: tail -f /tmp/goblin-backend.log${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend running at http://localhost:8000${NC}"

# Start frontend
echo -e "${BLUE}🎨 Starting Next.js frontend on port 3000...${NC}"
cd "$SCRIPT_DIR/../.."  # Go to monorepo root
nohup pnpm dev --host 0.0.0.0 </dev/null > /tmp/goblin-frontend.log 2>&1 &
FRONTEND_PID=$!
disown
echo "Frontend PID: $FRONTEND_PID"
cd "$SCRIPT_DIR"  # Return to app directory

# Wait for frontend to start
sleep 4

# Check if frontend is running
if ! lsof -i :3000 > /dev/null 2>&1; then
    echo -e "${RED}❌ Failed to start frontend. Check logs: tail -f /tmp/goblin-frontend.log${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Frontend running at http://localhost:3000${NC}"

echo ""
echo -e "${GREEN}🎉 All servers running!${NC}"
echo ""
echo "📊 Access the application:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "📝 View logs:"
echo "  Backend:  tail -f /tmp/goblin-backend.log"
echo "  Frontend: tail -f /tmp/goblin-frontend.log"
echo ""
echo "🛑 To stop servers:"
echo "  pkill -f 'uvicorn.*main:app' && pkill -f 'next'"
echo ""
