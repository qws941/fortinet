#!/bin/bash
# TS Configuration Migration Tool
# Migrates from old ts/cc configs to unified ts v3.0.0

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Paths
OLD_TS_CONFIG="/home/jclee/.config/ts"
OLD_CC_CONFIG="/home/jclee/.config/cc"
NEW_CONFIG_DIR="/home/jclee/.config/ts"
BACKUP_DIR="$NEW_CONFIG_DIR/backups/migration-$(date +%Y%m%d-%H%M%S)"

echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       TS Configuration Migration Tool v3.0${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo -e "${BLUE}📦 Backup directory: $BACKUP_DIR${NC}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKUP EXISTING CONFIGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

backup_configs() {
    echo -e "${YELLOW}🔄 Backing up existing configurations...${NC}"

    # Backup ts configs
    if [[ -d "$OLD_TS_CONFIG" ]]; then
        cp -r "$OLD_TS_CONFIG" "$BACKUP_DIR/ts-old" 2>/dev/null || true
        echo -e "${GREEN}✓ Backed up ts configs${NC}"
    fi

    # Backup cc configs
    if [[ -d "$OLD_CC_CONFIG" ]]; then
        cp -r "$OLD_CC_CONFIG" "$BACKUP_DIR/cc-old" 2>/dev/null || true
        echo -e "${GREEN}✓ Backed up cc configs${NC}"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MIGRATE PROJECTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

migrate_projects() {
    echo ""
    echo -e "${YELLOW}🔄 Migrating project configurations...${NC}"

    local projects_json="{"
    local first=true

    # Migrate from ts-enhanced.conf
    if [[ -f "$OLD_TS_CONFIG/ts-enhanced.conf" ]]; then
        while IFS='=' read -r key value; do
            [[ "$key" =~ ^PROJECT_PATH_(.+)$ ]] || continue

            local name="${BASH_REMATCH[1]}"
            local path=$(eval echo "$value" | tr -d '"')

            [[ "$first" == true ]] || projects_json+=","
            first=false

            projects_json+="\"$name\":\"$path\""
        done < <(grep "^PROJECT_PATH_" "$OLD_TS_CONFIG/ts-enhanced.conf" 2>/dev/null || true)
    fi

    # Merge from cc projects.conf
    if [[ -f "$OLD_CC_CONFIG/projects.conf" ]]; then
        while IFS='=' read -r name path; do
            # Skip comments and empty lines
            [[ "$name" =~ ^[[:space:]]*# ]] || [[ -z "$name" ]] && continue

            path=$(echo "$path" | tr -d '"' | xargs)

            [[ "$first" == true ]] || projects_json+=","
            first=false

            projects_json+="\"$name\":\"$path\""
        done < "$OLD_CC_CONFIG/projects.conf"
    fi

    projects_json+="}"

    # Remove duplicates and write
    echo "$projects_json" | jq -S '.' > "$NEW_CONFIG_DIR/projects.json"
    echo -e "${GREEN}✓ Migrated projects to JSON format${NC}"
    echo -e "${BLUE}  Found $(echo "$projects_json" | jq 'keys | length') projects${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MIGRATE AUTO COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

migrate_auto_commands() {
    echo ""
    echo -e "${YELLOW}🔄 Migrating auto-commands...${NC}"

    local hooks_dir="$NEW_CONFIG_DIR/hooks"
    mkdir -p "$hooks_dir"

    if [[ -f "$OLD_TS_CONFIG/ts-enhanced.conf" ]]; then
        while IFS='=' read -r key value; do
            [[ "$key" =~ ^AUTO_CMD_(.+)$ ]] || continue

            local name="${BASH_REMATCH[1]}"
            local command=$(eval echo "$value" | tr -d '"')

            # Create post_create hook for this project
            cat > "$hooks_dir/post_create_${name}.sh" <<EOF
#!/bin/bash
# Auto-command for $name project
# Migrated from ts-enhanced.conf

session_name="\$1"
session_path="\$2"

if [[ "\$session_name" == "$name" ]]; then
    tmux -S "/home/jclee/.tmux/sockets/\$session_name" send-keys -t "\$session_name" '$command' Enter
fi
EOF
            chmod +x "$hooks_dir/post_create_${name}.sh"
            echo -e "${GREEN}✓ Created hook for: $name${NC}"
        done < <(grep "^AUTO_CMD_" "$OLD_TS_CONFIG/ts-enhanced.conf" 2>/dev/null || true)
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MIGRATE AGENTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

migrate_agents() {
    echo ""
    echo -e "${YELLOW}🔄 Migrating agent configurations...${NC}"

    # Check both locations for agents.json
    local agents_found=false

    if [[ -f "$OLD_TS_CONFIG/agents.json" ]]; then
        cp "$OLD_TS_CONFIG/agents.json" "$NEW_CONFIG_DIR/agents.json"
        agents_found=true
    elif [[ -f "$OLD_CC_CONFIG/agents.json" ]]; then
        cp "$OLD_CC_CONFIG/agents.json" "$NEW_CONFIG_DIR/agents.json"
        agents_found=true
    fi

    if [[ "$agents_found" == true ]]; then
        echo -e "${GREEN}✓ Migrated agents configuration${NC}"
    else
        echo '{"agents": []}' > "$NEW_CONFIG_DIR/agents.json"
        echo -e "${BLUE}ℹ No existing agents found, created empty config${NC}"
    fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLEANUP OLD FILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cleanup_old_files() {
    echo ""
    echo -e "${YELLOW}🧹 Cleaning up old backup files...${NC}"

    local cleaned=0

    # Clean ts config backups
    if [[ -d "$OLD_TS_CONFIG" ]]; then
        find "$OLD_TS_CONFIG" -name "*.backup*" -type f -delete 2>/dev/null || true
        find "$OLD_TS_CONFIG" -name "*.bak.*" -type f -delete 2>/dev/null || true
        cleaned=$((cleaned + $(find "$OLD_TS_CONFIG" -name "*.backup*" -o -name "*.bak.*" 2>/dev/null | wc -l)))
    fi

    # Clean cc config backups
    if [[ -d "$OLD_CC_CONFIG" ]]; then
        find "$OLD_CC_CONFIG" -name "*.backup*" -type f -delete 2>/dev/null || true
        cleaned=$((cleaned + $(find "$OLD_CC_CONFIG" -name "*.backup*" 2>/dev/null | wc -l)))
    fi

    echo -e "${GREEN}✓ Cleaned up $cleaned old backup files${NC}"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GENERATE MIGRATION REPORT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

generate_report() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}         Migration Report${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    local projects_count=$(jq 'keys | length' "$NEW_CONFIG_DIR/projects.json" 2>/dev/null || echo 0)
    local hooks_count=$(find "$NEW_CONFIG_DIR/hooks" -name "*.sh" 2>/dev/null | wc -l)
    local agents_count=$(jq '.agents | length' "$NEW_CONFIG_DIR/agents.json" 2>/dev/null || echo 0)

    cat <<EOF

${GREEN}✓ Migration Complete!${NC}

${BOLD}Summary:${NC}
  • Projects migrated: $projects_count
  • Hooks created: $hooks_count
  • Agents configured: $agents_count
  • Backup location: $BACKUP_DIR

${BOLD}New Configuration:${NC}
  • Config dir: $NEW_CONFIG_DIR
  • Projects: $NEW_CONFIG_DIR/projects.json
  • Agents: $NEW_CONFIG_DIR/agents.json
  • Hooks: $NEW_CONFIG_DIR/hooks/

${BOLD}Next Steps:${NC}
  1. Review migrated configuration:
     ${CYAN}cat $NEW_CONFIG_DIR/projects.json | jq .${NC}

  2. Install unified ts command:
     ${CYAN}sudo cp /home/jclee/app/tmux/ts-unified.sh /usr/local/bin/ts${NC}
     ${CYAN}sudo chmod +x /usr/local/bin/ts${NC}

  3. Test new ts command:
     ${CYAN}/usr/local/bin/ts list --json${NC}

  4. Remove old configs (after verification):
     ${CYAN}rm -rf $OLD_TS_CONFIG/*.backup* $OLD_TS_CONFIG/*.bak.*${NC}
     ${CYAN}rm -rf $OLD_CC_CONFIG/*.backup*${NC}

${YELLOW}⚠ Important:${NC}
  - Old configs backed up to: $BACKUP_DIR
  - PATH priority may need adjustment to use new ts command
  - Test thoroughly before removing backups

EOF
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN EXECUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    # Check dependencies
    if ! command -v jq &>/dev/null; then
        echo -e "${RED}✗ jq is required but not installed${NC}" >&2
        exit 1
    fi

    # Run migration steps
    backup_configs
    migrate_projects
    migrate_auto_commands
    migrate_agents
    cleanup_old_files
    generate_report

    echo -e "${GREEN}🎉 Migration completed successfully!${NC}"
}

main "$@"
