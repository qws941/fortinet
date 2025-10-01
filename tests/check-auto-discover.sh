#!/bin/bash
# Check TS Auto-Discover Daemon Status

set -euo pipefail

readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly CYAN='\033[0;36m'
readonly YELLOW='\033[1;33m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}${BOLD}   TS Auto-Discover Daemon Status Check${NC}"
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}\n"

# 1. Check if service file exists
echo -e "${BOLD}1. Service File:${NC}"
if [[ -f "/etc/systemd/system/ts-auto-discover.service" ]]; then
    echo -e "   ${GREEN}✓${NC} Service file installed"
else
    echo -e "   ${RED}✗${NC} Service file not found"
    echo -e "   ${YELLOW}Run: ./install-auto-discover.sh${NC}"
fi
echo ""

# 2. Check if daemon script is executable
echo -e "${BOLD}2. Daemon Script:${NC}"
if [[ -x "/home/jclee/app/tmux/ts-auto-discover-daemon.sh" ]]; then
    echo -e "   ${GREEN}✓${NC} Daemon script executable"
else
    echo -e "   ${RED}✗${NC} Daemon script not executable"
    echo -e "   ${YELLOW}Run: chmod +x /home/jclee/app/tmux/ts-auto-discover-daemon.sh${NC}"
fi
echo ""

# 3. Check service status
echo -e "${BOLD}3. Service Status:${NC}"
if systemctl is-active --quiet ts-auto-discover; then
    echo -e "   ${GREEN}✓${NC} Service is running"

    # Show uptime
    uptime=$(systemctl show ts-auto-discover --property=ActiveEnterTimestamp --value)
    echo -e "   ${CYAN}Started at: $uptime${NC}"
else
    echo -e "   ${RED}✗${NC} Service is not running"
    echo -e "   ${YELLOW}Run: sudo systemctl start ts-auto-discover${NC}"
fi
echo ""

# 4. Check if enabled
echo -e "${BOLD}4. Auto-Start on Boot:${NC}"
if systemctl is-enabled --quiet ts-auto-discover; then
    echo -e "   ${GREEN}✓${NC} Enabled (will start on boot)"
else
    echo -e "   ${YELLOW}⚠${NC}  Disabled"
    echo -e "   ${YELLOW}Run: sudo systemctl enable ts-auto-discover${NC}"
fi
echo ""

# 5. Check log file
echo -e "${BOLD}5. Log File:${NC}"
if [[ -f "/home/jclee/.config/ts/auto-discover.log" ]]; then
    log_size=$(du -h /home/jclee/.config/ts/auto-discover.log | awk '{print $1}')
    log_lines=$(wc -l < /home/jclee/.config/ts/auto-discover.log)
    echo -e "   ${GREEN}✓${NC} Log file exists"
    echo -e "   ${CYAN}Size: $log_size, Lines: $log_lines${NC}"

    # Show last 3 lines
    echo -e "\n   ${BOLD}Last 3 log entries:${NC}"
    tail -3 /home/jclee/.config/ts/auto-discover.log | while read -r line; do
        echo -e "   ${CYAN}$line${NC}"
    done
else
    echo -e "   ${YELLOW}⚠${NC}  Log file not found (will be created on first run)"
fi
echo ""

# 6. Check lock file
echo -e "${BOLD}6. Lock File:${NC}"
if [[ -f "/home/jclee/.config/ts/auto-discover.lock" ]]; then
    lock_pid=$(cat /home/jclee/.config/ts/auto-discover.lock)
    echo -e "   ${YELLOW}⚠${NC}  Lock file exists (PID: $lock_pid)"

    if ps -p "$lock_pid" > /dev/null 2>&1; then
        echo -e "   ${CYAN}Discovery is currently running${NC}"
    else
        echo -e "   ${RED}✗${NC} Stale lock file (process not running)"
        echo -e "   ${YELLOW}Run: rm /home/jclee/.config/ts/auto-discover.lock${NC}"
    fi
else
    echo -e "   ${GREEN}✓${NC} No lock file (not currently scanning)"
fi
echo ""

# 7. Recent systemd logs
echo -e "${BOLD}7. Recent Systemd Logs:${NC}"
if journalctl -u ts-auto-discover -n 5 --no-pager > /dev/null 2>&1; then
    journalctl -u ts-auto-discover -n 5 --no-pager | tail -5 | while read -r line; do
        echo -e "   ${CYAN}$line${NC}"
    done
else
    echo -e "   ${YELLOW}⚠${NC}  No systemd logs available"
fi
echo ""

# Summary
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${BOLD}Summary:${NC}\n"

all_good=true

if [[ ! -f "/etc/systemd/system/ts-auto-discover.service" ]]; then
    all_good=false
fi

if ! systemctl is-active --quiet ts-auto-discover; then
    all_good=false
fi

if [[ "$all_good" == true ]]; then
    echo -e "${GREEN}${BOLD}✓ Everything is working correctly!${NC}"
    echo -e "${CYAN}Auto-discovery is running and will check for new projects every 5 minutes.${NC}"
else
    echo -e "${YELLOW}${BOLD}⚠ Some issues detected${NC}"
    echo -e "${CYAN}Follow the suggestions above to fix them.${NC}"
fi

echo ""
echo -e "${BOLD}Quick Commands:${NC}"
echo -e "  ${CYAN}sudo systemctl status ts-auto-discover${NC}      - Full status"
echo -e "  ${CYAN}tail -f ~/.config/ts/auto-discover.log${NC}      - Watch logs"
echo -e "  ${CYAN}journalctl -u ts-auto-discover -f${NC}           - Watch systemd logs"
echo -e "  ${CYAN}sudo systemctl restart ts-auto-discover${NC}     - Restart daemon"
