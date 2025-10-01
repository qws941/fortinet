#!/bin/bash
# Install TS CRUD command system

set -euo pipefail

readonly INSTALL_DIR="/home/jclee/.claude/bin"
readonly SOURCE_FILE="/home/jclee/app/tmux/ts-crud.sh"
readonly TARGET_FILE="$INSTALL_DIR/ts-crud"

# Colors
readonly GREEN='\033[0;32m'
readonly CYAN='\033[0;36m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

echo -e "${CYAN}Installing TS CRUD command system...${NC}\n"

# Create install directory
mkdir -p "$INSTALL_DIR"

# Copy and make executable
cp "$SOURCE_FILE" "$TARGET_FILE"
chmod +x "$TARGET_FILE"

echo -e "${GREEN}✓ Installed ts-crud to: $TARGET_FILE${NC}"

# Check if already in PATH
if [[ ":$PATH:" == *":$INSTALL_DIR:"* ]]; then
    echo -e "${GREEN}✓ $INSTALL_DIR is already in PATH${NC}"
else
    echo -e "${YELLOW}⚠️  $INSTALL_DIR is not in PATH${NC}"
    echo -e "${CYAN}Add this to your ~/.bashrc or ~/.zshrc:${NC}"
    echo -e "  export PATH=\"$INSTALL_DIR:\$PATH\""
fi

# Initialize database
echo -e "\n${CYAN}Initializing database...${NC}"
"$TARGET_FILE" sync

echo -e "\n${GREEN}✅ Installation complete!${NC}"
echo -e "\n${CYAN}Usage:${NC}"
echo -e "  ts-crud create <name> [path]  - Create new session"
echo -e "  ts-crud list                  - List all sessions"
echo -e "  ts-crud read <name>           - Show session info"
echo -e "  ts-crud update <name> ...     - Update session"
echo -e "  ts-crud delete <name>         - Delete session"
echo -e "  ts-crud help                  - Show full help"
echo -e "\n${CYAN}Try it:${NC}"
echo -e "  ts-crud help"
