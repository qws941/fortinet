#!/bin/bash
# TS Compatibility Configuration
# Source this file in your shell rc file to set up proper aliases

# Detect if this script is being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "This script should be sourced, not executed directly."
    echo "Add to your ~/.bashrc or ~/.zshrc:"
    echo "  source $(realpath "${BASH_SOURCE[0]}")"
    exit 1
fi

# Create aliases for disambiguation
alias ts-session='/usr/local/bin/ts'      # Tmux session manager
alias ts-timestamp='/usr/bin/ts'          # Timestamp utility (moreutils)
alias tmux-session='ts-session'           # Explicit alias

# Make 'ts' default to session manager (recommended)
# Comment this out if you prefer timestamp utility as default
alias ts='ts-session'

# Environment variables for customization
export TS_CONFIG_DIR="${TS_CONFIG_DIR:-$HOME/.config/ts}"
export TS_SOCKET_DIR="${TS_SOCKET_DIR:-$HOME/.tmux/sockets}"

# Shell completion for ts command
_ts_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Available commands
    opts="list ls kill resume claude cmd help version"

    # Add session names
    if [[ -d "$TS_SOCKET_DIR" ]]; then
        local sessions=$(find "$TS_SOCKET_DIR" -type s -exec basename {} \; 2>/dev/null)
        opts="$opts $sessions"
    fi

    case "${prev}" in
        kill|cmd)
            # Suggest session names for kill and cmd
            local sessions=$(find "$TS_SOCKET_DIR" -type s -exec basename {} \; 2>/dev/null)
            COMPREPLY=( $(compgen -W "${sessions}" -- ${cur}) )
            return 0
            ;;
        *)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
    esac
}

# Register completion
complete -F _ts_completion ts
complete -F _ts_completion ts-session

echo "✓ TS compatibility configuration loaded"
echo "  ts          → Tmux session manager"
echo "  ts-session  → Explicit tmux session manager"
echo "  ts-timestamp → Timestamp utility (moreutils)"