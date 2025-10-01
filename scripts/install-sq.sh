#!/bin/bash
# SQ (Squad) Installation Script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       SQ (Squad) Installation${NC}"
echo -e "${CYAN}       Multi-Agent Task Management${NC}"
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

# sq 명령어 설치
if [[ -f "$SCRIPT_DIR/sq" ]]; then
    sudo cp "$SCRIPT_DIR/sq" "$INSTALL_DIR/sq"
    sudo chmod +x "$INSTALL_DIR/sq"
    echo -e "${GREEN}✓ sq installed to $INSTALL_DIR/sq${NC}"
else
    echo -e "${RED}✗ sq not found${NC}"
    exit 1
fi

# ts-squad-integration.sh 설치
if [[ -f "$SCRIPT_DIR/ts-squad-integration.sh" ]]; then
    sudo cp "$SCRIPT_DIR/ts-squad-integration.sh" "$INSTALL_DIR/ts-squad-integration.sh"
    sudo chmod +x "$INSTALL_DIR/ts-squad-integration.sh"
    echo -e "${GREEN}✓ ts-squad-integration.sh installed${NC}"
fi

# 모니터링 스크립트 설치
if [[ -f "$SCRIPT_DIR/ts-squad-monitor.py" ]]; then
    sudo cp "$SCRIPT_DIR/ts-squad-monitor.py" "$INSTALL_DIR/sq-monitor"
    sudo chmod +x "$INSTALL_DIR/sq-monitor"
    echo -e "${GREEN}✓ sq-monitor installed${NC}"
fi

# 6. Systemd 서비스 생성
echo -e "${BLUE}⚙️  Creating systemd service for monitoring...${NC}"

cat > /tmp/sq-monitor.service << EOF
[Unit]
Description=SQ (Squad) Monitoring Service
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/sq-monitor continuous 30
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

if [[ -d /etc/systemd/system ]]; then
    sudo mv /tmp/sq-monitor.service /etc/systemd/system/
    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ Systemd service created${NC}"
    echo -e "${CYAN}Start with: sudo systemctl start sq-monitor${NC}"
    echo -e "${CYAN}Enable on boot: sudo systemctl enable sq-monitor${NC}"
else
    echo -e "${YELLOW}⚠ Systemd not available${NC}"
fi

# 7. Bash completion (선택)
echo -e "${BLUE}💡 Setting up bash completion...${NC}"

cat > /tmp/sq-completion.bash << 'EOF'
# SQ (Squad) bash completion

_sq_completion() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="spawn list attach checkpoint resume kill delegate dashboard init help"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
    elif [[ ${prev} == "attach" ]] || [[ ${prev} == "checkpoint" ]] || [[ ${prev} == "resume" ]] || [[ ${prev} == "kill" ]]; then
        # Agent ID completion from registry
        if [[ -f ~/.config/ts/agents.json ]]; then
            local agents=$(jq -r '.agents | keys[]' ~/.config/ts/agents.json 2>/dev/null)
            COMPREPLY=( $(compgen -W "${agents}" -- ${cur}) )
        fi
    fi

    return 0
}

complete -F _sq_completion sq
EOF

sudo mv /tmp/sq-completion.bash /etc/bash_completion.d/sq 2>/dev/null || {
    mkdir -p ~/.bash_completion.d
    mv /tmp/sq-completion.bash ~/.bash_completion.d/sq
    echo -e "${YELLOW}⚠ Installed to ~/.bash_completion.d/sq${NC}"
    echo -e "${CYAN}Add to ~/.bashrc:${NC}"
    echo -e "  source ~/.bash_completion.d/sq"
}

echo -e "${GREEN}✓ Bash completion installed${NC}"

# 8. 설치 완료
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}       ✅ SQ Installation Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo -e "  ${GREEN}sq spawn${NC} my-task feature/my-branch 'Task description'"
echo -e "  ${GREEN}sq list${NC}"
echo -e "  ${GREEN}sq attach${NC} agent-my-task"
echo -e "  ${GREEN}sq dashboard${NC}"
echo ""
echo -e "${CYAN}Monitoring:${NC}"
echo -e "  ${GREEN}sq-monitor${NC}                      # Run once"
echo -e "  ${GREEN}sq-monitor continuous 30${NC}        # Run every 30s"
echo -e "  ${GREEN}sudo systemctl start sq-monitor${NC} # Start as service"
echo ""
echo -e "${CYAN}Help:${NC}"
echo -e "  ${GREEN}sq help${NC}"
echo ""
echo -e "${BLUE}Happy multi-agent coding! 🚀${NC}"
echo ""
