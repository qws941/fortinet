#!/bin/bash
# TS-Claude Integration Patch
# Restores claude command functionality to ts

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SOCKET_DIR="/home/jclee/.tmux/sockets"
CLAUDE_BIN="/home/jclee/.claude/local/claude --dangerously-skip-permissions --mcp-config /home/jclee/.claude/mcp.json"

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}           TS-Claude Integration Installer${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

# Backup current ts
echo -e "\n${BLUE}Creating backup...${NC}"
sudo cp /usr/local/bin/ts /usr/local/bin/ts.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ Backup created${NC}"

# Create enhanced ts with claude integration
cat > /tmp/ts-enhanced-claude << 'TSEOF'
#!/bin/bash
# Enhanced TS with Claude Integration

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
CONFIG_DIR="$HOME/.config/ts"
CONFIG_FILE="$CONFIG_DIR/ts-enhanced.conf"
PROJECTS_CONF="$CONFIG_DIR/projects.conf"
LAST_SESSION="$CONFIG_DIR/last_session"
SOCKET_DIR="/home/jclee/.tmux/sockets"
CLAUDE_BIN="/home/jclee/.claude/local/claude --dangerously-skip-permissions --mcp-config /home/jclee/.claude/mcp.json"

# Create directories
mkdir -p "$CONFIG_DIR" "$SOCKET_DIR"

# Default values
declare -A AUTO_COMMANDS=()
declare -A PROJECT_PATHS=()

# Load config
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        while IFS='=' read -r key value; do
            if [[ "$key" =~ ^PROJECT_PATH_(.+)$ ]]; then
                local name="${BASH_REMATCH[1]}"
                PROJECT_PATHS["$name"]=$(eval echo "$value" | tr -d '"')
            elif [[ "$key" =~ ^AUTO_CMD_(.+)$ ]]; then
                local name="${BASH_REMATCH[1]}"
                AUTO_COMMANDS["$name"]=$(eval echo "$value" | tr -d '"')
            fi
        done < <(grep -E '^(PROJECT_PATH_|AUTO_CMD_)' "$CONFIG_FILE" 2>/dev/null || true)

        source "$CONFIG_FILE" 2>/dev/null || true
    fi
}

# Load config
load_config

# Session exists check
session_exists() {
    local name="$1"
    local socket_path="$SOCKET_DIR/$name"

    if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
        return 0
    fi
    return 1
}

# Attach to session
attach_session() {
    local name="$1"
    local socket_path="$SOCKET_DIR/$name"

    echo -e "${CYAN}🔗 Attaching to session: $name${NC}"
    echo "$name" > "$LAST_SESSION"

    if [[ -n "$TMUX" ]]; then
        tmux new-window -n "$name" "tmux -S '$socket_path' attach-session -t '$name'"
    else
        exec tmux -S "$socket_path" attach-session -t "$name"
    fi
}

# Create new session
create_session() {
    local name="$1"
    local path="${2:-$(pwd)}"
    local socket_path="$SOCKET_DIR/$name"

    [[ -S "$socket_path" ]] && rm -f "$socket_path"

    echo -e "${GREEN}🚀 Creating new session: $name${NC}"
    echo -e "${BLUE}📁 Path: $path${NC}"

    cd "$path" 2>/dev/null || path=$(pwd)
    tmux -S "$socket_path" new-session -d -s "$name" -c "$path"

    if [[ -n "${AUTO_COMMANDS[$name]}" ]]; then
        echo -e "${YELLOW}⚡ Running: ${AUTO_COMMANDS[$name]}${NC}"
        tmux -S "$socket_path" send-keys -t "$name" "${AUTO_COMMANDS[$name]}" Enter
    fi

    echo "$name" > "$LAST_SESSION"
    attach_session "$name"
}

