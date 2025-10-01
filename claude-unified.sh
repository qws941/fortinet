#!/bin/bash
# Claude Unified Command System
# All-in-one claude command for everything

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
MAGENTA='\033[0;95m'
NC='\033[0m'

# Configuration
SOCKET_DIR="/home/jclee/.tmux/sockets"
CONFIG_DIR="$HOME/.config/ts"
CLAUDE_HOME="/home/jclee/.claude"
CLAUDE_BIN="$CLAUDE_HOME/local/claude --dangerously-skip-permissions --mcp-config $CLAUDE_HOME/mcp.json"
CLAUDE_SOCKET="$SOCKET_DIR/claude"

# Ensure directories exist
mkdir -p "$CONFIG_DIR" "$SOCKET_DIR"

# Claude session management
claude_session_exists() {
    [[ -S "$CLAUDE_SOCKET" ]] && tmux -S "$CLAUDE_SOCKET" has-session -t claude 2>/dev/null
}

# Start or attach to Claude session
start_claude_session() {
    if ! claude_session_exists; then
        echo -e "${CYAN}🚀 Starting Claude session...${NC}"
        tmux -S "$CLAUDE_SOCKET" new-session -d -s claude -c "$CLAUDE_HOME" "$CLAUDE_BIN"
        sleep 2
        echo -e "${GREEN}✓ Claude session started${NC}"
    fi
}

# Attach to Claude session
attach_claude() {
    start_claude_session

    if [[ -n "${TMUX:-}" ]]; then
        echo -e "${YELLOW}📌 Opening Claude in new tmux window${NC}"
        tmux new-window -n claude "tmux -S '$CLAUDE_SOCKET' attach-session -t claude"
    else
        echo -e "${CYAN}🔗 Attaching to Claude session${NC}"
        exec tmux -S "$CLAUDE_SOCKET" attach-session -t claude
    fi
}

# Send command to Claude
send_to_claude() {
    local command="$*"

    if [[ -z "$command" ]]; then
        echo -e "${RED}Error: No command provided${NC}"
        return 1
    fi

    start_claude_session

    echo -e "${CYAN}📤 Sending to Claude: ${YELLOW}$command${NC}"
    tmux -S "$CLAUDE_SOCKET" send-keys -t claude "$command" Enter
    echo -e "${GREEN}✓ Command sent${NC}"

    # Show last few lines of output after a brief delay
    sleep 2
    echo -e "${BLUE}Recent output:${NC}"
    tmux -S "$CLAUDE_SOCKET" capture-pane -t claude -p | tail -5
}

