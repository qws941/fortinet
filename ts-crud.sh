#!/bin/bash
# TS CRUD - Complete CRUD Operations for Tmux Session Manager
# Version: 1.0.0
# Constitutional Compliance: v11.0

set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

readonly TS_VERSION="1.0.0-crud"
readonly TS_SOCKET_DIR="${TS_SOCKET_DIR:-/home/jclee/.tmux/sockets}"
readonly TS_CONFIG_DIR="${TS_CONFIG_DIR:-$HOME/.config/ts}"
readonly TS_DB="$TS_CONFIG_DIR/sessions.db"
readonly GRAFANA_LOKI_URL="${GRAFANA_LOKI_URL:-https://grafana.jclee.me/loki/api/v1/push}"

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

init_db() {
    mkdir -p "$TS_CONFIG_DIR" "$TS_SOCKET_DIR" 2>/dev/null || true

    if [[ ! -f "$TS_DB" ]]; then
        cat > "$TS_DB" <<'EOF'
{
  "sessions": [],
  "version": "1.0.0",
  "last_updated": ""
}
EOF
    fi
}

# Update timestamp
update_db_timestamp() {
    local temp=$(mktemp)
    jq ".last_updated = \"$(date -Iseconds)\"" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GRAFANA LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

log_to_grafana() {
    local operation="$1"
    local session_name="$2"
    local status="$3"
    local details="${4:-}"

    local log_entry=$(cat <<EOF
{
  "streams": [{
    "stream": {
      "job": "ts-crud",
      "operation": "$operation",
      "session": "$session_name",
      "status": "$status",
      "user": "${USER:-unknown}",
      "host": "$(hostname)"
    },
    "values": [["$(date +%s)000000000", "{\"operation\":\"$operation\",\"session\":\"$session_name\",\"status\":\"$status\",\"details\":\"$details\"}"]]
  }]
}
EOF
)

    curl -s -X POST -H "Content-Type: application/json" -d "$log_entry" "$GRAFANA_LOKI_URL" &>/dev/null &
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CREATE - Create new session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

create() {
    local name="$1"
    local path="${2:-$(pwd)}"
    local description="${3:-}"
    local tags="${4:-}"

    # Validate name
    if [[ -z "$name" ]] || [[ "$name" =~ [[:space:]/:] ]]; then
        echo -e "${RED}✗ Invalid session name: '$name'${NC}" >&2
        echo -e "${YELLOW}Name cannot contain spaces, slashes, or colons${NC}" >&2
        log_to_grafana "create" "$name" "error" "invalid_name"
        return 1
    fi

    # Check if session already exists
    if jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1; then
        echo -e "${RED}✗ Session already exists: $name${NC}" >&2
        echo -e "${YELLOW}Use 'ts update $name' to modify existing session${NC}" >&2
        log_to_grafana "create" "$name" "error" "already_exists"
        return 1
    fi

    # Resolve path
    path=$(realpath "$path" 2>/dev/null || echo "$path")

    if [[ ! -d "$path" ]]; then
        echo -e "${YELLOW}⚠️  Path does not exist: $path${NC}"
        echo -n -e "${CYAN}Create directory? [y/N]: ${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            mkdir -p "$path" || {
                echo -e "${RED}✗ Failed to create directory${NC}" >&2
                log_to_grafana "create" "$name" "error" "mkdir_failed"
                return 1
            }
        else
            echo -e "${RED}✗ Operation cancelled${NC}" >&2
            log_to_grafana "create" "$name" "cancelled" "path_not_exist"
            return 1
        fi
    fi

    # Create tmux session
    local socket_path="$TS_SOCKET_DIR/$name"

    # Clean existing socket
    [[ -S "$socket_path" ]] && rm -f "$socket_path"

    echo -e "${GREEN}🚀 Creating session: $name${NC}"

    if ! tmux -S "$socket_path" new-session -d -s "$name" -c "$path" 2>/dev/null; then
        echo -e "${RED}✗ Failed to create tmux session${NC}" >&2
        log_to_grafana "create" "$name" "error" "tmux_failed"
        return 1
    fi

    # Add to database
    local temp=$(mktemp)
    jq ".sessions += [{
        \"name\": \"$name\",
        \"path\": \"$path\",
        \"description\": \"$description\",
        \"tags\": \"$tags\",
        \"created_at\": \"$(date -Iseconds)\",
        \"updated_at\": \"$(date -Iseconds)\",
        \"socket\": \"$socket_path\",
        \"status\": \"active\"
    }]" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"
    update_db_timestamp

    echo -e "${GREEN}✓ Session created successfully${NC}"
    echo -e "${BLUE}  Name: $name${NC}"
    echo -e "${BLUE}  Path: $path${NC}"
    [[ -n "$description" ]] && echo -e "${BLUE}  Description: $description${NC}"
    [[ -n "$tags" ]] && echo -e "${BLUE}  Tags: $tags${NC}"

    log_to_grafana "create" "$name" "success" "path:$path"

    # Ask to attach
    echo -n -e "${CYAN}Attach to session? [Y/n]: ${NC}"
    read -r response
    if [[ -z "$response" ]] || [[ "$response" =~ ^[Yy]$ ]]; then
        attach "$name"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# READ - Read session information
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

