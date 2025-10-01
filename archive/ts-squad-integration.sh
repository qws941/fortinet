#!/bin/bash
# TS Squad Integration - Claude Squad features for ts command
# Adds git worktrees + multi-agent delegation capabilities

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 설정
SOCKET_DIR="/home/jclee/.tmux/sockets"
CONFIG_DIR="$HOME/.config/ts"
WORKTREE_BASE="$HOME/.ts-worktrees"
AGENT_REGISTRY="$CONFIG_DIR/agents.json"
SQUAD_CONFIG="$CONFIG_DIR/squad.conf"

# 디렉토리 생성
mkdir -p "$CONFIG_DIR" "$SOCKET_DIR" "$WORKTREE_BASE"

# Agent Registry 초기화
init_agent_registry() {
    if [[ ! -f "$AGENT_REGISTRY" ]]; then
        cat > "$AGENT_REGISTRY" << 'EOF'
{
  "agents": {},
  "active_count": 0,
  "max_agents": 10,
  "created_at": "",
  "last_updated": ""
}
EOF
        echo -e "${GREEN}✓ Agent registry initialized${NC}"
    fi
}

# Git Worktree 생성 및 에이전트 할당
spawn_agent() {
    local task_name="$1"
    local branch_name="$2"
    local task_description="$3"
    local auto_mode="${4:-false}"

    if [[ -z "$task_name" ]]; then
        echo -e "${YELLOW}Usage: ts squad spawn <task_name> [branch_name] [description] [--auto]${NC}"
        echo -e "${BLUE}Examples:${NC}"
        echo -e "  ts squad spawn fix-auth-bug feature/fix-auth 'Fix authentication bug'"
        echo -e "  ts squad spawn add-api feature/new-api 'Add REST API endpoints' --auto"
        return 1
    fi

    # branch_name이 없으면 task_name으로 생성
    if [[ -z "$branch_name" ]]; then
        branch_name="agent/$task_name-$(date +%s)"
    fi

    local agent_id="agent-$task_name"
    local worktree_path="$WORKTREE_BASE/$agent_id"
    local socket_path="$SOCKET_DIR/$agent_id"

    echo -e "${CYAN}🤖 Spawning agent: $agent_id${NC}"
    echo -e "${BLUE}📂 Worktree: $worktree_path${NC}"
    echo -e "${BLUE}🌿 Branch: $branch_name${NC}"

    # 1. Git Worktree 생성
    if [[ -d "$worktree_path" ]]; then
        echo -e "${YELLOW}⚠ Worktree already exists, removing...${NC}"
        git worktree remove -f "$worktree_path" 2>/dev/null || rm -rf "$worktree_path"
    fi

    # 현재 디렉토리가 git repo인지 확인
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${RED}✗ Current directory is not a git repository${NC}"
        return 1
    fi

    # Worktree 생성
    git worktree add -b "$branch_name" "$worktree_path" 2>/dev/null || {
        # 브랜치가 이미 존재하는 경우
        git worktree add "$worktree_path" "$branch_name" 2>/dev/null || {
            echo -e "${RED}✗ Failed to create worktree${NC}"
            return 1
        }
    }

    echo -e "${GREEN}✓ Worktree created${NC}"

    # 2. Tmux 세션 생성 (격리된)
    CLAUDE_BIN="/home/jclee/.claude/local/claude --dangerously-skip-permissions --mcp-config /home/jclee/.claude/mcp.json"

    tmux -S "$socket_path" new-session -d -s "$agent_id" \
        -c "$worktree_path" \
        "cd $worktree_path && export TASK_NAME='$task_name' && export TASK_DESCRIPTION='$task_description' && $CLAUDE_BIN --continue" 2>/dev/null

    if [[ $? -eq 0 ]]; then
        echo -e "${GREEN}✓ Tmux session created${NC}"

        # 3. 에이전트 레지스트리에 등록
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

        # jq로 JSON 업데이트
        jq --arg id "$agent_id" \
           --arg task "$task_name" \
           --arg branch "$branch_name" \
           --arg path "$worktree_path" \
           --arg socket "$socket_path" \
           --arg desc "$task_description" \
           --arg auto "$auto_mode" \
           --arg time "$timestamp" \
           '.agents[$id] = {
               "task_name": $task,
               "branch": $branch,
               "worktree_path": $path,
               "socket_path": $socket,
               "description": $desc,
               "auto_mode": ($auto == "true"),
               "status": "active",
               "created_at": $time,
               "last_active": $time
           } | .active_count = (.agents | length) | .last_updated = $time' \
           "$AGENT_REGISTRY" > "$AGENT_REGISTRY.tmp" && mv "$AGENT_REGISTRY.tmp" "$AGENT_REGISTRY"

        echo -e "${GREEN}✓ Agent registered${NC}"

        # 4. 초기 프롬프트 전송
        sleep 2
        local init_prompt="You are Agent $agent_id working on: $task_name"
        if [[ -n "$task_description" ]]; then
            init_prompt="$init_prompt\n\nTask Description: $task_description"
        fi
        init_prompt="$init_prompt\n\nYou are working in an isolated git worktree on branch '$branch_name'.\nAll changes you make are isolated from other agents.\n\nReady to start!"

        tmux -S "$socket_path" send-keys -t "$agent_id" "$init_prompt" C-m

        # 5. Grafana 로그 전송
        log_to_grafana "agent_spawned" "$agent_id" "$task_name" "$branch_name"

        echo -e "${GREEN}✅ Agent $agent_id spawned successfully${NC}"
        echo -e "${CYAN}💡 Attach with: ts squad attach $agent_id${NC}"

        if [[ "$auto_mode" == "true" ]]; then
            echo -e "${YELLOW}🤖 Running in AUTO mode (will auto-approve prompts)${NC}"
        fi

    else
        echo -e "${RED}✗ Failed to create tmux session${NC}"
        git worktree remove -f "$worktree_path"
        return 1
    fi
}

