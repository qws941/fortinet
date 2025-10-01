#!/bin/bash
# Create sessions manually

echo "Creating sessions..."

# xwiki session
echo "Creating xwiki session..."
ts create xwiki /home/jclee/synology/xwiki "XWiki Documentation" "synology,docs"

echo ""
echo "✓ Sessions created!"
echo "Use 'ts list' to see all sessions"
