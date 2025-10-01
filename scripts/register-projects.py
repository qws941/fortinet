#!/usr/bin/env python3
"""Register all projects from /app and /synology to ts database"""

import json
import os
from pathlib import Path
from datetime import datetime

DB_PATH = Path.home() / ".config" / "ts" / "sessions.db"
SOCKET_DIR = Path.home() / ".tmux" / "sockets"
APP_DIR = Path.home() / "app"
SYNOLOGY_DIR = Path.home() / "synology"

def load_database():
    """Load existing database"""
    if DB_PATH.exists():
        with open(DB_PATH) as f:
            return json.load(f)
    return {"sessions": [], "version": "5.0.0", "last_updated": ""}

def save_database(db):
    """Save database"""
    db["last_updated"] = datetime.now().isoformat()
    with open(DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)

def session_exists(db, name):
    """Check if session exists"""
    return any(s["name"] == name for s in db["sessions"])

def is_dev_project(path):
    """Check if directory is a development project"""
    indicators = ["package.json", "tsconfig.json", "go.mod", "docker-compose.yml"]
    return any((path / ind).exists() for ind in indicators)

def add_session(db, name, path, description, tags, auto_claude):
    """Add session to database"""
    session = {
        "name": name,
        "path": str(path),
        "description": description,
        "tags": tags,
        "auto_claude": auto_claude,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "socket": str(SOCKET_DIR / name),
        "status": "active"
    }
    db["sessions"].append(session)

def main():
    print("\033[0;36mRegistering all projects...\033[0m\n")

    db = load_database()
    discovered = 0
    skipped = 0

    # Scan /app
    print("\033[0;36m📁 Scanning /home/jclee/app...\033[0m")
    if APP_DIR.exists():
        for item in sorted(APP_DIR.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                name = item.name

                if session_exists(db, name):
                    print(f"  \033[1;33m⊖\033[0m {name}")
                    skipped += 1
                    continue

                print(f"  \033[0;32m+\033[0m {name}")

                auto_claude = is_dev_project(item)
                tags = "app,dev" if auto_claude else "app"

                add_session(db, name, item, f"Project in /app", tags, auto_claude)
                discovered += 1

    print()

    # Scan /synology
    print("\033[0;36m📁 Scanning /home/jclee/synology...\033[0m")
    if SYNOLOGY_DIR.exists():
        for item in sorted(SYNOLOGY_DIR.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                name = item.name  # No prefix - direct mapping

                if session_exists(db, name):
                    print(f"  \033[1;33m⊖\033[0m {name}")
                    skipped += 1
                    continue

                print(f"  \033[0;32m+\033[0m {name}")

                auto_claude = is_dev_project(item)
                tags = "synology,dev" if auto_claude else "synology"

                add_session(db, name, item, f"Project in /synology", tags, auto_claude)
                discovered += 1

    # Save database
    save_database(db)

    print()
    print("\033[0;32m✓ Registration complete!\033[0m")
    print(f"\033[0;36m  Discovered: {discovered} new session(s)\033[0m")
    print(f"\033[0;36m  Skipped: {skipped} existing session(s)\033[0m")
    print()
    print("\033[0;36mUse 'ts list' to see all sessions\033[0m")

if __name__ == "__main__":
    main()
