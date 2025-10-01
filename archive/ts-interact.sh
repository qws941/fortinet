#!/bin/bash
# TS Session Interaction Examples

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SOCKET_DIR="/home/jclee/.tmux/sockets"

# 1. 세션에 명령 보내기
send_to_session() {
    local session="$1"
    local command="$2"
    local socket="$SOCKET_DIR/$session"

    if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
        echo -e "${GREEN}📤 Sending to $session: $command${NC}"
        tmux -S "$socket" send-keys -t "$session" "$command" Enter
        return 0
    else
        echo -e "${RED}❌ Session $session not found${NC}"
        return 1
    fi
}

# 2. 세션의 출력 캡처
capture_output() {
    local session="$1"
    local socket="$SOCKET_DIR/$session"

    if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
        echo -e "${CYAN}📋 Capturing output from $session:${NC}"
        tmux -S "$socket" capture-pane -t "$session" -p | tail -20
    else
        echo -e "${RED}❌ Session $session not found${NC}"
    fi
}

# 3. 대화형 명령 실행
interactive_exec() {
    local session="$1"
    shift
    local commands=("$@")
    local socket="$SOCKET_DIR/$session"

    if [[ ! -S "$socket" ]] || ! tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
        echo -e "${YELLOW}🚀 Creating session: $session${NC}"
        tmux -S "$socket" new-session -d -s "$session"
        sleep 0.5
    fi

    echo -e "${CYAN}🔄 Interactive execution in $session${NC}"
    for cmd in "${commands[@]}"; do
        echo -e "${BLUE}  → $cmd${NC}"
        tmux -S "$socket" send-keys -t "$session" "$cmd" Enter
        sleep 0.5
    done

    # 결과 보기
    echo -e "${GREEN}📊 Results:${NC}"
    tmux -S "$socket" capture-pane -t "$session" -p | tail -10
}

# 4. 세션 모니터링
monitor_session() {
    local session="$1"
    local socket="$SOCKET_DIR/$session"

    echo -e "${CYAN}📊 Monitoring session: $session${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""

    while true; do
        if [[ -S "$socket" ]] && tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
            # 세션 정보
            local windows=$(tmux -S "$socket" list-windows -t "$session" -F "#{window_index}:#{window_name}" | wc -l)
            local panes=$(tmux -S "$socket" list-panes -t "$session" | wc -l)
            local current_cmd=$(tmux -S "$socket" display -p -t "$session" -F "#{pane_current_command}")

            printf "\r${GREEN}[%s]${NC} Windows: %d | Panes: %d | Running: %-20s" \
                "$(date +%H:%M:%S)" "$windows" "$panes" "$current_cmd"
        else
            printf "\r${RED}[%s] Session not active${NC}                    " "$(date +%H:%M:%S)"
        fi
        sleep 1
    done
}

# 5. 세션 간 파이프라인
pipe_sessions() {
    local source_session="$1"
    local dest_session="$2"
    local source_socket="$SOCKET_DIR/$source_session"
    local dest_socket="$SOCKET_DIR/$dest_session"

    echo -e "${CYAN}🔗 Piping from $source_session to $dest_session${NC}"

    # 소스 세션의 출력을 캡처
    local output=$(tmux -S "$source_socket" capture-pane -t "$source_session" -p | tail -1)

    # 대상 세션으로 전송
    if [[ -n "$output" ]]; then
        tmux -S "$dest_socket" send-keys -t "$dest_session" "$output" Enter
        echo -e "${GREEN}✓ Piped: $output${NC}"
    fi
}

# 6. 병렬 명령 실행
parallel_exec() {
    local command="$1"
    echo -e "${CYAN}🚀 Executing in parallel across all sessions:${NC}"
    echo -e "${BLUE}Command: $command${NC}"

    for socket in "$SOCKET_DIR"/*; do
        if [[ -S "$socket" ]]; then
            local session=$(basename "$socket")
            if tmux -S "$socket" has-session -t "$session" 2>/dev/null; then
                echo -e "${GREEN}  → $session${NC}"
                tmux -S "$socket" send-keys -t "$session" "$command" Enter &
            fi
        fi
    done
    wait
    echo -e "${GREEN}✓ Parallel execution complete${NC}"
}

# 메인 메뉴
show_menu() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           TS Session Interaction Menu${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}1.${NC} Send command to session"
    echo -e "${BLUE}2.${NC} Capture session output"
    echo -e "${BLUE}3.${NC} Interactive execution"
    echo -e "${BLUE}4.${NC} Monitor session"
    echo -e "${BLUE}5.${NC} Pipe between sessions"
    echo -e "${BLUE}6.${NC} Parallel execution"
    echo -e "${BLUE}7.${NC} List all sessions"
    echo -e "${BLUE}0.${NC} Exit"
    echo ""
}

# 예제 실행
if [[ "${1:-}" == "demo" ]]; then
    echo -e "${CYAN}🎬 Running TS Interaction Demo${NC}"
    echo ""

    # 테스트 세션 생성
    echo -e "${YELLOW}Creating test sessions...${NC}"
    tmux -S "$SOCKET_DIR/test1" new-session -d -s test1
    tmux -S "$SOCKET_DIR/test2" new-session -d -s test2

    # 명령 보내기
    send_to_session test1 "echo 'Hello from test1'"
    sleep 1

    # 출력 캡처
    capture_output test1

    # 병렬 실행
    parallel_exec "date"

    echo ""
    echo -e "${GREEN}Demo complete!${NC}"

elif [[ "${1:-}" == "menu" ]]; then
    # 대화형 메뉴
    while true; do
        show_menu
        read -p "Select option: " choice

        case $choice in
            1)
                read -p "Session name: " session
                read -p "Command: " command
                send_to_session "$session" "$command"
                ;;
            2)
                read -p "Session name: " session
                capture_output "$session"
                ;;
            3)
                read -p "Session name: " session
                echo "Enter commands (empty line to finish):"
                commands=()
                while true; do
                    read -p "> " cmd
                    [[ -z "$cmd" ]] && break
                    commands+=("$cmd")
                done
                interactive_exec "$session" "${commands[@]}"
                ;;
            4)
                read -p "Session name: " session
                monitor_session "$session"
                ;;
            5)
                read -p "Source session: " source
                read -p "Destination session: " dest
                pipe_sessions "$source" "$dest"
                ;;
            6)
                read -p "Command: " command
                parallel_exec "$command"
                ;;
            7)
                ts list
                ;;
            0)
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option${NC}"
                ;;
        esac

        echo ""
        read -p "Press Enter to continue..."
    done
else
    # 사용법 표시
    echo -e "${CYAN}TS Session Interaction Tool${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC}"
    echo -e "  $0 demo   - Run demonstration"
    echo -e "  $0 menu   - Interactive menu"
    echo ""
    echo -e "${YELLOW}Functions available:${NC}"
    echo -e "  • send_to_session <session> <command>"
    echo -e "  • capture_output <session>"
    echo -e "  • interactive_exec <session> <commands...>"
    echo -e "  • monitor_session <session>"
    echo -e "  • pipe_sessions <source> <dest>"
    echo -e "  • parallel_exec <command>"
    echo ""
    echo -e "${BLUE}Example:${NC}"
    echo -e "  source $0"
    echo -e "  send_to_session myapp 'npm start'"
    echo -e "  capture_output myapp"
fi