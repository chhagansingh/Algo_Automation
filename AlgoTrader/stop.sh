#!/bin/bash
# AlgoTrader — Stop server
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.server.pid"
PORT=8888

echo ""
echo "  AlgoTrader — Stopping server..."

# Kill by PID file
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    kill -9 "$PID" 2>/dev/null && echo "  Stopped PID $PID ✓" || echo "  PID $PID not found"
    rm -f "$PID_FILE"
fi

# Also kill anything still on the port
REMAINING=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$REMAINING" ]; then
    kill -9 $REMAINING 2>/dev/null
    echo "  Cleared port $PORT ✓"
fi

echo "  AlgoTrader stopped."
echo ""
