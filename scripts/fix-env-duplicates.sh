#!/bin/bash
# Environment Variable Deduplication Fix for ts command system

set -euo pipefail

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔧 Environment Variable Deduplication Tool${NC}"
echo -e "${CYAN}═══════════════════════════════════════════${NC}"

# Configuration paths
CONFIG_DIR="$HOME/.config/ts"
PROJECTS_CONF="$CONFIG_DIR/projects.conf"
REGISTRY_CONF="$CONFIG_DIR/registry.conf"
AUTO_SESSIONS_CONF="$CONFIG_DIR/auto-sessions.conf"
TS_ENHANCED_CONF="$CONFIG_DIR/ts-enhanced.conf"

# Function to deduplicate PATH-like variables
dedupe_path_var() {
    local var_name="$1"
    local current_value="${!var_name:-}"

    if [[ -z "$current_value" ]]; then
        return
    fi

    # Split by colon and remove duplicates while preserving order
    local deduped=$(echo "$current_value" | tr ':' '\n' | awk '!seen[$0]++' | tr '\n' ':' | sed 's/:$//')

    # Export the deduplicated value
    export "$var_name=$deduped"

    local original_count=$(echo "$current_value" | tr ':' '\n' | wc -l)
    local deduped_count=$(echo "$deduped" | tr ':' '\n' | wc -l)
    local removed=$((original_count - deduped_count))

    if [[ $removed -gt 0 ]]; then
        echo -e "${GREEN}✓ $var_name: Removed $removed duplicate entries${NC}"
    else
        echo -e "${BLUE}  $var_name: No duplicates found${NC}"
    fi
}

# Function to deduplicate configuration files
dedupe_config_file() {
    local file="$1"
    local description="$2"

    if [[ ! -f "$file" ]]; then
        echo -e "${YELLOW}  $description: File not found, skipping${NC}"
        return
    fi

    # Backup the file
    cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"

    # Count duplicates
    local total_lines=$(wc -l < "$file")
    local unique_lines=$(sort -u "$file" | wc -l)
    local duplicates=$((total_lines - unique_lines))

    if [[ $duplicates -gt 0 ]]; then
        # Remove duplicates (keep last occurrence)
        tac "$file" | awk '!seen[$0]++' | tac > "$file.tmp"
        mv "$file.tmp" "$file"
        echo -e "${GREEN}✓ $description: Removed $duplicates duplicate lines${NC}"
    else
        echo -e "${BLUE}  $description: No duplicates found${NC}"
    fi
}

# Function to clean dead tmux sockets
clean_dead_sockets() {
    local socket_dir="/home/jclee/.tmux/sockets"
    local cleaned=0

    if [[ -d "$socket_dir" ]]; then
        for socket in "$socket_dir"/*; do
            if [[ -S "$socket" ]]; then
                local session_name=$(basename "$socket")
                if ! tmux -S "$socket" has-session -t "$session_name" 2>/dev/null; then
                    rm -f "$socket"
                    ((cleaned++))
                fi
            fi
        done
    fi

    if [[ $cleaned -gt 0 ]]; then
        echo -e "${GREEN}✓ Cleaned $cleaned dead socket(s)${NC}"
    else
        echo -e "${BLUE}  No dead sockets found${NC}"
    fi
}

# Function to validate and fix ts command installation
fix_ts_command() {
    local ts_path="/usr/local/bin/ts"

    if [[ -f "$ts_path" ]]; then
        # Check for duplicate function definitions
        local duplicate_funcs=$(grep -E "^[a-z_]+\(\)" "$ts_path" | sort | uniq -d)

        if [[ -n "$duplicate_funcs" ]]; then
            echo -e "${YELLOW}⚠ Found duplicate function definitions in ts command:${NC}"
            echo "$duplicate_funcs"
            echo -e "${CYAN}  Consider reviewing $ts_path for duplicate code blocks${NC}"
        else
            echo -e "${BLUE}  ts command: No duplicate functions found${NC}"
        fi
    else
        echo -e "${RED}✗ ts command not found at $ts_path${NC}"
    fi
}

# Main execution
echo ""
echo -e "${CYAN}1. Cleaning environment variables...${NC}"
dedupe_path_var "PATH"
dedupe_path_var "LD_LIBRARY_PATH"
dedupe_path_var "PYTHONPATH"
dedupe_path_var "MANPATH"

echo ""
echo -e "${CYAN}2. Cleaning configuration files...${NC}"
mkdir -p "$CONFIG_DIR"
dedupe_config_file "$PROJECTS_CONF" "projects.conf"
dedupe_config_file "$REGISTRY_CONF" "registry.conf"
dedupe_config_file "$AUTO_SESSIONS_CONF" "auto-sessions.conf"
dedupe_config_file "$TS_ENHANCED_CONF" "ts-enhanced.conf"

echo ""
echo -e "${CYAN}3. Cleaning tmux sockets...${NC}"
clean_dead_sockets

echo ""
echo -e "${CYAN}4. Validating ts command...${NC}"
fix_ts_command

# Create shell function to prevent PATH duplication in new sessions
echo ""
echo -e "${CYAN}5. Installing deduplication hook...${NC}"

DEDUPE_SCRIPT="$CONFIG_DIR/dedupe_env.sh"
cat > "$DEDUPE_SCRIPT" << 'EOF'
# Automatic environment deduplication
dedupe_path() {
    local var_name="$1"
    local current_value="${!var_name:-}"
    [[ -z "$current_value" ]] && return
    local deduped=$(echo "$current_value" | tr ':' '\n' | awk '!seen[$0]++' | tr '\n' ':' | sed 's/:$//')
    export "$var_name=$deduped"
}

# Auto-dedupe common PATH variables
dedupe_path PATH
dedupe_path LD_LIBRARY_PATH
dedupe_path PYTHONPATH
dedupe_path MANPATH
EOF

chmod +x "$DEDUPE_SCRIPT"

# Add to bashrc if not already present
if ! grep -q "dedupe_env.sh" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "# Auto-deduplicate environment variables" >> ~/.bashrc
    echo "[[ -f \"$DEDUPE_SCRIPT\" ]] && source \"$DEDUPE_SCRIPT\"" >> ~/.bashrc
    echo -e "${GREEN}✓ Added deduplication hook to ~/.bashrc${NC}"
else
    echo -e "${BLUE}  Deduplication hook already installed${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Environment deduplication complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}To apply changes to current shell:${NC}"
echo -e "  ${YELLOW}source ~/.bashrc${NC}"
echo ""
echo -e "${CYAN}The deduplication will automatically run in:${NC}"
echo -e "  • New terminal sessions"
echo -e "  • New tmux sessions"
echo -e "  • ts command sessions"