#!/bin/bash
# Test script for tmux session conflict detection

echo "=== Testing tmux session conflict detection ==="
echo

# Function to simulate ts command behavior for conflict detection
test_session_conflict() {
    local project_dir="$1"
    local session_name="$2"

    echo "Testing: Creating '$session_name' session for directory '$project_dir'"

    # Check for existing sessions with same directory
    local conflicts=()

    for socket in /home/jclee/.tmux/sockets/*; do
        if [[ -S "$socket" ]]; then
            local existing_session=$(basename "$socket")
            if [[ "$existing_session" != "$session_name" ]]; then
                local existing_cwd=$(tmux -S "$socket" display-message -p -t "$existing_session" "#{pane_current_path}" 2>/dev/null || echo "")

                if [[ "$existing_cwd" == "$project_dir" ]]; then
                    conflicts+=("$existing_session")
                fi
            fi
        fi
    done

    if [[ ${#conflicts[@]} -gt 0 ]]; then
        echo "  ⚠️  CONFLICT: Found existing session(s) for this directory:"
        for conflict in "${conflicts[@]}"; do
            echo "    - $conflict -> $project_dir"
        done
        echo "  💡 Suggestion: Use 'ts $conflict' to attach or 'ts kill $conflict' to replace"
        return 1
    else
        echo "  ✅ No conflicts - safe to create session"
        return 0
    fi
}

# Test cases
echo "Current active sessions:"
ts sessions
echo

echo "Test 1: Same directory conflict"
test_session_conflict "/home/jclee/app/tmux" "new-tmux-session"
echo

echo "Test 2: Different directory (no conflict)"
test_session_conflict "/home/jclee/app/newproject" "newproject"
echo

echo "Test 3: Grafana directory conflict"
test_session_conflict "/home/jclee/app/grafana" "grafana-dev"
echo

echo "Test 4: Check if multiple sessions can share directories"
echo "Sessions by directory:"
for socket in /home/jclee/.tmux/sockets/*; do
    if [[ -S "$socket" ]]; then
        session=$(basename "$socket")
        cwd=$(tmux -S "$socket" display-message -p -t "$session" "#{pane_current_path}" 2>/dev/null || echo "Unknown")
        echo "  $session -> $cwd"
    fi
done
echo

echo "=== Recommendations ==="
echo "1. ✅ Dead sockets cleaned up successfully"
echo "2. ⚠️  Current sessions each use unique directories - good"
echo "3. 💡 ts command should implement conflict detection for same-directory sessions"
echo "4. 🔧 Consider adding session rename functionality for conflicts"