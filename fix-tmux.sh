#!/bin/bash
# Fix tmux issues

echo "Fixing tmux issues..."

# Kill duplicate attach processes
echo "Killing duplicate attach processes..."
ps aux | grep "tmux.*attach-session" | grep -v grep | awk '{print $2}' | while read pid; do
  echo "  Killing PID: $pid"
  kill $pid 2>/dev/null
done

# Clean dead sockets
echo "Cleaning dead sockets..."
for socket in /home/jclee/.tmux/sockets/*; do
  if [[ -S "$socket" ]]; then
    name=$(basename "$socket")
    if ! tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
      echo "  Removing dead socket: $name"
      rm -f "$socket"
    else
      echo "  Active: $name"
    fi
  fi
done

# Check main tmux session
echo ""
echo "Current tmux sessions:"
tmux ls 2>/dev/null || echo "No standard tmux sessions"

echo ""
echo "Socket-based sessions:"
for socket in /home/jclee/.tmux/sockets/*; do
  if [[ -S "$socket" ]]; then
    name=$(basename "$socket")
    if tmux -S "$socket" has-session -t "$name" 2>/dev/null; then
      windows=$(tmux -S "$socket" list-windows -t "$name" 2>/dev/null | wc -l)
      echo "  • $name: $windows windows"
    fi
  fi
done

echo ""
echo "✓ Tmux cleanup complete"