# TS Command Quick Reference

## 🚀 Essential Commands

```bash
ts                    # Resume last session or show list
ts <name>             # Create/attach to named session
ts <name> <path>      # Create session in specific path
ts list               # List all active sessions
ts kill <name>        # Kill a session
ts resume             # Resume last session
ts help               # Show help
ts version            # Show version info
```

## 🔧 Advanced Commands

```bash
ts claude             # Attach to Claude AI session
ts claude '<cmd>'     # Send command to Claude
ts cmd <sess> '<cmd>' # Send command to any session
```

## 🛡️ Conflict Resolution

```bash
# Session manager (this tool)
ts list
/usr/local/bin/ts list
ts-session list          # With compatibility script

# Timestamp utility (moreutils)
/usr/bin/ts -r < file
ts-timestamp -r < file   # With compatibility script
```

## ⚙️ Environment Variables

```bash
export TS_CONFIG_DIR="$HOME/.config/ts"
export TS_SOCKET_DIR="$HOME/.tmux/sockets"
```

## 📋 Session Name Rules

✅ **Valid**: `myproject`, `web-app`, `dev_env`, `test123`
❌ **Invalid**: `my project`, `web/app`, `dev:env`

## 🔍 Key Features

- ✅ Automatic conflict detection with timestamp utility
- ✅ Dead socket cleanup
- ✅ Session name validation
- ✅ Path validation with fallback
- ✅ Tmux nesting prevention
- ✅ Claude AI integration
- ✅ Auto-command execution
- ✅ Last session memory

## 📂 File Locations

- **Command**: `/usr/local/bin/ts`
- **Config**: `~/.config/ts/ts-enhanced.conf`
- **Projects**: `~/.config/ts/projects.conf`
- **Sockets**: `/home/jclee/.tmux/sockets/`
- **Last session**: `~/.config/ts/last_session`

## 🧪 Testing

```bash
cd /home/jclee/app/tmux
./test-ts-stability.sh
```

## 📚 Documentation

- Full guide: `TS-COMPATIBILITY-GUIDE.md`
- Project info: `CLAUDE.md`
- Compatibility: `ts-compatibility.sh`