# List sessions
list_sessions() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                Active Sessions${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local has_sessions=false

    for socket in "$SOCKET_DIR"/*; do
        if [[ -S "$socket" ]]; then
            local name=$(basename "$socket")
            if tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
                has_sessions=true
                local info=$(tmux -S "$socket" list-sessions -F "#{session_windows} windows, #{?session_attached,attached,detached}" 2>/dev/null | head -1)
                local pane_path=$(tmux -S "$socket" display-message -p -F "#{pane_current_path}" -t "$name" 2>/dev/null)

                echo -e "  ${GREEN}●${NC} ${name} - ${info}"
                [[ -n "$pane_path" ]] && echo -e "    ${BLUE}📁 $pane_path${NC}"
            fi
        fi
    done

    if [[ "$has_sessions" == false ]]; then
        echo -e "  ${YELLOW}No active sessions${NC}"
    fi

    if [[ -f "$LAST_SESSION" ]]; then
        local last=$(cat "$LAST_SESSION")
        echo ""
        echo -e "${PURPLE}Last session: $last${NC}"
    fi

    echo ""
    echo -e "${BLUE}Usage:${NC}"
    echo -e "  ${CYAN}ts${NC}              - Resume last or list sessions"
    echo -e "  ${CYAN}ts <name>${NC}       - Open/create specific session"
    echo -e "  ${CYAN}ts list${NC}         - Show all sessions"
    echo -e "  ${CYAN}ts kill <name>${NC}  - Kill session"
    echo -e "  ${CYAN}ts claude <cmd>${NC} - Send command to Claude"
    echo -e "  ${CYAN}ts cmd <s> <c>${NC}  - Send command to session"
    echo -e "  ${CYAN}ts resume${NC}       - Resume last session"
}

# Resume last session
resume_last() {
    if [[ -f "$LAST_SESSION" ]]; then
        local last=$(cat "$LAST_SESSION")
        if session_exists "$last"; then
            attach_session "$last"
        else
            echo -e "${YELLOW}⚠️  Last session '$last' not found${NC}"
            if [[ -n "${PROJECT_PATHS[$last]}" ]]; then
                create_session "$last" "${PROJECT_PATHS[$last]}"
            else
                echo -e "${RED}Cannot recreate session${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}No previous session found${NC}"
        list_sessions
    fi
}

# Send command to Claude
send_claude_command() {
    local command="$1"

    if [[ -z "$command" ]]; then
        echo -e "${YELLOW}Usage: ts claude '<command>'${NC}"
        echo -e "${BLUE}Example: ts claude 'help me fix this bug'${NC}"
        return 1
    fi

    # Check if claude session exists
    local claude_socket="$SOCKET_DIR/claude"

    if session_exists "claude"; then
        echo -e "${CYAN}📤 Sending to Claude: $command${NC}"
        tmux -S "$claude_socket" send-keys -t "claude" "$command" Enter
    else
        echo -e "${YELLOW}Starting Claude session...${NC}"
        tmux -S "$claude_socket" new-session -d -s "claude" -c "/home/jclee/.claude" "$CLAUDE_BIN"
        sleep 2
        echo -e "${CYAN}📤 Sending to Claude: $command${NC}"
        tmux -S "$claude_socket" send-keys -t "claude" "$command" Enter
    fi

    echo -e "${GREEN}✓ Command sent. Use 'ts claude' to attach to session${NC}"
}

# Send command to any session
send_to_session() {
    local session="$1"
    local command="$2"

    if [[ -z "$session" ]] || [[ -z "$command" ]]; then
        echo -e "${YELLOW}Usage: ts cmd <session> '<command>'${NC}"
        return 1
    fi

    local socket="$SOCKET_DIR/$session"

    if session_exists "$session"; then
        echo -e "${CYAN}📤 Sending to $session: $command${NC}"
        tmux -S "$socket" send-keys -t "$session" "$command" Enter
        echo -e "${GREEN}✓ Command sent${NC}"
    else
        echo -e "${RED}✗ Session not found: $session${NC}"
        echo -e "${YELLOW}Available sessions:${NC}"
        list_sessions
    fi
}

# Main logic
main() {
    if [[ -n "$TMUX" && "${1:-}" != "list" && "${1:-}" != "ls" && "${1:-}" != "kill" && "${1:-}" != "claude" && "${1:-}" != "cmd" ]]; then
        echo -e "${YELLOW}📌 Note: Running inside tmux - will open in new window${NC}"
    fi

    case "${1:-}" in
        "list"|"ls")
            list_sessions
            ;;

        "kill")
            if [[ -n "$2" ]]; then
                local socket_path="$SOCKET_DIR/$2"
                if tmux -S "$socket_path" kill-session -t "$2" 2>/dev/null; then
                    echo -e "${GREEN}✓ Killed session: $2${NC}"
                    rm -f "$socket_path"
                else
                    echo -e "${YELLOW}Session not found: $2${NC}"
                fi
            else
                echo -e "${RED}Usage: ts kill <name>${NC}"
            fi
            ;;

        "resume")
            resume_last
            ;;

        "claude")
            if [[ -n "$2" ]]; then
                shift
                send_claude_command "$*"
            else
                # Attach to claude session
                if session_exists "claude"; then
                    attach_session "claude"
                else
                    echo -e "${YELLOW}Starting new Claude session...${NC}"
                    create_session "claude" "/home/jclee/.claude"
                    tmux -S "$SOCKET_DIR/claude" send-keys -t "claude" "$CLAUDE_BIN" Enter
                fi
            fi
            ;;

        "cmd")
            send_to_session "$2" "$3"
            ;;

        "")
            if [[ -f "$LAST_SESSION" ]]; then
                resume_last
            else
                list_sessions
            fi
            ;;

        *)
            local name="$1"
            local project_path=""

            if session_exists "$name"; then
                attach_session "$name"
            else
                shift
                if [[ -n "$1" ]]; then
                    project_path="$1"
                elif [[ -n "${PROJECT_PATHS[$name]}" ]]; then
                    project_path="${PROJECT_PATHS[$name]}"
                else
                    project_path=$(pwd)
                fi

                create_session "$name" "$project_path"
            fi
            ;;
    esac
}

# Run main
main "$@"
TSEOF

# Install the new ts script
echo -e "\n${BLUE}Installing enhanced ts...${NC}"
sudo mv /tmp/ts-enhanced-claude /usr/local/bin/ts
sudo chmod +x /usr/local/bin/ts

echo -e "${GREEN}✓ Enhanced ts with Claude integration installed${NC}"

# Test the integration
echo -e "\n${CYAN}Testing integration...${NC}"
echo -e "${BLUE}Available commands:${NC}"
echo "  • ts list         - List sessions"
echo "  • ts claude       - Open Claude session"
echo "  • ts claude 'hi'  - Send command to Claude"
echo "  • ts cmd <s> <c>  - Send command to any session"

echo -e "\n${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ TS-Claude integration restored!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"