#!/bin/bash
# TS Master - Automated Backup Script
# Version: 4.0.0-master
# Created: 2025-10-01

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
BACKUP_ROOT="/home/jclee/app/tmux/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}     TS Master - Automated Backup System${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo ""

# Backup configuration
echo -e "${YELLOW}[1/5]${NC} Backing up configuration..."
if [[ -d /home/jclee/.config/ts ]]; then
    cp -r /home/jclee/.config/ts "$BACKUP_DIR/config"
    echo -e "${GREEN}✓${NC} Configuration backed up"
else
    echo -e "${YELLOW}⚠${NC} Configuration directory not found"
fi

# Backup socket directory metadata
echo -e "${YELLOW}[2/5]${NC} Backing up socket metadata..."
if [[ -d /home/jclee/.tmux/sockets ]]; then
    ls -la /home/jclee/.tmux/sockets > "$BACKUP_DIR/sockets-metadata.txt"
    echo -e "${GREEN}✓${NC} Socket metadata saved"
else
    echo -e "${YELLOW}⚠${NC} Socket directory not found"
fi

# Backup master script
echo -e "${YELLOW}[3/5]${NC} Backing up master script..."
cp /home/jclee/app/tmux/ts.sh "$BACKUP_DIR/ts.sh"
echo -e "${GREEN}✓${NC} Master script backed up"

# Backup system deployments
echo -e "${YELLOW}[4/5]${NC} Backing up system deployments..."
cp /usr/local/bin/ts "$BACKUP_DIR/ts-system"
cp /home/jclee/.local/bin/ts-advanced "$BACKUP_DIR/ts-local"
echo -e "${GREEN}✓${NC} System deployments backed up"

# Backup documentation
echo -e "${YELLOW}[5/5]${NC} Backing up documentation..."
cp /home/jclee/app/tmux/README-TS-MASTER.md "$BACKUP_DIR/"
cp /home/jclee/app/tmux/ISSUES-RESOLVED.md "$BACKUP_DIR/"
cp /home/jclee/app/tmux/test-ts-master.sh "$BACKUP_DIR/"
cp /home/jclee/app/tmux/quick-test.sh "$BACKUP_DIR/"
echo -e "${GREEN}✓${NC} Documentation backed up"

# Create manifest
echo -e "${YELLOW}Creating backup manifest...${NC}"
cat > "$BACKUP_DIR/MANIFEST.txt" <<EOF
TS Master Backup
================

Timestamp: $TIMESTAMP
Date: $(date)
User: $(whoami)
Hostname: $(hostname)

Contents:
---------
- config/                   : TS configuration directory
- sockets-metadata.txt      : Socket directory listing
- ts.sh                     : Master script source
- ts-system                 : System deployment (/usr/local/bin/ts)
- ts-local                  : Local deployment (~/.local/bin/ts-advanced)
- README-TS-MASTER.md       : User documentation
- ISSUES-RESOLVED.md        : Issue tracking document
- test-ts-master.sh         : Comprehensive test suite
- quick-test.sh             : Quick validation script

System Info:
------------
TS Version: $(grep 'readonly TS_VERSION=' /home/jclee/app/tmux/ts.sh | cut -d'"' -f2)
Build Date: $(grep 'readonly TS_BUILD_DATE=' /home/jclee/app/tmux/ts.sh | cut -d'"' -f2)
Active Sessions: $(/usr/local/bin/ts list 2>/dev/null | wc -l)
EOF

echo -e "${GREEN}✓${NC} Manifest created"

# Create compressed archive
echo ""
echo -e "${YELLOW}Creating compressed archive...${NC}"
cd "$BACKUP_ROOT"
tar -czf "ts-backup-$TIMESTAMP.tar.gz" "$TIMESTAMP"
ARCHIVE_SIZE=$(du -h "ts-backup-$TIMESTAMP.tar.gz" | cut -f1)

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Backup completed successfully!${NC}"
echo ""
echo -e "Backup Location:"
echo -e "  Directory: ${CYAN}$BACKUP_DIR${NC}"
echo -e "  Archive:   ${CYAN}$BACKUP_ROOT/ts-backup-$TIMESTAMP.tar.gz${NC}"
echo -e "  Size:      ${CYAN}$ARCHIVE_SIZE${NC}"
echo ""
echo -e "Restore Command:"
echo -e "  ${YELLOW}tar -xzf $BACKUP_ROOT/ts-backup-$TIMESTAMP.tar.gz -C $BACKUP_ROOT${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"

# Cleanup old backups (keep last 10)
BACKUP_COUNT=$(ls -1 "$BACKUP_ROOT"/ts-backup-*.tar.gz 2>/dev/null | wc -l)
if [[ $BACKUP_COUNT -gt 10 ]]; then
    echo ""
    echo -e "${YELLOW}Cleaning up old backups (keeping last 10)...${NC}"
    ls -1t "$BACKUP_ROOT"/ts-backup-*.tar.gz | tail -n +11 | xargs rm -f
    echo -e "${GREEN}✓${NC} Cleanup completed"
fi

# Log to Grafana
if command -v curl &> /dev/null; then
    GRAFANA_LOKI_URL="${GRAFANA_LOKI_URL:-https://grafana.jclee.me/loki/api/v1/push}"
    LOG_MESSAGE="TS backup created: $TIMESTAMP, size: $ARCHIVE_SIZE"

    curl -s -X POST "$GRAFANA_LOKI_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"streams\": [{
                \"stream\": {
                    \"job\": \"ts-backup\",
                    \"host\": \"$(hostname)\",
                    \"user\": \"$(whoami)\"
                },
                \"values\": [[\"$(date +%s)000000000\", \"$LOG_MESSAGE\"]]
            }]
        }" 2>/dev/null || true
fi

exit 0
