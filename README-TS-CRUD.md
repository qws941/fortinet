# TS CRUD - Complete CRUD Operations for Tmux Session Manager

## Overview

`ts-crud` provides full CRUD (Create, Read, Update, Delete) operations for managing tmux sessions with metadata, JSON database, and Grafana telemetry integration.

## Installation

```bash
./install-ts-crud.sh
```

The command will be installed as `ts-crud` in `/home/jclee/.claude/bin/`

## Features

- ✅ **Full CRUD Operations** - Create, Read, Update, Delete sessions
- ✅ **JSON Database** - Persistent metadata storage
- ✅ **Rich Metadata** - Name, path, description, tags, timestamps
- ✅ **Search & Filter** - Search by any field, filter by tags
- ✅ **Auto-Sync** - Sync database with actual tmux sessions
- ✅ **Grafana Telemetry** - All operations logged to Grafana Loki
- ✅ **Socket-Based** - Isolated tmux sessions
- ✅ **Constitutional Compliance** - v11.0 compliant

## CRUD Operations

### CREATE - Create New Session

```bash
# Basic creation
ts-crud create myproject

# Create with path
ts-crud create myproject /home/user/myproject

# Create with full metadata
ts-crud create myproject /home/user/myproject "My awesome project" "dev,web"

# Aliases
ts-crud c myproject
```

**Features:**
- Auto-creates directory if not exists
- Creates tmux session with socket isolation
- Saves metadata to JSON database
- Logs to Grafana
- Prompts to attach after creation

### READ - Read Session Information

```bash
# Pretty format (default)
ts-crud read myproject

# JSON format
ts-crud read myproject json

# Aliases
ts-crud r myproject
ts-crud show myproject
ts-crud info myproject
```

**Output includes:**
- Name, path, description, tags
- Status (active/inactive)
- Created/updated timestamps
- Tmux session info (windows, attached state)
- Current command and PID

### UPDATE - Update Session Metadata

```bash
# Update path
ts-crud update myproject --path /new/path

# Update description
ts-crud update myproject --description "Updated description"

# Update tags
ts-crud update myproject --tags "prod,api,critical"

# Update status
ts-crud update myproject --status inactive

# Multiple updates
ts-crud update myproject --path /new/path --tags "prod,api" --description "Production API"

# Aliases
ts-crud u myproject
ts-crud edit myproject
```

**Available options:**
- `--path <path>` - Update working directory
- `--description <desc>` - Update description
- `--tags <tags>` - Update comma-separated tags
- `--status <status>` - Update status (active/inactive)

### DELETE - Delete Session

```bash
# Delete with confirmation
ts-crud delete myproject

# Force delete (no confirmation)
ts-crud delete myproject --force
ts-crud delete myproject -f

# Aliases
ts-crud d myproject
ts-crud rm myproject
ts-crud remove myproject
```

**Behavior:**
- Prompts for confirmation (unless --force)
- Kills active tmux session
- Removes socket file
- Removes from database
- Logs to Grafana

## Additional Commands

### LIST - List All Sessions

```bash
# Pretty format (default)
ts-crud list

# JSON format
ts-crud list json

# Filter by tag
ts-crud list pretty dev
ts-crud list json prod

# Aliases
ts-crud ls
ts-crud l
```

### ATTACH - Attach to Session

```bash
ts-crud attach myproject

# Aliases
ts-crud a myproject
```

**Features:**
- Detects if tmux session is inactive
- Offers to recreate session
- Opens in new window if already in tmux

### SEARCH - Search Sessions

```bash
# Search all fields
ts-crud search myproject

# Search specific field
ts-crud search "dev" tags
ts-crud search "/home/user" path
ts-crud search "project" name
ts-crud search "api" description

# Aliases
ts-crud find myproject
ts-crud s myproject
```

**Available fields:**
- `name` - Search by session name
- `path` - Search by working directory
- `tags` - Search by tags
- `description` - Search by description
- `all` - Search all fields (default)

