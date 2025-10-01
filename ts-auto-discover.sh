#!/bin/bash
# Auto-discover and register sessions from /app and /synology

set -euo pipefail

readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

echo -e "${CYAN}Auto-discovering projects...${NC}\n"

# Directories to scan
APP_DIR="/home/jclee/app"
SYNOLOGY_DIR="/home/jclee/synology"

discovered=0

# Function to create session
create_if_not_exists() {
    local name="$1"
    local path="$2"
    local description="$3"
    local tags="$4"
    local auto_claude="$5"

    # Check if session exists in database
    if ts read "$name" >/dev/null 2>&1; then
        echo -e "  ${YELLOW}⊖ $name (already exists)${NC}"
        return
    fi

    echo -e "  ${GREEN}+ $name${NC}"

    # Directly add to database (don't create tmux session)
    local socket_path="/home/jclee/.tmux/sockets/$name"
    local db="/home/jclee/.config/ts/sessions.db"
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
    }]" "$db" > "$temp" && mv "$temp" "$db"

    ((discovered++))
}

echo -e "${CYAN}Scanning /home/jclee/app...${NC}"

if [[ -d "$APP_DIR" ]]; then
    for dir in "$APP_DIR"/*; do
        if [[ -d "$dir" && ! -L "$dir" ]]; then
            name=$(basename "$dir")

            # Skip hidden directories and system dirs
            [[ "$name" =~ ^\. ]] && continue

            # Determine if it should auto-start Claude
            auto_claude="false"
            tags="app"

            # Check for indicators of development projects
            if [[ -f "$dir/package.json" ]] || [[ -f "$dir/tsconfig.json" ]] || [[ -f "$dir/go.mod" ]]; then
                auto_claude="true"
                tags="app,dev"
            fi

            create_if_not_exists "$name" "$dir" "Project in /app" "$tags" "$auto_claude"
        fi
    done
fi

echo -e "\n${CYAN}Scanning /home/jclee/synology...${NC}"

if [[ -d "$SYNOLOGY_DIR" ]]; then
    for dir in "$SYNOLOGY_DIR"/*; do
        if [[ -d "$dir" && ! -L "$dir" ]]; then
            name=$(basename "$dir")

            # Skip hidden directories
            [[ "$name" =~ ^\. ]] && continue

            # Prefix with 'syn-' to distinguish from app
            session_name="syn-$name"

            auto_claude="false"
            tags="synology"

            # Check for indicators of development projects
            if [[ -f "$dir/package.json" ]] || [[ -f "$dir/tsconfig.json" ]] || [[ -f "$dir/docker-compose.yml" ]]; then
                auto_claude="true"
                tags="synology,dev"
            fi

            create_if_not_exists "$session_name" "$dir" "Project in /synology" "$tags" "$auto_claude"
        fi
    done
fi

echo -e "\n${GREEN}✓ Discovery complete${NC}"
echo -e "${CYAN}Discovered: $discovered new session(s)${NC}"

# Sync database
ts sync >/dev/null 2>&1 || true

echo -e "\n${CYAN}Use 'ts list' to see all sessions${NC}"
