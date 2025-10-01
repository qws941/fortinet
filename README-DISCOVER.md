# TS Discover - Interactive Project Discovery

## Overview

`ts discover` is an interactive project discovery and registration system for the TS (Tmux Session Manager). It automatically scans configured directories, detects project types, and allows you to selectively register projects to the ts database.

## Features

- **Automatic Project Detection**: Scans `/home/jclee/app` and `/home/jclee/synology` for projects
- **Intelligent Type Detection**: Recognizes Node.js, Go, Python, Rust, Docker projects
- **Smart Tagging**: Automatically tags projects based on detected files
- **Interactive Selection**: Choose which projects to register
- **Batch Operations**: Register all, specific ranges, or individual projects
- **Already Registered Detection**: Skips projects that are already in the database
- **Grafana Telemetry**: Logs all discovery operations to Grafana Loki

## Project Type Detection

The system detects project types based on marker files:

| Project Type | Marker Files | Auto Tags | Claude Auto-Start |
|--------------|--------------|-----------|-------------------|
| Node.js | `package.json` | `dev,node` | ✓ |
| TypeScript | `tsconfig.json` | `dev,node,typescript` | ✓ |
| Go | `go.mod` | `dev,go` | ✓ |
| Python | `requirements.txt`, `pyproject.toml`, `setup.py` | `dev,python` | ✓ |
| Rust | `Cargo.toml` | `dev,rust` | ✓ |
| Docker | `docker-compose.yml`, `Dockerfile` | `docker` | ✓ |
| Git | `.git/` directory | `git` | ✗ |
| Grafana | `grafana.ini` or directory name contains "grafana" | `monitoring,grafana` | ✗ |

## Usage

### Basic Discovery

```bash
# Interactive project discovery
ts discover

# Alternative command
ts scan
```

### Selection Options

When projects are discovered, you'll see:

```
═══════════════════════════════════════════════════
       Discovered Projects
═══════════════════════════════════════════════════

  NUM  NAME                 TYPE       TAGS
  ────────────────────────────────────────────────────────────
  1    demo-node            [node]     dev,node,app
  2    demo-go              [go]       dev,go,app
  3    demo-docker          [docker]   docker,app

Selection Options:
  1-3      Register specific project(s) (e.g., 1,3,5-7)
  all      Register all projects
  skip     Skip registration

Your choice: _
```

### Selection Examples

- **Register all**: `all` or `a`
- **Single project**: `1`
- **Multiple projects**: `1,3,5`
- **Range**: `1-3`
- **Mixed**: `1,3,5-7,10`
- **Skip**: `skip`, `s`, `n`, or `no`

## Integration

### With TS Master

The discover functionality is integrated into the main `ts` command:

```bash
ts discover    # Run discovery
ts list        # See registered sessions
ts attach demo-node  # Attach to discovered project
```

### With TS CRUD

All discovered projects are automatically added to the ts database with full CRUD support:

```bash
ts read demo-node         # View project details
ts update demo-node --tags "dev,node,production"
ts delete demo-node       # Remove from database
```

## Scan Paths

Default scan paths:
- `/home/jclee/app` - Main application directory
- `/home/jclee/synology` - Synology NAS mounted directory

Projects in `/home/jclee/synology` are automatically tagged with `synology`.
Projects in `/home/jclee/app` are tagged with `app`.

## Database Structure

Each discovered project is stored with:

```json
{
  "name": "demo-node",
  "path": "/home/jclee/app/demo-node",
  "description": "Node.js project in /app",
  "tags": "dev,node,app",
  "auto_claude": true,
  "created_at": "2025-10-01T06:30:00Z",
  "updated_at": "2025-10-01T06:30:00Z",
  "socket": "/home/jclee/.tmux/sockets/demo-node",
  "status": "active"
}
```

## Grafana Telemetry

All discovery operations are logged to Grafana Loki with:

- **Job**: `ts-discover`
- **Labels**: `operation`, `status`, `user`, `host`
- **Operations**: `discover`, `register`, `selection`
- **Statuses**: `running`, `success`, `cancelled`

Example queries:

```logql
# All discovery operations
{job="ts-discover"}

# Successful registrations
{job="ts-discover", operation="register", status="success"}

# User selections
{job="ts-discover", operation="selection"}
```

## Files

- **Main Script**: `/home/jclee/app/tmux/ts-discover-interactive.sh`
- **Integration**: `/usr/local/bin/ts` (discover/scan command)
- **Database**: `~/.config/ts/sessions.db`
- **Test Scripts**:
  - `/home/jclee/app/tmux/test-discover.sh` - Setup verification
  - `/home/jclee/app/tmux/test-discover-demo.sh` - Demo with test projects

## Examples

### Discover and Register All Projects

```bash
$ ts discover
═══════════════════════════════════════════════════
   TS Discover - Interactive Project Discovery
═══════════════════════════════════════════════════

📁 Scanning: /home/jclee/app

  + blacklist [node] dev,node,typescript,app
  + grafana [docker] docker,monitoring,grafana,app
  + mcp [node] dev,node,app

📁 Scanning: /home/jclee/synology

  + backup [unknown] synology
  + scripts [git] git,synology

═══════════════════════════════════════════════════

       Discovered Projects

  NUM  NAME                 TYPE       TAGS
  ────────────────────────────────────────────────────
  1    blacklist            [node]     dev,node,typescript,app
  2    grafana              [docker]   docker,monitoring,grafana,app
  3    mcp                  [node]     dev,node,app
  4    backup               [unknown]  synology
  5    scripts              [git]      git,synology

Your choice: all

Registering all projects...

  ✓ Registered: blacklist
  ✓ Registered: grafana
  ✓ Registered: mcp
  ✓ Registered: backup
  ✓ Registered: scripts

✓ All projects registered

Use 'ts list' to see all registered sessions
```

### Selective Registration

```bash
Your choice: 1,3,5

Registering selected projects...

  ✓ Registered: blacklist
  ✓ Registered: mcp
  ✓ Registered: scripts

✓ Registered 3 project(s)
```

## Benefits

1. **No Manual Registration**: Automatically discover all projects in configured directories
2. **Smart Defaults**: Intelligent project type detection and tagging
3. **Flexible Selection**: Choose exactly which projects to register
4. **Skip Already Registered**: Won't duplicate existing sessions
5. **Full Visibility**: See all discovered projects before registering
6. **Grafana Integration**: Complete observability of discovery operations

## Constitutional Compliance

This feature follows CLAUDE.md v11.0:
- ✓ All operations logged to Grafana Loki
- ✓ Environmental awareness via scan paths
- ✓ User intent analysis via interactive selection
- ✓ No local monitoring endpoints
- ✓ Constitutional audit compliance

## Future Enhancements

- [ ] Custom scan paths via configuration
- [ ] Project filtering by type/tags
- [ ] Batch update of existing projects
- [ ] Auto-discover on startup option
- [ ] Integration with Claude Code project templates
- [ ] Smart project recommendations based on usage patterns