# List all sessions (ts integration)
list_all_sessions() {
    echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}              All Active Sessions${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"

    local has_sessions=false

    for socket in "$SOCKET_DIR"/*; do
        [[ ! -S "$socket" ]] && continue

        local name=$(basename "$socket")
        if tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            has_sessions=true
            local info=$(tmux -S "$socket" list-sessions -F "#{session_windows} windows, #{?session_attached,attached,detached}" 2>/dev/null | head -1)
            local pane_path=$(tmux -S "$socket" display-message -p -F "#{pane_current_path}" -t "$name" 2>/dev/null)

            if [[ "$name" == "claude" ]]; then
                echo -e "  ${GREEN}🤖${NC} ${CYAN}$name${NC} - $info"
            else
                echo -e "  ${GREEN}●${NC} $name - $info"
            fi

            [[ -n "$pane_path" ]] && echo -e "    ${BLUE}📁 $pane_path${NC}"
        fi
    done

    if [[ "$has_sessions" == false ]]; then
        echo -e "  ${YELLOW}No active sessions${NC}"
    fi
}

# Session management
manage_session() {
    local action="$1"
    local session="${2:-}"

    case "$action" in
        "kill")
            if [[ -z "$session" ]]; then
                echo -e "${RED}Error: Session name required${NC}"
                echo -e "${YELLOW}Usage: claude kill <session>${NC}"
                return 1
            fi

            local socket="$SOCKET_DIR/$session"
            if tmux -S "$socket" kill-session -t "$session" 2>/dev/null; then
                rm -f "$socket"
                echo -e "${GREEN}✓ Killed session: $session${NC}"
            else
                echo -e "${RED}Session not found: $session${NC}"
            fi
            ;;

        "attach"|"open")
            if [[ -z "$session" ]]; then
                echo -e "${RED}Error: Session name required${NC}"
                echo -e "${YELLOW}Usage: claude open <session>${NC}"
                return 1
            fi

            local socket="$SOCKET_DIR/$session"
            if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
                if [[ -n "${TMUX:-}" ]]; then
                    tmux new-window -n "$session" "tmux -S '$socket' attach-session -t '$session'"
                else
                    exec tmux -S "$socket" attach-session -t "$session"
                fi
            else
                echo -e "${RED}Session not found: $session${NC}"
            fi
            ;;

        "new")
            if [[ -z "$session" ]]; then
                echo -e "${RED}Error: Session name required${NC}"
                echo -e "${YELLOW}Usage: claude new <session> [path]${NC}"
                return 1
            fi

            local path="${3:-$(pwd)}"
            local socket="$SOCKET_DIR/$session"

            echo -e "${CYAN}🚀 Creating session: $session${NC}"
            echo -e "${BLUE}📁 Path: $path${NC}"

            tmux -S "$socket" new-session -d -s "$session" -c "$path"
            echo -e "${GREEN}✓ Session created${NC}"
            ;;
    esac
}

# Send command to any session
send_to_session() {
    local session="$1"
    shift
    local command="$*"

    if [[ -z "$session" ]] || [[ -z "$command" ]]; then
        echo -e "${RED}Error: Session and command required${NC}"
        echo -e "${YELLOW}Usage: claude cmd <session> <command>${NC}"
        return 1
    fi

    local socket="$SOCKET_DIR/$session"

    if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
        echo -e "${CYAN}📤 Sending to $session: ${YELLOW}$command${NC}"
        tmux -S "$socket" send-keys -t "$session" "$command" Enter
        echo -e "${GREEN}✓ Command sent${NC}"
    else
        echo -e "${RED}Session not found: $session${NC}"
        echo -e "${YELLOW}Available sessions:${NC}"
        list_all_sessions
    fi
}

# Monitor Claude output
monitor_claude() {
    if ! claude_session_exists; then
        echo -e "${RED}Claude session not running${NC}"
        return 1
    fi

    echo -e "${CYAN}📊 Monitoring Claude output (Ctrl+C to stop)...${NC}"

    while true; do
        clear
        echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
        echo -e "${MAGENTA}           Claude Session Monitor${NC}"
        echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
        echo ""

        tmux -S "$CLAUDE_SOCKET" capture-pane -t claude -p | tail -30

        echo ""
        echo -e "${YELLOW}[Refreshing every 2 seconds...]${NC}"
        sleep 2
    done
}

# Interactive menu
show_menu() {
    echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}           Claude Unified Command${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Quick Commands:${NC}"
    echo -e "  ${YELLOW}claude${NC}                    - Attach to Claude session"
    echo -e "  ${YELLOW}claude <message>${NC}          - Send message to Claude"
    echo -e "  ${YELLOW}claude list${NC}               - List all sessions"
    echo -e "  ${YELLOW}claude monitor${NC}            - Monitor Claude output"
    echo ""
    echo -e "${CYAN}Session Management:${NC}"
    echo -e "  ${YELLOW}claude new <name> [path]${NC}  - Create new session"
    echo -e "  ${YELLOW}claude open <name>${NC}        - Open existing session"
    echo -e "  ${YELLOW}claude kill <name>${NC}        - Kill session"
    echo -e "  ${YELLOW}claude cmd <s> <command>${NC}  - Send command to session"
    echo ""
    echo -e "${CYAN}Advanced:${NC}"
    echo -e "  ${YELLOW}claude status${NC}             - Show Claude status"
    echo -e "  ${YELLOW}claude restart${NC}            - Restart Claude session"
    echo -e "  ${YELLOW}claude help${NC}               - Show this help"
}

# Status check
check_status() {
    echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}              System Status${NC}"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════${NC}"
    echo ""

    # Claude status
    if claude_session_exists; then
        echo -e "${GREEN}✓ Claude session: Running${NC}"

        # Get Claude process info
        local claude_pids=$(tmux -S "$CLAUDE_SOCKET" list-panes -t claude -F "#{pane_pid}" 2>/dev/null)
        if [[ -n "$claude_pids" ]]; then
            for pid in $claude_pids; do
                local cpu_mem=$(ps -p $pid -o %cpu,%mem,etime --no-headers 2>/dev/null || echo "N/A")
                [[ -n "$cpu_mem" ]] && echo -e "  ${BLUE}Process: PID=$pid CPU/MEM: $cpu_mem${NC}"
            done
        fi
    else
        echo -e "${YELLOW}○ Claude session: Not running${NC}"
    fi

    echo ""

    # Active sessions count
    local session_count=$(find "$SOCKET_DIR" -type s 2>/dev/null | while read socket; do
        local name=$(basename "$socket")
        tmux -S "$socket" has-session -t "$name" 2>/dev/null && echo "$name"
    done | wc -l)

    echo -e "${CYAN}Active sessions: $session_count${NC}"

    # Socket directory status
    local socket_count=$(ls -1 "$SOCKET_DIR" 2>/dev/null | wc -l)
    local dead_sockets=$((socket_count - session_count))

    if [[ $dead_sockets -gt 0 ]]; then
        echo -e "${YELLOW}Dead sockets: $dead_sockets (run 'claude clean' to remove)${NC}"
    fi

    # Configuration
    echo ""
    echo -e "${BLUE}Configuration:${NC}"
    echo -e "  Claude home: $CLAUDE_HOME"
    echo -e "  Socket dir: $SOCKET_DIR"
    echo -e "  Config dir: $CONFIG_DIR"
}

# Clean dead sockets
clean_sockets() {
    echo -e "${CYAN}🧹 Cleaning dead sockets...${NC}"

    local cleaned=0
    for socket in "$SOCKET_DIR"/*; do
        [[ ! -S "$socket" ]] && continue

        local name=$(basename "$socket")
        if ! tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            rm -f "$socket"
            echo -e "${YELLOW}  Removed: $name${NC}"
            ((cleaned++))
        fi
    done

    if [[ $cleaned -gt 0 ]]; then
        echo -e "${GREEN}✓ Cleaned $cleaned dead socket(s)${NC}"
    else
        echo -e "${BLUE}No dead sockets found${NC}"
    fi
}

# Main logic
main() {
    case "${1:-}" in
        "list"|"ls")
            list_all_sessions
            ;;

        "status")
            check_status
            ;;

        "monitor")
            monitor_claude
            ;;

        "restart")
            echo -e "${YELLOW}Restarting Claude session...${NC}"
            tmux -S "$CLAUDE_SOCKET" kill-session -t claude 2>/dev/null
            rm -f "$CLAUDE_SOCKET"
            sleep 1
            start_claude_session
            echo -e "${GREEN}✓ Claude session restarted${NC}"
            ;;

        "clean")
            clean_sockets
            ;;

        "new")
            manage_session "new" "$2" "$3"
            ;;

        "open"|"attach")
            if [[ -z "${2:-}" ]]; then
                attach_claude
            else
                manage_session "attach" "$2"
            fi
            ;;

        "kill")
            manage_session "kill" "$2"
            ;;

        "cmd")
            shift
            session="$1"
            shift
            send_to_session "$session" "$@"
            ;;

        "help"|"-h"|"--help")
            show_menu
            ;;

        "")
            # No arguments - attach to claude
            attach_claude
            ;;

        *)
            # Treat everything else as a message to Claude
            send_to_claude "$@"
            ;;
    esac
}

# Run main
main "$@"