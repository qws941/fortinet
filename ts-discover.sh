#!/bin/bash
# TS Discover - Interactive Project Discovery and Registration
# Version: 2.0.0
# Constitutional Compliance: v11.0

set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

readonly TS_CONFIG_DIR="${TS_CONFIG_DIR:-$HOME/.config/ts}"
readonly TS_DB="$TS_CONFIG_DIR/sessions.db"
readonly TS_SOCKET_DIR="/home/jclee/.tmux/sockets"
readonly GRAFANA_LOKI_URL="${GRAFANA_LOKI_URL:-https://grafana.jclee.me/loki/api/v1/push}"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# Scan directories
readonly SCAN_PATHS=(
    "/home/jclee/app"
    "/home/jclee/synology"
)

# Temporary files
DISCOVERED_PROJECTS=$(mktemp)
trap "rm -f $DISCOVERED_PROJECTS" EXIT

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GRAFANA LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

log_to_grafana() {
    local operation="$1"
    local details="$2"
    local status="$3"

    local log_entry=$(cat <<EOF
{
  "streams": [{
    "stream": {
      "job": "ts-discover",
      "operation": "$operation",
      "status": "$status",
      "user": "${USER:-unknown}",
      "host": "$(hostname)"
    },
    "values": [["$(date +%s)000000000", "{\"operation\":\"$operation\",\"details\":\"$details\",\"status\":\"$status\"}"]]
  }]
}
EOF
)

    curl -s -X POST -H "Content-Type: application/json" -d "$log_entry" "$GRAFANA_LOKI_URL" &>/dev/null &
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROJECT DETECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

detect_project_type() {
    local dir="$1"
    local type="unknown"
    local tags=""
    local auto_claude="false"

    # Node.js / TypeScript
    if [[ -f "$dir/package.json" ]]; then
        type="node"
        tags="dev,node"
        auto_claude="true"

        if [[ -f "$dir/tsconfig.json" ]]; then
            tags="$tags,typescript"
        fi
    fi

    # Go
    if [[ -f "$dir/go.mod" ]]; then
        type="go"
        tags="dev,go"
        auto_claude="true"
    fi

    # Python
    if [[ -f "$dir/requirements.txt" ]] || [[ -f "$dir/pyproject.toml" ]] || [[ -f "$dir/setup.py" ]]; then
        type="python"
        tags="dev,python"
        auto_claude="true"
    fi

    # Rust
    if [[ -f "$dir/Cargo.toml" ]]; then
        type="rust"
        tags="dev,rust"
        auto_claude="true"
    fi

    # Docker
    if [[ -f "$dir/docker-compose.yml" ]] || [[ -f "$dir/Dockerfile" ]]; then
        [[ "$tags" == "" ]] && tags="docker" || tags="$tags,docker"
        auto_claude="true"
    fi

    # Git repository
    if [[ -d "$dir/.git" ]]; then
        [[ "$tags" == "" ]] && tags="git" || tags="$tags,git"
    fi

    # Grafana / Monitoring
    if [[ "$dir" =~ grafana ]] || [[ -f "$dir/grafana.ini" ]]; then
        [[ "$tags" == "" ]] && tags="monitoring,grafana" || tags="$tags,monitoring,grafana"
    fi

    # Generic project (has some structure)
    if [[ "$type" == "unknown" ]]; then
        if [[ -d "$dir/src" ]] || [[ -d "$dir/lib" ]] || [[ -d "$dir/bin" ]]; then
            type="project"
            tags="project"
        fi
    fi

    echo "$type|$tags|$auto_claude"
}

scan_directory() {
    local base_path="$1"
    local base_name=$(basename "$base_path")

    echo -e "${CYAN}📁 Scanning: $base_path${NC}\n"

    if [[ ! -d "$base_path" ]]; then
        echo -e "${YELLOW}⚠️  Directory not found: $base_path${NC}\n"
        return
    fi

    local count=0

    for dir in "$base_path"/*; do
        if [[ -d "$dir" && ! -L "$dir" ]]; then
            local name=$(basename "$dir")

            # Skip hidden directories (starting with .)
            [[ "$name" =~ ^\. ]] && continue

            # Check if already registered
            if jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1; then
                echo -e "  ${YELLOW}⊖${NC} $name ${BLUE}(already registered)${NC}"
                continue
            fi

            # Detect project type
            local detection_result=$(detect_project_type "$dir")
            IFS='|' read -r proj_type tags auto_claude <<< "$detection_result"

            # Determine description
            local description="Project in /$base_name"
            case "$proj_type" in
                node) description="Node.js project in /$base_name" ;;
                go) description="Go project in /$base_name" ;;
                python) description="Python project in /$base_name" ;;
                rust) description="Rust project in /$base_name" ;;
                docker) description="Docker project in /$base_name" ;;
            esac

            # Add source location tag
            if [[ "$base_name" == "synology" ]]; then
                [[ "$tags" == "" ]] && tags="synology" || tags="$tags,synology"
            else
                [[ "$tags" == "" ]] && tags="app" || tags="$tags,app"
            fi

            # Save to discovered projects
            echo "$name|$dir|$description|$tags|$auto_claude|$proj_type" >> "$DISCOVERED_PROJECTS"

            # Display
            local type_display=""
            [[ "$proj_type" != "unknown" ]] && type_display="${CYAN}[$proj_type]${NC} "
            echo -e "  ${GREEN}+${NC} $name $type_display${BLUE}$tags${NC}"

            ((count++))
        fi
    done

    if [[ $count -eq 0 ]]; then
        echo -e "  ${YELLOW}No new projects found${NC}"
    fi

    echo ""
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AUTO REGISTRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

register_project() {
    local name="$1"
    local path="$2"
    local description="$3"
    local tags="$4"
    local auto_claude="$5"

    # Add to database
    local temp=$(mktemp)
    jq ".sessions += [{
        \"name\": \"$name\",
        \"path\": \"$path\",
        \"description\": \"$description\",
        \"tags\": \"$tags\",
        \"auto_claude\": $auto_claude,
        \"created_at\": \"$(date -Iseconds)\",
        \"updated_at\": \"$(date -Iseconds)\",
        \"socket\": \"$TS_SOCKET_DIR/$name\",
        \"status\": \"active\"
    }] | .last_updated = \"$(date -Iseconds)\"" "$TS_DB" > "$temp"
    mv "$temp" "$TS_DB"

    echo -e "  ${GREEN}✓${NC} Registered: $name"
    log_to_grafana "register" "$name" "success"
}

auto_register_all() {
    if [[ ! -s "$DISCOVERED_PROJECTS" ]]; then
        echo -e "${YELLOW}No new projects discovered${NC}"
        return 0
    fi

    local total_projects=$(wc -l < "$DISCOVERED_PROJECTS")

    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}Auto-Registering $total_projects discovered project(s)...${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}\n"

    local registered_count=0
    while IFS='|' read -r name path description tags auto_claude proj_type; do
        register_project "$name" "$path" "$description" "$tags" "$auto_claude"
        ((registered_count++))
    done < "$DISCOVERED_PROJECTS"

    echo ""
    echo -e "${GREEN}✓ Successfully registered $registered_count project(s)${NC}"
    log_to_grafana "auto_register" "count:$registered_count" "success"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    # Initialize database
    if [[ ! -f "$TS_DB" ]]; then
        echo -e "${RED}✗ Database not found: $TS_DB${NC}" >&2
        echo -e "${YELLOW}Run 'ts init' first to initialize the database${NC}" >&2
        exit 1
    fi

    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}   TS Discover - Auto Project Discovery${NC}"
    echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}\n"

    log_to_grafana "discover" "started" "running"

    # Scan all directories
    for scan_path in "${SCAN_PATHS[@]}"; do
        scan_directory "$scan_path"
    done

    # Auto-register all discovered projects
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}\n"
    auto_register_all

    # Final summary
    echo ""
    echo -e "${CYAN}Use 'ts list' to see all registered sessions${NC}"
    echo -e "${CYAN}Use 'ts attach <name>' to start working on a project${NC}"
}

main "$@"
