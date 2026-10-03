#!/bin/sh
# (Re)start the service on the Pi: endpoint + simulator on port 8000, detached.
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
pkill -f "python -m uvicorn app.server" 2>/dev/null
sleep 1
setsid nohup "$HOME/venv/bin/python" -m uvicorn app.server:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 < /dev/null &
sleep 4
tail -3 logs/uvicorn.log
