#!/bin/bash
# TS Session Alias System
# Use short names: blacklist instead of claude-blacklist

set -euo pipefail

ALIAS_DB="$HOME/.config/ts/aliases.json"
SOCKET_DIR="/home/jclee/.tmux/sockets"

# Initialize
mkdir -p "$(dirname "$ALIAS_DB")"
[[ -f "$ALIAS_DB" ]] || echo '{"aliases": {}}' > "$ALIAS_DB"

# Resolve alias to full session name
resolve_alias() {
    local input="$1"

    # Check if it's already a full session name
    if [[ -S "$SOCKET_DIR/$input" ]]; then
        echo "$input"
        return 0
    fi

    # Check alias database
    local full_name=$(jq -r --arg alias "$input" '.aliases[$alias] // empty' "$ALIAS_DB")
    if [[ -n "$full_name" ]]; then
        echo "$full_name"
        return 0
    fi

    # Try common patterns
    for prefix in "claude-" ""; do
        if [[ -S "$SOCKET_DIR/${prefix}${input}" ]]; then
            echo "${prefix}${input}"
            return 0
        fi
    done

    # Not found
    echo "$input"
    return 1
}

# Auto-create aliases for existing sessions
auto_create_aliases() {
    local updated=$(jq '.aliases = {}' "$ALIAS_DB")

    for socket in "$SOCKET_DIR"/*; do
        [[ -S "$socket" ]] || continue
        [[ "$(basename "$socket")" == ".lock" ]] && continue

        local full_name=$(basename "$socket")

        # Extract short name
        if [[ "$full_name" =~ ^claude-(.+)$ ]]; then
            local short_name="${BASH_REMATCH[1]}"
            updated=$(echo "$updated" | jq --arg short "$short_name" --arg full "$full_name" '.aliases[$short] = $full')
        fi
    done

    echo "$updated" > "$ALIAS_DB"
}

# Show all aliases
show_aliases() {
    echo -e "\033[0;36m═══════════════════════════════════════════════════\033[0m"
    echo -e "\033[0;36m\033[1m           Session Aliases\033[0m"
    echo -e "\033[0;36m═══════════════════════════════════════════════════\033[0m"

    jq -r '.aliases | to_entries[] | "\(.key) → \(.value)"' "$ALIAS_DB" | while IFS=' → ' read -r short full; do
        if [[ -S "$SOCKET_DIR/$full" ]]; then
            echo -e "  \033[0;32m✓\033[0m \033[1m$short\033[0m → $full"
        else
            echo -e "  \033[0;31m✗\033[0m \033[1m$short\033[0m → $full (inactive)"
        fi
    done
}

# Main
case "${1:-auto}" in
    "auto")
        auto_create_aliases
        ;;
    "show"|"list")
        show_aliases
        ;;
    "resolve")
        resolve_alias "$2"
        ;;
    *)
        resolve_alias "$1"
        ;;
esac
