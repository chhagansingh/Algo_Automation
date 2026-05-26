#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  AlgoTrader — One-command launcher
#  Usage: cd /Users/com/Desktop/R&D/AlgoTrader && ./start.sh
#  Or from anywhere: /Users/com/Desktop/R\&D/AlgoTrader/start.sh
# ─────────────────────────────────────────────────────────────────────────────

PORT=8888
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="http://localhost:$PORT"
LOG="$DIR/server.log"
PID_FILE="$DIR/.server.pid"

echo ""
echo "  ██████╗ ██╗      ██████╗  ██████╗ ████████╗██████╗  █████╗ ██████╗ ███████╗██████╗ "
echo "  ██╔══██╗██║     ██╔════╝ ██╔═══██╗╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗"
echo "  ██████╔╝██║     ██║  ███╗██║   ██║   ██║   ██████╔╝███████║██║  ██║█████╗  ██████╔╝"
echo "  ██╔══██╗██║     ██║   ██║██║   ██║   ██║   ██╔══██╗██╔══██║██║  ██║██╔══╝  ██╔══██╗"
echo "  ██████╔╝███████╗╚██████╔╝╚██████╔╝   ██║   ██║  ██║██║  ██║██████╔╝███████╗██║  ██║"
echo "  ╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═╝"
echo ""
echo "  NIFTY50 Algo Trading Dashboard  |  Port: $PORT"
echo "  ─────────────────────────────────────────────"
echo ""

# ── Step 1: Kill any existing process on port 5000 ────────────────────────────
echo "  [1/4] Checking port $PORT..."
EXISTING_PID=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$EXISTING_PID" ]; then
    echo "        Killing existing process on port $PORT (PID: $EXISTING_PID)..."
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 1
    echo "        Port $PORT cleared ✓"
else
    echo "        Port $PORT is free ✓"
fi

# Also kill by saved PID file if exists
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill -9 "$OLD_PID" 2>/dev/null
    rm -f "$PID_FILE"
fi

# ── Step 2: Go to project directory ──────────────────────────────────────────
echo "  [2/4] Project: $DIR"
cd "$DIR"

# ── Step 3: Start server in background ────────────────────────────────────────
echo "  [3/4] Starting AlgoTrader server..."
nohup python3 main.py > "$LOG" 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > "$PID_FILE"
echo "        Server PID: $SERVER_PID"
echo "        Logs: $LOG"

# Wait for server to be ready (poll up to 15 seconds)
echo "        Waiting for server to start..."
READY=0
for i in $(seq 1 15); do
    sleep 1
    if curl -s "$URL/api/dashboard" > /dev/null 2>&1; then
        READY=1
        break
    fi
    printf "        ."
done
echo ""

if [ $READY -eq 0 ]; then
    echo ""
    echo "  ⚠  Server did not start in time. Check logs:"
    echo "     tail -20 $LOG"
    echo ""
    exit 1
fi

# ── Step 4: Open browser ──────────────────────────────────────────────────────
echo "  [4/4] Opening browser → $URL"
open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null

echo ""
echo "  ✓  AlgoTrader is running!"
echo "  ─────────────────────────────────────────────"
echo "  Dashboard  : $URL"
echo "  Algo 1     : $URL/algo/algo1  (R&D Straddle)"
echo "  Algo 2     : $URL/algo/algo2  (NTB ScenB)"
echo "  Algo 3     : $URL/algo/algo3  (NiftyBot EMA)"
echo "  API Docs   : $URL/docs"
echo "  Logs       : tail -f $LOG"
echo "  Stop       : kill \$(cat $DIR/.server.pid)"
echo "  ─────────────────────────────────────────────"
echo ""
echo "  Server is running in background."
echo "  Close this terminal safely — server will keep running."
echo ""
