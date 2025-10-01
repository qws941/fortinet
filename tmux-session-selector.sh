#!/bin/bash
# Tmux 세션 선택기 - 인터랙티브 메뉴

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# 세션 목록 가져오기
get_sessions() {
    tmux ls -F "#{session_name}|#{session_windows}|#{session_created}|#{session_attached}" 2>/dev/null || echo ""
}

# 메인 메뉴 표시
show_menu() {
    clear
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║           🖥️  TMUX 세션 선택기                        ║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""

    sessions=$(get_sessions)

    if [ -z "$sessions" ]; then
        echo -e "${YELLOW}❌ 실행 중인 tmux 세션이 없습니다${NC}"
        echo ""
        echo -e "${GREEN}[N]${NC} 새 세션 생성"
        echo -e "${RED}[Q]${NC} 종료"
        return
    fi

    # 세션 목록을 배열로 저장
    declare -ga SESSION_ARRAY
    SESSION_ARRAY=()

    local index=1
    echo -e "${BOLD}📋 세션 목록:${NC}"
    echo ""

    while IFS='|' read -r name windows created attached; do
        SESSION_ARRAY+=("$name")

        if [ "$attached" = "1" ]; then
            status="${GREEN}🟢 연결됨${NC}"
        else
            status="${YELLOW}⚪ 분리됨${NC}"
        fi

        created_date=$(date -d "@$created" "+%Y-%m-%d %H:%M" 2>/dev/null || echo "unknown")

        echo -e "${BOLD}${BLUE}[$index]${NC} ${BOLD}$name${NC}"
        echo -e "    └─ 윈도우: ${windows}개 | 생성: ${created_date} | 상태: $status"
        echo ""

        ((index++))
    done <<< "$sessions"

    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}[1-${#SESSION_ARRAY[@]}]${NC} 세션 연결 (바로 attach)"
    echo -e "${CYAN}[숫자+V]${NC} 세션 상세 보기 (예: 1v)"
    echo -e "${GREEN}[N]${NC} 새 세션 생성"
    echo -e "${YELLOW}[K]${NC} 세션 종료"
    echo -e "${PURPLE}[L]${NC} 세션 목록 새로고침"
    echo -e "${BLUE}[W]${NC} 웹 인터페이스 열기 (http://localhost:3333)"
    echo -e "${RED}[Q]${NC} 종료"
    echo ""
}

# 세션 상세 보기
view_session_details() {
    local session_name=$1
    clear

    echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}   세션 상세 정보: $session_name       ${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
    echo ""

    # 세션 정보
    echo -e "${BOLD}📊 세션 정보:${NC}"
    tmux list-sessions -F "#{session_name}|#{session_windows}|#{session_created}|#{session_attached}|#{session_activity}" 2>/dev/null | \
    grep "^${session_name}|" | while IFS='|' read -r name windows created attached activity; do
        created_date=$(date -d "@$created" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "unknown")
        activity_date=$(date -d "@$activity" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "unknown")

        echo -e "  이름: ${BOLD}$name${NC}"
        echo -e "  윈도우 수: $windows개"
        echo -e "  생성 시간: $created_date"
        echo -e "  마지막 활동: $activity_date"

        if [ "$attached" = "1" ]; then
            echo -e "  상태: ${GREEN}🟢 연결됨${NC}"
        else
            echo -e "  상태: ${YELLOW}⚪ 분리됨${NC}"
        fi
    done

    echo ""
    echo -e "${BOLD}🪟 윈도우 목록:${NC}"
    tmux list-windows -t "$session_name" -F "#{window_index}|#{window_name}|#{window_active}|#{window_panes}|#{window_layout}" 2>/dev/null | \
    while IFS='|' read -r index wname active panes layout; do
        if [ "$active" = "1" ]; then
            marker="${GREEN}▶${NC}"
        else
            marker=" "
        fi
        echo -e "  $marker [$index] $wname (${panes}개 pane)"
    done

    echo ""
    echo -e "${BOLD}📸 현재 화면 캡처:${NC}"
    echo -e "${CYAN}─────────────────────────────────────${NC}"
    tmux capture-pane -t "$session_name" -p 2>/dev/null | tail -10 || echo "  (캡처 실패)"
    echo -e "${CYAN}─────────────────────────────────────${NC}"

    echo ""
    echo -e "${GREEN}[A]${NC} 이 세션에 연결"
    echo -e "${YELLOW}[K]${NC} 이 세션 종료"
    echo -e "${PURPLE}[B]${NC} 뒤로 가기"
    echo ""
    read -p "선택: " detail_choice

    case $detail_choice in
        [Aa])
            attach_session "$session_name"
            return 1  # exit main loop
            ;;
        [Kk])
            read -p "정말로 세션 '$session_name'을(를) 종료하시겠습니까? (y/N): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                tmux kill-session -t "$session_name"
                echo -e "${GREEN}✅ 세션이 종료되었습니다${NC}"
                sleep 1
            fi
            ;;
        *)
            # 뒤로 가기
            ;;
    esac

    return 0
}

# 세션 연결
attach_session() {
    local session_name=$1

    if [ -n "$TMUX" ]; then
        echo -e "${YELLOW}⚠️  이미 tmux 안에 있습니다${NC}"
        echo -e "${CYAN}💡 새 윈도우로 전환합니다...${NC}"
        tmux switch-client -t "$session_name"
    else
        echo -e "${GREEN}✅ 세션 '$session_name'에 연결합니다...${NC}"
        sleep 1
        tmux attach-session -t "$session_name"
    fi
}