# 에이전트 목록 보기
list_agents() {
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           TS Squad - Active Agents${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

    if [[ ! -f "$AGENT_REGISTRY" ]]; then
        echo -e "${YELLOW}No agents registered${NC}"
        return 0
    fi

    local active_count=$(jq -r '.active_count // 0' "$AGENT_REGISTRY")
    local max_agents=$(jq -r '.max_agents // 10' "$AGENT_REGISTRY")

    echo -e "\n${BLUE}📊 Agent Statistics:${NC}"
    echo -e "  Active: $active_count / $max_agents"

    echo -e "\n${BLUE}🤖 Active Agents:${NC}"
    printf "  %-20s %-25s %-20s %s\n" "AGENT ID" "TASK" "BRANCH" "STATUS"
    echo -e "  ${CYAN}────────────────────────────────────────────────────────────────────────────${NC}"

    jq -r '.agents | to_entries[] | "\(.key)|\(.value.task_name)|\(.value.branch)|\(.value.status)"' "$AGENT_REGISTRY" | \
    while IFS='|' read -r agent_id task_name branch status; do
        local status_icon=""
        case "$status" in
            "active") status_icon="${GREEN}●${NC}" ;;
            "paused") status_icon="${YELLOW}◐${NC}" ;;
            "failed") status_icon="${RED}✗${NC}" ;;
            *) status_icon="${BLUE}○${NC}" ;;
        esac
        printf "  %-20s %-25s %-20s %s %s\n" "$agent_id" "$task_name" "$branch" "$status_icon" "$status"
    done

    echo -e "\n${BLUE}💡 Commands:${NC}"
    echo -e "  ts squad spawn <task> [branch]  - Spawn new agent"
    echo -e "  ts squad attach <agent_id>      - Attach to agent session"
    echo -e "  ts squad kill <agent_id>        - Kill agent and cleanup"
    echo -e "  ts squad checkpoint <agent_id>  - Create checkpoint and pause"
    echo -e "  ts squad resume <agent_id>      - Resume paused agent"
    echo -e "  ts squad delegate <task>        - Auto-delegate to new agent"

    echo -e "\n${CYAN}════════════════════════════════════════════════════${NC}"
}

