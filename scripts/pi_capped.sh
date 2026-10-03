#!/bin/sh
# Second instance of the full service, capped like a 2 GB phone: 1 core (taskset) and 2 GB RAM, no swap
# (systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0). Port 8001; the demo on 8000 is untouched.
cd "$(dirname "$0")/.." || exit 1
systemctl --user stop sns-capped.scope 2>/dev/null
rm -f /tmp/capped.db
SNS_DB=/tmp/capped.db SNS_TIMER=0 setsid nohup systemd-run --user --scope -p MemoryMax=2G -p MemorySwapMax=0 \
  --unit=sns-capped taskset -c 0 "$HOME/venv/bin/python" -m uvicorn app.server:app --host 0.0.0.0 --port 8001 \
  > /tmp/capped.log 2>&1 < /dev/null &
i=0
until curl -s -o /dev/null localhost:8001/config; do i=$((i+1)); [ $i -gt 200 ] && echo "not up" && exit 1; sleep 2; done
echo "startup about $((i*2)) s"
systemctl --user show sns-capped.scope -p MemoryMax -p MemoryPeak -p MemoryCurrent
