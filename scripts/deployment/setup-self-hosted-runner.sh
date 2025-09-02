#!/bin/bash
# =============================================================================
# GitHub Self-Hosted Runner Setup Script
# Automates the installation and configuration of GitHub Actions runner
# =============================================================================

set -e

# Configuration
RUNNER_VERSION="${RUNNER_VERSION:-2.319.1}"
RUNNER_NAME="${RUNNER_NAME:-fortinet-runner-$(hostname)}"
RUNNER_WORKDIR="${RUNNER_WORKDIR:-/home/runner/actions-runner}"
RUNNER_USER="${RUNNER_USER:-runner}"
GITHUB_ORG="${GITHUB_ORG:-jclee}"
GITHUB_REPO="${GITHUB_REPO:-fortinet}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        log_warning "Running as root. Creating dedicated runner user..."
        CREATE_USER=true
    fi
    
    # Check required tools
    local required_tools=("curl" "tar" "git" "docker")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed"
            exit 1
        fi
    done
    
    log_success "All prerequisites met"
}

create_runner_user() {
    if [ "$CREATE_USER" = true ]; then
        log_info "Creating runner user..."
        
        # Create user if doesn't exist
        if ! id "$RUNNER_USER" &>/dev/null; then
            useradd -m -s /bin/bash "$RUNNER_USER"
            log_success "User $RUNNER_USER created"
        else
            log_info "User $RUNNER_USER already exists"
        fi
        
        # Add to docker group
        usermod -aG docker "$RUNNER_USER" 2>/dev/null || true
        
        # Create runner directory
        mkdir -p "$RUNNER_WORKDIR"
        chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_WORKDIR"
    fi
}

download_runner() {
    log_info "Downloading GitHub Actions Runner v${RUNNER_VERSION}..."
    
    cd "$RUNNER_WORKDIR"
    
    # Determine architecture
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)
            RUNNER_ARCH="x64"
            ;;
        aarch64|arm64)
            RUNNER_ARCH="arm64"
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
    
    # Download runner
    RUNNER_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
    
    if [ ! -f "actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz" ]; then
        curl -L "$RUNNER_URL" -o "actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
        tar xzf "actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
        rm "actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz"
        log_success "Runner downloaded and extracted"
    else
        log_info "Runner already downloaded"
    fi
}

configure_runner() {
    log_info "Configuring GitHub Actions Runner..."
    
    # Check if runner is already configured
    if [ -f "$RUNNER_WORKDIR/.runner" ]; then
        log_warning "Runner already configured. Skipping configuration."
        return
    fi
    
    # Get registration token
    if [ -z "$RUNNER_TOKEN" ]; then
        log_error "RUNNER_TOKEN environment variable not set"
        echo ""
        echo "To get a runner token:"
        echo "1. Go to https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/actions/runners/new"
        echo "2. Copy the token from the configuration command"
        echo "3. Run: export RUNNER_TOKEN=<your-token>"
        echo "4. Re-run this script"
        exit 1
    fi
    
    cd "$RUNNER_WORKDIR"
    
    # Configure runner
    if [ "$CREATE_USER" = true ]; then
        sudo -u "$RUNNER_USER" ./config.sh \
            --url "https://github.com/${GITHUB_ORG}/${GITHUB_REPO}" \
            --token "$RUNNER_TOKEN" \
            --name "$RUNNER_NAME" \
            --labels "self-hosted,linux,x64,docker" \
            --unattended \
            --replace
    else
        ./config.sh \
            --url "https://github.com/${GITHUB_ORG}/${GITHUB_REPO}" \
            --token "$RUNNER_TOKEN" \
            --name "$RUNNER_NAME" \
            --labels "self-hosted,linux,x64,docker" \
            --unattended \
            --replace
    fi
    
    log_success "Runner configured successfully"
}

install_dependencies() {
    log_info "Installing additional dependencies..."
    
    # Install Docker Compose if not present
    if ! command -v docker-compose &> /dev/null; then
        log_info "Installing Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
            -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        log_success "Docker Compose installed"
    fi
    
    # Install GitHub CLI if not present
    if ! command -v gh &> /dev/null; then
        log_info "Installing GitHub CLI..."
        curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
            dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
        chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | \
            tee /etc/apt/sources.list.d/github-cli.list > /dev/null
        apt update
        apt install gh -y
        log_success "GitHub CLI installed"
    fi
    
    # Install Helm if not present
    if ! command -v helm &> /dev/null; then
        log_info "Installing Helm..."
        curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3
        chmod +x get_helm.sh
        ./get_helm.sh
        rm get_helm.sh
        log_success "Helm installed"
    fi
    
    # Install Trivy for security scanning
    if ! command -v trivy &> /dev/null; then
        log_info "Installing Trivy..."
        wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | apt-key add -
        echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | \
            tee -a /etc/apt/sources.list.d/trivy.list
        apt update
        apt install trivy -y
        log_success "Trivy installed"
    fi
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/github-runner.service << EOF
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
ExecStart=$RUNNER_WORKDIR/run.sh
User=$RUNNER_USER
WorkingDirectory=$RUNNER_WORKDIR
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=5min
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable github-runner
    
    log_success "Systemd service created"
}

start_runner() {
    log_info "Starting GitHub Actions Runner..."
    
    if [ -f "/etc/systemd/system/github-runner.service" ]; then
        systemctl start github-runner
        sleep 3
        
        if systemctl is-active --quiet github-runner; then
            log_success "Runner started successfully"
            systemctl status github-runner --no-pager
        else
            log_error "Failed to start runner"
            journalctl -u github-runner -n 20 --no-pager
            exit 1
        fi
    else
        # Run interactively if no systemd
        if [ "$CREATE_USER" = true ]; then
            sudo -u "$RUNNER_USER" "$RUNNER_WORKDIR/run.sh" &
        else
            "$RUNNER_WORKDIR/run.sh" &
        fi
        log_success "Runner started in background"
    fi
}

print_summary() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}GitHub Self-Hosted Runner Setup Complete${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Runner Details:"
    echo "  Name: $RUNNER_NAME"
    echo "  Directory: $RUNNER_WORKDIR"
    echo "  User: $RUNNER_USER"
    echo "  Repository: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}"
    echo ""
    echo "Service Management:"
    echo "  Start: systemctl start github-runner"
    echo "  Stop: systemctl stop github-runner"
    echo "  Status: systemctl status github-runner"
    echo "  Logs: journalctl -u github-runner -f"
    echo ""
    echo "To view in GitHub:"
    echo "  https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/actions/runners"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo -e "${BLUE}GitHub Self-Hosted Runner Setup${NC}"
    echo "=================================="
    
    check_prerequisites
    create_runner_user
    download_runner
    configure_runner
    
    if [ "$EUID" -eq 0 ]; then
        install_dependencies
        create_systemd_service
    fi
    
    start_runner
    print_summary
}

# Run main function
main "$@"