read() {
    local name="$1"
    local format="${2:-pretty}"

    if ! jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1; then
        echo -e "${RED}✗ Session not found: $name${NC}" >&2
        log_to_grafana "read" "$name" "error" "not_found"
        return 1
    fi

    local session_data=$(jq -r ".sessions[] | select(.name == \"$name\")" "$TS_DB")

    if [[ "$format" == "json" ]]; then
        echo "$session_data" | jq '.'
        log_to_grafana "read" "$name" "success" "format:json"
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
    local status=$(echo "$session_data" | jq -r '.status')

    echo -e "\n${BOLD}Basic Information:${NC}"
    echo -e "  Name:        $name"
    echo -e "  Path:        $path"
    [[ "$description" != "null" ]] && [[ -n "$description" ]] && echo -e "  Description: $description"
    [[ "$tags" != "null" ]] && [[ -n "$tags" ]] && echo -e "  Tags:        $tags"
    echo -e "  Status:      $status"

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
    log_to_grafana "read" "$name" "success" "format:pretty"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UPDATE - Update session metadata
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

update() {
    local name="$1"
    shift

    if ! jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1; then
        echo -e "${RED}✗ Session not found: $name${NC}" >&2
        log_to_grafana "update" "$name" "error" "not_found"
        return 1
    fi

    local updates=""
    local update_details=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                local new_path=$(realpath "$2" 2>/dev/null || echo "$2")
                updates="$updates | .path = \"$new_path\""
                update_details="$update_details path:$new_path"
                shift 2
                ;;
            --description)
                updates="$updates | .description = \"$2\""
                update_details="$update_details description"
                shift 2
                ;;
            --tags)
                updates="$updates | .tags = \"$2\""
                update_details="$update_details tags:$2"
                shift 2
                ;;
            --status)
                updates="$updates | .status = \"$2\""
                update_details="$update_details status:$2"
                shift 2
                ;;
            *)
                echo -e "${RED}✗ Unknown option: $1${NC}" >&2
                echo -e "${YELLOW}Available options: --path, --description, --tags, --status${NC}" >&2
                return 1
                ;;
        esac
    done

    if [[ -z "$updates" ]]; then
        echo -e "${YELLOW}⚠️  No updates specified${NC}" >&2
        echo -e "${BLUE}Usage: ts update <name> [--path <path>] [--description <desc>] [--tags <tags>] [--status <status>]${NC}" >&2
        return 1
    fi

    # Apply updates
    local temp=$(mktemp)
    jq "(.sessions[] | select(.name == \"$name\")) |= ($updates | .updated_at = \"$(date -Iseconds)\")" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"
    update_db_timestamp

    echo -e "${GREEN}✓ Session updated: $name${NC}"
    echo -e "${BLUE}  Updates: $update_details${NC}"

    log_to_grafana "update" "$name" "success" "$update_details"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DELETE - Delete session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

