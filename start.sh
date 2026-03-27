#!/bin/bash
echo "=== Starting Claude UI ==="

# Ensure Ollama is running (runs on host, not in Docker)
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "[*] Starting Ollama..."
    ollama serve &>/dev/null &
    sleep 2
fi

cd ~/claude-ui
docker compose up -d --build

echo ""
echo "=== Claude UI is running ==="
echo "  Local:   http://localhost:3000"
echo "  Network: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "  Backend API: http://localhost:3001"
echo "  Logs: docker compose logs -f"
echo "  Stop: bash ~/claude-ui/stop.sh"