### SYNC - Sync Database with Tmux

```bash
ts-crud sync
```

**Operations:**
- Updates status for all sessions
- Cleans dead socket files
- Updates timestamps
- Logs sync results

## Database Structure

Location: `~/.config/ts/sessions.db`

```json
{
  "sessions": [
    {
      "name": "myproject",
      "path": "/home/user/myproject",
      "description": "My awesome project",
      "tags": "dev,web",
      "created_at": "2025-10-01T10:30:00+00:00",
      "updated_at": "2025-10-01T12:45:00+00:00",
      "socket": "/home/jclee/.tmux/sockets/myproject",
      "status": "active"
    }
  ],
  "version": "1.0.0",
  "last_updated": "2025-10-01T12:45:00+00:00"
}
```

## Grafana Integration

All operations are logged to Grafana Loki with:

**Labels:**
- `job`: "ts-crud"
- `operation`: create/read/update/delete/list/attach/search/sync
- `session`: session name
- `status`: success/error/cancelled
- `user`: current user
- `host`: hostname

**Log data:**
```json
{
  "operation": "create",
  "session": "myproject",
  "status": "success",
  "details": "path:/home/user/myproject"
}
```

## Configuration

- **Database**: `~/.config/ts/sessions.db`
- **Sockets**: `/home/jclee/.tmux/sockets/`
- **Config**: `~/.config/ts/`
- **Grafana**: `https://grafana.jclee.me/loki/api/v1/push`

## Examples

### Complete Workflow

```bash
# 1. Create a new project session
ts-crud create webapp /home/user/webapp "Web application" "dev,react,api"

# 2. Attach to it
ts-crud attach webapp

# ... work on project ...

# 3. Update metadata
ts-crud update webapp --tags "dev,react,api,production" --status active

# 4. List all sessions
ts-crud list

# 5. Search for production sessions
ts-crud search "production" tags

# 6. Read detailed info
ts-crud read webapp

# 7. Sync database
ts-crud sync

# 8. Delete when done
ts-crud delete webapp
```

### Managing Multiple Projects

```bash
# Create multiple project sessions
ts-crud create frontend /home/user/frontend "Frontend app" "dev,react"
ts-crud create backend /home/user/backend "Backend API" "dev,nodejs,api"
ts-crud create database /home/user/database "Database work" "dev,postgres"

# List all
ts-crud list

# Filter by tag
ts-crud list pretty dev

# Search
ts-crud search "api" tags

# Update all to production
ts-crud update frontend --tags "prod,react"
ts-crud update backend --tags "prod,nodejs,api"
```

## Command Aliases

All commands support short aliases:

| Command | Aliases |
|---------|---------|
| create  | c |
| read    | r, show, info |
| update  | u, edit |
| delete  | d, rm, remove |
| list    | ls, l |
| attach  | a |
| search  | find, s |

## Error Handling

All errors are:
- Displayed to user with clear messages
- Logged to Grafana
- Return appropriate exit codes

**Common errors:**
- Invalid session name (spaces, slashes, colons)
- Session already exists (on create)
- Session not found (on read/update/delete)
- Path does not exist (offers to create)
- Tmux session inactive (offers to recreate)

## Integration with Existing ts Command

`ts-crud` is designed to work alongside the existing `ts` command system. It provides enhanced CRUD operations while maintaining compatibility.

**Use `ts` for:**
- Quick session creation/attach
- Background tasks
- IPC communication

**Use `ts-crud` for:**
- Full metadata management
- Searching and filtering
- Database operations
- Detailed session info

## Constitutional Compliance

`ts-crud` follows CLAUDE.md v11.0:

- ✅ All operations logged to Grafana
- ✅ JSON-based data structure
- ✅ Socket-based session isolation
- ✅ Environmental awareness
- ✅ Error handling and recovery
- ✅ User confirmation for destructive operations

## Version

**Version:** 1.0.0-crud
**Build Date:** 2025-10-01
**Constitutional Compliance:** v11.0