# 에이전트에 연결
attach_agent() {
    local agent_id="$1"

    if [[ -z "$agent_id" ]]; then
        echo -e "${YELLOW}Usage: ts squad attach <agent_id>${NC}"
        list_agents
        return 1
    fi

    # 에이전트 존재 확인
    if ! jq -e ".agents[\"$agent_id\"]" "$AGENT_REGISTRY" > /dev/null 2>&1; then
        echo -e "${RED}✗ Agent not found: $agent_id${NC}"
        list_agents
        return 1
    fi

    local socket_path=$(jq -r ".agents[\"$agent_id\"].socket_path" "$AGENT_REGISTRY")

    if [[ ! -S "$socket_path" ]]; then
        echo -e "${RED}✗ Agent socket not found${NC}"
        return 1
    fi

    # tmux 안에 있는지 확인
    if [[ -n "$TMUX" ]]; then
        # 이미 tmux 안이면 새 윈도우로 열기
        tmux -S "$socket_path" new-window -t "$agent_id" -c "$(jq -r ".agents[\"$agent_id\"].worktree_path" "$AGENT_REGISTRY")"
    else
        # tmux 밖이면 attach
        tmux -S "$socket_path" attach-session -t "$agent_id"
    fi
}

# 에이전트 종료 및 정리
kill_agent() {
    local agent_id="$1"
    local cleanup_worktree="${2:-true}"

    if [[ -z "$agent_id" ]]; then
        echo -e "${YELLOW}Usage: ts squad kill <agent_id> [keep-worktree]${NC}"
        list_agents
        return 1
    fi

    # 에이전트 존재 확인
    if ! jq -e ".agents[\"$agent_id\"]" "$AGENT_REGISTRY" > /dev/null 2>&1; then
        echo -e "${RED}✗ Agent not found: $agent_id${NC}"
        return 1
    fi

    echo -e "${CYAN}🛑 Killing agent: $agent_id${NC}"

    local socket_path=$(jq -r ".agents[\"$agent_id\"].socket_path" "$AGENT_REGISTRY")
    local worktree_path=$(jq -r ".agents[\"$agent_id\"].worktree_path" "$AGENT_REGISTRY")
    local branch=$(jq -r ".agents[\"$agent_id\"].branch" "$AGENT_REGISTRY")

    # 1. Tmux 세션 종료
    if [[ -S "$socket_path" ]]; then
        tmux -S "$socket_path" kill-session -t "$agent_id" 2>/dev/null
        rm -f "$socket_path"
        echo -e "${GREEN}✓ Tmux session killed${NC}"
    fi

    # 2. Git Worktree 정리
    if [[ "$cleanup_worktree" == "true" && -d "$worktree_path" ]]; then
        echo -e "${YELLOW}⚠ Removing worktree: $worktree_path${NC}"
        git worktree remove -f "$worktree_path" 2>/dev/null
        echo -e "${GREEN}✓ Worktree removed${NC}"
    else
        echo -e "${BLUE}💾 Worktree preserved: $worktree_path${NC}"
    fi

    # 3. 레지스트리에서 제거
    jq --arg id "$agent_id" \
       'del(.agents[$id]) | .active_count = (.agents | length) | .last_updated = now | strftime("%Y-%m-%dT%H:%M:%SZ")' \
       "$AGENT_REGISTRY" > "$AGENT_REGISTRY.tmp" && mv "$AGENT_REGISTRY.tmp" "$AGENT_REGISTRY"

    # 4. Grafana 로그
    log_to_grafana "agent_killed" "$agent_id" "" "$branch"

    echo -e "${GREEN}✅ Agent $agent_id killed${NC}"
}

# 체크포인트 생성 (코드 저장 및 일시정지)
checkpoint_agent() {
    local agent_id="$1"
    local checkpoint_msg="${2:-Checkpoint by ts squad}"

    if [[ -z "$agent_id" ]]; then
        echo -e "${YELLOW}Usage: ts squad checkpoint <agent_id> [message]${NC}"
        list_agents
        return 1
    fi

    # 에이전트 존재 확인
    if ! jq -e ".agents[\"$agent_id\"]" "$AGENT_REGISTRY" > /dev/null 2>&1; then
        echo -e "${RED}✗ Agent not found: $agent_id${NC}"
        return 1
    fi

    local worktree_path=$(jq -r ".agents[\"$agent_id\"].worktree_path" "$AGENT_REGISTRY")
    local branch=$(jq -r ".agents[\"$agent_id\"].branch" "$AGENT_REGISTRY")

    echo -e "${CYAN}📸 Creating checkpoint for agent: $agent_id${NC}"

    cd "$worktree_path" || return 1

    # 1. Git commit
    git add . 2>/dev/null
    git commit -m "$checkpoint_msg" 2>/dev/null || {
        echo -e "${YELLOW}⚠ No changes to commit${NC}"
    }

    echo -e "${GREEN}✓ Checkpoint created${NC}"

    # 2. 에이전트 상태 변경
    jq --arg id "$agent_id" \
       --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
       '.agents[$id].status = "paused" | .agents[$id].last_checkpoint = $time' \
       "$AGENT_REGISTRY" > "$AGENT_REGISTRY.tmp" && mv "$AGENT_REGISTRY.tmp" "$AGENT_REGISTRY"

    # 3. Grafana 로그
    log_to_grafana "agent_checkpoint" "$agent_id" "$checkpoint_msg" "$branch"

    echo -e "${GREEN}✅ Agent $agent_id checkpointed and paused${NC}"
    echo -e "${CYAN}💡 Resume with: ts squad resume $agent_id${NC}"
}

