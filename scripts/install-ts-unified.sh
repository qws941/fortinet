#!/bin/bash
# TS Unified Installation Script
# Installs ts v3.0.0 unified system with backup of old version

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}     TS Unified Installation v3.0.0${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}✗ Do not run this script as root${NC}" >&2
   echo -e "${YELLOW}Run without sudo - the script will ask for permission when needed${NC}" >&2
   exit 1
fi

# Backup old ts command
if [[ -f /usr/local/bin/ts ]]; then
    echo -e "${YELLOW}📦 Backing up old ts command...${NC}"
    sudo cp /usr/local/bin/ts /usr/local/bin/ts.backup-$(date +%Y%m%d-%H%M%S)
    echo -e "${GREEN}✓ Old ts backed up${NC}"
fi

# Install ts-unified
echo -e "${BLUE}🚀 Installing ts-unified...${NC}"
sudo cp /home/jclee/app/tmux/ts-unified.sh /usr/local/bin/ts
sudo chmod +x /usr/local/bin/ts
echo -e "${GREEN}✓ Installed: /usr/local/bin/ts${NC}"

# Install ts-bg
echo -e "${BLUE}🚀 Installing ts-bg...${NC}"
sudo cp /home/jclee/app/tmux/ts-bg-manager.sh /usr/local/bin/ts-bg
sudo chmod +x /usr/local/bin/ts-bg
echo -e "${GREEN}✓ Installed: /usr/local/bin/ts-bg${NC}"

# Run migration if needed
if [[ ! -f /home/jclee/.config/ts/projects.json ]]; then
    echo ""
    echo -e "${YELLOW}⚠ No unified config found. Running migration...${NC}"
    /home/jclee/app/tmux/migrate-ts-config.sh
fi

# Verify installation
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}           Verification${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

ts version 2>&1 | head -10

echo ""
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo ""
echo -e "${BOLD}Quick Start:${NC}"
echo -e "  ${CYAN}ts list${NC}              - List all sessions"
echo -e "  ${CYAN}ts <name>${NC}            - Create/attach to session"
echo -e "  ${CYAN}ts-bg label <s> <l>${NC}  - Label a session"
echo -e "  ${CYAN}ts-bg search <l>${NC}     - Search by label"
echo -e "  ${CYAN}ts-bg start <s> <w> <c>${NC} - Start background task"
echo ""
echo -e "${YELLOW}Note: Restart your shell or run 'hash -r' to refresh PATH${NC}"