delete() {
    local name="$1"
    local force="${2:-false}"

    if ! jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1; then
        echo -e "${RED}✗ Session not found: $name${NC}" >&2
        log_to_grafana "delete" "$name" "error" "not_found"
        return 1
    fi

    # Confirm deletion
    if [[ "$force" != "--force" ]] && [[ "$force" != "-f" ]]; then
        echo -e "${YELLOW}⚠️  Are you sure you want to delete session: $name?${NC}"
        echo -n -e "${CYAN}Type 'yes' to confirm: ${NC}"
        read -r response
        if [[ "$response" != "yes" ]]; then
            echo -e "${BLUE}✓ Deletion cancelled${NC}"
            log_to_grafana "delete" "$name" "cancelled" "user_cancelled"
            return 0
        fi
    fi

    # Kill tmux session if active
    local socket_path="$TS_SOCKET_DIR/$name"
    if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
        echo -e "${YELLOW}🛑 Killing active tmux session...${NC}"
        tmux -S "$socket_path" kill-session -t "$name" 2>/dev/null || true
        rm -f "$socket_path"
    fi

    # Remove from database
    local temp=$(mktemp)
    jq ".sessions = [.sessions[] | select(.name != \"$name\")]" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"
    update_db_timestamp

    echo -e "${GREEN}✓ Session deleted: $name${NC}"
    log_to_grafana "delete" "$name" "success" "deleted"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LIST - List all sessions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

list() {
    local format="${1:-pretty}"
    local filter_tag="${2:-}"

    if [[ "$format" == "json" ]]; then
        if [[ -n "$filter_tag" ]]; then
            jq ".sessions[] | select(.tags | contains(\"$filter_tag\"))" "$TS_DB"
        else
            jq '.sessions[]' "$TS_DB"
        fi
        log_to_grafana "list" "all" "success" "format:json"
        return 0
    fi

    # Pretty format
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}       TS CRUD - Session Manager${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local sessions
    if [[ -n "$filter_tag" ]]; then
        sessions=$(jq -r ".sessions[] | select(.tags | contains(\"$filter_tag\")) | .name" "$TS_DB")
        echo -e "\n${BLUE}Filtered by tag: $filter_tag${NC}"
    else
        sessions=$(jq -r '.sessions[].name' "$TS_DB")
    fi

    if [[ -z "$sessions" ]]; then
        echo -e "\n${YELLOW}No sessions found${NC}"
        log_to_grafana "list" "all" "success" "empty"
        return 0
    fi

    echo -e "\n${BOLD}Active Sessions:${NC}"
    printf "  %-20s %-10s %-40s %s\n" "NAME" "STATUS" "PATH" "DESCRIPTION"
    echo -e "  ────────────────────────────────────────────────────────────────────────────────────────"

    local count=0
    while IFS= read -r name; do
        local session_data=$(jq -r ".sessions[] | select(.name == \"$name\")" "$TS_DB")
        local path=$(echo "$session_data" | jq -r '.path')
        local description=$(echo "$session_data" | jq -r '.description // ""' | cut -c1-30)
        local socket=$(echo "$session_data" | jq -r '.socket')
        local status_icon

        if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            status_icon="${GREEN}●${NC}"
        else
            status_icon="${RED}○${NC}"
        fi

        printf "  %-20s %b %-40s %s\n" "$name" "$status_icon" "${path:0:40}" "$description"
        ((count++))
    done <<< "$sessions"

    echo ""
    echo -e "${BLUE}Total: $count session(s)${NC}"
    log_to_grafana "list" "all" "success" "count:$count"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ATTACH - Attach to session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

attach() {
    local name="$1"

    if ! jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1; then
        echo -e "${RED}✗ Session not found in database: $name${NC}" >&2
        log_to_grafana "attach" "$name" "error" "not_found"
        return 1
    fi

    local socket_path="$TS_SOCKET_DIR/$name"

    if [[ ! -S "$socket_path" ]] || ! tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  Session exists in database but tmux session is not active${NC}"
        echo -n -e "${CYAN}Recreate session? [Y/n]: ${NC}"
        read -r response
        if [[ -z "$response" ]] || [[ "$response" =~ ^[Yy]$ ]]; then
            local path=$(jq -r ".sessions[] | select(.name == \"$name\") | .path" "$TS_DB")
            tmux -S "$socket_path" new-session -d -s "$name" -c "$path" 2>/dev/null || {
                echo -e "${RED}✗ Failed to recreate session${NC}" >&2
                log_to_grafana "attach" "$name" "error" "recreate_failed"
                return 1
            }
        else
            log_to_grafana "attach" "$name" "cancelled" "session_inactive"
            return 1
        fi
    fi

    echo -e "${CYAN}🔗 Attaching to: $name${NC}"
    log_to_grafana "attach" "$name" "success" "attached"

    if [[ -n "${TMUX:-}" ]]; then
        tmux new-window -n "$name" "tmux -S '$socket_path' attach-session -t '$name'"
    else
        exec tmux -S "$socket_path" attach-session -t "$name"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEARCH - Search sessions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

search() {
    local query="$1"
    local field="${2:-all}"

    if [[ -z "$query" ]]; then
        echo -e "${RED}✗ Search query required${NC}" >&2
        return 1
    fi

    echo -e "${CYAN}Searching for: $query (field: $field)${NC}\n"

    local results
    case "$field" in
        name)
            results=$(jq -r ".sessions[] | select(.name | contains(\"$query\")) | .name" "$TS_DB")
            ;;
        path)
            results=$(jq -r ".sessions[] | select(.path | contains(\"$query\")) | .name" "$TS_DB")
            ;;
        tags)
            results=$(jq -r ".sessions[] | select(.tags | contains(\"$query\")) | .name" "$TS_DB")
            ;;
        description)
            results=$(jq -r ".sessions[] | select(.description | contains(\"$query\")) | .name" "$TS_DB")
            ;;
        all)
            results=$(jq -r ".sessions[] | select(.name + .path + .tags + .description | contains(\"$query\")) | .name" "$TS_DB")
            ;;
        *)
            echo -e "${RED}✗ Invalid field: $field${NC}" >&2
            echo -e "${YELLOW}Available fields: name, path, tags, description, all${NC}" >&2
            return 1
            ;;
    esac

    if [[ -z "$results" ]]; then
        echo -e "${YELLOW}No sessions found matching: $query${NC}"
        log_to_grafana "search" "$query" "success" "no_results"
        return 0
    fi

    echo -e "${GREEN}Found sessions:${NC}"
    while IFS= read -r name; do
        echo -e "  ${BLUE}●${NC} $name"
    done <<< "$results"

    log_to_grafana "search" "$query" "success" "found"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYNC - Sync database with actual tmux sessions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

