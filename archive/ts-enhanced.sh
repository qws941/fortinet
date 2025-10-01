#!/bin/bash
# Enhanced ts command additions - to be integrated into main ts script

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
        echo -e "  ts add api ../api-server             # Add relative path"
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

    # Backup existing config
    if [[ -f "$config_file" ]]; then
        cp "$config_file" "$config_file.bak"
    fi

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

    # Optional: Create session immediately
    echo -e "${YELLOW}Create session now? (y/N):${NC}"
    read -r create_session
    if [[ "$create_session" =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Creating session...${NC}"
        smart_attach_session "$project_name"
    fi
}

# Remove project from known projects registry
del_project() {
    local project_name="$1"

    if [[ -z "$project_name" ]]; then
        echo -e "${YELLOW}Usage: ts del <project_name>${NC}"
        echo -e "${BLUE}Available projects to remove:${NC}"
        local config_file="$HOME/.config/ts/projects.conf"
        if [[ -f "$config_file" ]]; then
            while IFS='=' read -r name path; do
                [[ -n "$name" && "$name" != \#* ]] && printf "  %-15s -> %s\n" "$name" "$path"
            done < "$config_file" | sort
        fi
        echo ""
        echo -e "${CYAN}Built-in projects (cannot be removed):${NC}"
        load_custom_projects
        local builtin_projects=("claude" "local" "blacklist" "blacklist-api" "claude-flow" "cloudflare" "data" "docs" "fortinet" "grafana" "hycu" "mcp" "propose" "resume" "safework" "splunk" "tmp" "tmux")
        for project in "${builtin_projects[@]}"; do
            if [[ -n "${KNOWN_PROJECTS[$project]}" ]]; then
                printf "  %-15s -> %s\n" "$project" "${KNOWN_PROJECTS[$project]}"
            fi
        done
        return 1
    fi

    # Load existing projects
    load_custom_projects

    # Check if it's a built-in project
    local builtin_projects=("claude" "local" "blacklist" "blacklist-api" "claude-flow" "cloudflare" "data" "docs" "fortinet" "grafana" "hycu" "mcp" "propose" "resume" "safework" "splunk" "tmp" "tmux")
    for builtin in "${builtin_projects[@]}"; do
        if [[ "$project_name" == "$builtin" ]]; then
            echo -e "${RED}✗ Cannot remove built-in project: $project_name${NC}"
            echo -e "${BLUE}Built-in projects are part of the ts script configuration${NC}"
            return 1
        fi
    done

    local config_file="$HOME/.config/ts/projects.conf"

    if [[ ! -f "$config_file" ]]; then
        echo -e "${YELLOW}⚠ No custom projects configured${NC}"
        return 1
    fi

    # Check if project exists in config
    if ! grep -q "^$project_name=" "$config_file"; then
        echo -e "${YELLOW}⚠ Project not found: $project_name${NC}"
        echo -e "${BLUE}Available projects:${NC}"
        while IFS='=' read -r name path; do
            [[ -n "$name" && "$name" != \#* ]] && printf "  %-15s -> %s\n" "$name" "$path"
        done < "$config_file" | sort
        return 1
    fi

    # Get project path for confirmation
    local project_path=$(grep "^$project_name=" "$config_file" | cut -d'=' -f2- | tr -d '"')

    # Check if there's an active session
    local socket_path="$SOCKET_DIR/$project_name"
    local has_session=false
    if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$project_name" 2>/dev/null; then
        has_session=true
    fi

    # Confirmation
    echo -e "${YELLOW}⚠ Remove project '$project_name'?${NC}"
    echo -e "${BLUE}📂 Path: $project_path${NC}"
    if [[ "$has_session" == true ]]; then
        echo -e "${RED}🔴 Active session will remain (use 'ts kill $project_name' to close)${NC}"
    fi
    echo -e "${CYAN}This only removes the project shortcut, not the directory${NC}"
    echo ""
    echo -e "${YELLOW}Continue? (y/N):${NC}"
    read -r confirm

    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Cancelled${NC}"
        return 0
    fi

    # Backup and remove
    cp "$config_file" "$config_file.bak"
    sed -i "/^$project_name=/d" "$config_file"

    echo -e "${GREEN}✓ Removed project: $project_name${NC}"

    if [[ "$has_session" == true ]]; then
        echo -e "${YELLOW}💡 Active session still running${NC}"
        echo -e "${BLUE}To close: ts kill $project_name${NC}"
    fi
}

# List all projects (built-in + custom)
list_all_projects() {
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}    All Known Projects${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

    # Load custom projects
    load_custom_projects

    echo -e "\n${BLUE}Built-in Projects:${NC}"
    local builtin_projects=("claude" "local" "blacklist" "blacklist-api" "claude-flow" "cloudflare" "data" "docs" "fortinet" "grafana" "hycu" "mcp" "propose" "resume" "safework" "splunk" "tmp" "tmux")

    for project in "${builtin_projects[@]}"; do
        if [[ -n "${KNOWN_PROJECTS[$project]}" ]]; then
            local status=""
            local socket_path="$SOCKET_DIR/$project"
            if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$project" 2>/dev/null; then
                status="${GREEN}[ACTIVE]${NC}"
            else
                status="${YELLOW}[IDLE]${NC}"
            fi
            printf "  %-15s -> %-40s %s\n" "$project" "${KNOWN_PROJECTS[$project]}" "$status"
        fi
    done

    # Custom projects
    local config_file="$HOME/.config/ts/projects.conf"
    if [[ -f "$config_file" ]]; then
        echo -e "\n${BLUE}Custom Projects:${NC}"
        while IFS='=' read -r name path; do
            if [[ -n "$name" && "$name" != \#* ]]; then
                local status=""
                local socket_path="$SOCKET_DIR/$name"
                if [[ -S "$socket_path" ]] && tmux -S "$socket_path" has-session -t "$name" 2>/dev/null; then
                    status="${GREEN}[ACTIVE]${NC}"
                else
                    status="${YELLOW}[IDLE]${NC}"
                fi
                printf "  %-15s -> %-40s %s\n" "$name" "$(eval echo "$path")" "$status"
            fi
        done < "$config_file" | sort
    else
        echo -e "\n${YELLOW}No custom projects configured${NC}"
        echo -e "${BLUE}Use 'ts add <name> [path]' to add projects${NC}"
    fi

    echo -e "\n${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Commands: ts add <name> [path] | ts del <name> | ts projects${NC}"
}

# Send command to Claude session with verification
send_claude_command() {
    local session_name="$1"
    local command="$2"
    local priority="${3:-normal}"

    if [[ -z "$session_name" ]] || [[ -z "$command" ]]; then
        echo -e "${YELLOW}Usage: ts cmd <session> <command> [priority]${NC}"
        echo -e "${BLUE}Examples:${NC}"
        echo -e "  ts cmd tmux 'analyze this code'${NC}"
        echo -e "  ts cmd grafana 'show dashboard status' urgent${NC}"
        echo -e "  ts cmd safework -p 'quick help with API'${NC}"
        echo ""
        echo -e "${CYAN}Available sessions:${NC}"
        ts sessions
        return 1
    fi

    # Handle priority flag
    if [[ "$session_name" == "-p" ]]; then
        priority="urgent"
        session_name="$command"
        command="$3"
    fi

    local socket_path="$SOCKET_DIR/$session_name"

    # Check if session exists
    if [[ ! -S "$socket_path" ]]; then
        # Try partial matching
        local found_session=""
        for socket in "$SOCKET_DIR"/*; do
            if [[ -S "$socket" ]] && [[ "$(basename "$socket")" == *"$session_name"* ]]; then
                found_session=$(basename "$socket")
                socket_path="$socket"
                session_name="$found_session"
                break
            fi
        done

        if [[ -z "$found_session" ]]; then
            echo -e "${RED}✗ Session not found: $session_name${NC}"
            echo -e "${BLUE}Available sessions:${NC}"
            ts sessions
            return 1
        fi
    fi

    # Check if session is active
    if ! tmux -S "$socket_path" has-session -t "$session_name" 2>/dev/null; then
        echo -e "${RED}✗ Session not active: $session_name${NC}"
        return 1
    fi

    # Check if Claude is running
    local claude_running=$(tmux -S "$socket_path" list-panes -t "$session_name" -F "#{pane_current_command}" 2>/dev/null | grep -c "node\|claude" || echo "0")

    if [[ $claude_running -eq 0 ]]; then
        echo -e "${YELLOW}⚠ Claude not running in session: $session_name${NC}"
        echo -e "${BLUE}Start Claude first or use 'ts restart $session_name'${NC}"
        return 1
    fi

    # Prepare command with priority prefix
    local formatted_command="$command"
    if [[ "$priority" == "urgent" ]]; then
        formatted_command="[URGENT] $command"
    fi

    # Send command to session
    echo -e "${CYAN}📤 Sending to $session_name:${NC}"
    echo -e "${BLUE}💬 $formatted_command${NC}"

    tmux -S "$socket_path" send-keys -t "$session_name" "$formatted_command" C-m

    echo -e "${GREEN}✓ Command sent${NC}"

    # Optional: Show recent response
    echo -e "${YELLOW}Wait for response? (y/N):${NC}"
    read -r -t 5 wait_response || wait_response="n"

    if [[ "$wait_response" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🔄 Waiting for response...${NC}"
        sleep 2
        echo -e "${CYAN}Recent output:${NC}"
        tmux -S "$socket_path" capture-pane -t "$session_name" -p | tail -10
    fi
}

# Validate all commands and check for duplicates
validate_commands() {
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}🔍 Command Validation Report${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

    # Test all main commands
    local commands=("ls" "list" "sessions" "kill" "killall" "bg" "log" "watch" "send" "ask" "talk" "bridge" "share" "restart" "config" "mcp" "monitor" "status" "add" "del" "projects" "cmd" "help")

    echo -e "\n${BLUE}📋 Available Commands:${NC}"
    for cmd in "${commands[@]}"; do
        echo -e "  ✓ ts $cmd"
    done

    # Check for command conflicts
    echo -e "\n${BLUE}🔍 Checking for conflicts:${NC}"
    local conflicts=()

    # Check if any commands might overlap
    for i in "${!commands[@]}"; do
        for j in "${!commands[@]}"; do
            if [[ $i -ne $j ]] && [[ "${commands[$i]}" == "${commands[$j]}"* ]] && [[ ${#commands[$i]} -lt ${#commands[$j]} ]]; then
                conflicts+=("${commands[$i]} ↔ ${commands[$j]}")
            fi
        done
    done

    if [[ ${#conflicts[@]} -eq 0 ]]; then
        echo -e "  ${GREEN}✓ No command conflicts detected${NC}"
    else
        echo -e "  ${YELLOW}⚠ Potential conflicts:${NC}"
        for conflict in "${conflicts[@]}"; do
            echo -e "    $conflict"
        done
    fi

    # Test session operations
    echo -e "\n${BLUE}🧪 Testing Session Operations:${NC}"

    # Check socket directory
    if [[ -d "$SOCKET_DIR" ]]; then
        echo -e "  ✓ Socket directory exists: $SOCKET_DIR"
        local socket_count=$(find "$SOCKET_DIR" -name "*" -type s | wc -l)
        echo -e "  ✓ Active sockets: $socket_count"
    else
        echo -e "  ${RED}✗ Socket directory missing${NC}"
    fi

    # Check MCP configuration
    echo -e "\n${BLUE}🔧 MCP Configuration:${NC}"
    local mcp_config="/home/jclee/.claude/mcp.json"
    if [[ -f "$mcp_config" ]]; then
        echo -e "  ✓ MCP config exists"
        local server_count=$(jq '.mcpServers | length' "$mcp_config" 2>/dev/null || echo "0")
        echo -e "  ✓ MCP servers: $server_count"
    else
        echo -e "  ${YELLOW}⚠ MCP config not found${NC}"
    fi

    echo -e "\n${CYAN}════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Validation Complete${NC}"
}

# Test the new commands
test_new_commands() {
    echo "Testing new ts commands..."

    echo "1. Testing ts add command:"
    echo "   ts add test-project /tmp/test-project"

    echo "2. Testing ts del command:"
    echo "   ts del test-project"

    echo "3. Testing ts cmd command:"
    echo "   ts cmd tmux 'show current status'"

    echo "4. Testing ts projects command:"
    echo "   ts projects"

    echo "5. Testing ts validate command:"
    echo "   ts validate"
}