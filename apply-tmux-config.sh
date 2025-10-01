#!/bin/bash
# Apply optimized tmux configuration

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}    Applying Optimized Tmux Configuration${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Backup existing config
if [[ -f ~/.claude/config/tmux.conf ]]; then
    echo -e "${YELLOW}📦 Backing up existing config...${NC}"
    cp ~/.claude/config/tmux.conf ~/.claude/config/tmux.conf.backup-$(date +%Y%m%d-%H%M%S)
    echo -e "${GREEN}✓ Backup created${NC}"
fi

# Copy optimized config
echo -e "${CYAN}🔧 Installing optimized config...${NC}"
cp /home/jclee/app/tmux/tmux-optimized.conf ~/.claude/config/tmux.conf
echo -e "${GREEN}✓ Config installed${NC}"

# Install TPM if not exists
if [[ ! -d ~/.tmux/plugins/tpm ]]; then
    echo -e "${CYAN}📦 Installing Tmux Plugin Manager (TPM)...${NC}"
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm 2>/dev/null || {
        echo -e "${YELLOW}⚠ TPM already exists or git failed${NC}"
    }
    echo -e "${GREEN}✓ TPM installed${NC}"
fi

# Reload tmux config for all sessions
echo -e "${CYAN}🔄 Reloading tmux configuration...${NC}"

for socket in /home/jclee/.tmux/sockets/*; do
    if [[ -S "$socket" ]]; then
        session=$(basename "$socket")
        tmux -S "$socket" source-file ~/.tmux.conf 2>/dev/null && {
            echo -e "${GREEN}✓ Reloaded: $session${NC}"
        } || {
            echo -e "${YELLOW}⚠ Skipped: $session (not active)${NC}"
        }
    fi
done

echo ""
echo -e "${GREEN}✅ Configuration applied!${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}    Performance Improvements${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}✓${NC} Escape time: 10ms (faster command sequences)"
echo -e "  ${GREEN}✓${NC} Status refresh: 5s (reduced lag)"
echo -e "  ${GREEN}✓${NC} History: 100,000 lines"
echo -e "  ${GREEN}✓${NC} Mouse support: enabled"
echo -e "  ${GREEN}✓${NC} Vim-style navigation"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}    New Key Bindings${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}Prefix:${NC} Ctrl-a (instead of Ctrl-b)"
echo -e "  ${YELLOW}Split horizontal:${NC} Ctrl-a |"
echo -e "  ${YELLOW}Split vertical:${NC} Ctrl-a -"
echo -e "  ${YELLOW}Navigate panes:${NC} Alt + Arrow keys"
echo -e "  ${YELLOW}Reload config:${NC} Ctrl-a r"
echo -e "  ${YELLOW}New session:${NC} Ctrl-a N"
echo -e "  ${YELLOW}Kill session:${NC} Ctrl-a K"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}    Next Steps${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "1. Install plugins:"
echo -e "   ${CYAN}Ctrl-a I${NC} (capital I)"
echo ""
echo -e "2. Test session labels:"
echo -e "   ${CYAN}ts-bg label \$(tmux display-message -p '#S') 'test,label'${NC}"
echo ""
echo -e "3. Reload config in running sessions:"
echo -e "   ${CYAN}Ctrl-a r${NC}"
echo ""
