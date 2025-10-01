#!/bin/bash
# Install TS Integrated (CRUD + Session + Background + IPC)

set -euo pipefail

readonly INSTALL_DIR="/home/jclee/.claude/bin"
readonly SOURCE_FILE="/home/jclee/app/tmux/ts.sh"
readonly TARGET_FILE="$INSTALL_DIR/ts"

# Colors
readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

echo -e "${CYAN}Installing TS Master v5.0.0 (Integrated)...${NC}\n"

# Backup existing ts if exists
if [[ -f "$TARGET_FILE" ]]; then
    echo -e "${YELLOW}Backing up existing ts command...${NC}"
    cp "$TARGET_FILE" "$TARGET_FILE.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy and make executable
cp "$SOURCE_FILE" "$TARGET_FILE"
chmod +x "$TARGET_FILE"

echo -e "${GREEN}✓ Installed ts to: $TARGET_FILE${NC}"

# Check if already in PATH
if [[ ":$PATH:" == *":$INSTALL_DIR:"* ]]; then
    echo -e "${GREEN}✓ $INSTALL_DIR is already in PATH${NC}"
else
    echo -e "${YELLOW}⚠️  $INSTALL_DIR is not in PATH${NC}"
    echo -e "${CYAN}Add this to your ~/.bashrc or ~/.zshrc:${NC}"
    echo -e "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi

# Initialize system
echo -e "\n${CYAN}Initializing system...${NC}"
"$TARGET_FILE" sync 2>/dev/null || true

echo -e "\n${GREEN}✅ Installation complete!${NC}"
echo -e "\n${CYAN}TS Master v5.0.0 Features:${NC}"
echo -e "  ✓ Full CRUD operations"
echo -e "  ✓ JSON database with metadata"
echo -e "  ✓ Session management"
echo -e "  ✓ Background tasks"
echo -e "  ✓ Inter-process communication (IPC)"
echo -e "  ✓ Grafana telemetry"
echo -e "  ✓ Socket-based isolation"

echo -e "\n${CYAN}Quick Start:${NC}"
echo -e "  ts list                              - List all sessions"
echo -e "  ts create myproject /path \"desc\" \"tags\" - Create with metadata"
echo -e "  ts myproject                         - Quick attach/create"
echo -e "  ts read myproject                    - Show session info"
echo -e "  ts update myproject --tags \"prod\"    - Update metadata"
echo -e "  ts search \"dev\" tags                 - Search sessions"
echo -e "  ts help                              - Full help"

echo -e "\n${CYAN}Try it:${NC}"
echo -e "  ts help"
