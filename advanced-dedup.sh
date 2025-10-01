#!/bin/bash
# Advanced Deduplication System for TS Environment
# Version 2.0 - Real-time monitoring and prevention

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
CONFIG_DIR="$HOME/.config/ts"
DEDUP_DB="$CONFIG_DIR/dedup.db"
DEDUP_LOG="$CONFIG_DIR/dedup.log"
DEDUP_STATS="$CONFIG_DIR/dedup.stats"
SOCKET_DIR="/home/jclee/.tmux/sockets"

# Create directories
mkdir -p "$CONFIG_DIR"

# Initialize database
init_dedup_db() {
    cat > "$DEDUP_DB" << EOF
# Deduplication Database
# Format: TYPE|KEY|VALUE|TIMESTAMP|COUNT
EOF
    echo -e "${GREEN}✓ Initialized deduplication database${NC}"
}

# Advanced PATH deduplication with scoring
dedupe_path_advanced() {
    local var_name="$1"
    local current_value="${!var_name:-}"

    if [[ -z "$current_value" ]]; then
        return
    fi

    # Analyze PATH entries
    declare -A path_scores
    declare -A path_counts
    declare -A first_occurrence
    local index=0

    # Score each path entry
    while IFS=: read -r path_entry; do
        [[ -z "$path_entry" ]] && continue

        # Count occurrences
        path_counts["$path_entry"]=$((${path_counts["$path_entry"]:-0} + 1))

        # Store first occurrence index
        if [[ -z "${first_occurrence[$path_entry]:-}" ]]; then
            first_occurrence["$path_entry"]=$index
        fi

        # Calculate priority score
        local score=100

        # System paths get higher priority
        [[ "$path_entry" =~ ^/usr/(local/)?s?bin ]] && ((score+=50))
        [[ "$path_entry" =~ ^/s?bin ]] && ((score+=40))
        [[ "$path_entry" =~ ^/usr/(local/)?bin ]] && ((score+=30))

        # User paths
        [[ "$path_entry" =~ ^"$HOME" ]] && ((score+=20))

        # Snap paths (lower priority)
        [[ "$path_entry" =~ snap ]] && ((score-=10))

        # Games paths (lowest priority)
        [[ "$path_entry" =~ games ]] && ((score-=20))

        path_scores["$path_entry"]=$score
        ((index++))
    done <<< "${current_value//:/$'\n'}"

    # Build deduplicated PATH with intelligent ordering
    local deduped_array=()
    declare -A seen

    # First pass: Add high-priority unique system paths
    for path_entry in "${!path_scores[@]}"; do
        if [[ ${path_counts[$path_entry]} -eq 1 ]] && [[ ${path_scores[$path_entry]} -ge 120 ]]; then
            if [[ -z "${seen[$path_entry]:-}" ]]; then
                deduped_array+=("$path_entry")
                seen["$path_entry"]=1
            fi
        fi
    done

    # Second pass: Add remaining paths by first occurrence
    while IFS=: read -r path_entry; do
        [[ -z "$path_entry" ]] && continue
        if [[ -z "${seen[$path_entry]:-}" ]]; then
            deduped_array+=("$path_entry")
            seen["$path_entry"]=1
        fi
    done <<< "${current_value//:/$'\n'}"

    # Join array to string
    local deduped=$(IFS=:; echo "${deduped_array[*]}")

    # Export the result
    export "$var_name=$deduped"

    # Statistics
    local original_count=$(echo "$current_value" | tr ':' '\n' | grep -c .)
    local deduped_count=$(echo "$deduped" | tr ':' '\n' | grep -c .)
    local removed=$((original_count - deduped_count))

    # Log to database
    echo "PATH|$var_name|deduplicated|$(date +%s)|$removed" >> "$DEDUP_DB"

    if [[ $removed -gt 0 ]]; then
        echo -e "${GREEN}✓ $var_name: Removed $removed duplicates (${original_count}→${deduped_count})${NC}"

        # Show what was removed
        for path_entry in "${!path_counts[@]}"; do
            if [[ ${path_counts[$path_entry]} -gt 1 ]]; then
                echo -e "${YELLOW}  Duplicate removed: $path_entry (×${path_counts[$path_entry]})${NC}"
            fi
        done
    else
        echo -e "${BLUE}  $var_name: Already optimized${NC}"
    fi
}