# 일시정지된 에이전트 재개
resume_agent() {
    local agent_id="$1"

    if [[ -z "$agent_id" ]]; then
        echo -e "${YELLOW}Usage: ts squad resume <agent_id>${NC}"
        list_agents
        return 1
    fi

    # 에이전트 존재 확인
    if ! jq -e ".agents[\"$agent_id\"]" "$AGENT_REGISTRY" > /dev/null 2>&1; then
        echo -e "${RED}✗ Agent not found: $agent_id${NC}"
        return 1
    fi

    local status=$(jq -r ".agents[\"$agent_id\"].status" "$AGENT_REGISTRY")
    if [[ "$status" != "paused" ]]; then
        echo -e "${YELLOW}⚠ Agent is not paused (status: $status)${NC}"
        return 1
    fi

    echo -e "${CYAN}▶️  Resuming agent: $agent_id${NC}"

    # 상태 변경
    jq --arg id "$agent_id" \
       --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
       '.agents[$id].status = "active" | .agents[$id].last_active = $time' \
       "$AGENT_REGISTRY" > "$AGENT_REGISTRY.tmp" && mv "$AGENT_REGISTRY.tmp" "$AGENT_REGISTRY"

    # Grafana 로그
    log_to_grafana "agent_resumed" "$agent_id" "" ""

    echo -e "${GREEN}✅ Agent $agent_id resumed${NC}"
    echo -e "${CYAN}💡 Attach with: ts squad attach $agent_id${NC}"
}

# 작업 자동 위임 (새 에이전트 생성 및 작업 할당)
delegate_task() {
    local task_description="$1"
    local auto_mode="${2:-false}"

    if [[ -z "$task_description" ]]; then
        echo -e "${YELLOW}Usage: ts squad delegate '<task_description>' [--auto]${NC}"
        echo -e "${BLUE}Examples:${NC}"
        echo -e "  ts squad delegate 'Fix the login authentication bug'"
        echo -e "  ts squad delegate 'Add REST API for user management' --auto"
        return 1
    fi

    echo -e "${CYAN}🎯 Delegating task to new agent...${NC}"
    echo -e "${BLUE}📝 Task: $task_description${NC}"

    # 자동으로 task_name 생성
    local task_name=$(echo "$task_description" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-30)
    local branch_name="agent/$task_name-$(date +%s)"

    # 에이전트 생성
    spawn_agent "$task_name" "$branch_name" "$task_description" "$auto_mode"
}

# Grafana 로그 전송
log_to_grafana() {
    local event="$1"
    local agent_id="$2"
    local message="$3"
    local branch="$4"

    # Loki 엔드포인트 (실제 환경에 맞게 수정)
    local loki_url="http://localhost:3100/loki/api/v1/push"

    # 타임스탬프 (나노초)
    local timestamp=$(date +%s%N)

    # JSON 페이로드
    local payload=$(cat <<EOF
{
  "streams": [
    {
      "stream": {
        "job": "ts-squad",
        "event": "$event",
        "agent_id": "$agent_id",
        "branch": "$branch"
      },
      "values": [
        ["$timestamp", "$message"]
      ]
    }
  ]
}
EOF
)

    # Loki로 전송 (에러 무시)
    curl -s -X POST "$loki_url" \
        -H "Content-Type: application/json" \
        -d "$payload" > /dev/null 2>&1 || true
}

