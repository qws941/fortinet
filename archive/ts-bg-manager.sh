#!/bin/bash
# TS Background Task Manager
# Manages background processes within tmux sessions with labeling and monitoring

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Configuration
SOCKET_DIR="/home/jclee/.tmux/sockets"
STATE_DIR="$HOME/.config/ts/state"
BG_TASKS_DB="$STATE_DIR/background_tasks.json"
LABELS_DB="$STATE_DIR/session_labels.json"

mkdir -p "$STATE_DIR"

# Initialize databases
[[ -f "$BG_TASKS_DB" ]] || echo '{"tasks": {}}' > "$BG_TASKS_DB"
[[ -f "$LABELS_DB" ]] || echo '{"sessions": {}}' > "$LABELS_DB"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION LABELING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

label_session() {
    local session_name="$1"
    local labels="$2"  # Comma-separated labels

    if [[ -z "$session_name" ]] || [[ -z "$labels" ]]; then
        echo -e "${RED}Usage: ts-bg label <session> <labels>${NC}" >&2
        echo -e "${BLUE}Example: ts-bg label claude-blacklist 'backend,api,production'${NC}" >&2
        return 1
    fi

    # Convert comma-separated to JSON array
    local labels_array=$(echo "$labels" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$";""))')

    # Update labels database
    local updated=$(jq \
        --arg session "$session_name" \
        --argjson labels "$labels_array" \
        '.sessions[$session] = {labels: $labels, updated: (now | strftime("%Y-%m-%dT%H:%M:%SZ"))}' \
        "$LABELS_DB")

    echo "$updated" > "$LABELS_DB"

    echo -e "${GREEN}✓ Labeled session: $session_name${NC}"
    echo -e "${BLUE}  Labels: $(echo "$labels_array" | jq -r 'join(", ")')${NC}"
}

show_labels() {
    local session_name="${1:-}"

    if [[ -n "$session_name" ]]; then
        # Show labels for specific session
        local labels=$(jq -r --arg s "$session_name" '.sessions[$s].labels // [] | join(", ")' "$LABELS_DB")
        if [[ -n "$labels" ]]; then
            echo -e "${CYAN}Labels for $session_name:${NC} $labels"
        else
            echo -e "${YELLOW}No labels found for: $session_name${NC}"
        fi
    else
        # Show all labels
        echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}              Session Labels${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

        jq -r '.sessions | to_entries[] | "\(.key): \(.value.labels | join(", "))"' "$LABELS_DB" | \
        while IFS=: read -r session labels; do
            echo -e "  ${GREEN}●${NC} ${BOLD}$session${NC}"
            echo -e "    ${BLUE}🏷️  $labels${NC}"
        done
    fi
}

search_by_label() {
    local search_label="$1"

    if [[ -z "$search_label" ]]; then
        echo -e "${RED}Usage: ts-bg search <label>${NC}" >&2
        return 1
    fi

    echo -e "${CYAN}Sessions with label '$search_label':${NC}"

    jq -r \
        --arg searchlabel "$search_label" \
        '.sessions | to_entries[] | select(.value.labels | any(. == $searchlabel)) | .key' \
        "$LABELS_DB" | \
    while read -r session; do
        if [[ -S "$SOCKET_DIR/$session" ]]; then
            local status=$(tmux -S "$SOCKET_DIR/$session" list-sessions -F "#{?session_attached,attached,detached}" 2>/dev/null | head -1)
            echo -e "  ${GREEN}●${NC} $session [$status]"
        fi
    done
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKGROUND TASK MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

start_background_task() {
    local session_name="$1"
    local window_name="$2"
    local command="$3"
    local task_type="${4:-generic}"

    if [[ -z "$session_name" ]] || [[ -z "$window_name" ]] || [[ -z "$command" ]]; then
        echo -e "${RED}Usage: ts-bg start <session> <window-name> '<command>' [type]${NC}" >&2
        echo -e "${BLUE}Example: ts-bg start claude-blacklist dev-server 'npm run dev' dev-server${NC}" >&2
        return 1
    fi

    local socket_path="$SOCKET_DIR/$session_name"

    if [[ ! -S "$socket_path" ]]; then
        echo -e "${RED}✗ Session does not exist: $session_name${NC}" >&2
        return 1
    fi

    # Create new window for background task
    tmux -S "$socket_path" new-window -t "$session_name" -n "$window_name" -d

    # Send command to window
    tmux -S "$socket_path" send-keys -t "$session_name:$window_name" "$command" Enter

    # Record task in database
    local task_id="${session_name}:${window_name}"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local updated=$(jq \
        --arg task_id "$task_id" \
        --arg session "$session_name" \
        --arg window "$window_name" \
        --arg command "$command" \
        --arg type "$task_type" \
        --arg started "$timestamp" \
        '.tasks[$task_id] = {
            session: $session,
            window: $window,
            command: $command,
            type: $type,
            started: $started,
            status: "running",
            pid: null
        }' \
        "$BG_TASKS_DB")

    echo "$updated" > "$BG_TASKS_DB"

    echo -e "${GREEN}✓ Started background task: $window_name${NC}"
    echo -e "${BLUE}  Session: $session_name${NC}"
    echo -e "${BLUE}  Command: $command${NC}"
    echo -e "${BLUE}  Type: $task_type${NC}"
}

list_background_tasks() {
    local session_name="${1:-}"

    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           Background Tasks${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local query='.tasks | to_entries[]'
    if [[ -n "$session_name" ]]; then
        query+=\ "| select(.value.session == \"$session_name\")"
    fi

    jq -r "$query | \"\(.value.session):\(.value.window)|\(.value.type)|\(.value.command)|\(.value.status)\"" "$BG_TASKS_DB" | \
    while IFS='|' read -r task_id type command status; do
        # Check if task is actually running
        local session_window="${task_id%:*}"
        local window="${task_id##*:}"

        if tmux -S "$SOCKET_DIR/$session_window" list-windows -t "$session_window" -F "#{window_name}" 2>/dev/null | grep -q "^${window}$"; then
            echo -e "  ${GREEN}●${NC} ${BOLD}$task_id${NC} [$status]"
            echo -e "    ${PURPLE}Type:${NC} $type"
            echo -e "    ${BLUE}Command:${NC} $command"
        fi
    done
}

stop_background_task() {
    local task_id="$1"

    if [[ -z "$task_id" ]]; then
        echo -e "${RED}Usage: ts-bg stop <session>:<window>${NC}" >&2
        echo -e "${BLUE}Example: ts-bg stop claude-blacklist:dev-server${NC}" >&2
        return 1
    fi

    local session="${task_id%:*}"
    local window="${task_id##*:}"
    local socket_path="$SOCKET_DIR/$session"

    if tmux -S "$socket_path" kill-window -t "$session:$window" 2>/dev/null; then
        # Update database
        local updated=$(jq \
            --arg task_id "$task_id" \
            'if .tasks[$task_id] then .tasks[$task_id].status = "stopped" | .tasks[$task_id].stopped = (now | strftime("%Y-%m-%dT%H:%M:%SZ")) else . end' \
            "$BG_TASKS_DB")

        echo "$updated" > "$BG_TASKS_DB"

        echo -e "${GREEN}✓ Stopped background task: $task_id${NC}"
    else
        echo -e "${RED}✗ Failed to stop task: $task_id${NC}" >&2
        return 1
    fi
}

attach_to_task() {
    local task_id="$1"

    if [[ -z "$task_id" ]]; then
        echo -e "${RED}Usage: ts-bg attach <session>:<window>${NC}" >&2
        return 1
    fi

    local session="${task_id%:*}"
    local window="${task_id##*:}"
    local socket_path="$SOCKET_DIR/$session"

    if [[ -n "${TMUX:-}" ]]; then
        # Inside tmux - switch window
        tmux switch-client -t "$session:$window"
    else
        # Outside tmux - attach to session and select window
        tmux -S "$socket_path" attach-session -t "$session:$window"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUICK TEMPLATES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

start_dev_server() {
    local session="$1"
    local command="${2:-npm run dev}"

    start_background_task "$session" "dev-server" "$command" "dev-server"
    label_session "$session" "development,active"
}

start_test_watcher() {
    local session="$1"
    local command="${2:-npm test -- --watch}"

    start_background_task "$session" "test-watch" "$command" "test-watcher"
}

start_log_monitor() {
    local session="$1"
    local log_file="${2:-./logs/app.log}"

    start_background_task "$session" "logs" "tail -f $log_file" "log-monitor"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GRAFANA INTEGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

export_to_grafana() {
    echo -e "${CYAN}📊 Exporting to Grafana...${NC}"

    # Get all tasks
    local tasks=$(jq -c '.tasks | to_entries[]' "$BG_TASKS_DB")

    while IFS= read -r task; do
        local task_id=$(echo "$task" | jq -r '.key')
        local session=$(echo "$task" | jq -r '.value.session')
        local window=$(echo "$task" | jq -r '.value.window')
        local type=$(echo "$task" | jq -r '.value.type')
        local status=$(echo "$task" | jq -r '.value.status')

        # Get session labels
        local labels=$(jq -r --arg s "$session" '.sessions[$s].labels // [] | join(",")' "$LABELS_DB")

        echo -e "${BLUE}  • $task_id [$status] labels: $labels${NC}"
    done

    echo -e "${GREEN}✓ Task data ready for Grafana ingestion${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI INTERFACE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_help() {
    cat <<EOF
${CYAN}═══════════════════════════════════════════════════${NC}
${BOLD}TS Background Task Manager${NC}
${CYAN}═══════════════════════════════════════════════════${NC}

${BOLD}Session Labeling:${NC}
  ts-bg label <session> <labels>    Add labels to session
  ts-bg labels [session]             Show session labels
  ts-bg search <label>               Find sessions by label

${BOLD}Background Tasks:${NC}
  ts-bg start <session> <name> '<cmd>' [type]
                                     Start background task
  ts-bg list [session]               List all background tasks
  ts-bg stop <session>:<window>      Stop background task
  ts-bg attach <session>:<window>    Attach to background task

${BOLD}Quick Templates:${NC}
  ts-bg dev <session> [cmd]          Start dev server
  ts-bg test <session> [cmd]         Start test watcher
  ts-bg logs <session> [file]        Start log monitor

${BOLD}Integration:${NC}
  ts-bg export                       Export to Grafana

${BOLD}Examples:${NC}
  ${CYAN}# Label a session${NC}
  ts-bg label claude-blacklist 'backend,api,production'

  ${CYAN}# Start dev server${NC}
  ts-bg start claude-blacklist dev-server 'npm run dev' dev-server

  ${CYAN}# Quick dev server start${NC}
  ts-bg dev claude-blacklist

  ${CYAN}# Find all production sessions${NC}
  ts-bg search production

  ${CYAN}# Attach to background task${NC}
  ts-bg attach claude-blacklist:dev-server
EOF
}

main() {
    local command="${1:-}"
    shift || true

    case "$command" in
        "label")
            label_session "$@"
            ;;

        "labels")
            show_labels "$@"
            ;;

        "search")
            search_by_label "$@"
            ;;

        "start")
            start_background_task "$@"
            ;;

        "list")
            list_background_tasks "$@"
            ;;

        "stop")
            stop_background_task "$@"
            ;;

        "attach")
            attach_to_task "$@"
            ;;

        "dev")
            start_dev_server "$@"
            ;;

        "test")
            start_test_watcher "$@"
            ;;

        "logs")
            start_log_monitor "$@"
            ;;

        "export")
            export_to_grafana
            ;;

        "help"|"-h"|"--help"|"")
            show_help
            ;;

        *)
            echo -e "${RED}Unknown command: $command${NC}" >&2
            show_help
            exit 1
            ;;
    esac
}

main "$@"
