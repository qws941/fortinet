# TS Command - Compatibility & Stability Guide

## Overview

The `ts` command has been stabilized to resolve conflicts with the system `ts` command from the `moreutils` package and improve overall compatibility and error handling.

## Version Information

- **Version**: 2.0.0-stable
- **Type**: Tmux Session Manager
- **Location**: `/usr/local/bin/ts`

## Conflict Resolution

### The Problem

Two different `ts` commands exist on the system:
1. `/usr/local/bin/ts` - **Tmux Session Manager** (this tool)
2. `/usr/bin/ts` - **Timestamp Utility** (from moreutils package)

### The Solution

The improved `ts` command includes **automatic conflict detection**:

```bash
# These commands are detected and redirected
ts -r          # Timestamp flag → Shows error
ts -i          # Timestamp flag → Shows error
ts '%Y-%m-%d'  # Timestamp format → Shows error
```

When timestamp-related flags are detected, the command shows:
```
⚠️  This is tmux session manager 'ts', not the timestamp utility.
Use '/usr/bin/ts' for timestamp functionality (moreutils).
For tmux session help, use: ts help
```

## Command Disambiguation

### Aliases (Recommended)

Source the compatibility script in your shell:

```bash
# Add to ~/.bashrc or ~/.zshrc
source /home/jclee/app/tmux/ts-compatibility.sh
```

This provides clear aliases:
- `ts` → Tmux session manager (default)
- `ts-session` → Explicit tmux session manager
- `ts-timestamp` → Timestamp utility (moreutils)
- `tmux-session` → Alternative alias

### Manual Usage

```bash
# For session management
/usr/local/bin/ts list

# For timestamp utility
/usr/bin/ts -r < logfile
```

## New Features

### 1. Improved Error Handling

- **Session name validation**: Prevents invalid names (spaces, slashes, colons)
- **Path validation**: Checks if directories exist before creating sessions
- **Socket cleanup**: Automatically removes dead socket files
- **Config validation**: Safely loads configuration files

### 2. Better Feedback

```bash
# Clear error messages
$ ts "invalid session"
✗ Invalid session name: 'invalid session'
Session names cannot contain spaces, slashes, or colons

# Path validation
$ ts mysession /nonexistent
⚠️  Path does not exist: /nonexistent
Using current directory instead
```

### 3. Enhanced Commands

```bash
ts version     # Show version and compatibility info
ts help        # Show usage help
ts list        # List all active sessions
ts kill <name> # Kill session with validation
```

### 4. Environment Variables

Customize behavior with environment variables:

```bash
export TS_CONFIG_DIR="$HOME/.config/ts"      # Override config location
export TS_SOCKET_DIR="$HOME/.tmux/sockets"   # Override socket location
```

## Usage Examples

### Basic Session Management

```bash
# Create or attach to session
ts myproject /path/to/project

# List all sessions
ts list
ts ls

# Kill a session
ts kill myproject

# Resume last session
ts resume
ts    # (no arguments also resumes last)
```

### Claude Integration

```bash
# Attach to Claude session
ts claude

# Send command to Claude
ts claude 'help me debug this'

# Send command to any session
ts cmd myproject 'npm test'
```

### Inside Tmux

When running `ts` inside an existing tmux session:
- Non-interactive commands work normally (list, kill, etc.)
- Session attachment opens in a **new window** (prevents nesting issues)
- Clear notification shown: "Running inside tmux - will open in new window"

## Error Handling

### Strict Mode

The command now runs with `set -euo pipefail` for better error detection.

### Validation Checks

1. **Tmux availability**: Checks if tmux is installed
2. **Directory creation**: Validates config and socket directories
3. **Session names**: Rejects invalid characters
4. **Path existence**: Verifies directories before use
5. **Socket health**: Cleans up dead sockets automatically

### Exit Codes

- `0` - Success
- `1` - General error (invalid arguments, session not found, etc.)
- `2` - Invalid session name format

## Configuration

### Config File Location

Default: `~/.config/ts/ts-enhanced.conf`

Override: Set `TS_CONFIG_DIR` environment variable

### Project Paths

Define project paths in config:

```bash
PROJECT_PATH_myproject="/home/user/projects/myproject"
PROJECT_PATH_webapp="/var/www/app"
```

### Auto Commands

Run commands automatically when creating sessions:

```bash
AUTO_CMD_webapp="npm run dev"
AUTO_CMD_monitoring="docker-compose up -d"
```

## Testing

### Stability Test Suite

Run the included test suite:

```bash
cd /home/jclee/app/tmux
./test-ts-stability.sh
```

Tests include:
- Version and help commands
- Conflict detection
- Session name validation
- Session creation and cleanup
- Socket cleanup verification
- Config directory checks

## Troubleshooting

### Problem: Command conflicts with timestamp utility

**Solution**: Use explicit paths or aliases:
```bash
/usr/local/bin/ts list      # Session manager
/usr/bin/ts -r < file        # Timestamp utility
```

### Problem: Dead sockets accumulate

**Solution**: The command now automatically cleans dead sockets on startup

### Problem: Session names with spaces fail

**Solution**: This is now validated and rejected with a clear error message. Use hyphens or underscores instead:
```bash
ts my-project    # Good
ts my_project    # Good
ts "my project"  # Bad - will be rejected
```

### Problem: Path doesn't exist

**Solution**: The command validates paths and falls back to current directory with a warning

### Problem: Running inside tmux causes nesting

**Solution**: The command automatically detects tmux and opens sessions in new windows instead of nesting

## Best Practices

1. **Use descriptive session names** without special characters
2. **Configure project paths** in the config file for quick access
3. **Set up shell aliases** using the compatibility script
4. **Run the test suite** after updates to verify stability
5. **Use environment variables** for custom configurations
6. **Check `ts version`** to verify installation

## Integration with Grafana Observability

All `ts` operations should be logged to Grafana for observability:

```bash
# Operations are logged to grafana.jclee.me/loki with labels:
# - job: "ts-command"
# - session: "<session-name>"
# - user: "$USER"
```

## Migration from Old Version

If upgrading from a previous version:

1. **Backup existing sessions**: Sessions are preserved, no migration needed
2. **Update shell config**: Source the new compatibility script
3. **Test conflict detection**: Run `ts -r` to verify
4. **Verify socket cleanup**: Old dead sockets will be cleaned automatically
5. **Review configuration**: Config format remains compatible

## Future Improvements

- [ ] JSON output mode for scripting
- [ ] Session templates
- [ ] Remote session support
- [ ] Integration with Grafana dashboards
- [ ] Session health monitoring
- [ ] Automatic session backup/restore

## Support

For issues or questions:
- Check this guide first
- Run `ts version` to verify installation
- Run `ts help` for command usage
- Check `/home/jclee/app/tmux/CLAUDE.md` for integration details