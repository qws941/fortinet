#!/bin/bash

# Agent Manager Script for Grafana Monitoring System
set -e

COMPOSE_FILE="docker-compose-agents.yml"
MAIN_COMPOSE="docker-compose.yml"
LOG_DIR="./logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if Docker and Docker Compose are installed
check_requirements() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi

    print_status "Requirements check passed"
}

# Build agent images
build_agents() {
    print_status "Building agent images..."
    docker-compose -f $COMPOSE_FILE build --no-cache
    print_status "Agent images built successfully"
}

# Start all agents
start_agents() {
    print_status "Starting all agents..."

    # Ensure main services are running
    if [ -f "$MAIN_COMPOSE" ]; then
        print_status "Ensuring main monitoring services are running..."
        docker-compose -f $MAIN_COMPOSE up -d
    fi

    # Start agents
    docker-compose -f $COMPOSE_FILE up -d
    print_status "All agents started successfully"
}

# Stop all agents
stop_agents() {
    print_status "Stopping all agents..."
    docker-compose -f $COMPOSE_FILE down
    print_status "All agents stopped"
}

# Restart specific agent
restart_agent() {
    local agent_name=$1
    if [ -z "$agent_name" ]; then
        print_error "Agent name required"
        exit 1
    fi

    print_status "Restarting $agent_name..."
    docker-compose -f $COMPOSE_FILE restart $agent_name
    print_status "$agent_name restarted successfully"
}

# View agent logs
view_logs() {
    local agent_name=$1
    if [ -z "$agent_name" ]; then
        # Show all agent logs
        docker-compose -f $COMPOSE_FILE logs -f --tail=50
    else
        # Show specific agent logs
        docker-compose -f $COMPOSE_FILE logs -f --tail=50 $agent_name
    fi
}

# Check agent status
check_status() {
    print_status "Agent Status:"
    echo "----------------------------------------"
    docker-compose -f $COMPOSE_FILE ps
    echo "----------------------------------------"

    # Check individual agent health
    for agent in metric-labeling-agent alert-manager-agent log-scanner-agent predictive-analytics-agent; do
        if docker ps --format "table {{.Names}}" | grep -q $agent; then
            status=$(docker inspect --format='{{.State.Health.Status}}' $agent 2>/dev/null || echo "no healthcheck")
            if [ "$status" == "healthy" ]; then
                echo -e "$agent: ${GREEN}healthy${NC}"
            elif [ "$status" == "unhealthy" ]; then
                echo -e "$agent: ${RED}unhealthy${NC}"
            else
                echo -e "$agent: ${YELLOW}$status${NC}"
            fi
        else
            echo -e "$agent: ${RED}not running${NC}"
        fi
    done
}

# Scale agent
scale_agent() {
    local agent_name=$1
    local count=$2

    if [ -z "$agent_name" ] || [ -z "$count" ]; then
        print_error "Usage: scale <agent-name> <count>"
        exit 1
    fi

    print_status "Scaling $agent_name to $count instances..."
    docker-compose -f $COMPOSE_FILE up -d --scale $agent_name=$count
    print_status "$agent_name scaled to $count instances"
}

# Clean up logs
cleanup_logs() {
    print_warning "Cleaning up agent logs..."
    find $LOG_DIR -name "*.log" -mtime +7 -delete
    print_status "Old logs cleaned up"
}

# Monitor agent resources
monitor_resources() {
    print_status "Agent Resource Usage:"
    echo "----------------------------------------"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" \
        metric-labeling-agent alert-manager-agent log-scanner-agent predictive-analytics-agent agent-supervisor
}

# Update agent configuration
update_config() {
    local config_file="./config/agents/config.yml"

    if [ ! -f "$config_file" ]; then
        print_warning "Creating default configuration..."
        mkdir -p ./config/agents
        cat > $config_file <<EOF
# Agent Configuration
agents:
  metric_labeling:
    enabled: true
    interval: 60
    batch_size: 1000

  alert_manager:
    enabled: true
    interval: 30
    grouping_threshold: 0.7

  log_scanner:
    enabled: true
    interval: 30
    patterns_update: daily

  predictive_analytics:
    enabled: true
    interval: 300
    prediction_window: 3600
EOF
        print_status "Configuration file created at $config_file"
    else
        print_status "Configuration file already exists at $config_file"
    fi
}

# Main menu
show_help() {
    echo "Grafana Agent Manager"
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  build              Build agent Docker images"
    echo "  start              Start all agents"
    echo "  stop               Stop all agents"
    echo "  restart [agent]    Restart specific agent or all agents"
    echo "  status             Check agent status"
    echo "  logs [agent]       View agent logs"
    echo "  scale <agent> <n>  Scale agent to n instances"
    echo "  monitor            Monitor agent resource usage"
    echo "  cleanup            Clean up old logs"
    echo "  config             Update agent configuration"
    echo "  help               Show this help message"
}

# Main execution
case "$1" in
    build)
        check_requirements
        build_agents
        ;;
    start)
        check_requirements
        start_agents
        check_status
        ;;
    stop)
        stop_agents
        ;;
    restart)
        if [ -z "$2" ]; then
            stop_agents
            start_agents
        else
            restart_agent "$2"
        fi
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs "$2"
        ;;
    scale)
        scale_agent "$2" "$3"
        ;;
    monitor)
        monitor_resources
        ;;
    cleanup)
        cleanup_logs
        ;;
    config)
        update_config
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac