#!/bin/bash
# TS Unified - Advanced Tmux Session Manager with Plugin System
# Version: 3.0.0-unified
# Grafana Telemetry Integration + Constitutional Compliance

set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Version and Metadata
readonly TS_VERSION="3.0.0-unified"
readonly TS_BUILD_DATE="2025-10-01"
readonly TS_CONSTITUTIONAL_COMPLIANCE="v11.0"

# Paths
readonly TS_ROOT="/home/jclee/app/tmux"
readonly TS_CONFIG_DIR="${TS_CONFIG_DIR:-$HOME/.config/ts}"
readonly TS_PLUGIN_DIR="$TS_CONFIG_DIR/plugins"
readonly TS_HOOKS_DIR="$TS_CONFIG_DIR/hooks"
readonly TS_SOCKET_DIR="${TS_SOCKET_DIR:-/home/jclee/.tmux/sockets}"
readonly TS_STATE_DIR="$TS_CONFIG_DIR/state"
readonly TS_BACKUP_DIR="$TS_CONFIG_DIR/backups"

# Config Files
readonly TS_CONFIG="$TS_CONFIG_DIR/config.json"
readonly TS_PROJECTS="$TS_CONFIG_DIR/projects.json"
readonly TS_REGISTRY="$TS_CONFIG_DIR/registry.json"
readonly TS_AGENTS="$TS_CONFIG_DIR/agents.json"
readonly TS_LAST_SESSION="$TS_STATE_DIR/last_session"
readonly TS_LOCKFILE="$TS_STATE_DIR/.lock"

# Grafana Integration
readonly GRAFANA_LOKI_URL="${GRAFANA_LOKI_URL:-https://grafana.jclee.me/loki/api/v1/push}"
readonly GRAFANA_JOB_NAME="ts-command"

# Claude Integration
readonly CLAUDE_BIN="/home/jclee/.claude/local/claude"
readonly CLAUDE_MCP_CONFIG="/home/jclee/.claude/mcp.json"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly PURPLE='\033[0;35m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# Icons
readonly ICON_SUCCESS="✓"
readonly ICON_ERROR="✗"
readonly ICON_WARNING="⚠"
readonly ICON_INFO="ℹ"
readonly ICON_ROCKET="🚀"
readonly ICON_FOLDER="📁"
readonly ICON_SESSION="●"
readonly ICON_CLEANUP="🧹"
readonly ICON_PLUGIN="🔌"
readonly ICON_TELEMETRY="📊"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INITIALIZATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Create required directories
init_directories() {
    local dirs=(
        "$TS_CONFIG_DIR"
        "$TS_PLUGIN_DIR"
        "$TS_HOOKS_DIR"
        "$TS_SOCKET_DIR"
        "$TS_STATE_DIR"
        "$TS_BACKUP_DIR"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir" 2>/dev/null || {
            echo -e "${RED}${ICON_ERROR} Failed to create directory: $dir${NC}" >&2
            return 1
        }
    done
}

# Initialize default config if not exists
init_config() {
    if [[ ! -f "$TS_CONFIG" ]]; then
        cat > "$TS_CONFIG" <<'EOF'
{
  "version": "3.0.0",
  "socket_dir": "/home/jclee/.tmux/sockets",
  "default_shell": "/bin/bash",
  "auto_cleanup": true,
  "grafana_telemetry": true,
  "json_output": false,
  "plugins_enabled": true,
  "hooks_enabled": true,
  "constitutional_compliance": true,
  "features": {
    "auto_dedup": true,
    "session_persistence": true,
    "nested_tmux_detection": true,
    "claude_integration": true
  }
}
EOF
    fi

    if [[ ! -f "$TS_PROJECTS" ]]; then
        echo '{}' > "$TS_PROJECTS"
    fi

    if [[ ! -f "$TS_REGISTRY" ]]; then
        cat > "$TS_REGISTRY" <<'EOF'
{
  "sessions": {},
  "metadata": {
    "last_updated": "",
    "total_sessions": 0
  }
}
EOF
    fi

    if [[ ! -f "$TS_AGENTS" ]]; then
        echo '{"agents": []}' > "$TS_AGENTS"
    fi
}

# Check dependencies
check_dependencies() {
    local deps=(tmux jq curl)
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            missing+=("$dep")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo -e "${RED}${ICON_ERROR} Missing dependencies: ${missing[*]}${NC}" >&2
        echo -e "${YELLOW}Install with: sudo apt-get install ${missing[*]}${NC}" >&2
        return 1
    fi
}

# Initialize system
init_system() {
    check_dependencies || return 1
    init_directories || return 1
    init_config || return 1
    cleanup_dead_sockets
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GRAFANA TELEMETRY (Constitutional Requirement)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

log_to_grafana() {
    local command="$1"
    local args="${2:-}"
    local exit_code="${3:-0}"
    local duration_ms="${4:-0}"
    local metadata="${5:-{}}"

    # Check if telemetry is enabled
    local telemetry_enabled=$(jq -r '.grafana_telemetry // true' "$TS_CONFIG" 2>/dev/null)
    [[ "$telemetry_enabled" != "true" ]] && return 0

    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    local session_name="${TS_CURRENT_SESSION:-unknown}"
    local user="${USER:-unknown}"
    local hostname="${HOSTNAME:-unknown}"

    local log_entry=$(cat <<EOF
{
  "streams": [
    {
      "stream": {
        "job": "$GRAFANA_JOB_NAME",
        "command": "$command",
        "session": "$session_name",
        "user": "$user",
        "hostname": "$hostname",
        "version": "$TS_VERSION"
      },
      "values": [
        [
          "$(date +%s)000000000",
          $(jq -n \
            --arg cmd "$command" \
            --arg args "$args" \
            --argjson exit_code "$exit_code" \
            --argjson duration "$duration_ms" \
            --argjson meta "$metadata" \
            '{
              timestamp: $timestamp,
              command: $cmd,
              args: $args,
              exit_code: $exit_code,
              duration_ms: $duration,
              metadata: $meta
            }' | jq -c '.')
        ]
      ]
    }
  ]
}
EOF
)

    # Send to Grafana Loki (non-blocking)
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$log_entry" \
        "$GRAFANA_LOKI_URL" &>/dev/null &
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SOCKET MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cleanup_dead_sockets() {
    local cleaned=0

    for socket in "$TS_SOCKET_DIR"/*; do
        [[ -e "$socket" ]] || continue

        local name=$(basename "$socket")

        # Skip lock file
        [[ "$name" == ".lock" ]] && continue

        if [[ -S "$socket" ]] && ! tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            rm -f "$socket"
            ((cleaned++))
        fi
    done

    if [[ $cleaned -gt 0 ]]; then
        log_to_grafana "cleanup" "dead_sockets" 0 0 "{\"cleaned\": $cleaned}"
    fi
}

session_exists() {
    local name="$1"

    # Validate session name
    if [[ -z "$name" ]] || [[ "$name" =~ [[:space:]/:] ]]; then
        return 2
    fi

    local socket_path="$TS_SOCKET_DIR/$name"

    if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
        return 0
    fi
    return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION OPERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

list_sessions() {
    local output_format="${1:-text}"
    local start_time=$(date +%s%3N)

    if [[ "$output_format" == "json" ]]; then
        local sessions_json="["
        local first=true

        for socket in "$TS_SOCKET_DIR"/*; do
            if [[ -S "$socket" ]]; then
                local name=$(basename "$socket")

                if tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
                    local windows=$(tmux -S "$socket" list-sessions -F "#{session_windows}" 2>/dev/null | head -1)
                    local attached=$(tmux -S "$socket" list-sessions -F "#{?session_attached,1,0}" 2>/dev/null | head -1)
                    local path=$(tmux -S "$socket" display-message -p -F "#{pane_current_path}" -t "$name" 2>/dev/null)

                    [[ "$first" == true ]] || sessions_json+=","
                    first=false

                    sessions_json+=$(jq -n \
                        --arg name "$name" \
                        --argjson windows "$windows" \
                        --argjson attached "$attached" \
                        --arg path "$path" \
                        '{name: $name, windows: $windows, attached: ($attached == 1), path: $path}')
                fi
            fi
        done

        sessions_json+="]"
        echo "$sessions_json" | jq '.'
    else
        echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
        echo -e "${CYAN}${BOLD}            Active Sessions (TS v${TS_VERSION})${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

        local has_sessions=false

        for socket in "$TS_SOCKET_DIR"/*; do
            if [[ -S "$socket" ]]; then
                local name=$(basename "$socket")

                if tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
                    has_sessions=true
                    local info=$(tmux -S "$socket" list-sessions -F "#{session_windows} windows, #{?session_attached,attached,detached}" 2>/dev/null | head -1)
                    local pane_path=$(tmux -S "$socket" display-message -p -F "#{pane_current_path}" -t "$name" 2>/dev/null)

                    echo -e "  ${GREEN}${ICON_SESSION}${NC} ${BOLD}$name${NC} - $info"
                    [[ -n "$pane_path" ]] && echo -e "    ${BLUE}${ICON_FOLDER} $pane_path${NC}"
                fi
            fi
        done

        if [[ "$has_sessions" == false ]]; then
            echo -e "  ${YELLOW}No active sessions${NC}"
        fi

        if [[ -f "$TS_LAST_SESSION" ]]; then
            local last=$(cat "$TS_LAST_SESSION")
            echo ""
            echo -e "${PURPLE}Last session: $last${NC}"
        fi
    fi

    local end_time=$(date +%s%3N)
    local duration=$((end_time - start_time))
    log_to_grafana "list" "$output_format" 0 "$duration"
}

create_session() {
    local name="$1"
    local path="${2:-$(pwd)}"
    local socket_path="$TS_SOCKET_DIR/$name"
    local start_time=$(date +%s%3N)

    # Validate session name
    if [[ -z "$name" ]] || [[ "$name" =~ [[:space:]/:] ]]; then
        echo -e "${RED}${ICON_ERROR} Invalid session name: '$name'${NC}" >&2
        log_to_grafana "create" "$name" 1 0 '{"error": "invalid_name"}'
        return 1
    fi

    # Validate path
    if [[ ! -d "$path" ]]; then
        echo -e "${YELLOW}${ICON_WARNING} Path does not exist: $path${NC}" >&2
        path=$(pwd)
    fi

    # Clean up existing socket
    [[ -S "$socket_path" ]] && rm -f "$socket_path"

    echo -e "${GREEN}${ICON_ROCKET} Creating session: $name${NC}"
    echo -e "${BLUE}${ICON_FOLDER} Path: $path${NC}"

    # Create session
    if ! tmux -S "$socket_path" new-session -d -s "$name" -c "$path" 2>/dev/null; then
        echo -e "${RED}${ICON_ERROR} Failed to create session${NC}" >&2
        local end_time=$(date +%s%3N)
        log_to_grafana "create" "$name" 1 $((end_time - start_time)) '{"error": "tmux_failed"}'
        return 1
    fi

    # Save last session
    echo "$name" > "$TS_LAST_SESSION"

    # Run hooks
    run_hook "post_create" "$name" "$path"

    local end_time=$(date +%s%3N)
    log_to_grafana "create" "$name" 0 $((end_time - start_time)) "{\"path\": \"$path\"}"

    attach_session "$name"
}

attach_session() {
    local name="$1"
    local socket_path="$TS_SOCKET_DIR/$name"
    local start_time=$(date +%s%3N)

    if ! session_exists "$name"; then
        echo -e "${RED}${ICON_ERROR} Session does not exist: $name${NC}" >&2
        return 1
    fi

    echo -e "${CYAN}🔗 Attaching to session: $name${NC}"
    echo "$name" > "$TS_LAST_SESSION"

    if [[ -n "${TMUX:-}" ]]; then
        # Inside tmux - open in new window
        tmux new-window -n "$name" "tmux -S '$socket_path' attach-session -t '$name'"
    else
        # Outside tmux - attach directly
        local end_time=$(date +%s%3N)
        log_to_grafana "attach" "$name" 0 $((end_time - start_time))
        exec tmux -S "$socket_path" attach-session -t "$name"
    fi
}

kill_session() {
    local name="$1"
    local socket_path="$TS_SOCKET_DIR/$name"
    local start_time=$(date +%s%3N)

    if tmux -S "$socket_path" kill-session -t "$name" 2>/dev/null; then
        echo -e "${GREEN}${ICON_SUCCESS} Killed session: $name${NC}"
        rm -f "$socket_path"

        # Clear last session if it was the killed one
        if [[ -f "$TS_LAST_SESSION" ]] && [[ "$(cat "$TS_LAST_SESSION")" == "$name" ]]; then
            rm -f "$TS_LAST_SESSION"
        fi

        local end_time=$(date +%s%3N)
        log_to_grafana "kill" "$name" 0 $((end_time - start_time))
    else
        echo -e "${YELLOW}Session not found: $name${NC}"
        return 1
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PLUGIN SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

load_plugins() {
    local plugins_enabled=$(jq -r '.plugins_enabled // true' "$TS_CONFIG" 2>/dev/null)
    [[ "$plugins_enabled" != "true" ]] && return 0

    for plugin in "$TS_PLUGIN_DIR"/*.sh; do
        [[ -f "$plugin" ]] || continue
        [[ -x "$plugin" ]] || continue

        source "$plugin" 2>/dev/null || {
            echo -e "${YELLOW}${ICON_WARNING} Failed to load plugin: $(basename "$plugin")${NC}" >&2
        }
    done
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HOOK SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

run_hook() {
    local hook_name="$1"
    shift
    local args=("$@")

    local hooks_enabled=$(jq -r '.hooks_enabled // true' "$TS_CONFIG" 2>/dev/null)
    [[ "$hooks_enabled" != "true" ]] && return 0

    local hook_script="$TS_HOOKS_DIR/${hook_name}.sh"

    if [[ -x "$hook_script" ]]; then
        "$hook_script" "${args[@]}" 2>/dev/null || true
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN COMMAND HANDLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_help() {
    cat <<EOF
${CYAN}═══════════════════════════════════════════════════${NC}
${BOLD}TS - Unified Tmux Session Manager v${TS_VERSION}${NC}
${CYAN}═══════════════════════════════════════════════════${NC}

${BOLD}Session Management:${NC}
  ts                    Resume last session or list all
  ts list [--json]      List all active sessions
  ts <name> [path]      Create or attach to session
  ts kill <name>        Kill a session
  ts resume             Resume last session

${BOLD}Advanced Features:${NC}
  ts config             Edit configuration
  ts plugins            Manage plugins
  ts hooks              Manage hooks
  ts migrate            Migrate from old ts configs
  ts cleanup            Clean up dead sockets and backups

${BOLD}Information:${NC}
  ts version            Show version info
  ts help               Show this help

${BOLD}Grafana Telemetry:${NC}
  All commands are logged to Grafana Loki
  Job: $GRAFANA_JOB_NAME
  URL: $GRAFANA_LOKI_URL

${BOLD}Configuration:${NC}
  Config: $TS_CONFIG
  Sockets: $TS_SOCKET_DIR
  Plugins: $TS_PLUGIN_DIR
  Hooks: $TS_HOOKS_DIR

${YELLOW}Constitutional Compliance: $TS_CONSTITUTIONAL_COMPLIANCE${NC}
EOF
}

show_version() {
    cat <<EOF
${CYAN}═══════════════════════════════════════════════════${NC}
${BOLD}TS - Unified Tmux Session Manager${NC}
${CYAN}═══════════════════════════════════════════════════${NC}
${GREEN}Version:${NC} $TS_VERSION
${GREEN}Build Date:${NC} $TS_BUILD_DATE
${GREEN}Constitutional Compliance:${NC} $TS_CONSTITUTIONAL_COMPLIANCE
${GREEN}Tmux Version:${NC} $(tmux -V)
${GREEN}Socket Dir:${NC} $TS_SOCKET_DIR
${GREEN}Config Dir:${NC} $TS_CONFIG_DIR
${GREEN}Grafana Integration:${NC} Enabled
${GREEN}Plugin System:${NC} Enabled
${GREEN}Hook System:${NC} Enabled
EOF
}

main() {
    # Initialize system
    init_system || return 1

    # Load plugins
    load_plugins

    local command="${1:-}"
    shift || true

    case "$command" in
        "list"|"ls")
            list_sessions "${1:-text}"
            ;;

        "kill")
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts kill <name>${NC}"; return 1; }
            kill_session "$1"
            ;;

        "resume")
            if [[ -f "$TS_LAST_SESSION" ]]; then
                attach_session "$(cat "$TS_LAST_SESSION")"
            else
                list_sessions
            fi
            ;;

        "help"|"-h"|"--help")
            show_help
            ;;

        "version"|"-v"|"--version")
            show_version
            ;;

        "config")
            ${EDITOR:-nano} "$TS_CONFIG"
            ;;

        "cleanup")
            cleanup_dead_sockets
            echo -e "${GREEN}${ICON_CLEANUP} Cleanup complete${NC}"
            ;;

        "")
            if [[ -f "$TS_LAST_SESSION" ]]; then
                attach_session "$(cat "$TS_LAST_SESSION")"
            else
                list_sessions
            fi
            ;;

        *)
            local name="$command"
            local path="${1:-$(pwd)}"

            if session_exists "$name"; then
                attach_session "$name"
            else
                create_session "$name" "$path"
            fi
            ;;
    esac
}

# Run main
main "$@"
