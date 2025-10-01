#!/bin/bash
# TS Squad Installation Script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       TS Squad Installation${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo ""

# 1. 필수 도구 확인
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

MISSING_DEPS=()

if ! command -v tmux &> /dev/null; then
    MISSING_DEPS+=("tmux")
fi

if ! command -v git &> /dev/null; then
    MISSING_DEPS+=("git")
fi

if ! command -v jq &> /dev/null; then
    MISSING_DEPS+=("jq")
fi

if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${RED}✗ Missing dependencies: ${MISSING_DEPS[*]}${NC}"
    echo -e "${YELLOW}Install with:${NC}"
    echo -e "  ${GREEN}sudo apt install tmux git jq python3 python3-pip${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites found${NC}"

# 2. Python 패키지 확인
echo -e "${BLUE}🐍 Checking Python packages...${NC}"

if ! python3 -c "import requests" 2>/dev/null; then
    echo -e "${YELLOW}Installing requests...${NC}"
    pip3 install --user requests
fi

echo -e "${GREEN}✓ Python packages ready${NC}"

# 3. 디렉토리 구조 생성
echo -e "${BLUE}📂 Creating directory structure...${NC}"

mkdir -p ~/.config/ts
mkdir -p ~/.tmux/sockets
mkdir -p ~/.ts-worktrees

echo -e "${GREEN}✓ Directories created${NC}"

# 4. Agent Registry 초기화
echo -e "${BLUE}📝 Initializing agent registry...${NC}"

AGENT_REGISTRY="$HOME/.config/ts/agents.json"

if [[ ! -f "$AGENT_REGISTRY" ]]; then
    cat > "$AGENT_REGISTRY" << 'EOF'
{
  "agents": {},
  "active_count": 0,
  "max_agents": 10,
  "created_at": "",
  "last_updated": ""
}
EOF
    echo -e "${GREEN}✓ Agent registry created${NC}"
else
    echo -e "${YELLOW}⚠ Agent registry already exists${NC}"
fi

# 5. 스크립트 설치
echo -e "${BLUE}🔧 Installing scripts...${NC}"

INSTALL_DIR="/usr/local/bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ts-squad 명령어 설치
if [[ -f "$SCRIPT_DIR/ts-squad-integration.sh" ]]; then
    sudo cp "$SCRIPT_DIR/ts-squad-integration.sh" "$INSTALL_DIR/ts-squad"
    sudo chmod +x "$INSTALL_DIR/ts-squad"
    echo -e "${GREEN}✓ ts-squad installed to $INSTALL_DIR/ts-squad${NC}"
else
    echo -e "${RED}✗ ts-squad-integration.sh not found${NC}"
    exit 1
fi

# 모니터링 스크립트 설치
if [[ -f "$SCRIPT_DIR/ts-squad-monitor.py" ]]; then
    sudo cp "$SCRIPT_DIR/ts-squad-monitor.py" "$INSTALL_DIR/ts-squad-monitor"
    sudo chmod +x "$INSTALL_DIR/ts-squad-monitor"
    echo -e "${GREEN}✓ ts-squad-monitor installed${NC}"
fi

# 6. 기존 ts 명령어 확인 및 통합
echo -e "${BLUE}🔗 Integrating with existing ts command...${NC}"

if command -v ts &> /dev/null; then
    TS_PATH=$(which ts)
    echo -e "${YELLOW}Found existing ts at: $TS_PATH${NC}"

    # Backup
    if [[ ! -f "$TS_PATH.backup" ]]; then
        sudo cp "$TS_PATH" "$TS_PATH.backup"
        echo -e "${GREEN}✓ Backed up to $TS_PATH.backup${NC}"
    fi

    # ts 명령어에 squad 서브커맨드 추가 여부 확인
    if grep -q "squad" "$TS_PATH" 2>/dev/null; then
        echo -e "${YELLOW}⚠ ts command already has squad integration${NC}"
    else
        echo -e "${CYAN}To integrate squad into ts command, add this to your ts script:${NC}"
        cat << 'EOF'

# TS Squad Integration
if [[ "$1" == "squad" ]]; then
    shift
    exec /usr/local/bin/ts-squad "$@"
fi
EOF
    fi
else
    echo -e "${YELLOW}⚠ ts command not found, creating standalone ts-squad command${NC}"
fi

# 7. Systemd 서비스 생성 (선택)
echo -e "${BLUE}⚙️  Creating systemd service for monitoring...${NC}"

cat > /tmp/ts-squad-monitor.service << EOF
[Unit]
Description=TS Squad Monitoring Service
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/ts-squad-monitor continuous 30
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

if [[ -d /etc/systemd/system ]]; then
    sudo mv /tmp/ts-squad-monitor.service /etc/systemd/system/
    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ Systemd service created${NC}"
    echo -e "${CYAN}Start with: sudo systemctl start ts-squad-monitor${NC}"
    echo -e "${CYAN}Enable on boot: sudo systemctl enable ts-squad-monitor${NC}"
else
    echo -e "${YELLOW}⚠ Systemd not available, run monitor manually${NC}"
fi

# 8. 설치 완료
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}       ✅ TS Squad Installation Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo -e "  ${GREEN}ts-squad spawn${NC} my-task feature/my-branch 'Task description'"
echo -e "  ${GREEN}ts-squad list${NC}"
echo -e "  ${GREEN}ts-squad attach${NC} agent-my-task"
echo -e "  ${GREEN}ts-squad dashboard${NC}"
echo ""
echo -e "${CYAN}Monitoring:${NC}"
echo -e "  ${GREEN}ts-squad-monitor${NC}                # Run once"
echo -e "  ${GREEN}ts-squad-monitor continuous 30${NC}  # Run every 30s"
echo -e "  ${GREEN}sudo systemctl start ts-squad-monitor${NC}  # Start as service"
echo ""
echo -e "${CYAN}Documentation:${NC}"
echo -e "  ${GREEN}ts-squad help${NC}"
echo ""
echo -e "${BLUE}Happy multi-agent coding! 🚀${NC}"
echo ""
