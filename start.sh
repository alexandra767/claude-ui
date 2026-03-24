#!/bin/bash
echo "=== Starting Claude UI ==="

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "[*] Starting Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

# Start backend
echo "[*] Starting backend on port 3001..."
cd ~/claude-ui/backend
# Load env file
set -a; [ -f .env ] && source .env; set +a
nohup python3 main.py > /tmp/claude-ui-backend.log 2>&1 &
echo $! > /tmp/claude-ui-backend.pid
echo "    Backend PID: $(cat /tmp/claude-ui-backend.pid)"

# Start frontend
echo "[*] Starting frontend on port 3000..."
cd ~/claude-ui/frontend
nohup npm run dev > /tmp/claude-ui-frontend.log 2>&1 &
echo $! > /tmp/claude-ui-frontend.pid
echo "    Frontend PID: $(cat /tmp/claude-ui-frontend.pid)"

sleep 3

echo ""
echo "=== Claude UI is running ==="
echo "  Local:   http://localhost:3000"
echo "  Network: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "  Backend API: http://localhost:3001"
echo "  Logs: tail -f /tmp/claude-ui-backend.log"
echo "        tail -f /tmp/claude-ui-frontend.log"
echo ""
echo "  Stop: bash ~/claude-ui/stop.sh"
