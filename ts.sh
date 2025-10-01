#!/bin/bash
# TS Master - Unified Tmux Session Manager with CRUD
# Version: 5.0.0-integrated
# Constitutional Compliance: v11.0

set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

readonly TS_VERSION="5.0.0-integrated"
readonly TS_BUILD_DATE="2025-10-01"
readonly TS_ROOT="/home/jclee/app/tmux"
readonly TS_CONFIG_DIR="${TS_CONFIG_DIR:-$HOME/.config/ts}"
readonly TS_SOCKET_DIR="${TS_SOCKET_DIR:-/home/jclee/.tmux/sockets}"
readonly TS_STATE_DIR="$TS_CONFIG_DIR/state"
readonly TS_IPC_DIR="$TS_CONFIG_DIR/ipc"
readonly TS_BG_DIR="$TS_CONFIG_DIR/bg"

# Config Files
readonly TS_CONFIG="$TS_CONFIG_DIR/config.json"
readonly TS_DB="$TS_CONFIG_DIR/sessions.db"
readonly TS_LAST_SESSION="$TS_STATE_DIR/last_session"

# Integration
readonly GRAFANA_LOKI_URL="${GRAFANA_LOKI_URL:-https://grafana.jclee.me/loki/api/v1/push}"
readonly CLAUDE_BIN="/home/jclee/.claude/local/claude"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INITIALIZATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

init_system() {
    mkdir -p "$TS_CONFIG_DIR" "$TS_SOCKET_DIR" "$TS_STATE_DIR" "$TS_IPC_DIR" "$TS_BG_DIR" 2>/dev/null || true

    if [[ ! -f "$TS_CONFIG" ]]; then
        cat > "$TS_CONFIG" <<'EOF'
{
  "version": "5.0.0",
  "socket_dir": "/home/jclee/.tmux/sockets",
  "grafana_telemetry": true,
  "auto_dedup": true,
  "background_tasks": true,
  "ipc_enabled": true,
  "crud_enabled": true
}
EOF
    fi

    if [[ ! -f "$TS_DB" ]]; then
        cat > "$TS_DB" <<'EOF'
{
  "sessions": [],
  "version": "5.0.0",
  "last_updated": ""
}
EOF
    fi

    cleanup_dead_sockets
}

