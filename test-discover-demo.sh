#!/bin/bash
# Demo: TS Discover with test projects

set -euo pipefail

readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

# Temporarily modify the discover script to scan /tmp/test-projects
echo -e "${CYAN}${BOLD}Demo: Running ts discover on /tmp/test-projects${NC}\n"

# Create a temporary version of discover script
TEMP_DISCOVER=$(mktemp)
cat > "$TEMP_DISCOVER" <<'EOF'
#!/bin/bash
set -euo pipefail

readonly TS_CONFIG_DIR="${TS_CONFIG_DIR:-$HOME/.config/ts}"
readonly TS_DB="$TS_CONFIG_DIR/sessions.db"
readonly TS_SOCKET_DIR="/home/jclee/.tmux/sockets"

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

DISCOVERED_PROJECTS=$(mktemp)
trap "rm -f $DISCOVERED_PROJECTS" EXIT

detect_project_type() {
    local dir="$1"
    local type="unknown"
    local tags=""
    local auto_claude="false"

    if [[ -f "$dir/package.json" ]]; then
        type="node"
        tags="dev,node"
        auto_claude="true"
    elif [[ -f "$dir/go.mod" ]]; then
        type="go"
        tags="dev,go"
        auto_claude="true"
    elif [[ -f "$dir/Dockerfile" ]]; then
        type="docker"
        tags="docker"
        auto_claude="true"
    fi

    echo "$type|$tags|$auto_claude"
}

echo -e "${CYAN}📁 Scanning: /tmp/test-projects${NC}\n"

for dir in /tmp/test-projects/*; do
    if [[ -d "$dir" ]]; then
        name=$(basename "$dir")

        if jq -e ".sessions[] | select(.name == \"$name\")" "$TS_DB" >/dev/null 2>&1; then
            echo -e "  ${YELLOW}⊖${NC} $name ${BLUE}(already registered)${NC}"
            continue
        fi

        detection_result=$(detect_project_type "$dir")
        IFS='|' read -r proj_type tags auto_claude <<< "$detection_result"

        description="Test project"
        echo "$name|$dir|$description|$tags|$auto_claude|$proj_type" >> "$DISCOVERED_PROJECTS"

        echo -e "  ${GREEN}+${NC} $name ${CYAN}[$proj_type]${NC} ${BLUE}$tags${NC}"
    fi
done

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}\n"

if [[ ! -s "$DISCOVERED_PROJECTS" ]]; then
    echo -e "${YELLOW}No new projects discovered${NC}"
    exit 0
fi

echo -e "${CYAN}${BOLD}       Discovered Projects${NC}\n"
printf "  %-4s %-20s %-10s %-40s\n" "NUM" "NAME" "TYPE" "TAGS"
echo -e "  ────────────────────────────────────────────────────────────────────────────────"

line_num=0
while IFS='|' read -r name path description tags auto_claude proj_type; do
    ((line_num++))
    printf "  ${BOLD}%-4d${NC} %-20s ${CYAN}%-10s${NC} ${BLUE}%-40s${NC}\n" \
        "$line_num" "$name" "[$proj_type]" "$tags"
done < "$DISCOVERED_PROJECTS"

echo ""
echo -e "${BOLD}This is a demo - no actual registration${NC}"
echo -e "${CYAN}In real usage, you would see selection options here${NC}"
EOF

chmod +x "$TEMP_DISCOVER"
"$TEMP_DISCOVER"
rm -f "$TEMP_DISCOVER"

echo ""
echo -e "${CYAN}Test projects created in /tmp/test-projects:${NC}"
ls -la /tmp/test-projects/