# 모든 에이전트 상태 요약
dashboard() {
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           TS Squad Dashboard${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

    if [[ ! -f "$AGENT_REGISTRY" ]]; then
        echo -e "${YELLOW}No agents registered${NC}"
        return 0
    fi

    local total=$(jq -r '.agents | length' "$AGENT_REGISTRY")
    local active=$(jq -r '[.agents[] | select(.status == "active")] | length' "$AGENT_REGISTRY")
    local paused=$(jq -r '[.agents[] | select(.status == "paused")] | length' "$AGENT_REGISTRY")
    local failed=$(jq -r '[.agents[] | select(.status == "failed")] | length' "$AGENT_REGISTRY")

    echo -e "\n${BLUE}📊 Overall Statistics:${NC}"
    echo -e "  Total Agents:  $total"
    echo -e "  ${GREEN}Active:${NC}        $active"
    echo -e "  ${YELLOW}Paused:${NC}        $paused"
    echo -e "  ${RED}Failed:${NC}        $failed"

    echo -e "\n${BLUE}🌿 Git Worktrees:${NC}"
    git worktree list 2>/dev/null | grep "$WORKTREE_BASE" | while read -r line; do
        echo -e "  $line"
    done

    echo -e "\n${BLUE}💾 Disk Usage:${NC}"
    du -sh "$WORKTREE_BASE" 2>/dev/null | awk '{print "  Worktrees: " $1}'

    echo -e "\n${CYAN}════════════════════════════════════════════════════${NC}"
}

# 메인 명령 라우팅
case "${1:-help}" in
    "spawn"|"create")
        shift
        spawn_agent "$@"
        ;;

    "list"|"ls")
        list_agents
        ;;

    "attach"|"connect"|"join")
        shift
        attach_agent "$@"
        ;;

    "kill"|"stop"|"terminate")
        shift
        kill_agent "$@"
        ;;

    "checkpoint"|"save")
        shift
        checkpoint_agent "$@"
        ;;

    "resume"|"continue")
        shift
        resume_agent "$@"
        ;;

    "delegate"|"assign")
        shift
        delegate_task "$@"
        ;;

    "dashboard"|"status"|"dash")
        dashboard
        ;;

    "init")
        init_agent_registry
        echo -e "${GREEN}✅ TS Squad initialized${NC}"
        ;;

    "help"|*)
        echo -e "${CYAN}TS Squad - Multi-Agent Task Management${NC}"
        echo -e "${BLUE}Inspired by Claude Squad with git worktrees${NC}"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo -e "  ${GREEN}ts squad spawn${NC} <task> [branch] [desc] [--auto]"
        echo -e "    Spawn new agent with isolated git worktree"
        echo ""
        echo -e "  ${GREEN}ts squad list${NC}"
        echo -e "    List all active agents"
        echo ""
        echo -e "  ${GREEN}ts squad attach${NC} <agent_id>"
        echo -e "    Attach to agent's tmux session"
        echo ""
        echo -e "  ${GREEN}ts squad checkpoint${NC} <agent_id> [message]"
        echo -e "    Create checkpoint and pause agent"
        echo ""
        echo -e "  ${GREEN}ts squad resume${NC} <agent_id>"
        echo -e "    Resume paused agent"
        echo ""
        echo -e "  ${GREEN}ts squad kill${NC} <agent_id> [keep-worktree]"
        echo -e "    Kill agent and cleanup worktree"
        echo ""
        echo -e "  ${GREEN}ts squad delegate${NC} '<task_description>' [--auto]"
        echo -e "    Auto-delegate task to new agent"
        echo ""
        echo -e "  ${GREEN}ts squad dashboard${NC}"
        echo -e "    Show comprehensive status dashboard"
        echo ""
        echo -e "${CYAN}Examples:${NC}"
        echo -e "  ts squad spawn fix-auth feature/fix-auth 'Fix authentication bug'"
        echo -e "  ts squad delegate 'Add REST API endpoints' --auto"
        echo -e "  ts squad list"
        echo -e "  ts squad attach agent-fix-auth"
        echo -e "  ts squad checkpoint agent-fix-auth 'Completed phase 1'"
        echo -e "  ts squad kill agent-fix-auth"
        ;;
esac
