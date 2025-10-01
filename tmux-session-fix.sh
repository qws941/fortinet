#!/bin/bash
# Tmux Session Nesting Fix and Enhancement Script

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║            Tmux Session Nesting Fix & Enhancement        ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${BLUE}🔍 Current Status:${NC}"

# 현재 tmux 중첩 상태 확인
if [[ -n "$TMUX" ]]; then
    echo -e "  ${RED}⚠️  TMUX NESTING DETECTED${NC}"
    echo -e "  Current session: ${YELLOW}$(tmux display-message -p '#S')${NC}"
    echo -e "  Socket: ${YELLOW}$TMUX${NC}"
else
    echo -e "  ${GREEN}✓ No tmux nesting detected${NC}"
fi

# 활성 소켓 수 확인
socket_count=$(ls /home/jclee/.tmux/sockets/ 2>/dev/null | wc -l)
echo -e "  Active sockets: ${CYAN}$socket_count${NC}"

# 설정 파일 상태
config_status=$(wc -l < /home/jclee/.tmux.conf)
echo -e "  Tmux config lines: ${CYAN}$config_status${NC}"

echo -e "\n${BLUE}🛠️  Applied Fixes:${NC}"
echo -e "  ${GREEN}✓${NC} Enhanced tmux configuration with nesting detection"
echo -e "  ${GREEN}✓${NC} Session management improvements"
echo -e "  ${GREEN}✓${NC} Performance optimizations"
echo -e "  ${GREEN}✓${NC} Enhanced ts command (ts-v2) with nesting prevention"
echo -e "  ${GREEN}✓${NC} Advanced session health monitoring"

echo -e "\n${BLUE}🚀 Available Commands:${NC}"
echo -e "  ${CYAN}ts-v2${NC}                     - Enhanced ts with nesting prevention"
echo -e "  ${CYAN}ts-v2 nesting-check${NC}       - Check for session nesting"
echo -e "  ${CYAN}ts-v2 dashboard${NC}           - Advanced session dashboard"
echo -e "  ${CYAN}ts-v2 clean${NC}               - Clean dead sessions"
echo -e "  ${CYAN}tmux source ~/.tmux.conf${NC}  - Reload tmux configuration"

echo -e "\n${BLUE}🔧 Quick Actions:${NC}"

# 옵션 메뉴
while true; do
    echo -e "\nChoose an action:"
    echo -e "  ${YELLOW}1${NC}) Test nesting detection"
    echo -e "  ${YELLOW}2${NC}) Show enhanced dashboard"
    echo -e "  ${YELLOW}3${NC}) Clean dead sessions"
    echo -e "  ${YELLOW}4${NC}) Reload tmux configuration"
    echo -e "  ${YELLOW}5${NC}) Exit current tmux session (if nested)"
    echo -e "  ${YELLOW}q${NC}) Quit"

    read -p "Enter choice [1-5, q]: " choice

    case $choice in
        1)
            echo -e "\n${BLUE}🔍 Running nesting detection...${NC}"
            ts-v2 nesting-check
            ;;
        2)
            echo -e "\n${BLUE}📊 Showing enhanced dashboard...${NC}"
            ts-v2 dashboard
            break
            ;;
        3)
            echo -e "\n${BLUE}🧹 Cleaning dead sessions...${NC}"
            ts-v2 clean
            ;;
        4)
            echo -e "\n${BLUE}🔄 Reloading tmux configuration...${NC}"
            if [[ -n "$TMUX" ]]; then
                tmux source-file ~/.tmux.conf
                echo -e "${GREEN}✓ Configuration reloaded${NC}"
            else
                echo -e "${YELLOW}⚠️  Not in tmux session${NC}"
            fi
            ;;
        5)
            if [[ -n "$TMUX" ]]; then
                echo -e "\n${YELLOW}Exiting current tmux session...${NC}"
                echo -e "${BLUE}You can reconnect later with: ts-v2 tmux${NC}"
                exit
            else
                echo -e "\n${YELLOW}⚠️  Not in tmux session${NC}"
            fi
            ;;
        q|Q)
            echo -e "\n${GREEN}✅ Session fix completed!${NC}"
            echo -e "${BLUE}💡 Remember to use 'ts-v2' for enhanced session management${NC}"
            break
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            ;;
    esac
done

echo -e "\n${CYAN}📝 Summary of Improvements:${NC}"
echo -e "  • Enhanced nesting detection and prevention"
echo -e "  • Improved session health monitoring"
echo -e "  • Advanced dashboard with status visualization"
echo -e "  • Automated cleanup of dead sessions"
echo -e "  • Better performance with optimized settings"
echo -e "  • Color-coded status indicators"

echo -e "\n${BLUE}🎯 Next Steps:${NC}"
echo -e "  1. Use ${CYAN}ts-v2${NC} instead of ${CYAN}ts${NC} for enhanced features"
echo -e "  2. Run ${CYAN}ts-v2 nesting-check${NC} before creating new sessions"
echo -e "  3. Use ${CYAN}ts-v2 dashboard${NC} to monitor all sessions"
echo -e "  4. Original ts command backed up as ${CYAN}ts-original${NC}"

echo -e "\n${GREEN}✨ Tmux session management has been enhanced!${NC}"