sync() {
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

        local temp=$(mktemp)
        jq "(.sessions[] | select(.name == \"$name\")) |= (.status = \"$new_status\" | .updated_at = \"$(date -Iseconds)\")" "$TS_DB" > "$temp"
        mv "$temp" "$TS_DB"

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

    update_db_timestamp

    echo ""
    echo -e "${GREEN}✓ Sync complete${NC}"
    echo -e "${BLUE}  Synced: $synced session(s)${NC}"
    echo -e "${BLUE}  Cleaned: $cleaned socket(s)${NC}"

    log_to_grafana "sync" "all" "success" "synced:$synced cleaned:$cleaned"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_help() {
    cat <<EOF
${CYAN}═══════════════════════════════════════════════════${NC}
${BOLD}TS CRUD - Tmux Session Manager with CRUD Operations${NC}
${BOLD}Version: $TS_VERSION${NC}
${CYAN}═══════════════════════════════════════════════════${NC}

${BOLD}CRUD Operations:${NC}

${GREEN}CREATE:${NC}
  ts create <name> [path] [description] [tags]
      Create a new session with metadata

${GREEN}READ:${NC}
  ts read <name> [format]
      Read session information (format: pretty|json)

  ts list [format] [tag]
      List all sessions (format: pretty|json)

${GREEN}UPDATE:${NC}
  ts update <name> [options]
      --path <path>              Update working directory
      --description <desc>       Update description
      --tags <tags>              Update tags
      --status <status>          Update status

${GREEN}DELETE:${NC}
  ts delete <name> [--force]
      Delete a session (with confirmation)

${BOLD}Additional Commands:${NC}
  ts attach <name>              Attach to a session
  ts search <query> [field]     Search sessions (field: name|path|tags|description|all)
  ts sync                       Sync database with actual tmux sessions
  ts help                       Show this help

${BOLD}Examples:${NC}
  ${CYAN}# Create a session${NC}
  ts create myproject /home/user/myproject "My awesome project" "dev,web"

  ${CYAN}# Read session info${NC}
  ts read myproject
  ts read myproject json

  ${CYAN}# Update session${NC}
  ts update myproject --path /new/path --tags "prod,api"

  ${CYAN}# List sessions${NC}
  ts list
  ts list json
  ts list pretty dev

  ${CYAN}# Search${NC}
  ts search "myproject"
  ts search "dev" tags

  ${CYAN}# Delete session${NC}
  ts delete myproject
  ts delete myproject --force

${BOLD}Configuration:${NC}
  Database: $TS_DB
  Sockets:  $TS_SOCKET_DIR
  Config:   $TS_CONFIG_DIR

${BOLD}Features:${NC}
  ✓ Full CRUD operations
  ✓ JSON database with metadata
  ✓ Grafana telemetry integration
  ✓ Session search and filtering
  ✓ Auto-sync with tmux
  ✓ Constitutional compliance v11.0
EOF
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    init_db

    local command="${1:-help}"
    shift || true

    case "$command" in
        create|c)
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts create <name> [path] [description] [tags]${NC}"; exit 1; }
            create "$@"
            ;;
        read|r|show|info)
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts read <name> [format]${NC}"; exit 1; }
            read "$@"
            ;;
        update|u|edit)
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts update <name> [options]${NC}"; exit 1; }
            update "$@"
            ;;
        delete|d|rm|remove)
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts delete <name> [--force]${NC}"; exit 1; }
            delete "$@"
            ;;
        list|ls|l)
            list "$@"
            ;;
        attach|a)
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts attach <name>${NC}"; exit 1; }
            attach "$@"
            ;;
        search|find|s)
            [[ -n "${1:-}" ]] || { echo -e "${RED}Usage: ts search <query> [field]${NC}"; exit 1; }
            search "$@"
            ;;
        sync)
            sync
            ;;
        help|h|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown command: $command${NC}"
            echo -e "${YELLOW}Run 'ts help' for usage information${NC}"
            exit 1
            ;;
    esac
}

main "$@"
