#!/bin/bash
echo "=== Stopping Claude UI ==="
cd ~/claude-ui
docker compose down
echo "=== Claude UI stopped ==="