cleanup_dead_sockets() {
    for socket in "$TS_SOCKET_DIR"/*; do
        [[ -e "$socket" ]] || continue
        local name=$(basename "$socket")
        [[ "$name" == ".lock" ]] && continue

        if [[ -S "$socket" ]] && ! tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            rm -f "$socket"
        fi
    done
}

update_db_timestamp() {
    local temp=$(mktemp)
    jq ".last_updated = \"$(date -Iseconds)\"" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GRAFANA TELEMETRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

log_to_grafana() {
    local command="$1"
    local args="${2:-}"
    local exit_code="${3:-0}"

    local log_entry=$(cat <<EOF
{
  "streams": [{
    "stream": {
      "job": "ts-command",
      "command": "$command",
      "user": "${USER:-unknown}",
      "version": "$TS_VERSION"
    },
    "values": [["$(date +%s)000000000", "{\"command\":\"$command\",\"args\":\"$args\",\"exit_code\":$exit_code}"]]
  }]
}
EOF
)

    curl -s -X POST -H "Content-Type: application/json" -d "$log_entry" "$GRAFANA_LOKI_URL" &>/dev/null &
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATABASE HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

db_session_exists() {
    local name="$1"
    jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1
}

db_add_session() {
    local name="$1"
    local path="$2"
    local description="${3:-}"
    local tags="${4:-}"
    local auto_claude="${5:-false}"
    local socket_path="$TS_SOCKET_DIR/$name"

    local temp=$(mktemp)
    jq ".sessions += [{
        \"name\": \"$name\",
        \"path\": \"$path\",
        \"description\": \"$description\",
        \"tags\": \"$tags\",
        \"auto_claude\": $auto_claude,
        \"created_at\": \"$(date -Iseconds)\",
        \"updated_at\": \"$(date -Iseconds)\",
        \"socket\": \"$socket_path\",
        \"status\": \"active\"
    }]" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"
    update_db_timestamp
}

db_update_session() {
    local name="$1"
    shift

    local updates=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path) updates+=(".path = \"$2\""); shift 2 ;;
            --description) updates+=(".description = \"$2\""); shift 2 ;;
            --tags) updates+=(".tags = \"$2\""); shift 2 ;;
            --status) updates+=(".status = \"$2\""); shift 2 ;;
            --auto-claude) updates+=(".auto_claude = $2"); shift 2 ;;
            *) shift ;;
        esac
    done

    if [[ ${#updates[@]} -gt 0 ]]; then
        local update_expr=$(printf " | %s" "${updates[@]}")
        update_expr="${update_expr# | }"  # Remove leading " | "
        local temp=$(mktemp)
        jq "(.sessions[] | select(.name == \"$name\")) |= ($update_expr | .updated_at = \"$(date -Iseconds)\")" "$TS_DB" > "$temp"
        mv "$temp" "$TS_DB"
        update_db_timestamp
    fi
}

db_remove_session() {
    local name="$1"
    local temp=$(mktemp)
    jq ".sessions = [.sessions[] | select(.name != \"$name\")]" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"
    update_db_timestamp
}

db_get_session() {
    local name="$1"
    jq -r ".sessions[] | select(.name == \"$name\")" "$TS_DB"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

session_exists() {
    local name="$1"
    local socket_path="$TS_SOCKET_DIR/$name"

    if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
        return 0
    fi
    return 1
}

list_sessions() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}       TS Master v${TS_VERSION}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local sessions=$(jq -r '.sessions[].name' "$TS_DB" 2>/dev/null || echo "")

    if [[ -z "$sessions" ]]; then
        # Fallback to socket-based listing
        local has_sessions=false
        for socket in "$TS_SOCKET_DIR"/*; do
            if [[ -S "$socket" ]]; then
                local name=$(basename "$socket")
                [[ "$name" == ".lock" ]] && continue

                if tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
                    has_sessions=true
                    local info=$(tmux -S "$socket" list-sessions -F "#{session_windows} windows, #{?session_attached,attached,detached}" 2>/dev/null | head -1)
                    local path=$(tmux -S "$socket" display-message -p -F "#{pane_current_path}" -t "$name" 2>/dev/null)

                    echo -e "  ${GREEN}●${NC} ${BOLD}$name${NC} - $info"
                    [[ -n "$path" ]] && echo -e "    ${BLUE}📁 $path${NC}"
                fi
            fi
        done

        if [[ "$has_sessions" == false ]]; then
            echo -e "  ${YELLOW}No active sessions${NC}"
        fi
    else
        # Database-based listing
        printf "\n  %-20s %-10s %-40s %s\n" "NAME" "STATUS" "PATH" "DESCRIPTION"
        echo -e "  ────────────────────────────────────────────────────────────────────────────────────"

        while IFS= read -r name; do
            [[ -z "$name" ]] && continue

            local session_data=$(db_get_session "$name")
            local path=$(echo "$session_data" | jq -r '.path')
            local description=$(echo "$session_data" | jq -r '.description // ""' | cut -c1-30)
            local socket="$TS_SOCKET_DIR/$name"
            local status_icon

            if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
                status_icon="${GREEN}●${NC}"
            else
                status_icon="${RED}○${NC}"
            fi

            printf "  %-20s %b %-40s %s\n" "$name" "$status_icon" "${path:0:40}" "$description"
        done <<< "$sessions"
    fi

    if [[ -f "$TS_LAST_SESSION" ]]; then
        echo ""
        echo -e "${CYAN}Last: $(cat "$TS_LAST_SESSION")${NC}"
    fi

    log_to_grafana "list" "" 0
}

create_session() {
    local name="$1"
    local path="${2:-$(pwd)}"
    local description="${3:-}"
    local tags="${4:-}"
    local auto_claude="${5:-false}"
    local socket_path="$TS_SOCKET_DIR/$name"

    # Validate name
    if [[ -z "$name" ]] || [[ "$name" =~ [[:space:]/:] ]]; then
        echo -e "${RED}✗ Invalid session name${NC}" >&2
        return 1
    fi

    # Kill duplicate default tmux session
    if tmux has-session -t "$name" 2>/dev/null; then
        echo -e "${YELLOW}⚠️ Removing duplicate from default tmux${NC}"
        tmux kill-session -t "$name" 2>/dev/null || true
    fi

    # Resolve path
    path=$(realpath "$path" 2>/dev/null || echo "$path")

    if [[ ! -d "$path" ]]; then
        mkdir -p "$path" 2>/dev/null || true
    fi

    # Clean existing socket
    [[ -S "$socket_path" ]] && rm -f "$socket_path"

    echo -e "${GREEN}🚀 Creating session: $name${NC}"

    if ! tmux -S "$socket_path" new-session -d -s "$name" -c "$path" 2>/dev/null; then
        echo -e "${RED}✗ Failed to create session${NC}" >&2
        return 1
    fi

    # Add to database
    local should_auto_claude="false"
    if [[ "$auto_claude" == "true" ]] || [[ "$auto_claude" == "--claude" ]]; then
        should_auto_claude="true"
    fi
    db_add_session "$name" "$path" "$description" "$tags" "$should_auto_claude"

    # Auto-start Claude if requested
    if [[ "$should_auto_claude" == "true" ]]; then
        echo -e "${CYAN}🤖 Starting Claude in session...${NC}"
        tmux -S "$socket_path" send-keys -t "$name" "cd $path && claude --dangerously-skip-permissions --mcp-config /home/jclee/.claude/mcp.json" Enter
        sleep 1
    fi

    echo "$name" > "$TS_LAST_SESSION"
    log_to_grafana "create" "$name" 0

    echo -e "${GREEN}✓ Session created${NC}"
    echo -e "${BLUE}  Path: $path${NC}"
    [[ -n "$description" ]] && echo -e "${BLUE}  Description: $description${NC}"
    [[ -n "$tags" ]] && echo -e "${BLUE}  Tags: $tags${NC}"

    attach_session "$name"
}

attach_session() {
    local name="$1"
    local socket_path="$TS_SOCKET_DIR/$name"

    if ! session_exists "$name"; then
        # Check if in database
        if db_session_exists "$name"; then
            echo -e "${YELLOW}⚠️  Session exists in database but tmux session is not active${NC}"
            echo -n -e "${CYAN}Recreate session? [Y/n]: ${NC}"
            read -r response
            if [[ -z "$response" ]] || [[ "$response" =~ ^[Yy]$ ]]; then
                local session_data=$(db_get_session "$name")
                local path=$(echo "$session_data" | jq -r '.path')
                local auto_claude=$(echo "$session_data" | jq -r '.auto_claude // false')

                tmux -S "$socket_path" new-session -d -s "$name" -c "$path" 2>/dev/null || {
                    echo -e "${RED}✗ Failed to recreate session${NC}" >&2
                    return 1
                }

                # Auto-start Claude if configured
                if [[ "$auto_claude" == "true" ]]; then
                    echo -e "${CYAN}🤖 Starting Claude in session...${NC}"
                    tmux -S "$socket_path" send-keys -t "$name" "cd $path && claude --dangerously-skip-permissions --mcp-config /home/jclee/.claude/mcp.json" Enter
                    sleep 1
                fi
            else
                return 1
            fi
        else
            echo -e "${RED}✗ Session does not exist: $name${NC}" >&2
            return 1
        fi
    fi

    echo -e "${CYAN}🔗 Attaching to: $name${NC}"
    echo "$name" > "$TS_LAST_SESSION"

    if [[ -n "${TMUX:-}" ]]; then
        tmux new-window -n "$name" "tmux -S '$socket_path' attach-session -t '$name'"
    else
        log_to_grafana "attach" "$name" 0
        exec tmux -S "$socket_path" attach-session -t "$name"
    fi
}

kill_session() {
    local name="$1"
    local force="${2:-false}"
    local socket_path="$TS_SOCKET_DIR/$name"

    # Confirmation unless forced
    if [[ "$force" != "--force" ]] && [[ "$force" != "-f" ]]; then
        echo -e "${YELLOW}⚠️  Are you sure you want to delete session: $name?${NC}"
        echo -n -e "${CYAN}Type 'yes' to confirm: ${NC}"
        read -r response
        if [[ "$response" != "yes" ]]; then
            echo -e "${BLUE}✓ Deletion cancelled${NC}"
            return 0
        fi
    fi

    # Kill socket-based session
    if tmux -S "$socket_path" kill-session -t "$name" 2>/dev/null; then
        echo -e "${GREEN}✓ Killed socket session: $name${NC}"
        rm -f "$socket_path"
    fi

    # Kill default tmux session
    if tmux has-session -t "$name" 2>/dev/null; then
        tmux kill-session -t "$name" 2>/dev/null || true
        echo -e "${GREEN}✓ Killed default tmux session: $name${NC}"
    fi

    # Remove from database
    if db_session_exists "$name"; then
        db_remove_session "$name"
        echo -e "${GREEN}✓ Removed from database${NC}"
    fi

    [[ -f "$TS_LAST_SESSION" ]] && [[ "$(cat "$TS_LAST_SESSION")" == "$name" ]] && rm -f "$TS_LAST_SESSION"

    log_to_grafana "kill" "$name" 0
}

clean_all() {
    local force="${1:-false}"

    echo -e "${YELLOW}🧹 Cleaning all sessions...${NC}"

    # Confirmation unless forced
    if [[ "$force" != "--force" ]] && [[ "$force" != "-f" ]]; then
        echo -e "${RED}⚠️  This will delete ALL sessions!${NC}"
        echo -n -e "${CYAN}Type 'yes' to confirm: ${NC}"
        read -r response
        if [[ "$response" != "yes" ]]; then
            echo -e "${BLUE}✓ Cleanup cancelled${NC}"
            return 0
        fi
    fi

    # Socket-based sessions
    for socket in "$TS_SOCKET_DIR"/*; do
        if [[ -S "$socket" ]]; then
            local name=$(basename "$socket")
            [[ "$name" == ".lock" ]] && continue
            echo "  Killing: $name"
            tmux -S "$socket" kill-session -t "$name" 2>/dev/null || true
            rm -f "$socket"
        fi
    done

    # Default tmux sessions
    if tmux ls 2>/dev/null | grep -q '^'; then
        tmux ls 2>/dev/null | awk -F: '{print $1}' | while read session; do
            echo "  Killing default: $session"
            tmux kill-session -t "$session" 2>/dev/null || true
        done
    fi

    # Clear database
    cat > "$TS_DB" <<'EOF'
{
  "sessions": [],
  "version": "5.0.0",
  "last_updated": ""
}
EOF
    update_db_timestamp

    rm -f "$TS_LAST_SESSION"
    echo -e "${GREEN}✓ All sessions cleaned${NC}"
    log_to_grafana "clean" "" 0
}

propose_clean() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}     Proposed Sessions to Clean${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local inactive_sessions=()
    local old_sessions=()
    local total_proposed=0

    # Get current timestamp
    local now=$(date +%s)
    local week_ago=$((now - 604800))  # 7 days in seconds

    echo -e "\n${BOLD}Analyzing sessions...${NC}\n"

    # Check all sessions in database
    local sessions=$(jq -r '.sessions[].name' "$TS_DB" 2>/dev/null || echo "")

    if [[ -z "$sessions" ]]; then
        echo -e "${GREEN}✓ No sessions in database${NC}"
        return 0
    fi

    printf "  %-20s %-12s %-15s %s\n" "NAME" "STATUS" "LAST UPDATED" "REASON"
    echo -e "  ────────────────────────────────────────────────────────────────────"

    while IFS= read -r name; do
        [[ -z "$name" ]] && continue

        local session_data=$(db_get_session "$name")
        local socket="$TS_SOCKET_DIR/$name"
        local updated=$(echo "$session_data" | jq -r '.updated_at')
        local updated_ts=$(date -d "$updated" +%s 2>/dev/null || echo "0")
        local reason=""
        local should_clean=false

        # Check if session is inactive
        if [[ ! -S "$socket" ]] || ! tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            reason="Inactive (tmux not running)"
            inactive_sessions+=("$name")
            should_clean=true
        # Check if session is old (> 7 days)
        elif [[ $updated_ts -lt $week_ago ]]; then
            local days_old=$(( (now - updated_ts) / 86400 ))
            reason="Old (${days_old} days)"
            old_sessions+=("$name")
            should_clean=true
        fi

        if [[ "$should_clean" == true ]]; then
            printf "  %-20s %-12s %-15s %s\n" "$name" "${RED}○${NC}" "$updated" "$reason"
            ((total_proposed++))
        fi
    done <<< "$sessions"

    echo ""

    if [[ $total_proposed -eq 0 ]]; then
        echo -e "${GREEN}✓ No sessions need cleaning${NC}"
        return 0
    fi

    echo -e "${YELLOW}Proposed to clean: $total_proposed session(s)${NC}"
    echo -e "${BLUE}  Inactive: ${#inactive_sessions[@]}${NC}"
    echo -e "${BLUE}  Old (>7 days): ${#old_sessions[@]}${NC}"

    echo -e "\n${CYAN}Options:${NC}"
    echo -e "  1. Clean all proposed sessions"
    echo -e "  2. Clean only inactive sessions"
    echo -e "  3. Clean only old sessions"
    echo -e "  4. Cancel"
    echo ""
    echo -n -e "${CYAN}Select option [1-4]: ${NC}"
    read -r option

    case "$option" in
        1)
            echo -e "\n${YELLOW}Cleaning all proposed sessions...${NC}"
            for name in "${inactive_sessions[@]}" "${old_sessions[@]}"; do
                kill_session "$name" --force
            done
            ;;
        2)
            echo -e "\n${YELLOW}Cleaning inactive sessions...${NC}"
            for name in "${inactive_sessions[@]}"; do
                kill_session "$name" --force
            done
            ;;
        3)
            echo -e "\n${YELLOW}Cleaning old sessions...${NC}"
            for name in "${old_sessions[@]}"; do
                kill_session "$name" --force
            done
            ;;
        *)
            echo -e "${BLUE}✓ Cleanup cancelled${NC}"
            return 0
            ;;
    esac

    echo -e "\n${GREEN}✓ Cleanup complete${NC}"
    log_to_grafana "propose_clean" "completed" 0
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CRUD OPERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

crud_read() {
    local name="$1"
    local format="${2:-pretty}"

    if ! db_session_exists "$name"; then
        echo -e "${RED}✗ Session not found: $name${NC}" >&2
        return 1
    fi

    local session_data=$(db_get_session "$name")

    if [[ "$format" == "json" ]]; then
        echo "$session_data" | jq '.'
        return 0
    fi

    # Pretty format
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}    Session: $name${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local path=$(echo "$session_data" | jq -r '.path')
    local description=$(echo "$session_data" | jq -r '.description')
    local tags=$(echo "$session_data" | jq -r '.tags')
    local created=$(echo "$session_data" | jq -r '.created_at')
    local updated=$(echo "$session_data" | jq -r '.updated_at')
    local socket=$(echo "$session_data" | jq -r '.socket')

    echo -e "\n${BOLD}Basic Information:${NC}"
    echo -e "  Name:        $name"
    echo -e "  Path:        $path"
    [[ "$description" != "null" ]] && [[ -n "$description" ]] && echo -e "  Description: $description"
    [[ "$tags" != "null" ]] && [[ -n "$tags" ]] && echo -e "  Tags:        $tags"

    echo -e "\n${BOLD}Timestamps:${NC}"
    echo -e "  Created:     $created"
    echo -e "  Updated:     $updated"

    # Check actual tmux status
    if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
        echo -e "\n${BOLD}Tmux Status:${NC}"
        local tmux_info=$(tmux -S "$socket" list-sessions -t "$name" -F "#{session_windows} windows, #{?session_attached,attached,detached}" 2>/dev/null)
        echo -e "  ${GREEN}●${NC} Active - $tmux_info"

        local cmd=$(tmux -S "$socket" display-message -t "$name" -p "#{pane_current_command}" 2>/dev/null)
        local pid=$(tmux -S "$socket" display-message -t "$name" -p "#{pane_pid}" 2>/dev/null)
        echo -e "  Command:     $cmd"
        echo -e "  PID:         $pid"
    else
        echo -e "\n${BOLD}Tmux Status:${NC}"
        echo -e "  ${RED}○${NC} Inactive"
    fi

    echo ""
}

crud_update() {
    local name="$1"
    shift

    if ! db_session_exists "$name"; then
        echo -e "${RED}✗ Session not found: $name${NC}" >&2
        return 1
    fi

    if [[ $# -eq 0 ]]; then
        echo -e "${YELLOW}⚠️  No updates specified${NC}" >&2
        echo -e "${BLUE}Usage: ts update <name> [--path <path>] [--description <desc>] [--tags <tags>] [--status <status>]${NC}" >&2
        return 1
    fi

    db_update_session "$name" "$@"

    echo -e "${GREEN}✓ Session updated: $name${NC}"
    log_to_grafana "update" "$name" 0
}

crud_search() {
    local query="$1"
    local field="${2:-all}"

    if [[ -z "$query" ]]; then
        echo -e "${RED}✗ Search query required${NC}" >&2
        return 1
    fi

    echo -e "${CYAN}Searching for: $query (field: $field)${NC}\n"

    local results
    case "$field" in
        name) results=$(jq -r ".sessions[] | select(.name | contains(\"$query\")) | .name" "$TS_DB") ;;
        path) results=$(jq -r ".sessions[] | select(.path | contains(\"$query\")) | .name" "$TS_DB") ;;
        tags) results=$(jq -r ".sessions[] | select(.tags | contains(\"$query\")) | .name" "$TS_DB") ;;
        description) results=$(jq -r ".sessions[] | select(.description | contains(\"$query\")) | .name" "$TS_DB") ;;
        all) results=$(jq -r ".sessions[] | select(.name + .path + .tags + .description | contains(\"$query\")) | .name" "$TS_DB") ;;
        *)
            echo -e "${RED}✗ Invalid field: $field${NC}" >&2
            return 1
            ;;
    esac

    if [[ -z "$results" ]]; then
        echo -e "${YELLOW}No sessions found matching: $query${NC}"
        return 0
    fi

    echo -e "${GREEN}Found sessions:${NC}"
    while IFS= read -r name; do
        echo -e "  ${BLUE}●${NC} $name"
    done <<< "$results"
}

crud_sync() {
    echo -e "${CYAN}🔄 Syncing database with tmux sessions...${NC}\n"

    local synced=0
    local cleaned=0

    # Update status for all sessions in database
    local sessions=$(jq -r '.sessions[].name' "$TS_DB")
    while IFS= read -r name; do
        [[ -z "$name" ]] && continue

        local socket_path="$TS_SOCKET_DIR/$name"
        local new_status

        if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
            new_status="active"
        else
            new_status="inactive"
        fi

        db_update_session "$name" --status "$new_status"
        echo -e "  ${BLUE}$name${NC}: $new_status"
        ((synced++))
    done <<< "$sessions"

    # Clean dead sockets
    for socket in "$TS_SOCKET_DIR"/*; do
        [[ -e "$socket" ]] || continue
        local name=$(basename "$socket")

        if [[ -S "$socket" ]] && ! tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            rm -f "$socket"
            echo -e "  ${YELLOW}Cleaned dead socket: $name${NC}"
            ((cleaned++))
        fi
    done

    echo ""
    echo -e "${GREEN}✓ Sync complete${NC}"
    echo -e "${BLUE}  Synced: $synced session(s)${NC}"
    echo -e "${BLUE}  Cleaned: $cleaned socket(s)${NC}"

    log_to_grafana "sync" "all" 0
}

discover_sessions() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}     Auto-Discovering Projects${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local app_dir="/home/jclee/app"
    local synology_dir="/home/jclee/synology"
    local discovered=0
    local skipped=0

    echo -e "\n${BOLD}Scanning directories...${NC}\n"

    # Scan /app
    if [[ -d "$app_dir" ]]; then
        echo -e "${CYAN}📁 /home/jclee/app:${NC}"
        for dir in "$app_dir"/*; do
            if [[ -d "$dir" && ! -L "$dir" ]]; then
                local name=$(basename "$dir")
                [[ "$name" =~ ^\. ]] && continue

                if db_session_exists "$name"; then
                    echo -e "  ${YELLOW}⊖${NC} $name (already exists)"
                    ((skipped++))
                else
                    echo -e "  ${GREEN}+${NC} $name"

                    local auto_claude="false"
                    local tags="app"

                    # Check for dev indicators
                    if [[ -f "$dir/package.json" ]] || [[ -f "$dir/tsconfig.json" ]] || [[ -f "$dir/go.mod" ]]; then
                        auto_claude="true"
                        tags="app,dev"
                    fi

                    db_add_session "$name" "$dir" "Project in /app" "$tags" "$auto_claude"
                    ((discovered++))
                fi
            fi
        done
    fi

    echo ""

    # Scan /synology
    if [[ -d "$synology_dir" ]]; then
        echo -e "${CYAN}📁 /home/jclee/synology:${NC}"
        for dir in "$synology_dir"/*; do
            if [[ -d "$dir" && ! -L "$dir" ]]; then
                local name=$(basename "$dir")
                [[ "$name" =~ ^\. ]] && continue

                # Use original name (no prefix)
                if db_session_exists "$name"; then
                    echo -e "  ${YELLOW}⊖${NC} $name (already exists)"
                    ((skipped++))
                else
                    echo -e "  ${GREEN}+${NC} $name"

                    local auto_claude="false"
                    local tags="synology"

                    # Check for dev indicators
                    if [[ -f "$dir/package.json" ]] || [[ -f "$dir/docker-compose.yml" ]]; then
                        auto_claude="true"
                        tags="synology,dev"
                    fi

                    db_add_session "$name" "$dir" "Project in /synology" "$tags" "$auto_claude"
                    ((discovered++))
                fi
            fi
        done
    fi

    echo ""
    echo -e "${GREEN}✓ Discovery complete${NC}"
    echo -e "${CYAN}  Discovered: $discovered new session(s)${NC}"
    echo -e "${CYAN}  Skipped: $skipped existing session(s)${NC}"

    log_to_grafana "discover" "completed" 0
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKGROUND TASK MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

bg_start() {
    local task_name="$1"
    local command="$2"
    local session_name="bg-$task_name"

    if session_exists "$session_name"; then
        echo -e "${YELLOW}⚠️  Task already running: $task_name${NC}"
        return 1
    fi

    create_session "$session_name" "$(pwd)" "Background task: $task_name" "background"
    tmux -S "$TS_SOCKET_DIR/$session_name" send-keys -t "$session_name" "$command" Enter

    echo "$task_name:$(date +%s):$command" >> "$TS_BG_DIR/tasks.log"
    echo -e "${GREEN}✓ Started background task: $task_name${NC}"
    log_to_grafana "bg_start" "$task_name" 0
}

bg_list() {
    echo -e "${CYAN}Background Tasks:${NC}"

    if [[ ! -f "$TS_BG_DIR/tasks.log" ]] || [[ ! -s "$TS_BG_DIR/tasks.log" ]]; then
        echo -e "  ${YELLOW}No background tasks${NC}"
        return
    fi

    while IFS=: read -r task_name timestamp command; do
        local session_name="bg-$task_name"
        if session_exists "$session_name"; then
            echo -e "  ${GREEN}●${NC} $task_name - ${command:0:50}..."
        fi
    done < "$TS_BG_DIR/tasks.log"
}

bg_stop() {
    local task_name="$1"
    local session_name="bg-$task_name"

    if session_exists "$session_name"; then
        kill_session "$session_name"
        echo -e "${GREEN}✓ Stopped: $task_name${NC}"
        log_to_grafana "bg_stop" "$task_name" 0
    else
        echo -e "${YELLOW}⚠️  Task not running: $task_name${NC}"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IPC (Inter-Process Communication)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ipc_send() {
    local target_session="$1"
    local message="$2"

    if ! session_exists "$target_session"; then
        echo -e "${RED}✗ Target session not found: $target_session${NC}" >&2
        return 1
    fi

    local socket_path="$TS_SOCKET_DIR/$target_session"
    tmux -S "$socket_path" send-keys -t "$target_session" "$message" Enter

    echo -e "${GREEN}✓ Message sent to $target_session${NC}"
    log_to_grafana "ipc_send" "$target_session" 0
}

ipc_broadcast() {
    local message="$1"
    local count=0

    for socket in "$TS_SOCKET_DIR"/*; do
        if [[ -S "$socket" ]]; then
            local name=$(basename "$socket")
            [[ "$name" == ".lock" ]] && continue

            if tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
                tmux -S "$socket" send-keys -t "$name" "$message" Enter
                ((count++))
            fi
        fi
    done

    echo -e "${GREEN}✓ Broadcast to $count sessions${NC}"
    log_to_grafana "ipc_broadcast" "$count" 0
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELP AND VERSION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_help() {
    cat <<EOF
${CYAN}═══════════════════════════════════════════════════${NC}
${BOLD}TS Master - Unified Tmux Session Manager v${TS_VERSION}${NC}
${CYAN}═══════════════════════════════════════════════════${NC}

${BOLD}Session Management:${NC}
  ts                          Resume last or list sessions
  ts list                     List all active sessions
  ts <name> [path] [desc] [tags]  Create/attach to session
  ts kill <name> [--force]    Kill specific session (with confirmation)
  ts clean [--force]          Clean all sessions (with confirmation)
  ts propose                  Propose sessions to clean (smart cleanup)
  ts resume                   Resume last session

${BOLD}CRUD Operations:${NC}
  ts create <name> [path] [desc] [tags] [--claude]  Create with metadata
  ts read <name> [format]                           Read session info (pretty|json)
  ts update <name> [options]                        Update session metadata
    --path <path>                     Update working directory
    --description <desc>              Update description
    --tags <tags>                     Update tags
    --status <status>                 Update status
    --auto-claude <true|false>        Enable/disable auto Claude start
  ts search <query> [field]                         Search sessions
  ts sync                                           Sync database with tmux

${BOLD}Background Tasks:${NC}
  ts bg start <name> <cmd>    Start background task
  ts bg list                  List background tasks
  ts bg stop <name>           Stop background task
  ts bg attach <name>         Attach to background task

${BOLD}IPC (Inter-Process Communication):${NC}
  ts ipc send <session> <msg>    Send message to session
  ts ipc broadcast <msg>         Broadcast to all sessions

${BOLD}System:${NC}
  ts version                  Show version info
  ts help                     Show this help

${BOLD}Features:${NC}
  ✓ Full CRUD operations with metadata
  ✓ JSON database with search & filter
  ✓ Socket-based session isolation
  ✓ Auto duplicate detection/cleanup
  ✓ Grafana telemetry integration
  ✓ Background task management
  ✓ Inter-session communication
  ✓ Constitutional compliance v11.0

${BOLD}Examples:${NC}
  ${CYAN}# Create session with metadata${NC}
  ts create myproject /home/user/myproject "My project" "dev,web"

  ${CYAN}# Create session with auto-Claude${NC}
  ts create myproject /home/user/myproject "My project" "dev,web" --claude

  ${CYAN}# Read session info${NC}
  ts read myproject

  ${CYAN}# Update session - enable auto Claude${NC}
  ts update myproject --auto-claude true

  ${CYAN}# Update session metadata${NC}
  ts update myproject --path /new/path --tags "prod,api"

  ${CYAN}# Search sessions${NC}
  ts search "dev" tags

  ${CYAN}# Quick create and attach${NC}
  ts myproject

${BOLD}Configuration:${NC}
  Config:   $TS_CONFIG
  Database: $TS_DB
  Sockets:  $TS_SOCKET_DIR
  State:    $TS_STATE_DIR
EOF
}

show_version() {
    cat <<EOF
${CYAN}═══════════════════════════════════════════════════${NC}
${BOLD}TS Master - Unified Tmux Session Manager${NC}
${CYAN}═══════════════════════════════════════════════════${NC}
${GREEN}Version:${NC} $TS_VERSION
${GREEN}Build:${NC} $TS_BUILD_DATE
${GREEN}Tmux:${NC} $(tmux -V)
${GREEN}Grafana:${NC} Enabled
${GREEN}Features:${NC} Session + CRUD + Background + IPC
${GREEN}Database:${NC} $TS_DB
EOF
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN COMMAND HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    init_system

    local command="${1:-}"
    shift || true

    case "$command" in
        # Session Management
        "list"|"ls"|"")
            if [[ -z "$command" ]] && [[ -f "$TS_LAST_SESSION" ]]; then
                attach_session "$(cat "$TS_LAST_SESSION")"
            else
                list_sessions
            fi
            ;;

        "kill"|"delete"|"del"|"rm")
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts kill <name> [--force]${NC}"; exit 1; }
            kill_session "$1" "$2"
            ;;

        "clean")
            clean_all "$1"
            ;;

        "propose"|"propose-clean"|"pc")
            propose_clean
            ;;

        "resume")
            if [[ -f "$TS_LAST_SESSION" ]]; then
                attach_session "$(cat "$TS_LAST_SESSION")"
            else
                echo -e "${YELLOW}No last session${NC}"
                list_sessions
            fi
            ;;

        # CRUD Operations
        "create"|"c")
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts create <name> [path] [description] [tags]${NC}"; exit 1; }
            create_session "$@"
            ;;

        "read"|"r"|"show"|"info")
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts read <name> [format]${NC}"; exit 1; }
            crud_read "$@"
            ;;

        "update"|"u"|"edit")
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts update <name> [options]${NC}"; exit 1; }
            crud_update "$@"
            ;;

        "search"|"find"|"s")
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts search <query> [field]${NC}"; exit 1; }
            crud_search "$@"
            ;;

        "sync")
            crud_sync
            ;;

        "discover"|"disc"|"scan")
            discover_sessions
            ;;

        "register"|"regi"|"reg")
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts register <name> [path] [--open]${NC}"; exit 1; }
            local reg_name="$1"
            shift

            local reg_path="$(pwd)"
            local reg_desc="Registered manually"
            local reg_tags="manual"
            local auto_open="false"

            # Parse arguments
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --open|-o)
                        auto_open="true"
                        shift
                        ;;
                    *)
                        if [[ -d "$1" ]]; then
                            reg_path="$1"
                        fi
                        shift
                        ;;
                esac
            done

            if db_session_exists "$reg_name"; then
                echo -e "${YELLOW}⚠️  Session '$reg_name' already exists${NC}"
                ts read "$reg_name"
                exit 1
            fi

            # Detect if dev project
            local auto_claude="false"
            if [[ -f "$reg_path/package.json" ]] || [[ -f "$reg_path/tsconfig.json" ]] || [[ -f "$reg_path/go.mod" ]] || [[ -f "$reg_path/docker-compose.yml" ]]; then
                auto_claude="true"
                reg_tags="manual,dev"
            fi

            db_add_session "$reg_name" "$reg_path" "$reg_desc" "$reg_tags" "$auto_claude"

            echo -e "${GREEN}✓ Session registered: $reg_name${NC}"
            echo -e "${CYAN}  Path: $reg_path${NC}"
            echo -e "${CYAN}  Auto-Claude: $auto_claude${NC}"
            log_to_grafana "register" "$reg_name" 0

            # Auto-open if requested
            if [[ "$auto_open" == "true" ]]; then
                echo -e "${CYAN}→ Opening session...${NC}"
                attach_session "$reg_name"
            fi
            ;;

        # Background Tasks
        "bg")
            local bg_cmd="${1:-list}"
            shift || true

            case "$bg_cmd" in
                start)
                    [[ -n "${1:-}" ]] && [[ -n "${2:-}" ]] || { echo -e "${RED}Usage: ts bg start <name> <command>${NC}"; exit 1; }
                    bg_start "$1" "$2"
                    ;;
                list)
                    bg_list
                    ;;
                stop)
                    [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts bg stop <name>${NC}"; exit 1; }
                    bg_stop "$1"
                    ;;
                attach)
                    [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts bg attach <name>${NC}"; exit 1; }
                    attach_session "bg-$1"
                    ;;
                *)
                    echo -e "${RED}Unknown bg command: $bg_cmd${NC}"
                    echo -e "Try: ts bg {start|list|stop|attach}"
                    exit 1
                    ;;
            esac
            ;;

        # IPC
        "ipc")
            local ipc_cmd="${1:-}"
            shift || true

            case "$ipc_cmd" in
                send)
                    [[ -n "${1:-}" ]] && [[ -n "${2:-}" ]] || { echo -e "${RED}Usage: ts ipc send <session> <message>${NC}"; exit 1; }
                    ipc_send "$1" "$2"
                    ;;
                broadcast)
                    [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts ipc broadcast <message>${NC}"; exit 1; }
                    ipc_broadcast "$1"
                    ;;
                *)
                    echo -e "${RED}Unknown ipc command: $ipc_cmd${NC}"
                    echo -e "Try: ts ipc {send|broadcast}"
                    exit 1
                    ;;
            esac
            ;;

        # System
        "help"|"-h"|"--help")
            show_help
            ;;

        "version"|"-v"|"--version")
            show_version
            ;;

        # Default: Session command or create/attach
        *)
            local name="$command"

            # Check if this is a send-keys command (session has additional args)
            if session_exists "$name" && [[ -n "${1:-}" ]]; then
                # Send command to session
                local session_cmd="$*"
                local socket_path="$TS_SOCKET_DIR/$name"

                echo -e "${CYAN}→ Sending to $name: ${BOLD}$session_cmd${NC}"
                tmux -S "$socket_path" send-keys -t "$name" "$session_cmd" Enter

                echo -e "${GREEN}✓ Command sent${NC}"
                log_to_grafana "send_command" "$name" 0
            elif session_exists "$name"; then
                # Just attach
                attach_session "$name"
            else
                # Create new session
                local path="${1:-$(pwd)}"
                local description="${2:-}"
                local tags="${3:-}"
                create_session "$name" "$path" "$description" "$tags"
            fi
            ;;
    esac
}

main "$@"
