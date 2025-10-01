# TS Unified v3.0.0 - Advanced Tmux Session Manager

## 🎯 Overview

TS Unified is a complete rewrite of the ts command system with:
- **Plugin Architecture**: Extensible via plugins
- **Hook System**: Lifecycle hooks for automation
- **Session Labeling**: Tag and organize sessions
- **Background Task Management**: Run processes in dedicated windows
- **Grafana Telemetry**: Full observability integration
- **JSON API**: Machine-readable output
- **Constitutional Compliance**: Follows CLAUDE.md v11.0

## 📦 Installation

```bash
# Install unified ts system
./install-ts-unified.sh

# Or manual installation
sudo cp ts-unified.sh /usr/local/bin/ts
sudo cp ts-bg-manager.sh /usr/local/bin/ts-bg
sudo chmod +x /usr/local/bin/{ts,ts-bg}

# Migrate existing configs
./migrate-ts-config.sh
```

## 🚀 Quick Start

### Basic Session Management

```bash
# List all sessions
ts list                    # Human-readable
ts list --json             # JSON output

# Create/attach to session
ts blacklist               # Auto-detects project path
ts myproject /path/to/dir  # Explicit path

# Resume last session
ts resume

# Kill session
ts kill myproject
```

### Session Labeling

```bash
# Label a session
ts-bg label claude-blacklist 'backend,api,production'
ts-bg label claude-planka 'frontend,kanban,staging'

# View all labels
ts-bg labels

# View labels for specific session
ts-bg labels claude-blacklist

# Search by label
ts-bg search production    # Find all production sessions
ts-bg search backend       # Find all backend sessions
```

### Background Task Management

```bash
# Start background task
ts-bg start claude-blacklist dev-server 'npm run dev' dev-server

# Quick templates
ts-bg dev claude-blacklist              # Start dev server
ts-bg test claude-blacklist             # Start test watcher
ts-bg logs claude-blacklist ./logs/app.log  # Monitor logs

# List background tasks
ts-bg list                              # All tasks
ts-bg list claude-blacklist             # Session-specific

# Attach to background task
ts-bg attach claude-blacklist:dev-server

# Stop background task
ts-bg stop claude-blacklist:dev-server
```

## 📋 Configuration

### Main Config: `~/.config/ts/config.json`

```json
{
  "version": "3.0.0",
  "socket_dir": "/home/jclee/.tmux/sockets",
  "default_shell": "/bin/bash",
  "auto_cleanup": true,
  "grafana_telemetry": true,
  "json_output": false,
  "plugins_enabled": true,
  "hooks_enabled": true,
  "constitutional_compliance": true,
  "features": {
    "auto_dedup": true,
    "session_persistence": true,
    "nested_tmux_detection": true,
    "claude_integration": true
  }
}
```

### Projects: `~/.config/ts/projects.json`

```json
{
  "blacklist": "/home/jclee/app/blacklist",
  "grafana": "/home/jclee/app/grafana",
  "tmux": "/home/jclee/app/tmux"
}
```

### Session Labels: `~/.config/ts/state/session_labels.json`

```json
{
  "sessions": {
    "claude-blacklist": {
      "labels": ["backend", "api", "production"],
      "updated": "2025-10-01T05:00:00Z"
    }
  }
}
```

### Background Tasks: `~/.config/ts/state/background_tasks.json`

```json
{
  "tasks": {
    "claude-blacklist:dev-server": {
      "session": "claude-blacklist",
      "window": "dev-server",
      "command": "npm run dev",
      "type": "dev-server",
      "started": "2025-10-01T05:00:00Z",
      "status": "running"
    }
  }
}
```

## 🔌 Plugin System

Create plugins in `~/.config/ts/plugins/`:

```bash
# Example plugin: ~/.config/ts/plugins/git-status.sh
#!/bin/bash
# Git status plugin for ts

show_git_status() {
    local session_path="$1"
    cd "$session_path" 2>/dev/null || return 0

    if git rev-parse --git-dir >/dev/null 2>&1; then
        local branch=$(git branch --show-current)
        local status=$(git status --short | wc -l)
        echo "🔀 Branch: $branch | Changes: $status"
    fi
}
```

## 🪝 Hook System

Create hooks in `~/.config/ts/hooks/`:

```bash
# Example: ~/.config/ts/hooks/post_create.sh
#!/bin/bash
# Post-create hook - runs after session creation

session_name="$1"
session_path="$2"

# Auto-start dev server for specific projects
if [[ "$session_name" =~ ^claude-(blacklist|fortinet|planka)$ ]]; then
    sleep 2
    ts-bg dev "$session_name"
fi
```

## 📊 Grafana Integration

All ts commands are automatically logged to Grafana Loki:

```yaml
Job: ts-command
Labels:
  - command: create|list|kill|attach
  - session: session-name
  - user: username
  - hostname: hostname
  - version: 3.0.0

Fields:
  - timestamp
  - full_command
  - args
  - exit_code
  - duration_ms
  - metadata
```

