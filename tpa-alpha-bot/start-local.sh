#!/bin/bash
# TPA Alpha Bot - Local Development Startup Script
# Run this from the tpa-alpha-bot directory

set -e

echo "🚀 Starting TPA Alpha Bot (Local Development)"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from example...${NC}"
    cp .env.example .env
    echo "✏️  Please edit .env with your credentials before running services"
fi

echo -e "${BLUE}1. Backend API Server${NC}"
echo "   Starting FastAPI on port 8000..."
cd backend
pip install -r requirements.txt > /dev/null 2>&1 || echo "Skipping pip install"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend PID: $BACKEND_PID${NC}"
sleep 2

echo ""
echo -e "${BLUE}2. Frontend React App${NC}"
echo "   Starting Vite dev server on port 5173..."
cd ../frontend
npm install > /dev/null 2>&1 || echo "npm install skipped"
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend PID: $FRONTEND_PID${NC}"
sleep 3

echo ""
echo -e "${BLUE}3. Discord Bot${NC}"
echo "   Starting Discord bot..."
cd ../bot
pip install -r ../backend/requirements.txt > /dev/null 2>&1 || echo "Skipping pip install"
python bot.py &
BOT_PID=$!
echo -e "${GREEN}✓ Bot PID: $BOT_PID${NC}"

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All Services Started!${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "📍 URLs:"
echo "   Frontend:  http://localhost:5173"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/docs"
echo ""
echo "🔧 Environment: $(grep ENVIRONMENT .env | cut -d= -f2)"
echo "🗄️  Database: $(grep DATABASE_URL .env | cut -d= -f2)"
echo "💬 Discord Bot Token: $(grep DISCORD_BOT_TOKEN .env | cut -d= -f2 | cut -c1-20)..."
echo ""
echo "📋 Service PIDs:"
echo "   Backend:   $BACKEND_PID"
echo "   Frontend:  $FRONTEND_PID"
echo "   Bot:       $BOT_PID"
echo ""
echo "⏹️  To stop services:"
echo "   kill $BACKEND_PID $FRONTEND_PID $BOT_PID"
echo "   OR press Ctrl+C"
echo ""

wait
