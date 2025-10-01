#!/bin/bash
# Final Deduplication Solution for TS Environment

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

CONFIG_DIR="$HOME/.config/ts"
SOCKET_DIR="/home/jclee/.tmux/sockets"
LOG_FILE="$CONFIG_DIR/dedup.log"

mkdir -p "$CONFIG_DIR"

# Simple and effective PATH deduplication
dedupe_path() {
    local var_name="$1"
    local current_value="${!var_name:-}"

    [[ -z "$current_value" ]] && return

    # Remove duplicates while preserving order
    local deduped=$(echo "$current_value" | tr ':' '\n' | awk '!seen[$0]++' | paste -sd: -)

    # Count removed duplicates
    local original_count=$(echo "$current_value" | tr ':' '\n' | wc -l)
    local deduped_count=$(echo "$deduped" | tr ':' '\n' | wc -l)
    local removed=$((original_count - deduped_count))

    if [[ $removed -gt 0 ]]; then
        export "$var_name=$deduped"
        echo -e "${GREEN}✓ $var_name: Removed $removed duplicates${NC}"
        echo "[$(date)] $var_name: Removed $removed duplicates" >> "$LOG_FILE"
    else
        echo -e "${BLUE}  $var_name: No duplicates found${NC}"
    fi
}

# Config file deduplication
dedupe_config() {
    local file="$1"

    [[ ! -f "$file" ]] && return

    local basename=$(basename "$file")
    cp "$file" "$file.bak.$(date +%s)"

    # Remove duplicate lines, keep last occurrence
    tac "$file" | awk '!seen[$0]++' | tac > "$file.tmp"

    local original_lines=$(wc -l < "$file")
    local new_lines=$(wc -l < "$file.tmp")
    local removed=$((original_lines - new_lines))

    if [[ $removed -gt 0 ]]; then
        mv "$file.tmp" "$file"
        echo -e "${GREEN}✓ $basename: Removed $removed duplicate lines${NC}"
        echo "[$(date)] $basename: Removed $removed duplicate lines" >> "$LOG_FILE"
    else
        rm -f "$file.tmp"
        echo -e "${BLUE}  $basename: No duplicates found${NC}"
    fi
}

# Clean dead sockets
clean_sockets() {
    local cleaned=0

    for socket in "$SOCKET_DIR"/*; do
        [[ ! -S "$socket" ]] && continue

        local name=$(basename "$socket")

        # Skip special files
        [[ "$name" == ".lock" ]] && continue
        [[ "$name" =~ ^-- ]] && { rm -f "$socket"; ((cleaned++)); continue; }

        # Remove dead sockets
        if ! tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
            rm -f "$socket"
            ((cleaned++))
        fi
    done

    if [[ $cleaned -gt 0 ]]; then
        echo -e "${GREEN}✓ Cleaned $cleaned dead socket(s)${NC}"
        echo "[$(date)] Cleaned $cleaned dead socket(s)" >> "$LOG_FILE"
    else
        echo -e "${BLUE}  All sockets healthy${NC}"
    fi
}

# Main execution
main() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           Environment Deduplication Tool${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo ""

    # 1. Environment variables
    echo -e "${CYAN}1. Cleaning environment variables...${NC}"
    dedupe_path "PATH"
    dedupe_path "LD_LIBRARY_PATH"
    dedupe_path "PYTHONPATH"
    dedupe_path "MANPATH"

    # 2. Config files
    echo -e "\n${CYAN}2. Cleaning configuration files...${NC}"
    for conf in "$CONFIG_DIR"/*.conf; do
        [[ -f "$conf" ]] && dedupe_config "$conf"
    done

    # 3. Sockets
    echo -e "\n${CYAN}3. Cleaning tmux sockets...${NC}"
    clean_sockets

    # 4. Install permanent fix
    echo -e "\n${CYAN}4. Installing permanent fix...${NC}"

    local hook_file="$CONFIG_DIR/auto_dedup.sh"
    cat > "$hook_file" << 'EOF'
# Auto-deduplication on shell startup
dedupe_path_auto() {
    local var="$1"
    local val="${!var:-}"
    [[ -n "$val" ]] && export "$var=$(echo "$val" | tr ':' '\n' | awk '!s[$0]++' | paste -sd: -)"
}
dedupe_path_auto PATH
dedupe_path_auto LD_LIBRARY_PATH
dedupe_path_auto PYTHONPATH
EOF

    # Add to bashrc if not present
    if ! grep -q "auto_dedup.sh" ~/.bashrc 2>/dev/null; then
        echo "[ -f '$hook_file' ] && source '$hook_file'" >> ~/.bashrc
        echo -e "${GREEN}✓ Added auto-deduplication to ~/.bashrc${NC}"
    else
        echo -e "${BLUE}  Auto-deduplication already installed${NC}"
    fi

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Deduplication complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Apply changes:${NC} source ~/.bashrc"
}

# Run main
main "$@"