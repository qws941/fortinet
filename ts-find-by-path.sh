#!/bin/bash
# Find ts session by current path

DB="/home/jclee/.config/ts/sessions.db"
CURRENT_PATH=$(pwd)

# Find matching session
MATCHED=$(jq -r --arg path "$CURRENT_PATH" '.sessions[] | select(.path == $path) | .name' "$DB" 2>/dev/null)

if [[ -n "$MATCHED" ]]; then
    echo "$MATCHED"
else
    # Try to find parent path match
    PARENT_MATCH=$(jq -r --arg path "$CURRENT_PATH" '.sessions[] | select($path | startswith(.path)) | .name' "$DB" 2>/dev/null | head -1)
    if [[ -n "$PARENT_MATCH" ]]; then
        echo "$PARENT_MATCH"
    fi
fi
