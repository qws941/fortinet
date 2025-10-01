# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is an advanced tmux session management system with Grafana monitoring integration and AI-powered analytics agents. The codebase implements a custom `ts` command system for managing tmux sessions with automatic project registration, session persistence, and comprehensive monitoring capabilities.

## Key Commands

### Building and Running

```bash
# TypeScript Validation Module
cd validate/
npm install          # Install dependencies
npm run build        # Compile TypeScript
npm run dev          # Run in development mode
npm run watch        # Watch mode for development

# Docker Services
docker-compose up -d                          # Main services (Grafana, Prometheus, PostgreSQL)
docker-compose -f docker-compose-agents.yml up -d       # Monitoring agents
docker-compose -f docker-compose-claude-agents.yml up -d # Claude AI agents

# Install ts command system
./install-advanced-ts.sh    # Install enhanced ts command
./add-commands-to-ts.sh      # Add custom commands to ts

# Project Discovery
ts discover          # Interactive project discovery and registration
ts scan              # Alias for 'ts discover'
```

### Testing

```bash
# Test agent systems
./test-agent-system.py         # Test agent communication
./test-concurrent-processing.py # Test concurrent processing
./test-session-conflicts.sh     # Test tmux session conflicts
./verify-ts-behavior.sh         # Verify ts command behavior

# Python files can be run directly (they're executable)
./intelligent-alert-manager.py
./predictive-analytics.py
```

## Architecture

### Core Components

1. **TS Command System** (`/usr/local/bin/ts`, `ts-crud.sh`, `ts-discover-interactive.sh`)
   - Custom tmux session manager with project registration
   - Socket-based session management in `/home/jclee/.tmux/sockets`
   - Configuration stored in `~/.config/ts/`
   - Auto-detection of existing sessions
   - Nested tmux support (opens in new windows when inside tmux)
   - **Interactive Project Discovery**: Automatically scan `/app` and `/synology` directories
   - **Smart Type Detection**: Recognizes Node.js, Go, Python, Rust, Docker projects
   - **Database-backed**: JSON database with full CRUD operations
   - **Grafana Integration**: All discovery operations logged to Loki

2. **Monitoring Stack**
   - **Grafana**: Main observability platform (port 3000)
   - **Prometheus**: Metrics collection (port 9090)
   - **Loki**: Log aggregation (port 3100)
   - **PostgreSQL**: Grafana backend storage
   - All services defined in `docker-compose.yml`

3. **AI Agent System**
   - **Orchestrator** (`claude-agent-orchestrator.py`): Manages worker agents
   - **Workers** (`claude-agent-worker.py`): Process tasks concurrently
   - **Alert Manager** (`intelligent-alert-manager.py`): ML-powered alert correlation
   - **Analytics** (`predictive-analytics.py`): Predictive failure detection
   - **Log Scanner** (`log-scanner-agent.py`): Pattern detection in logs
   - **Metric Labeling** (`metric-labeling-engine.py`): Auto-labeling for metrics

### Data Flow

1. Tmux sessions → Socket files → TS command interface
2. Application logs → Promtail → Loki → Grafana
3. Metrics → Prometheus → Grafana dashboards
4. Alerts → Alert Manager → AI correlation → Action recommendations

## Session Management Protocol

The ts command system uses socket-based isolation where each session has its own socket in `/home/jclee/.tmux/sockets/`. This prevents session conflicts and allows multiple concurrent sessions. The system automatically:
- Detects if you're already in a tmux session
- Creates new windows instead of nesting sessions
- Cleans up dead sockets
- Maintains session registry with metadata

## Configuration Files

- `~/.config/ts/sessions.db`: JSON database with all session metadata (CRUD operations)
- `~/.config/ts/config.json`: TS master configuration
- `~/.tmux/sockets/`: Socket files for each tmux session
- `agent-config.yml`: Agent system configuration
- `docker-compose*.yml`: Service definitions

## TS Commands Reference

### Session Management
- `ts` - Resume last session or list all sessions
- `ts list` - List all active sessions
- `ts <name> [path]` - Create/attach to session
- `ts kill <name>` - Kill specific session
- `ts clean` - Clean all sessions

### Project Discovery (NEW)
- `ts discover` - Interactive project discovery and registration
- `ts scan` - Alias for 'ts discover'

### CRUD Operations
- `ts create <name> [path] [description] [tags]` - Create new session with metadata
- `ts read <name> [format]` - Read session information (format: pretty|json)
- `ts update <name> [--path|--description|--tags|--status]` - Update session metadata
- `ts delete <name> [--force]` - Delete session
- `ts attach <name>` - Attach to session
- `ts search <query> [field]` - Search sessions
- `ts sync` - Sync database with actual tmux sessions

### Background Tasks
- `ts bg start <name> <cmd>` - Start background task
- `ts bg list` - List background tasks
- `ts bg stop <name>` - Stop background task
- `ts bg attach <name>` - Attach to background task

### IPC
- `ts ipc send <session> <msg>` - Send message to session
- `ts ipc broadcast <msg>` - Broadcast to all sessions

## Important Notes

- The system uses Python 3.9 for agents (as specified in Dockerfiles)
- All Python scripts are executable and use system python3
- TypeScript validation module uses Node.js with TypeScript 5.9.2
- Grafana requires PostgreSQL for persistent storage
- Socket directory must exist before creating sessions
- The ts command automatically handles tmux nesting scenarios

## Monitoring Integration

All operations should be observable through Grafana at `http://localhost:3000`. The system follows a "if it's not in Grafana, it didn't happen" philosophy. Key dashboards monitor:
- Session health and activity
- Agent performance metrics
- Log aggregation and analysis
- Predictive analytics results
- Alert correlation patterns