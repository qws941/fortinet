#!/bin/bash
# TS Auto-Discover Daemon
# Automatically discovers and registers new projects every 5 minutes
# Version: 1.0.0

set -euo pipefail

readonly CYAN='\033[0;36m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

readonly DISCOVER_SCRIPT="/home/jclee/app/tmux/ts-discover.sh"
readonly LOG_FILE="/home/jclee/.config/ts/auto-discover.log"
readonly LOCK_FILE="/home/jclee/.config/ts/auto-discover.lock"
readonly INTERVAL=300  # 5 minutes

log() {
    echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"
}

run_discovery() {
    # Check if already running
    if [[ -f "$LOCK_FILE" ]]; then
        log "Discovery already running, skipping..."
        return
    fi

    # Create lock file
    echo $$ > "$LOCK_FILE"
    trap "rm -f $LOCK_FILE" EXIT

    log "Starting auto-discovery..."

    if [[ -x "$DISCOVER_SCRIPT" ]]; then
        "$DISCOVER_SCRIPT" >> "$LOG_FILE" 2>&1
        log "Discovery completed successfully"
    else
        log "ERROR: Discover script not found or not executable: $DISCOVER_SCRIPT"
    fi

    rm -f "$LOCK_FILE"
}

# Main daemon loop
echo -e "${CYAN}${BOLD}TS Auto-Discover Daemon Started${NC}"
echo -e "${GREEN}Interval: $INTERVAL seconds (5 minutes)${NC}"
echo -e "${CYAN}Log: $LOG_FILE${NC}\n"

log "=== TS Auto-Discover Daemon Started ==="

# Initial discovery
run_discovery

# Continuous loop
while true; do
    sleep "$INTERVAL"
    run_discovery
done
