#!/bin/bash
# Install Advanced TS Command System

echo "🚀 Installing Advanced TS Command System..."

# 백업 생성
sudo cp /usr/local/bin/ts /usr/local/bin/ts-basic.backup

# 고급 기능을 통합한 새로운 ts 스크립트 생성
cat > /tmp/ts-ultimate << 'EOF'
#!/bin/bash
# Ultimate TS Command - Auto-registration, Duplicate Removal, Session Management

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 설정
SOCKET_DIR="/home/jclee/.tmux/sockets"
CONFIG_DIR="$HOME/.config/ts"
PROJECTS_CONF="$CONFIG_DIR/projects.conf"
REGISTRY_CONF="$CONFIG_DIR/registry.conf"
CLAUDE_BIN="/home/jclee/.claude/local/claude --dangerously-skip-permissions --mcp-config /home/jclee/.claude/mcp.json"
TS_ORIGINAL="/usr/local/bin/ts-original"

# 디렉토리 생성
mkdir -p "$CONFIG_DIR" "$SOCKET_DIR"

# 프로젝트 로드
load_projects() {
    declare -gA KNOWN_PROJECTS=(
        ["claude"]="/home/jclee/.claude"
        ["tmux"]="/home/jclee/app/tmux"
        ["grafana"]="/home/jclee/app/grafana"
        ["safework"]="/home/jclee/app/safework"
    )

    if [[ -f "$PROJECTS_CONF" ]]; then
        while IFS='=' read -r name path; do
            [[ -n "$name" && "$name" != \#* ]] && KNOWN_PROJECTS["$name"]=$(eval echo "$path")
        done < "$PROJECTS_CONF"
    fi
}

# 중복 제거
clean_duplicates() {
    echo -e "${BLUE}🧹 Cleaning duplicates...${NC}"

    # 프로젝트 설정 중복 제거
    if [[ -f "$PROJECTS_CONF" ]]; then
        cp "$PROJECTS_CONF" "$PROJECTS_CONF.backup"
        awk '!seen[$0]++' "$PROJECTS_CONF" > "$PROJECTS_CONF.tmp"
        mv "$PROJECTS_CONF.tmp" "$PROJECTS_CONF"
        echo -e "${GREEN}✓ Removed duplicates from projects${NC}"
    fi

    # 죽은 소켓 제거
    for socket in "$SOCKET_DIR"/*; do
        if [[ -S "$socket" ]]; then
            local session_name=$(basename "$socket")
            if ! tmux -S "$socket" has-session -t "$session_name" 2>/dev/null; then
                rm -f "$socket"
                echo -e "${YELLOW}✓ Removed dead socket: $session_name${NC}"
            fi
        fi
    done
}

# 자동 등록 시스템
auto_register() {
    local name="$1"
    local path="${2:-$PWD}"

    if [[ -z "$name" ]]; then
        echo -e "${RED}Usage: ts register <name> [path]${NC}"
        return 1
    fi

    path=$(realpath "$path" 2>/dev/null || echo "$path")

    echo -e "${CYAN}🚀 Auto-registering: $name${NC}"

    # 디렉토리 생성
    if [[ ! -d "$path" ]]; then
        mkdir -p "$path" || return 1
        echo -e "${GREEN}✓ Created directory: $path${NC}"
    fi

    # 프로젝트 등록
    echo "$name=\"$path\"" >> "$PROJECTS_CONF"

    # 레지스트리 메타데이터
    cat >> "$REGISTRY_CONF" << REGEOF
[$name]
path=$path
created=$(date +%Y-%m-%d_%H:%M:%S)
auto_session=true
status=registered
REGEOF

    echo -e "${GREEN}✓ Project registered${NC}"

    # 자동 세션 생성
    echo -e "${BLUE}🔄 Creating session...${NC}"
    local socket_path="$SOCKET_DIR/$name"

    cd "$path"
    export CLAUDE_CONFIG_DIR="/home/jclee/.claude"

    tmux -S "$socket_path" new-session -d -s "$name" \
        -c "$path" \
        "$CLAUDE_BIN --continue" 2>/dev/null

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✓ Session created${NC}"

        # 초기 설정
        sleep 2
        tmux -S "$socket_path" send-keys -t "$name" \
            "Project '$name' registered and ready for development in $path" C-m
    fi

    # 프로젝트 설정
    cd "$path"

    # Git 초기화
    if [[ ! -d ".git" ]]; then
        git init . >/dev/null 2>&1
        echo -e "${GREEN}✓ Git initialized${NC}"
    fi

    # README 생성
    if [[ ! -f "README.md" ]]; then
        cat > README.md << READMEEOF
# $name

Auto-registered project with ts command system.

## Quick Start

\`\`\`bash
ts $name              # Open Claude session
ts cmd $name "help"   # Send command
ts dashboard          # View all projects
\`\`\`

Created: $(date +%Y-%m-%d)
Path: $path
READMEEOF
        echo -e "${GREEN}✓ README created${NC}"
    fi

    echo -e "${GREEN}✅ Auto-registration complete: $name${NC}"
    echo -e "${CYAN}💡 Use: ts $name${NC}"
}

# 세션 상태 확인
check_health() {
    local name="$1"
    local socket_path="$SOCKET_DIR/$name"

    if [[ ! -S "$socket_path" ]]; then
        echo "dead"
        return 1
    fi

    if ! tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
        echo "inactive"
        return 1
    fi

    local claude_running=$(tmux -S "$socket_path" list-panes -t "$name" -F "#{pane_current_command}" 2>/dev/null | grep -c "node\|claude" || echo "0")

    if [[ $claude_running -gt 0 ]]; then
        echo "healthy"
    else
        echo "no_claude"
    fi
}

# 대시보드
show_dashboard() {
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           TS Advanced Dashboard${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

    load_projects

    local total=0
    local active=0
    local healthy=0

    echo -e "\n${BLUE}📊 Project Status:${NC}"
    for name in "${!KNOWN_PROJECTS[@]}"; do
        ((total++))
        local path="${KNOWN_PROJECTS[$name]}"
        local health=$(check_health "$name")
        local icon=""

        case "$health" in
            "healthy") icon="${GREEN}●${NC}"; ((active++)); ((healthy++)) ;;
            "no_claude") icon="${YELLOW}◐${NC}"; ((active++)) ;;
            "inactive") icon="${RED}○${NC}" ;;
            "dead") icon="${RED}✗${NC}" ;;
        esac

        printf "  %-15s %s %-12s %s\n" "$name" "$icon" "[$health]" "$path"
    done

    echo -e "\n${BLUE}📈 Statistics:${NC}"
    echo -e "  Total: $total | Active: $active | Healthy: $healthy"

    echo -e "\n${BLUE}🚀 Commands:${NC}"
    echo -e "  ts register <name> [path]  - Auto-register project"
    echo -e "  ts clean                   - Remove duplicates"
    echo -e "  ts recover <name>          - Auto-recover session"
    echo -e "  ts dashboard               - Show this dashboard"
}

# 자동 복구
auto_recover() {
    local name="$1"

    if [[ -z "$name" ]]; then
        echo -e "${YELLOW}Usage: ts recover <name>${NC}"
        return 1
    fi

    load_projects
    local path="${KNOWN_PROJECTS[$name]}"

    if [[ -z "$path" ]]; then
        echo -e "${RED}✗ Project not found: $name${NC}"
        return 1
    fi

    echo -e "${BLUE}🔧 Recovering session: $name${NC}"

    # 죽은 소켓 정리
    local socket_path="$SOCKET_DIR/$name"
    if [[ -S "$socket_path" ]] && ! tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
        rm -f "$socket_path"
    fi

    # 세션 재생성
    cd "$path"
    export CLAUDE_CONFIG_DIR="/home/jclee/.claude"

    tmux -S "$socket_path" new-session -d -s "$name" \
        -c "$path" \
        "$CLAUDE_BIN --continue" 2>/dev/null

    echo -e "${GREEN}✓ Session recovered${NC}"
}

# 메인 명령 처리
case "${1:-}" in
    "register"|"reg")
        auto_register "$2" "$3"
        ;;
    "clean"|"cleanup")
        clean_duplicates
        ;;
    "dashboard"|"dash")
        show_dashboard
        ;;
    "recover"|"fix")
        auto_recover "$2"
        ;;
    "health"|"check")
        if [[ -n "$2" ]]; then
            health=$(check_health "$2")
            echo -e "${BLUE}$2: $health${NC}"
        else
            show_dashboard
        fi
        ;;
    *)
        # 기존 ts 명령으로 전달 (add, del, cmd, projects 등)
        exec "$TS_ORIGINAL" "$@"
        ;;
esac
EOF

# 새로운 ts 설치
sudo mv /tmp/ts-ultimate /usr/local/bin/ts
sudo chmod +x /usr/local/bin/ts

echo "✅ Advanced TS installed!"

# 초기 정리 실행
echo ""
echo "🧹 Running initial cleanup..."
ts clean

echo ""
echo "📊 Current status:"
ts dashboard

echo ""
echo "🎉 Advanced TS Features Ready:"
echo "  ✅ Auto-registration: ts register <name> [path]"
echo "  ✅ Duplicate removal: ts clean"
echo "  ✅ Session recovery: ts recover <name>"
echo "  ✅ Health monitoring: ts health [name]"
echo "  ✅ Advanced dashboard: ts dashboard"
echo ""
echo "💡 Try: ts register myproject"