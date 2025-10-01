#!/bin/bash
# Install TS Auto-Discover Daemon as systemd service

set -euo pipefail

readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly YELLOW='\033[1;33m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

echo -e "${CYAN}${BOLD}Installing TS Auto-Discover Daemon${NC}\n"

# 1. Make daemon executable
echo -e "${BOLD}1. Making daemon executable...${NC}"
chmod +x /home/jclee/app/tmux/ts-auto-discover-daemon.sh
chmod +x /home/jclee/app/tmux/ts-discover.sh
echo -e "${GREEN}✓ Done${NC}\n"

# 2. Create log directory
echo -e "${BOLD}2. Creating log directory...${NC}"
mkdir -p /home/jclee/.config/ts
touch /home/jclee/.config/ts/auto-discover.log
echo -e "${GREEN}✓ Done${NC}\n"

# 3. Install systemd service
echo -e "${BOLD}3. Installing systemd service...${NC}"
sudo cp /home/jclee/app/tmux/systemd/ts-auto-discover.service /etc/systemd/system/
sudo systemctl daemon-reload
echo -e "${GREEN}✓ Service installed${NC}\n"

# 4. Enable and start service
echo -e "${BOLD}4. Enabling and starting service...${NC}"
sudo systemctl enable ts-auto-discover.service
sudo systemctl start ts-auto-discover.service
echo -e "${GREEN}✓ Service started${NC}\n"

# 5. Check status
echo -e "${BOLD}5. Service status:${NC}"
sudo systemctl status ts-auto-discover.service --no-pager

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}✓ Installation Complete!${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}\n"

echo -e "${BOLD}Useful commands:${NC}"
echo -e "  ${CYAN}sudo systemctl status ts-auto-discover${NC}   - Check status"
echo -e "  ${CYAN}sudo systemctl stop ts-auto-discover${NC}     - Stop daemon"
echo -e "  ${CYAN}sudo systemctl restart ts-auto-discover${NC}  - Restart daemon"
echo -e "  ${CYAN}tail -f ~/.config/ts/auto-discover.log${NC}   - View logs"
echo -e "  ${CYAN}journalctl -u ts-auto-discover -f${NC}        - View systemd logs"
echo ""
echo -e "${YELLOW}The daemon will run every 5 minutes automatically.${NC}"
echo -e "${YELLOW}It will discover and register new projects without any manual intervention.${NC}"