# Deep configuration file deduplication
dedupe_config_deep() {
    local file="$1"
    local description="$2"

    if [[ ! -f "$file" ]]; then
        return
    fi

    # Backup
    cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"

    # Analyze duplicates
    declare -A line_counts
    declare -A key_values
    local total_lines=0
    local duplicate_lines=0

    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        ((total_lines++))

        # Count occurrences
        ((line_counts["$line"]++))

        # For key=value pairs, track latest value
        if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            key_values["$key"]="$value"
        fi
    done < "$file"

    # Count duplicates
    for line in "${!line_counts[@]}"; do
        if [[ ${line_counts["$line"]} -gt 1 ]]; then
            duplicate_lines=$((duplicate_lines + line_counts["$line"] - 1))
        fi
    done

    if [[ $duplicate_lines -gt 0 ]]; then
        # Smart deduplication - preserve last occurrence
        {
            declare -A seen_lines
            declare -A seen_keys

            # Read file in reverse, keep first (originally last) occurrence
            tac "$file" | while IFS= read -r line; do
                [[ -z "$line" ]] && continue

                # For key=value pairs
                if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
                    local key="${BASH_REMATCH[1]}"
                    if [[ -z "${seen_keys[$key]:-}" ]]; then
                        echo "$line"
                        seen_keys["$key"]=1
                    fi
                else
                    # For other lines
                    if [[ -z "${seen_lines[$line]:-}" ]]; then
                        echo "$line"
                        seen_lines["$line"]=1
                    fi
                fi
            done | tac
        } > "$file.tmp"

        mv "$file.tmp" "$file"

        echo -e "${GREEN}✓ $description: Removed $duplicate_lines duplicates${NC}"
        echo "CONFIG|$file|deduplicated|$(date +%s)|$duplicate_lines" >> "$DEDUP_DB"

        # Show duplicate statistics
        echo -e "${CYAN}  Duplicate analysis:${NC}"
        for line in "${!line_counts[@]}"; do
            if [[ ${line_counts["$line"]} -gt 1 ]]; then
                echo -e "${YELLOW}    '${line:0:50}...' (×${line_counts["$line"]})${NC}"
            fi
        done | head -5
    else
        echo -e "${BLUE}  $description: No duplicates${NC}"
    fi
}