# 새 세션 생성
create_session() {
    clear
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}       새 세션 생성                     ${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
    echo ""

    read -p "세션 이름: " session_name

    if [ -z "$session_name" ]; then
        echo -e "${RED}❌ 세션 이름을 입력해야 합니다${NC}"
        sleep 2
        return
    fi

    # 이미 존재하는지 확인
    if tmux has-session -t "$session_name" 2>/dev/null; then
        echo -e "${RED}❌ 세션 '$session_name'이(가) 이미 존재합니다${NC}"
        sleep 2
        return
    fi

    read -p "작업 디렉토리 [기본: $HOME]: " work_dir
    work_dir=${work_dir:-$HOME}

    if [ ! -d "$work_dir" ]; then
        echo -e "${RED}❌ 디렉토리 '$work_dir'이(가) 존재하지 않습니다${NC}"
        sleep 2
        return
    fi

    echo ""
    echo -e "${GREEN}✅ 세션 '$session_name' 생성 중...${NC}"

    if [ -n "$TMUX" ]; then
        tmux new-session -d -s "$session_name" -c "$work_dir"
        echo -e "${GREEN}✅ 세션이 생성되었습니다${NC}"
        sleep 1
    else
        tmux new-session -s "$session_name" -c "$work_dir"
    fi
}

# 세션 종료
kill_session() {
    clear
    echo -e "${BOLD}${RED}═══════════════════════════════════════${NC}"
    echo -e "${BOLD}${RED}       세션 종료                        ${NC}"
    echo -e "${BOLD}${RED}═══════════════════════════════════════${NC}"
    echo ""

    sessions=$(get_sessions)
    if [ -z "$sessions" ]; then
        echo -e "${YELLOW}❌ 실행 중인 세션이 없습니다${NC}"
        sleep 2
        return
    fi

    declare -a kill_array
    kill_array=()

    local index=1
    while IFS='|' read -r name windows created attached; do
        kill_array+=("$name")
        echo -e "${BOLD}${RED}[$index]${NC} $name"
        ((index++))
    done <<< "$sessions"

    echo ""
    echo -e "${RED}[A]${NC} 모든 세션 종료 (위험!)"
    echo -e "${GREEN}[C]${NC} 취소"
    echo ""
    read -p "선택: " choice

    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#kill_array[@]}" ]; then
        local session_name="${kill_array[$((choice-1))]}"
        echo ""
        read -p "정말로 세션 '$session_name'을(를) 종료하시겠습니까? (y/N): " confirm

        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            tmux kill-session -t "$session_name"
            echo -e "${GREEN}✅ 세션 '$session_name'이(가) 종료되었습니다${NC}"
        else
            echo -e "${YELLOW}취소되었습니다${NC}"
        fi
        sleep 1
    elif [ "$choice" = "A" ] || [ "$choice" = "a" ]; then
        echo ""
        echo -e "${RED}⚠️  경고: 모든 세션을 종료합니다!${NC}"
        read -p "정말로 모든 세션을 종료하시겠습니까? (yes 입력): " confirm

        if [ "$confirm" = "yes" ]; then
            tmux kill-server
            echo -e "${GREEN}✅ 모든 세션이 종료되었습니다${NC}"
            sleep 1
            exit 0
        else
            echo -e "${YELLOW}취소되었습니다${NC}"
            sleep 1
        fi
    fi
}

# 웹 인터페이스 열기
open_web_interface() {
    echo -e "${BLUE}🌐 웹 인터페이스를 여는 중...${NC}"

    # 서버가 실행 중인지 확인
    if ! curl -s http://localhost:3333/ > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  웹 서버가 실행 중이지 않습니다${NC}"
        echo -e "${GREEN}시작하시겠습니까? (y/N)${NC}"
        read -p ": " start_server

        if [ "$start_server" = "y" ] || [ "$start_server" = "Y" ]; then
            cd /home/jclee/app/tmux/web-tmux-interface
            ./start.sh
        fi
    else
        # 브라우저로 열기
        if command -v xdg-open > /dev/null; then
            xdg-open http://localhost:3333
        elif command -v open > /dev/null; then
            open http://localhost:3333
        else
            echo -e "${CYAN}브라우저에서 다음 주소를 여세요:${NC}"
            echo "http://localhost:3333"
        fi
    fi

    sleep 2
}

# 메인 루프
main() {
    while true; do
        show_menu

        read -p "선택: " choice

        sessions=$(get_sessions)
        declare -a menu_array
        menu_array=()

        while IFS='|' read -r name windows created attached; do
            menu_array+=("$name")
        done <<< "$sessions"

        # 숫자+v 패턴 체크 (예: 1v, 2v)
        if [[ $choice =~ ^([0-9]+)[vV]$ ]]; then
            num="${BASH_REMATCH[1]}"
            if [ "$num" -ge 1 ] && [ "$num" -le "${#menu_array[@]}" ]; then
                session_name="${menu_array[$((num-1))]}"
                view_session_details "$session_name"
                if [ $? -eq 1 ]; then
                    break
                fi
            else
                echo -e "${RED}❌ 잘못된 번호입니다${NC}"
                sleep 1
            fi
            continue
        fi

        case $choice in
            [0-9]*)
                if [ "$choice" -ge 1 ] && [ "$choice" -le "${#menu_array[@]}" ]; then
                    session_name="${menu_array[$((choice-1))]}"
                    attach_session "$session_name"
                    break
                else
                    echo -e "${RED}❌ 잘못된 번호입니다${NC}"
                    sleep 1
                fi
                ;;
            [Nn])
                create_session
                ;;
            [Kk])
                kill_session
                ;;
            [Ll])
                continue
                ;;
            [Ww])
                open_web_interface
                ;;
            [Qq])
                clear
                echo -e "${CYAN}👋 안녕히 가세요!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ 잘못된 입력입니다${NC}"
                sleep 1
                ;;
        esac
    done
}

# 스크립트 시작
main
