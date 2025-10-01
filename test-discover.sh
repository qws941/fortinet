#!/bin/bash
# Test TS Discover functionality

set -euo pipefail

readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly YELLOW='\033[1;33m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

echo -e "${CYAN}${BOLD}Testing TS Discover Functionality${NC}\n"

# 1. Check if database exists
echo -e "${BOLD}1. Checking database...${NC}"
if [[ -f "$HOME/.config/ts/sessions.db" ]]; then
    echo -e "${GREEN}✓ Database exists${NC}"
    echo -e "${CYAN}  Location: $HOME/.config/ts/sessions.db${NC}"
else
    echo -e "${YELLOW}⚠️  Database not found, initializing...${NC}"
    mkdir -p "$HOME/.config/ts"
    cat > "$HOME/.config/ts/sessions.db" <<'EOF'
{
  "sessions": [],
  "version": "1.0.0",
  "last_updated": ""
}
EOF
    echo -e "${GREEN}✓ Database initialized${NC}"
fi
echo ""

# 2. Show current registered sessions
echo -e "${BOLD}2. Currently registered sessions:${NC}"
session_count=$(jq '.sessions | length' "$HOME/.config/ts/sessions.db")
if [[ "$session_count" -eq 0 ]]; then
    echo -e "${YELLOW}  No sessions registered yet${NC}"
else
    echo -e "${CYAN}  Total: $session_count session(s)${NC}"
    jq -r '.sessions[] | "  - \(.name) (\(.path))"' "$HOME/.config/ts/sessions.db"
fi
echo ""

# 3. Test project detection
echo -e "${BOLD}3. Testing project detection logic...${NC}"

detect_project_type() {
    local dir="$1"
    local type="unknown"
    local tags=""

    if [[ -f "$dir/package.json" ]]; then
        type="node"
        tags="dev,node"
        if [[ -f "$dir/tsconfig.json" ]]; then
            tags="$tags,typescript"
        fi
    elif [[ -f "$dir/go.mod" ]]; then
        type="go"
        tags="dev,go"
    elif [[ -f "$dir/docker-compose.yml" ]]; then
        type="docker"
        tags="docker"
    elif [[ -d "$dir/.git" ]]; then
        type="git"
        tags="git"
    fi

    echo "$type|$tags"
}

# Test on current directory
current_detection=$(detect_project_type "$(pwd)")
IFS='|' read -r type tags <<< "$current_detection"
echo -e "${CYAN}  Current directory ($PWD):${NC}"
echo -e "    Type: ${BOLD}$type${NC}"
echo -e "    Tags: ${BOLD}$tags${NC}"
echo ""

# 4. Display available scan paths
echo -e "${BOLD}4. Available scan paths:${NC}"
for path in "/home/jclee/app" "/home/jclee/synology"; do
    if [[ -d "$path" ]]; then
        project_count=$(find "$path" -maxdepth 1 -type d ! -name ".*" | wc -l)
        ((project_count--)) # Exclude the base directory itself
        echo -e "${GREEN}✓${NC} $path ${CYAN}($project_count potential projects)${NC}"
    else
        echo -e "${YELLOW}⚠️${NC} $path ${YELLOW}(not found)${NC}"
    fi
done
echo ""

# 5. Ready to run
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Ready to test!${NC}\n"
echo -e "Run the following commands to test discovery:\n"
echo -e "  ${CYAN}ts discover${NC}          - Interactive project discovery"
echo -e "  ${CYAN}ts scan${NC}              - Alias for 'ts discover'"
echo -e "  ${CYAN}ts list${NC}              - List registered sessions (after discovery)"
echo -e "  ${CYAN}ts read <name>${NC}       - View session details"
echo ""
echo -e "${YELLOW}Note: Make sure ts-discover-interactive.sh is executable${NC}"
echo -e "${CYAN}  chmod +x /home/jclee/app/tmux/ts-discover-interactive.sh${NC}"
