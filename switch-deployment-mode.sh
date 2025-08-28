#!/bin/bash

# =============================================================================
# FortiGate Nextrade - Deployment Mode Switcher
# Easily switch between different deployment configurations
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# Available deployment modes
MODES=(
    "default:Standard deployment with Redis"
    "dev:Development with Prometheus monitoring"
    "msa:Microservices architecture with Kong, Consul, RabbitMQ"
    "secure:Full security-hardened stack with monitoring"
    "standalone:Single container, no external dependencies"
    "verify:Version verification mode"
    "watchtower:Auto-update enabled deployment"
)

show_help() {
    echo -e "${BLUE}FortiGate Nextrade - Deployment Mode Switcher${NC}"
    echo
    echo "Usage: $0 [MODE] [OPTIONS]"
    echo
    echo "Available modes:"
    for mode in "${MODES[@]}"; do
        mode_name="${mode%%:*}"
        mode_desc="${mode#*:}"
        printf "  %-12s %s\n" "$mode_name" "$mode_desc"
    done
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -l, --list     List available deployment modes"
    echo "  -s, --status   Show current deployment mode"
    echo "  -c, --check    Validate current configuration"
    echo "  -t, --template Copy template for current mode"
    echo "  -r, --restart  Restart services after mode change"
    echo
    echo "Examples:"
    echo "  $0 dev                    # Switch to development mode"
    echo "  $0 msa --restart          # Switch to MSA mode and restart"
    echo "  $0 secure --template      # Switch to secure mode and copy template"
    echo
}

show_status() {
    if [[ ! -f "$ENV_FILE" ]]; then
        echo -e "${RED}❌ No .env file found${NC}"
        return 1
    fi
    
    current_profile=$(grep "^COMPOSE_PROFILES=" "$ENV_FILE" | cut -d'=' -f2- | sed 's/[[:space:]]*#.*//' | tr -d ' ')
    current_mode=$(grep "^APP_MODE=" "$ENV_FILE" | cut -d'=' -f2- | sed 's/[[:space:]]*#.*//' | tr -d ' ')
    
    echo -e "${BLUE}Current Configuration:${NC}"
    echo "  Profile: $current_profile"
    echo "  App Mode: $current_mode"
    
    # Check if Docker Compose is running
    if docker-compose ps >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker Compose is available${NC}"
        
        # Show running services
        running_services=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)
        total_services=$(docker-compose config --services 2>/dev/null | wc -l)
        
        if [[ $running_services -gt 0 ]]; then
            echo -e "${GREEN}✅ Services running: $running_services/$total_services${NC}"
        else
            echo -e "${YELLOW}⚠️  No services currently running${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Docker Compose not available or no compose file${NC}"
    fi
}

check_config() {
    echo -e "${BLUE}Validating configuration...${NC}"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        echo -e "${RED}❌ .env file not found${NC}"
        return 1
    fi
    
    # Check for required variables
    required_vars=("COMPOSE_PROFILES" "APP_MODE" "WEB_APP_PORT")
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE"; then
            echo -e "${RED}❌ Missing required variable: $var${NC}"
            return 1
        fi
    done
    
    # Check Docker Compose file
    if [[ ! -f "$SCRIPT_DIR/docker-compose.yml" ]]; then
        echo -e "${RED}❌ docker-compose.yml not found${NC}"
        return 1
    fi
    
    # Validate Docker Compose configuration
    if ! docker-compose config >/dev/null 2>&1; then
        echo -e "${RED}❌ Invalid Docker Compose configuration${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Configuration is valid${NC}"
    return 0
}

copy_template() {
    local mode="$1"
    local template_file="$SCRIPT_DIR/.env.$mode.example"
    
    if [[ ! -f "$template_file" ]]; then
        echo -e "${YELLOW}⚠️  No template available for mode: $mode${NC}"
        return 1
    fi
    
    echo -e "${BLUE}Copying template for $mode mode...${NC}"
    
    # Backup current .env if it exists
    if [[ -f "$ENV_FILE" ]]; then
        backup_file="$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$ENV_FILE" "$backup_file"
        echo -e "${GREEN}✅ Current .env backed up to: $backup_file${NC}"
    fi
    
    # Copy template
    cp "$template_file" "$ENV_FILE"
    echo -e "${GREEN}✅ Template copied to .env${NC}"
    echo -e "${YELLOW}⚠️  Please review and update the configuration before deployment${NC}"
}

switch_mode() {
    local mode="$1"
    local copy_template_flag="$2"
    local restart_flag="$3"
    
    # Validate mode
    valid_mode=false
    for available_mode in "${MODES[@]}"; do
        available_mode_name="${available_mode%%:*}"
        if [[ "$mode" == "$available_mode_name" ]]; then
            valid_mode=true
            break
        fi
    done
    
    if [[ "$valid_mode" != "true" ]]; then
        echo -e "${RED}❌ Invalid mode: $mode${NC}"
        echo "Available modes: $(printf "%s " "${MODES[@]/%:*/}")"
        return 1
    fi
    
    echo -e "${BLUE}Switching to $mode mode...${NC}"
    
    # Copy template if requested or if no .env exists
    if [[ "$copy_template_flag" == "true" ]] || [[ ! -f "$ENV_FILE" ]]; then
        copy_template "$mode"
    else
        # Just update the COMPOSE_PROFILES in existing .env
        if [[ -f "$ENV_FILE" ]]; then
            sed -i "s/^COMPOSE_PROFILES=.*/COMPOSE_PROFILES=$mode/" "$ENV_FILE"
            echo -e "${GREEN}✅ Updated COMPOSE_PROFILES to $mode${NC}"
        else
            echo -e "${RED}❌ No .env file found. Use --template to create from template${NC}"
            return 1
        fi
    fi
    
    # Validate configuration
    if ! check_config; then
        echo -e "${RED}❌ Configuration validation failed${NC}"
        return 1
    fi
    
    # Restart services if requested
    if [[ "$restart_flag" == "true" ]]; then
        echo -e "${BLUE}Restarting services...${NC}"
        
        # Stop existing services
        docker-compose down --remove-orphans 2>/dev/null || true
        
        # Start with new profile
        docker-compose --profile "$mode" up -d
        
        echo -e "${GREEN}✅ Services restarted with $mode profile${NC}"
    fi
    
    echo -e "${GREEN}✅ Successfully switched to $mode mode${NC}"
    show_status
}

# Parse command line arguments
MODE=""
COPY_TEMPLATE="false"
RESTART="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -l|--list)
            echo "Available deployment modes:"
            for mode in "${MODES[@]}"; do
                mode_name="${mode%%:*}"
                mode_desc="${mode#*:}"
                printf "  %-12s %s\n" "$mode_name" "$mode_desc"
            done
            exit 0
            ;;
        -s|--status)
            show_status
            exit 0
            ;;
        -c|--check)
            check_config
            exit $?
            ;;
        -t|--template)
            COPY_TEMPLATE="true"
            shift
            ;;
        -r|--restart)
            RESTART="true"
            shift
            ;;
        -*)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
        *)
            if [[ -z "$MODE" ]]; then
                MODE="$1"
            else
                echo -e "${RED}❌ Multiple modes specified${NC}"
                show_help
                exit 1
            fi
            shift
            ;;
    esac
done

# Main logic
if [[ -z "$MODE" ]]; then
    show_help
    exit 0
fi

switch_mode "$MODE" "$COPY_TEMPLATE" "$RESTART"