# Real-time monitoring
monitor_duplicates() {
    echo -e "${CYAN}🔍 Real-time Duplicate Monitor${NC}"
    echo -e "${YELLOW}Monitoring environment and configurations...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""

    local check_interval=5
    declare -A last_path_hash
    declare -A last_config_hash

    while true; do
        # Check PATH variables
        for var in PATH LD_LIBRARY_PATH PYTHONPATH MANPATH; do
            local current_value="${!var:-}"
            [[ -z "$current_value" ]] && continue

            local current_hash=$(echo "$current_value" | md5sum | cut -d' ' -f1)

            if [[ "${last_path_hash[$var]:-}" != "$current_hash" ]]; then
                local dup_count=$(echo "$current_value" | tr ':' '\n' | sort | uniq -d | wc -l)

                if [[ $dup_count -gt 0 ]]; then
                    echo -e "${RED}[$(date +%H:%M:%S)] ⚠ $var has $dup_count duplicates!${NC}"
                    dedupe_path_advanced "$var"
                fi

                last_path_hash[$var]=$current_hash
            fi
        done

        # Check configuration files
        for conf in "$CONFIG_DIR"/*.conf; do
            [[ -f "$conf" ]] || continue

            local current_hash=$(md5sum "$conf" 2>/dev/null | cut -d' ' -f1)
            local conf_name=$(basename "$conf")

            if [[ "${last_config_hash[$conf_name]:-}" != "$current_hash" ]]; then
                local dup_count=$(sort "$conf" | uniq -d | wc -l)

                if [[ $dup_count -gt 0 ]]; then
                    echo -e "${RED}[$(date +%H:%M:%S)] ⚠ $conf_name has $dup_count duplicate lines!${NC}"
                    dedupe_config_deep "$conf" "$conf_name"
                fi

                last_config_hash[$conf_name]=$current_hash
            fi
        done

        # Check tmux sockets
        local dead_sockets=0
        for socket in "$SOCKET_DIR"/*; do
            if [[ -S "$socket" ]]; then
                local session_name=$(basename "$socket")
                if ! tmux -S "$socket" has-session -t "$session_name" 2>/dev/null; then
                    ((dead_sockets++))
                fi
            fi
        done

        if [[ $dead_sockets -gt 0 ]]; then
            echo -e "${YELLOW}[$(date +%H:%M:%S)] 🧹 Cleaning $dead_sockets dead socket(s)${NC}"
            for socket in "$SOCKET_DIR"/*; do
                if [[ -S "$socket" ]]; then
                    local session_name=$(basename "$socket")
                    if ! tmux -S "$socket" has-session -t "$session_name" 2>/dev/null; then
                        rm -f "$socket"
                    fi
                fi
            done
        fi

        sleep $check_interval
    done
}

# Statistics report
show_statistics() {
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}           Deduplication Statistics${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    if [[ -f "$DEDUP_DB" ]]; then
        local total_removed=$(grep -E "deduplicated" "$DEDUP_DB" 2>/dev/null | awk -F'|' '{sum+=$5} END {print sum+0}')
        local path_removed=$(grep "^PATH" "$DEDUP_DB" 2>/dev/null | awk -F'|' '{sum+=$5} END {print sum+0}')
        local config_removed=$(grep "^CONFIG" "$DEDUP_DB" 2>/dev/null | awk -F'|' '{sum+=$5} END {print sum+0}')

        echo -e "${GREEN}Total duplicates removed: $total_removed${NC}"
        echo -e "${BLUE}  PATH duplicates: $path_removed${NC}"
        echo -e "${BLUE}  Config duplicates: $config_removed${NC}"

        echo ""
        echo -e "${CYAN}Recent activity:${NC}"
        tail -5 "$DEDUP_DB" 2>/dev/null | while IFS='|' read -r type key action timestamp count; do
            local date_str=$(date -d "@$timestamp" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "$timestamp")
            echo -e "  ${YELLOW}[$date_str]${NC} $type: $action ($count items)"
        done
    else
        echo -e "${YELLOW}No statistics available yet${NC}"
    fi
}

# Auto-fix system
auto_fix_all() {
    echo -e "${CYAN}🔧 Advanced Auto-Fix System${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"

    # Initialize database if needed
    [[ ! -f "$DEDUP_DB" ]] && init_dedup_db

    # 1. Environment variables
    echo -e "\n${BLUE}1. Environment Variables${NC}"
    for var in PATH LD_LIBRARY_PATH PYTHONPATH MANPATH CDPATH FPATH; do
        [[ -n "${!var:-}" ]] && dedupe_path_advanced "$var"
    done

    # 2. Configuration files
    echo -e "\n${BLUE}2. Configuration Files${NC}"
    for conf in "$CONFIG_DIR"/*.conf; do
        [[ -f "$conf" ]] && dedupe_config_deep "$conf" "$(basename "$conf")"
    done

    # 3. Socket cleanup
    echo -e "\n${BLUE}3. Socket Cleanup${NC}"
    local cleaned=0
    for socket in "$SOCKET_DIR"/*; do
        if [[ -S "$socket" ]]; then
            local session_name=$(basename "$socket")
            # Skip invalid session names
            if [[ "$session_name" =~ ^-- ]] || [[ "$session_name" == ".lock" ]]; then
                rm -f "$socket"
                echo -e "${YELLOW}  Removed invalid socket: $session_name${NC}"
                ((cleaned++))
                continue
            fi
            if ! tmux -S "$socket" has-session -t "$session_name" 2>/dev/null; then
                rm -f "$socket"
                echo -e "${YELLOW}  Removed dead socket: $session_name${NC}"
                ((cleaned++))
            fi
        fi
    done

    if [[ $cleaned -eq 0 ]]; then
        echo -e "${BLUE}  All sockets healthy${NC}"
    fi

    # 4. Install permanent fix
    echo -e "\n${BLUE}4. Installing Permanent Fix${NC}"
    local dedup_hook="$CONFIG_DIR/dedup_hook.sh"
    cat > "$dedup_hook" << 'HOOK'
#!/bin/bash
# Auto-deduplication hook
dedupe_path_silent() {
    local var_name="$1"
    local current="${!var_name:-}"
    [[ -z "$current" ]] && return
    local deduped=$(echo "$current" | tr ':' '\n' | awk '!seen[$0]++' | tr '\n' ':' | sed 's/:$//')
    export "$var_name=$deduped"
}

# Silent deduplication on shell start
dedupe_path_silent PATH
dedupe_path_silent LD_LIBRARY_PATH
dedupe_path_silent PYTHONPATH
HOOK

    chmod +x "$dedup_hook"

    # Add to shell configs if not present
    for rc in ~/.bashrc ~/.zshrc ~/.profile; do
        if [[ -f "$rc" ]] && ! grep -q "dedup_hook.sh" "$rc" 2>/dev/null; then
            echo "source '$dedup_hook' 2>/dev/null" >> "$rc"
            echo -e "${GREEN}  ✓ Added hook to $(basename "$rc")${NC}"
        fi
    done

    # Show statistics
    echo ""
    show_statistics
}

# Main menu
case "${1:-}" in
    "init")
        init_dedup_db
        ;;
    "monitor")
        monitor_duplicates
        ;;
    "stats")
        show_statistics
        ;;
    "fix")
        auto_fix_all
        ;;
    "path")
        dedupe_path_advanced "PATH"
        ;;
    "clean")
        # Quick clean
        echo -e "${CYAN}Quick Clean${NC}"
        dedupe_path_advanced "PATH"
        for conf in "$CONFIG_DIR"/*.conf; do
            [[ -f "$conf" ]] && dedupe_config_deep "$conf" "$(basename "$conf")"
        done
        ;;
    *)
        echo -e "${CYAN}Advanced Deduplication System v2.0${NC}"
        echo ""
        echo -e "${YELLOW}Usage:${NC}"
        echo -e "  $0 fix      - Run complete auto-fix"
        echo -e "  $0 monitor  - Real-time monitoring"
        echo -e "  $0 stats    - Show statistics"
        echo -e "  $0 clean    - Quick clean"
        echo -e "  $0 path     - Fix PATH only"
        echo -e "  $0 init     - Initialize database"
        echo ""
        echo -e "${BLUE}Features:${NC}"
        echo -e "  • Intelligent PATH ordering"
        echo -e "  • Deep config analysis"
        echo -e "  • Real-time monitoring"
        echo -e "  • Automatic prevention"
        echo -e "  • Statistics tracking"
        ;;
esac