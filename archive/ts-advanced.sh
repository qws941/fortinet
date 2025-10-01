#!/bin/bash
# Advanced TS Command System - Auto-registration and Session Management

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
AUTO_SESSIONS_CONF="$CONFIG_DIR/auto-sessions.conf"
CLAUDE_BIN="/home/jclee/.claude/local/claude --dangerously-skip-permissions --mcp-config /home/jclee/.claude/mcp.json"

# 디렉토리 생성
mkdir -p "$CONFIG_DIR" "$SOCKET_DIR"

# 중복 제거 함수
remove_duplicates() {
    local file="$1"
    if [[ -f "$file" ]]; then
        # 백업 생성
        cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"

        # 중복 제거 (마지막 항목 유지)
        awk '!seen[$0]++' "$file" > "$file.tmp"
        mv "$file.tmp" "$file"

        echo -e "${GREEN}✓ Removed duplicates from $(basename "$file")${NC}"
    fi
}

# 전체 시스템 중복 제거
clean_all_duplicates() {
    echo -e "${CYAN}🧹 Cleaning all duplicates from ts system...${NC}"

    # 설정 파일들 중복 제거
    for conf in "$PROJECTS_CONF" "$REGISTRY_CONF" "$AUTO_SESSIONS_CONF"; do
        remove_duplicates "$conf"
    done

    # 죽은 소켓 제거
    echo -e "${BLUE}Cleaning dead sockets...${NC}"
    for socket in "$SOCKET_DIR"/*; do
        if [[ -S "$socket" ]]; then
            local session_name=$(basename "$socket")
            if ! tmux -S "$socket" has-session -t "$session_name" 2>/dev/null; then
                rm -f "$socket"
                echo -e "${YELLOW}✓ Removed dead socket: $session_name${NC}"
            fi
        fi
    done

    echo -e "${GREEN}✅ System cleanup complete${NC}"
}

# 프로젝트 자동 등록 시스템
auto_register_project() {
    local project_name="$1"
    local project_path="${2:-$PWD}"
    local auto_session="${3:-true}"
    local auto_setup="${4:-true}"

    if [[ -z "$project_name" ]]; then
        echo -e "${RED}Error: Project name required${NC}"
        return 1
    fi

    # 절대 경로로 변환
    project_path=$(realpath "$project_path" 2>/dev/null || echo "$project_path")

    echo -e "${CYAN}🚀 Auto-registering project: $project_name${NC}"
    echo -e "${BLUE}📂 Path: $project_path${NC}"

    # 디렉토리 생성
    if [[ ! -d "$project_path" ]]; then
        mkdir -p "$project_path" || {
            echo -e "${RED}✗ Failed to create directory${NC}"
            return 1
        }
        echo -e "${GREEN}✓ Created directory${NC}"
    fi

    # 프로젝트 등록
    echo "$project_name=\"$project_path\"" >> "$PROJECTS_CONF"

    # 레지스트리에 메타데이터 저장
    cat >> "$REGISTRY_CONF" << EOF
[$project_name]
path=$project_path
created=$(date +%Y-%m-%d_%H:%M:%S)
auto_session=$auto_session
auto_setup=$auto_setup
status=registered
last_accessed=never
EOF

    echo -e "${GREEN}✓ Project registered${NC}"

    # 자동 세션 생성
    if [[ "$auto_session" == "true" ]]; then
        echo -e "${BLUE}🔄 Creating automatic session...${NC}"
        create_auto_session "$project_name" "$project_path"
    fi

    # 자동 설정
    if [[ "$auto_setup" == "true" ]]; then
        echo -e "${BLUE}⚙️ Running automatic setup...${NC}"
        auto_project_setup "$project_name" "$project_path"
    fi

    # 자동 세션 목록에 추가
    echo "$project_name:$auto_session" >> "$AUTO_SESSIONS_CONF"

    echo -e "${GREEN}✅ Auto-registration complete: $project_name${NC}"
    echo -e "${CYAN}💡 Use: ts $project_name${NC}"
}

# 자동 세션 생성
create_auto_session() {
    local project_name="$1"
    local project_path="$2"
    local socket_path="$SOCKET_DIR/$project_name"

    # 기존 세션 확인
    if tmux -S "$socket_path" has-session -t "$project_name" 2>/dev/null; then
        echo -e "${YELLOW}⚠ Session already exists, attaching...${NC}"
        return 0
    fi

    # Claude 환경 설정
    cd "$project_path"
    export CLAUDE_CONFIG_DIR="/home/jclee/.claude"

    # 백그라운드 세션 생성
    tmux -S "$socket_path" new-session -d -s "$project_name" \
        -c "$project_path" \
        "$CLAUDE_BIN --continue" 2>/dev/null

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✓ Auto-session created${NC}"

        # 초기 설정 명령 전송
        sleep 2
        tmux -S "$socket_path" send-keys -t "$project_name" \
            "Project: $project_name initialized in $project_path. Ready for development!" C-m
    else
        echo -e "${RED}✗ Failed to create session${NC}"
    fi
}

# 프로젝트 자동 설정
auto_project_setup() {
    local project_name="$1"
    local project_path="$2"

    cd "$project_path"

    # 프로젝트 타입 감지 및 설정
    echo -e "${BLUE}🔍 Detecting project type...${NC}"

    # Git 초기화
    if [[ ! -d ".git" ]]; then
        git init . >/dev/null 2>&1
        echo -e "${GREEN}✓ Git repository initialized${NC}"
    fi

    # .gitignore 생성
    if [[ ! -f ".gitignore" ]]; then
        cat > .gitignore << 'EOF'
# TS Sessions
.ts/
.claude/

# Logs
*.log
logs/

# Temporary files
*.tmp
.DS_Store

# Node modules
node_modules/

# Environment files
.env
.env.local

# Cache
.cache/
*.cache
EOF
        echo -e "${GREEN}✓ .gitignore created${NC}"
    fi

    # 프로젝트 README 생성
    if [[ ! -f "README.md" ]]; then
        cat > README.md << EOF
# $project_name

Project automatically registered with ts command system.

## Quick Start

\`\`\`bash
ts $project_name    # Open Claude session
ts list            # Show all sessions
ts $project_name cmd "help with this project"
\`\`\`

## Created

- **Date**: $(date +%Y-%m-%d)
- **Path**: $project_path
- **TS Session**: $project_name

## Commands

- \`ts $project_name\` - Open/attach to Claude session
- \`ts cmd $project_name "<command>"\` - Send command to Claude
- \`ts del $project_name\` - Remove from registry

EOF
        echo -e "${GREEN}✓ README.md created${NC}"
    fi

    # 프로젝트 메타데이터 디렉토리
    mkdir -p ".ts"
    echo "project_name=$project_name" > ".ts/config"
    echo "created=$(date +%Y-%m-%d_%H:%M:%S)" >> ".ts/config"
    echo "auto_managed=true" >> ".ts/config"

    echo -e "${GREEN}✓ Project setup complete${NC}"
}

# 지능형 프로젝트 찾기
smart_find_project() {
    local query="$1"
    local matches=()

    # 정확한 매치 먼저 확인
    if [[ -n "${KNOWN_PROJECTS[$query]}" ]]; then
        echo "${KNOWN_PROJECTS[$query]}"
        return 0
    fi

    # 부분 매치 검색
    for key in "${!KNOWN_PROJECTS[@]}"; do
        if [[ "$key" == *"$query"* ]]; then
            matches+=("$key:${KNOWN_PROJECTS[$key]}")
        fi
    done

    # 결과 처리
    if [[ ${#matches[@]} -eq 0 ]]; then
        return 1
    elif [[ ${#matches[@]} -eq 1 ]]; then
        echo "${matches[0]#*:}"
        return 0
    else
        echo -e "${YELLOW}Multiple matches found:${NC}"
        for match in "${matches[@]}"; do
            echo "  ${match%:*} -> ${match#*:}"
        done
        return 2
    fi
}

# 세션 상태 모니터링
monitor_session_health() {
    local session_name="$1"
    local socket_path="$SOCKET_DIR/$session_name"

    if [[ ! -S "$socket_path" ]]; then
        echo "dead"
        return 1
    fi

    if ! tmux -S "$socket_path" has-session -t "$session_name" 2>/dev/null; then
        echo "inactive"
        return 1
    fi

    # Claude 프로세스 확인
    local claude_running=$(tmux -S "$socket_path" list-panes -t "$session_name" -F "#{pane_current_command}" 2>/dev/null | grep -c "node\|claude" || echo "0")

    if [[ $claude_running -gt 0 ]]; then
        echo "healthy"
        return 0
    else
        echo "no_claude"
        return 1
    fi
}

# 자동 복구 시스템
auto_recovery() {
    local session_name="$1"
    local project_path="$2"

    echo -e "${BLUE}🔧 Auto-recovering session: $session_name${NC}"

    # 죽은 소켓 정리
    local socket_path="$SOCKET_DIR/$session_name"
    if [[ -S "$socket_path" ]] && ! tmux -S "$socket_path" has-session -t "$session_name" 2>/dev/null; then
        rm -f "$socket_path"
    fi

    # 세션 재생성
    create_auto_session "$session_name" "$project_path"

    echo -e "${GREEN}✓ Session recovered${NC}"
}

# 프로젝트 상태 대시보드
show_project_dashboard() {
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           TS Advanced Project Dashboard${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

    # 로드 프로젝트 목록
    load_custom_projects

    echo -e "\n${BLUE}📊 Project Statistics:${NC}"
    local total_projects=0
    local active_sessions=0
    local healthy_sessions=0

    for key in "${!KNOWN_PROJECTS[@]}"; do
        ((total_projects++))
        local health=$(monitor_session_health "$key")
        case "$health" in
            "healthy") ((active_sessions++)); ((healthy_sessions++)) ;;
            "no_claude") ((active_sessions++)) ;;
        esac
    done

    echo -e "  Total Projects: $total_projects"
    echo -e "  Active Sessions: $active_sessions"
    echo -e "  Healthy Sessions: $healthy_sessions"

    echo -e "\n${BLUE}🚀 Project Status:${NC}"
    for key in "${!KNOWN_PROJECTS[@]}"; do
        local path="${KNOWN_PROJECTS[$key]}"
        local health=$(monitor_session_health "$key")
        local status_icon=""

        case "$health" in
            "healthy") status_icon="${GREEN}●${NC}" ;;
            "no_claude") status_icon="${YELLOW}◐${NC}" ;;
            "inactive") status_icon="${RED}○${NC}" ;;
            "dead") status_icon="${RED}✗${NC}" ;;
        esac

        printf "  %-15s %s %-12s %s\n" "$key" "$status_icon" "[$health]" "$path"
    done

    echo -e "\n${BLUE}💡 Quick Actions:${NC}"
    echo -e "  ts register <name> [path]  - Register new project"
    echo -e "  ts recover <name>          - Auto-recover session"
    echo -e "  ts clean                   - Remove duplicates"
    echo -e "  ts dashboard               - Show this dashboard"

    echo -e "\n${CYAN}════════════════════════════════════════════════════${NC}"
}

# 설정 로드 함수
load_custom_projects() {
    declare -gA KNOWN_PROJECTS

    # 내장 프로젝트
    KNOWN_PROJECTS["claude"]="/home/jclee/.claude"
    KNOWN_PROJECTS["tmux"]="/home/jclee/app/tmux"
    KNOWN_PROJECTS["grafana"]="/home/jclee/app/grafana"
    KNOWN_PROJECTS["safework"]="/home/jclee/app/safework"

    # 커스텀 프로젝트 로드
    if [[ -f "$PROJECTS_CONF" ]]; then
        while IFS='=' read -r name path; do
            [[ -n "$name" && "$name" != \#* ]] && KNOWN_PROJECTS["$name"]=$(eval echo "$path")
        done < "$PROJECTS_CONF"
    fi
}

# 메인 처리 함수들
case "${1:-}" in
    "register"|"reg")
        # 고급 프로젝트 등록
        auto_register_project "$2" "$3" "${4:-true}" "${5:-true}"
        ;;

    "clean"|"cleanup")
        # 전체 시스템 정리
        clean_all_duplicates
        ;;

    "dashboard"|"dash"|"status")
        # 프로젝트 대시보드
        show_project_dashboard
        ;;

    "recover"|"fix")
        # 세션 자동 복구
        if [[ -n "$2" ]]; then
            load_custom_projects
            if [[ -n "${KNOWN_PROJECTS[$2]}" ]]; then
                auto_recovery "$2" "${KNOWN_PROJECTS[$2]}"
            else
                echo -e "${RED}✗ Project not found: $2${NC}"
            fi
        else
            echo -e "${YELLOW}Usage: ts recover <project_name>${NC}"
        fi
        ;;

    "health"|"check")
        # 건강 상태 확인
        if [[ -n "$2" ]]; then
            health=$(monitor_session_health "$2")
            echo -e "${BLUE}Session $2: $health${NC}"
        else
            echo -e "${BLUE}Checking all sessions...${NC}"
            load_custom_projects
            for key in "${!KNOWN_PROJECTS[@]}"; do
                health=$(monitor_session_health "$key")
                echo -e "  $key: $health"
            done
        fi
        ;;

    *)
        # 기존 ts 명령으로 전달
        exec /usr/local/bin/ts-original "$@"
        ;;
esac