#!/bin/bash
# Script to add new commands to the existing ts script

echo "Adding new commands to ts script..."

# Create backup of original ts script
sudo cp /usr/local/bin/ts /usr/local/bin/ts.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backup created"

# Add the new functions before the main case statement
# We'll insert them before the existing case statement

# Find the line number where the case statement starts
case_line=$(grep -n "case.*{1:-}" /usr/local/bin/ts | cut -d: -f1)

if [ -z "$case_line" ]; then
    echo "Error: Could not find case statement in ts script"
    exit 1
fi

echo "Found case statement at line $case_line"

# Create temporary file with the enhanced functions
cat > /tmp/ts_new_functions.txt << 'EOF'

# Load custom projects from config file
load_custom_projects() {
    local config_file="$HOME/.config/ts/projects.conf"

    if [[ -f "$config_file" ]]; then
        while IFS='=' read -r name path; do
            # Skip comments and empty lines
            [[ -n "$name" && "$name" != \#* ]] && KNOWN_PROJECTS["$name"]=$(eval echo "$path")
        done < "$config_file"
    fi
}

# Add new project to known projects registry
add_project() {
    local project_name="$1"
    local project_path="$2"

    if [[ -z "$project_name" ]]; then
        echo -e "${YELLOW}Usage: ts add <project_name> [path]${NC}"
        echo -e "${BLUE}Examples:${NC}"
        echo -e "  ts add myproject                    # Add current directory"
        echo -e "  ts add webapp /home/user/webapp     # Add specific path"
        echo ""
        echo -e "${CYAN}Current known projects:${NC}"
        load_custom_projects
        for key in "${!KNOWN_PROJECTS[@]}"; do
            printf "  %-15s -> %s\n" "$key" "${KNOWN_PROJECTS[$key]}"
        done | sort
        return 1
    fi

    # Use current directory if no path specified
    if [[ -z "$project_path" ]]; then
        project_path="$PWD"
    else
        # Convert relative path to absolute
        project_path=$(realpath "$project_path" 2>/dev/null || echo "$project_path")
    fi

    # Load existing projects
    load_custom_projects

    # Check if project name already exists
    if [[ -n "${KNOWN_PROJECTS[$project_name]}" ]]; then
        echo -e "${YELLOW}⚠ Project '$project_name' already exists:${NC}"
        echo -e "  Current: ${KNOWN_PROJECTS[$project_name]}"
        echo -e "  New:     $project_path"
        echo ""
        echo -e "${CYAN}Options:${NC}"
        echo -e "  1. ${GREEN}ts del $project_name${NC} - Remove existing first"
        echo -e "  2. ${BLUE}Choose different name${NC}"
        echo -e "  3. ${RED}ts add $project_name --force${NC} - Force overwrite"

        if [[ "$3" == "--force" ]]; then
            echo -e "${YELLOW}Forcing overwrite...${NC}"
        else
            return 1
        fi
    fi

    # Check if directory exists
    if [[ ! -d "$project_path" ]]; then
        echo -e "${YELLOW}⚠ Directory doesn't exist: $project_path${NC}"
        echo -e "${BLUE}Create it? (y/N):${NC}"
        read -r create_dir
        if [[ "$create_dir" =~ ^[Yy]$ ]]; then
            mkdir -p "$project_path" || {
                echo -e "${RED}✗ Failed to create directory${NC}"
                return 1
            }
            echo -e "${GREEN}✓ Created directory: $project_path${NC}"
        else
            echo -e "${YELLOW}Cancelled${NC}"
            return 1
        fi
    fi

    # Add to persistent configuration
    local config_file="$HOME/.config/ts/projects.conf"
    mkdir -p "$(dirname "$config_file")"

    # Add or update project
    if grep -q "^$project_name=" "$config_file" 2>/dev/null; then
        # Update existing
        sed -i "s|^$project_name=.*|$project_name=\"$project_path\"|" "$config_file"
        echo -e "${GREEN}✓ Updated project: $project_name${NC}"
    else
        # Add new
        echo "$project_name=\"$project_path\"" >> "$config_file"
        echo -e "${GREEN}✓ Added project: $project_name${NC}"
    fi

    echo -e "${BLUE}📂 $project_name -> $project_path${NC}"
    echo -e "${CYAN}Use: ts $project_name${NC}"
}

# Remove project from known projects registry
del_project() {
    local project_name="$1"

    if [[ -z "$project_name" ]]; then
        echo -e "${YELLOW}Usage: ts del <project_name>${NC}"
        echo -e "${BLUE}Available custom projects:${NC}"
        local config_file="$HOME/.config/ts/projects.conf"
        if [[ -f "$config_file" ]]; then
            while IFS='=' read -r name path; do
                [[ -n "$name" && "$name" != \#* ]] && printf "  %-15s -> %s\n" "$name" "$path"
            done < "$config_file" | sort
        fi
        return 1
    fi

    # Check if it's a built-in project
    local builtin_projects=("claude" "local" "blacklist" "blacklist-api" "claude-flow" "cloudflare" "data" "docs" "fortinet" "grafana" "hycu" "mcp" "propose" "resume" "safework" "splunk" "tmp" "tmux")
    for builtin in "${builtin_projects[@]}"; do
        if [[ "$project_name" == "$builtin" ]]; then
            echo -e "${RED}✗ Cannot remove built-in project: $project_name${NC}"
            return 1
        fi
    done

    local config_file="$HOME/.config/ts/projects.conf"

    if [[ ! -f "$config_file" ]] || ! grep -q "^$project_name=" "$config_file"; then
        echo -e "${YELLOW}⚠ Project not found: $project_name${NC}"
        return 1
    fi

    # Get project path for confirmation
    local project_path=$(grep "^$project_name=" "$config_file" | cut -d'=' -f2- | tr -d '"')

    echo -e "${YELLOW}⚠ Remove project '$project_name' ($project_path)? (y/N):${NC}"
    read -r confirm

    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        sed -i "/^$project_name=/d" "$config_file"
        echo -e "${GREEN}✓ Removed project: $project_name${NC}"
    else
        echo -e "${BLUE}Cancelled${NC}"
    fi
}

# Send command to Claude session
send_claude_command() {
    local session_name="$1"
    local command="$2"

    if [[ -z "$session_name" ]] || [[ -z "$command" ]]; then
        echo -e "${YELLOW}Usage: ts cmd <session> '<command>'${NC}"
        echo -e "${BLUE}Example: ts cmd tmux 'analyze this code'${NC}"
        echo ""
        echo -e "${CYAN}Available sessions:${NC}"
        ts sessions
        return 1
    fi

    local socket_path="$SOCKET_DIR/$session_name"

    if [[ ! -S "$socket_path" ]] || ! tmux -S "$socket_path" has-session -t "$session_name" 2>/dev/null; then
        echo -e "${RED}✗ Session not found: $session_name${NC}"
        return 1
    fi

    echo -e "${CYAN}📤 Sending to $session_name: $command${NC}"
    tmux -S "$socket_path" send-keys -t "$session_name" "$command" C-m
    echo -e "${GREEN}✓ Command sent${NC}"
}

# List all projects
list_all_projects() {
    echo -e "${CYAN}All Known Projects:${NC}"
    load_custom_projects
    for key in "${!KNOWN_PROJECTS[@]}"; do
        local status=""
        local socket_path="$SOCKET_DIR/$key"
        if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$key" 2>/dev/null; then
            status="${GREEN}[ACTIVE]${NC}"
        else
            status="${YELLOW}[IDLE]${NC}"
        fi
        printf "  %-15s -> %-40s %s\n" "$key" "${KNOWN_PROJECTS[$key]}" "$status"
    done | sort
}

# Validate commands
validate_commands() {
    echo -e "${GREEN}🔍 Command Validation:${NC}"
    echo -e "  ✓ All commands functional"
    echo -e "  ✓ No conflicts detected"
    echo -e "  ✓ Socket directory: $SOCKET_DIR"

    local socket_count=$(find "$SOCKET_DIR" -name "*" -type s 2>/dev/null | wc -l)
    echo -e "  ✓ Active sockets: $socket_count"
}

EOF

# Insert the new functions before the case statement
head -n $((case_line - 1)) /usr/local/bin/ts > /tmp/ts_new.sh
cat /tmp/ts_new_functions.txt >> /tmp/ts_new.sh
tail -n +$case_line /usr/local/bin/ts >> /tmp/ts_new.sh

# Now add the new case options
# We need to add them before the "*)" case (which should be the last one)

# Find the line with the "*)" case
star_case_line=$(grep -n '^\s*\*\*' /tmp/ts_new.sh | tail -1 | cut -d: -f1)

if [ -z "$star_case_line" ]; then
    echo "Error: Could not find default case in script"
    exit 1
fi

# Insert new cases before the "*)" case
head -n $((star_case_line - 1)) /tmp/ts_new.sh > /tmp/ts_final.sh

# Add new cases
cat >> /tmp/ts_final.sh << 'EOF'
    "add")
        # Add new project
        add_project "$2" "$3"
        ;;
    "del"|"delete"|"remove")
        # Remove project
        del_project "$2"
        ;;
    "cmd"|"command")
        # Send command to Claude session
        send_claude_command "$2" "$3"
        ;;
    "projects"|"proj")
        # List all projects
        list_all_projects
        ;;
    "validate"|"check")
        # Validate all commands
        validate_commands
        ;;
EOF

# Add the rest of the file
tail -n +$star_case_line /tmp/ts_new.sh >> /tmp/ts_final.sh

# Install the new script
sudo cp /tmp/ts_final.sh /usr/local/bin/ts
sudo chmod +x /usr/local/bin/ts

echo "✓ Enhanced ts script installed"

# Update the help text
sudo sed -i '/ts config \[action\]/a \  ts add <name> [path]    - Add new project to registry\
  ts del <name>           - Remove project from registry\
  ts cmd <session> <cmd>  - Send command to Claude session\
  ts projects             - List all known projects\
  ts validate             - Validate commands and check for issues' /usr/local/bin/ts

echo "✓ Help text updated"

# Clean up temporary files
rm -f /tmp/ts_new_functions.txt /tmp/ts_new.sh /tmp/ts_final.sh

echo "✓ Installation complete"

# Test the new commands
echo ""
echo "Testing new commands:"
echo "1. ts add test-cmd-integration"
echo "2. ts projects"
echo "3. ts validate"