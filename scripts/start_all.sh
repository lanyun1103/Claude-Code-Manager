#!/bin/bash
# Start multiple CCM instances, each with its own SSH key and database
#
# Usage: ./scripts/start_all.sh
# Stop:  Ctrl+C (kills all instances)

set -e
cd "$(dirname "$0")/.."

PORTS=(8000 8100 8200 8300 8400 8500)
NAMES=(xiaoyu binyu sunzhen weiyao chengsong shaohu)
TOKENS=(
    "SlXGAkAkry4qKsC2j336PnHKdpHZ2gc5CRfEL97mseI"
    "GZ_Dbn-yDgHXxyDSDD3r6EIqm_iEjdYleXpNei_6Ums"
    "8qExxc3ilVpASajLbVWcJUPLTTgJWwSgEn0CGs7FI-8"
    "yjqxt-7H4S-sGnFRmSqVrNCw6smGThKCYY3-Dad7y5g"
    "rkc98c9QwMIla6bcjwnnKw_hJdRmnBujqURUp8vyWLY"
    "y12tTzdn-0UuDqdAUdO96eqEtzChCA8ZE1ezZoOSykY"
)
PIDS=()

cleanup() {
    echo ""
    echo "Stopping all instances..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait
    echo "All instances stopped."
}
trap cleanup INT TERM

for i in "${!PORTS[@]}"; do
    port="${PORTS[$i]}"
    name="${NAMES[$i]}"
    SSH_KEY="$HOME/.ssh/ccm_${port}"
    if [ "$port" = "8000" ]; then
        DB="sqlite+aiosqlite:///./claude_manager.db"
    else
        DB="sqlite+aiosqlite:///./claude_manager_${port}.db"
    fi
    if [ "$port" = "8000" ]; then
        WORKSPACE="$HOME/.claude-code-manager"
    else
        WORKSPACE="$HOME/Projects/ccm_${port}_${name}"
    fi

    if [ ! -f "$SSH_KEY" ]; then
        echo "Warning: SSH key $SSH_KEY not found, skipping port $port"
        continue
    fi

    mkdir -p "$WORKSPACE"

    echo "Starting instance on port $port (SSH key: $SSH_KEY, workspace: $WORKSPACE)"
    GIT_SSH_KEY_PATH="$SSH_KEY" \
    DATABASE_URL="$DB" \
    WORKSPACE_DIR="$WORKSPACE" \
    AUTH_TOKEN="${TOKENS[$i]}" \
    PORT="$port" \
    uv run uvicorn backend.main:app --host 0.0.0.0 --port "$port" &
    PIDS+=($!)
done

echo ""
echo "Started ${#PIDS[@]} instances: ${PORTS[*]}"
echo "Press Ctrl+C to stop all."
wait