Query in Grafana:
```logql
{job="ts-command"} | json | command="create"
{job="ts-command", session="claude-blacklist"}
rate({job="ts-command"}[5m])
```

## 🎨 Real-World Examples

### Example 1: Production Backend Workflow

```bash
# Label production backend sessions
ts-bg label claude-blacklist 'backend,api,production'
ts-bg label claude-manager 'backend,admin,production'

# Start dev servers
ts-bg dev claude-blacklist
ts-bg dev claude-manager

# Monitor logs
ts-bg logs claude-blacklist ./logs/app.log

# Find all production sessions
ts-bg search production

# Attach to specific task
ts-bg attach claude-blacklist:dev-server
```

### Example 2: Multi-Project Development

```bash
# Label frontend projects
ts-bg label claude-planka 'frontend,kanban,react'
ts-bg label cm-web 'frontend,web,vue'

# Start all frontend dev servers
for session in $(ts-bg search frontend | awk '{print $2}'); do
    ts-bg dev "$session"
done

# List all running tasks
ts-bg list
```

### Example 3: Monitoring and Observability

```bash
# Label with observability focus
ts-bg label grafana 'monitoring,observability,infrastructure'
ts-bg label prometheus 'monitoring,metrics,infrastructure'

# Find all infrastructure sessions
ts-bg search infrastructure

# Export to Grafana
ts-bg export
```

## 🔄 Migration from Old TS

```bash
# Run migration script
./migrate-ts-config.sh

# Verify migration
cat ~/.config/ts/projects.json | jq .
ls -la ~/.config/ts/hooks/

# Backup location
ls ~/.config/ts/backups/migration-*/
```

## 🛠️ Troubleshooting

### Issue: ts command not found
```bash
# Check installation
which ts
ls -la /usr/local/bin/ts

# Refresh PATH
hash -r
# or restart shell
```

### Issue: PATH conflict with old ts
```bash
# Check all ts commands in PATH
which -a ts

# Ensure /usr/local/bin is first
echo $PATH

# Fix: Remove ~/.claude/bin/ts or adjust PATH order
```

### Issue: Sessions not showing up
```bash
# Check sockets
ls -la /home/jclee/.tmux/sockets/

# Clean dead sockets
ts cleanup

# Verify tmux
tmux -V
```

### Issue: Labels not persisting
```bash
# Check permissions
ls -la ~/.config/ts/state/

# Check JSON syntax
jq . ~/.config/ts/state/session_labels.json
```

## 📚 Advanced Usage

### Custom Hook for Auto-Deployment

```bash
# ~/.config/ts/hooks/post_create_blacklist.sh
#!/bin/bash
session_name="$1"
session_path="$2"

if [[ "$session_name" == "blacklist" ]]; then
    # Start dev server
    ts-bg dev blacklist

    # Start test watcher
    ts-bg test blacklist 'npm test -- --watch'

    # Monitor logs
    ts-bg logs blacklist ./logs/app.log
fi
```

### Plugin: Docker Status

```bash
# ~/.config/ts/plugins/docker-status.sh
#!/bin/bash

show_docker_status() {
    local session_name="$1"
    local containers=$(docker ps --filter "name=$session_name" --format "{{.Names}}" | wc -l)

    if [[ $containers -gt 0 ]]; then
        echo "🐳 Docker containers: $containers"
    fi
}
```

## 📊 Metrics & Monitoring

Key metrics tracked:
- Session creation/destruction rate
- Session lifetime
- Background task uptime
- Label usage distribution
- Command execution duration

View in Grafana:
```logql
# Session creation rate
rate({job="ts-command", command="create"}[5m])

# Average session lifetime
avg_over_time({job="ts-command"} | json | duration_ms > 0 [1h])

# Most used labels
topk(10, count by (label) ({job="ts-command"} | json))
```

## 🚀 Future Enhancements

Planned features:
- [ ] Web UI for session management
- [ ] Real-time session activity dashboard
- [ ] Auto-scaling for resource-intensive tasks
- [ ] Integration with CI/CD pipelines
- [ ] Cloud backup/restore for sessions
- [ ] Multi-host session orchestration

## 📝 License

Part of the tmux project - internal use.

## 🤝 Contributing

Located at: `/home/jclee/app/tmux/`

Key files:
- `ts-unified.sh` - Main command
- `ts-bg-manager.sh` - Background task manager
- `migrate-ts-config.sh` - Migration tool
- `install-ts-unified.sh` - Installation script

## 🔗 Related Tools

- `cc` - Claude Code unified command
- `sq` - Session quick switcher
- `tmux` - Terminal multiplexer
- Grafana - Observability platform

---

**TS Unified v3.0.0** - Constitutional Compliance: v11.0
**Grafana Integration**: Enabled
**Last Updated**: 2025-10-01
