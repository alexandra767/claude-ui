#!/bin/bash
echo "=== Stopping Claude UI ==="

if [ -f /tmp/claude-ui-backend.pid ]; then
    kill $(cat /tmp/claude-ui-backend.pid) 2>/dev/null
    rm -f /tmp/claude-ui-backend.pid
    echo "[*] Backend stopped"
fi

if [ -f /tmp/claude-ui-frontend.pid ]; then
    kill $(cat /tmp/claude-ui-frontend.pid) 2>/dev/null
    rm -f /tmp/claude-ui-frontend.pid
    echo "[*] Frontend stopped"
fi

# Also kill any lingering processes
pkill -f "python3 main.py" 2>/dev/null
pkill -f "vite.*claude-ui" 2>/dev/null

echo "=== Claude UI stopped ==="
