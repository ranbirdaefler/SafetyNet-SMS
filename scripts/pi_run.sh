#!/bin/sh
# (Re)start the service on the Pi: endpoint + simulator on port 8000, detached.
# TZ=EAT-3 (Kenya time) for the app process only; the Pi system clock stays as it is.
cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
pkill -f "python -m uvicorn app.server" 2>/dev/null
sleep 1
TZ=EAT-3 setsid nohup "$HOME/venv/bin/python" -m uvicorn app.server:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 < /dev/null &
sleep 4
tail -3 logs/uvicorn.log
