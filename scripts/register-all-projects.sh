#!/bin/bash
# Register all projects from /app and /synology to ts database

set -euo pipefail

readonly DB="/home/jclee/.config/ts/sessions.db"
readonly SOCKET_DIR="/home/jclee/.tmux/sockets"
readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

echo -e "${CYAN}Registering all projects...${NC}\n"

# Create temp file for new database
TEMP_DB=$(mktemp)
cp "$DB" "$TEMP_DB"

discovered=0
skipped=0

# Get existing session names
existing_sessions=$(jq -r '.sessions[].name' "$DB" 2>/dev/null || echo "")

# Function to check if session exists
session_exists() {
    echo "$existing_sessions" | grep -qx "$1"
}

# Function to add session
add_session() {
    local name="$1"
    local path="$2"
    local description="$3"
    local tags="$4"
    local auto_claude="$5"

    jq ".sessions += [{
        \"name\": \"$name\",
        \"path\": \"$path\",
        \"description\": \"$description\",
        \"tags\": \"$tags\",
        \"auto_claude\": $auto_claude,
        \"created_at\": \"$(date -Iseconds)\",
        \"updated_at\": \"$(date -Iseconds)\",
        \"socket\": \"$SOCKET_DIR/$name\",
        \"status\": \"active\"
    }] | .last_updated = \"$(date -Iseconds)\"" "$TEMP_DB" > "${TEMP_DB}.new"
    mv "${TEMP_DB}.new" "$TEMP_DB"
}

# Scan /app
echo -e "${CYAN}📁 Scanning /home/jclee/app...${NC}"
for dir in /home/jclee/app/*; do
    if [[ -d "$dir" && ! -L "$dir" ]]; then
        name=$(basename "$dir")

        # Skip hidden directories
        [[ "$name" =~ ^\. ]] && continue

        if session_exists "$name"; then
            echo -e "  ${YELLOW}⊖${NC} $name"
            ((skipped++))
            continue
        fi

        echo -e "  ${GREEN}+${NC} $name"

        # Detect dev projects
        auto_claude="false"
        tags="app"
        if [[ -f "$dir/package.json" ]] || [[ -f "$dir/tsconfig.json" ]] || [[ -f "$dir/go.mod" ]] || [[ -f "$dir/docker-compose.yml" ]]; then
            auto_claude="true"
            tags="app,dev"
        fi

        add_session "$name" "$dir" "Project in /app" "$tags" "$auto_claude"
        ((discovered++))
    fi
done

echo ""

# Scan /synology
echo -e "${CYAN}📁 Scanning /home/jclee/synology...${NC}"
for dir in /home/jclee/synology/*; do
    if [[ -d "$dir" && ! -L "$dir" ]]; then
        name=$(basename "$dir")

        # Skip hidden directories
        [[ "$name" =~ ^\. ]] && continue

        # Use same name (no prefix)
        if session_exists "$name"; then
            echo -e "  ${YELLOW}⊖${NC} $name"
            ((skipped++))
            continue
        fi

        echo -e "  ${GREEN}+${NC} $name"

        # Detect dev projects
        auto_claude="false"
        tags="synology"
        if [[ -f "$dir/package.json" ]] || [[ -f "$dir/tsconfig.json" ]] || [[ -f "$dir/docker-compose.yml" ]]; then
            auto_claude="true"
            tags="synology,dev"
        fi

        add_session "$name" "$dir" "Project in /synology" "$tags" "$auto_claude"
        ((discovered++))
    fi
done

# Save database
mv "$TEMP_DB" "$DB"

echo ""
echo -e "${GREEN}✓ Registration complete!${NC}"
echo -e "${CYAN}  Discovered: $discovered new session(s)${NC}"
echo -e "${CYAN}  Skipped: $skipped existing session(s)${NC}"
echo ""
echo -e "${CYAN}Use 'ts list' to see all sessions${NC}"
