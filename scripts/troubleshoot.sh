#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Troubleshooting Script
# Comprehensive diagnostics and issue resolution
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONTAINER_NAME="${CONTAINER_NAME:-fortinet-app}"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-registry.jclee.me}"
DOCKER_IMAGE_NAME="${DOCKER_IMAGE_NAME:-fortinet}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${BLUE}[INFO]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
header() { echo -e "${CYAN}=== $1 ===${NC}"; }

# Help function
show_help() {
    cat << EOF
FortiGate Nextrade Troubleshooting Script

Usage: $0 [OPTIONS] [CHECK]

Available Checks:
    all             Run all checks (default)
    system          System requirements and resources
    docker          Docker installation and configuration
    network         Network connectivity and ports
    container       Container status and health
    logs            Application logs analysis
    config          Configuration validation
    permissions     File permissions and access
    services        External service connectivity
    performance     Performance analysis
    registry        Docker registry connectivity

Options:
    -h, --help      Show this help message
    -v, --verbose   Verbose output
    -f, --fix       Attempt to fix issues automatically
    -o, --output    Output format (text|json|html)
    --save-report   Save troubleshooting report to file

Examples:
    $0                          # Run all checks
    $0 docker network           # Check Docker and network only
    $0 --fix --verbose          # Run all checks with auto-fix
    $0 --output json --save-report  # Generate JSON report
EOF
}

# Global variables
VERBOSE=false
AUTO_FIX=false
OUTPUT_FORMAT="text"
SAVE_REPORT=false
REPORT_FILE=""
ISSUES_FOUND=0
ISSUES_FIXED=0

# Parse command line arguments
CHECKS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--fix)
            AUTO_FIX=true
            shift
            ;;
        -o|--output)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        --save-report)
            SAVE_REPORT=true
            shift
            ;;
        all|system|docker|network|container|logs|config|permissions|services|performance|registry)
            CHECKS+=("$1")
            shift
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Default to all checks if none specified
if [[ ${#CHECKS[@]} -eq 0 ]]; then
    CHECKS=("all")
fi

# Change to project directory
cd "$PROJECT_DIR"

# Initialize report
init_report() {
    if [[ "$SAVE_REPORT" == true ]]; then
        REPORT_FILE="troubleshooting-report-$(date +%Y%m%d-%H%M%S).${OUTPUT_FORMAT}"
        log "Report will be saved to: $REPORT_FILE"
    fi
}

# Issue tracking
add_issue() {
    local severity="$1"
    local component="$2" 
    local description="$3"
    local fix="${4:-}"
    
    ((ISSUES_FOUND++))
    
    case "$severity" in
        "ERROR")
            error "[$component] $description"
            ;;
        "WARNING") 
            warning "[$component] $description"
            ;;
        "INFO")
            log "[$component] $description"
            ;;
    esac
    
    if [[ -n "$fix" ]] && [[ "$AUTO_FIX" == true ]]; then
        log "Attempting fix: $fix"
        if eval "$fix"; then
            success "Issue fixed automatically"
            ((ISSUES_FIXED++))
        else
            error "Auto-fix failed"
        fi
    fi
}

# System checks
check_system() {
    header "System Requirements Check"
    
    # Check OS
    local os_info
    os_info=$(uname -a)
    log "Operating System: $os_info"
    
    # Check memory
    local memory_total memory_available
    if command -v free &> /dev/null; then
        memory_total=$(free -h | grep Mem | awk '{print $2}')
        memory_available=$(free -h | grep Mem | awk '{print $7}')
        log "Memory: $memory_available available of $memory_total total"
        
        # Check if we have enough memory (at least 2GB available)
        local memory_gb
        memory_gb=$(free -g | grep Mem | awk '{print $7}')
        if [[ $memory_gb -lt 2 ]]; then
            add_issue "WARNING" "SYSTEM" "Low available memory: ${memory_available}" "echo 'Consider freeing up memory or increasing system RAM'"
        fi
    else
        add_issue "WARNING" "SYSTEM" "Cannot check memory usage - 'free' command not found"
    fi
    
    # Check disk space
    local disk_available
    disk_available=$(df -h . | tail -1 | awk '{print $4}')
    log "Disk space available: $disk_available"
    
    # Check if we have enough disk space (at least 5GB)
    local disk_gb
    disk_gb=$(df -G . | tail -1 | awk '{print $4}')
    if [[ $disk_gb -lt 5 ]]; then
        add_issue "WARNING" "SYSTEM" "Low disk space: $disk_available" "docker system prune -f"
    fi
    
    # Check CPU cores
    local cpu_cores
    cpu_cores=$(nproc 2>/dev/null || echo "unknown")
    log "CPU cores: $cpu_cores"
    
    # Check system load
    if command -v uptime &> /dev/null; then
        local load_avg
        load_avg=$(uptime | awk -F'load average:' '{print $2}')
        log "Load average: $load_avg"
    fi
}

# Docker checks
check_docker() {
    header "Docker Installation Check"
    
    # Check Docker installation
    if ! command -v docker &> /dev/null; then
        add_issue "ERROR" "DOCKER" "Docker is not installed" "curl -fsSL https://get.docker.com | sh"
        return 1
    fi
    
    local docker_version
    docker_version=$(docker --version)
    log "Docker version: $docker_version"
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        add_issue "ERROR" "DOCKER" "Docker daemon is not running" "sudo systemctl start docker"
        return 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        add_issue "ERROR" "DOCKER" "Docker Compose is not available" "pip install docker-compose"
        return 1
    fi
    
    local compose_version
    compose_version=$(docker-compose --version 2>/dev/null || docker compose version)
    log "Docker Compose version: $compose_version"
    
    # Check Docker permissions
    if ! docker ps &> /dev/null; then
        add_issue "WARNING" "DOCKER" "Docker permission issue" "sudo usermod -aG docker \$USER && newgrp docker"
    fi
    
    # Check Docker disk usage
    local docker_usage
    docker_usage=$(docker system df --format "table {{.Type}}\t{{.TotalCount}}\t{{.Size}}")
    log "Docker disk usage:"
    echo "$docker_usage"
    
    # Check for excessive Docker usage
    local docker_size_gb
    docker_size_gb=$(docker system df | grep "Local Volumes" | awk '{print $3}' | sed 's/GB.*//' | cut -d'.' -f1)
    if [[ "$docker_size_gb" =~ ^[0-9]+$ ]] && [[ $docker_size_gb -gt 10 ]]; then
        add_issue "WARNING" "DOCKER" "High Docker disk usage: ${docker_size_gb}GB" "docker system prune -f"
    fi
}

# Network checks
check_network() {
    header "Network Connectivity Check"
    
    # Check port availability
    local ports=("7777" "8765" "9090")
    for port in "${ports[@]}"; do
        if netstat -tlnp 2>/dev/null | grep ":$port " &> /dev/null; then
            local process
            process=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}')
            log "Port $port is in use by: $process"
        else
            log "Port $port is available"
        fi
    done
    
    # Check Docker networks
    local fortinet_networks
    fortinet_networks=$(docker network ls | grep fortinet || echo "")
    if [[ -n "$fortinet_networks" ]]; then
        log "FortiNet Docker networks:"
        echo "$fortinet_networks"
    else
        log "No FortiNet Docker networks found"
    fi
    
    # Check external connectivity
    log "Checking external connectivity..."
    if ping -c 1 8.8.8.8 &> /dev/null; then
        success "Internet connectivity: OK"
    else
        add_issue "WARNING" "NETWORK" "No internet connectivity"
    fi
    
    # Check DNS resolution
    if nslookup google.com &> /dev/null; then
        success "DNS resolution: OK"
    else
        add_issue "WARNING" "NETWORK" "DNS resolution issues"
    fi
}

# Container checks
check_container() {
    header "Container Status Check"
    
    # Check if container exists
    if ! docker ps -a -f name="$CONTAINER_NAME" --format "{{.Names}}" | grep -q "$CONTAINER_NAME"; then
        add_issue "WARNING" "CONTAINER" "Container '$CONTAINER_NAME' does not exist"
        return 1
    fi
    
    # Check container status
    local container_status
    container_status=$(docker inspect --format='{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null)
    log "Container status: $container_status"
    
    if [[ "$container_status" != "running" ]]; then
        add_issue "ERROR" "CONTAINER" "Container is not running: $container_status" "docker start $CONTAINER_NAME"
        return 1
    fi
    
    # Check health status
    local health_status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "no-healthcheck")
    log "Health status: $health_status"
    
    if [[ "$health_status" == "unhealthy" ]]; then
        add_issue "ERROR" "CONTAINER" "Container is unhealthy"
    fi
    
    # Check resource usage
    local stats
    stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" "$CONTAINER_NAME" 2>/dev/null || echo "Unable to get stats")
    log "Resource usage: $stats"
    
    # Check container logs for errors
    local error_count
    error_count=$(docker logs "$CONTAINER_NAME" 2>&1 | grep -i "error\|exception\|traceback" | wc -l)
    if [[ $error_count -gt 0 ]]; then
        add_issue "WARNING" "CONTAINER" "Found $error_count error/exception entries in logs"
    fi
    
    # Check restart count
    local restart_count
    restart_count=$(docker inspect --format='{{.RestartCount}}' "$CONTAINER_NAME" 2>/dev/null || echo "0")
    if [[ $restart_count -gt 5 ]]; then
        add_issue "WARNING" "CONTAINER" "High restart count: $restart_count"
    fi
}

# Log analysis
check_logs() {
    header "Log Analysis"
    
    if ! docker ps -q -f name="$CONTAINER_NAME" &> /dev/null; then
        add_issue "WARNING" "LOGS" "Container not running - cannot check logs"
        return 1
    fi
    
    # Check recent logs
    local log_lines
    log_lines=$(docker logs --tail 100 "$CONTAINER_NAME" 2>&1 | wc -l)
    log "Recent log entries: $log_lines"
    
    # Check for common issues
    local startup_errors
    startup_errors=$(docker logs "$CONTAINER_NAME" 2>&1 | grep -i "failed to start\|startup error\|initialization failed" | wc -l)
    if [[ $startup_errors -gt 0 ]]; then
        add_issue "ERROR" "LOGS" "Found $startup_errors startup errors"
    fi
    
    # Check for permission errors
    local permission_errors
    permission_errors=$(docker logs "$CONTAINER_NAME" 2>&1 | grep -i "permission denied\|access denied" | wc -l)
    if [[ $permission_errors -gt 0 ]]; then
        add_issue "ERROR" "LOGS" "Found $permission_errors permission errors"
    fi
    
    # Check for network errors
    local network_errors
    network_errors=$(docker logs "$CONTAINER_NAME" 2>&1 | grep -i "connection refused\|timeout\|network error" | wc -l)
    if [[ $network_errors -gt 0 ]]; then
        add_issue "WARNING" "LOGS" "Found $network_errors network-related errors"
    fi
    
    # Show recent critical logs
    if [[ "$VERBOSE" == true ]]; then
        log "Recent critical log entries:"
        docker logs --tail 20 "$CONTAINER_NAME" 2>&1 | grep -i "error\|warning\|critical" | head -10 || echo "No critical entries found"
    fi
}

# Configuration checks
check_config() {
    header "Configuration Validation"
    
    # Check environment file
    local env_files=(".env" ".env.production" ".env.docker")
    local env_found=false
    
    for env_file in "${env_files[@]}"; do
        if [[ -f "$env_file" ]]; then
            log "Environment file found: $env_file"
            env_found=true
            
            # Check for required variables
            local required_vars=("WEB_APP_PORT" "APP_MODE")
            for var in "${required_vars[@]}"; do
                if grep -q "^$var=" "$env_file"; then
                    log "✓ $var is configured"
                else
                    add_issue "WARNING" "CONFIG" "$var not found in $env_file"
                fi
            done
            
            # Check for sensitive data exposure
            if grep -E "(PASSWORD|SECRET|KEY|TOKEN)=" "$env_file" | grep -v "=\$\|=your\|=change\|=generate" | head -1 &> /dev/null; then
                add_issue "WARNING" "CONFIG" "Potential sensitive data in $env_file"
            fi
            
            break
        fi
    done
    
    if [[ "$env_found" == false ]]; then
        add_issue "ERROR" "CONFIG" "No environment file found" "cp .env.example .env"
    fi
    
    # Check Docker Compose file
    if [[ -f "docker-compose.production.yml" ]]; then
        log "Docker Compose file found"
        
        # Validate Docker Compose syntax
        if docker-compose -f docker-compose.production.yml config &> /dev/null; then
            success "Docker Compose syntax is valid"
        else
            add_issue "ERROR" "CONFIG" "Docker Compose syntax errors"
        fi
    else
        add_issue "ERROR" "CONFIG" "docker-compose.production.yml not found"
    fi
    
    # Check Dockerfile
    if [[ -f "Dockerfile.production" ]]; then
        log "Production Dockerfile found"
    else
        add_issue "WARNING" "CONFIG" "Dockerfile.production not found"
    fi
}

# Permission checks
check_permissions() {
    header "File Permissions Check"
    
    # Check directory permissions
    local dirs=("data" "logs" "scripts")
    for dir in "${dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            local perms
            perms=$(ls -ld "$dir" | awk '{print $1}')
            log "$dir permissions: $perms"
            
            # Check if directory is writable
            if [[ ! -w "$dir" ]]; then
                add_issue "ERROR" "PERMISSIONS" "$dir is not writable" "chmod 755 $dir"
            fi
        else
            add_issue "WARNING" "PERMISSIONS" "Directory $dir does not exist" "mkdir -p $dir"
        fi
    done
    
    # Check script permissions
    if [[ -f "scripts/deploy.sh" ]]; then
        if [[ -x "scripts/deploy.sh" ]]; then
            success "Deploy script is executable"
        else
            add_issue "ERROR" "PERMISSIONS" "Deploy script is not executable" "chmod +x scripts/deploy.sh"
        fi
    fi
    
    # Check Docker socket permissions
    if [[ -S "/var/run/docker.sock" ]]; then
        local docker_perms
        docker_perms=$(ls -l /var/run/docker.sock | awk '{print $1}')
        log "Docker socket permissions: $docker_perms"
    fi
}

# Service connectivity checks
check_services() {
    header "External Service Connectivity"
    
    # Check Docker registry
    if [[ -n "$DOCKER_REGISTRY" ]]; then
        log "Checking registry connectivity: $DOCKER_REGISTRY"
        if curl -s --connect-timeout 10 "https://$DOCKER_REGISTRY" &> /dev/null; then
            success "Registry is accessible"
        else
            add_issue "WARNING" "SERVICES" "Cannot connect to Docker registry: $DOCKER_REGISTRY"
        fi
    fi
    
    # Check FortiManager connectivity (if configured)
    if [[ -f ".env" ]] && grep -q "FORTIMANAGER_HOST=" .env; then
        local fm_host
        fm_host=$(grep "FORTIMANAGER_HOST=" .env | cut -d'=' -f2)
        if [[ -n "$fm_host" ]] && [[ "$fm_host" != "your-fortimanager-host.com" ]]; then
            log "Checking FortiManager connectivity: $fm_host"
            if ping -c 1 "$fm_host" &> /dev/null; then
                success "FortiManager is reachable"
            else
                add_issue "WARNING" "SERVICES" "Cannot reach FortiManager: $fm_host"
            fi
        fi
    fi
    
    # Check application health endpoint
    local app_port="${WEB_APP_PORT:-7777}"
    if curl -s --connect-timeout 5 "http://localhost:$app_port/api/health" &> /dev/null; then
        success "Application health endpoint is responding"
    else
        add_issue "WARNING" "SERVICES" "Application health endpoint not responding"
    fi
}

# Performance analysis
check_performance() {
    header "Performance Analysis"
    
    if ! docker ps -q -f name="$CONTAINER_NAME" &> /dev/null; then
        add_issue "WARNING" "PERFORMANCE" "Container not running - cannot check performance"
        return 1
    fi
    
    # Check container resource usage
    local cpu_usage mem_usage
    cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" "$CONTAINER_NAME" 2>/dev/null | sed 's/%//')
    mem_usage=$(docker stats --no-stream --format "{{.MemPerc}}" "$CONTAINER_NAME" 2>/dev/null | sed 's/%//')
    
    log "CPU usage: ${cpu_usage}%"
    log "Memory usage: ${mem_usage}%"
    
    # Check for high resource usage
    if [[ "${cpu_usage%.*}" -gt 80 ]]; then
        add_issue "WARNING" "PERFORMANCE" "High CPU usage: ${cpu_usage}%"
    fi
    
    if [[ "${mem_usage%.*}" -gt 80 ]]; then
        add_issue "WARNING" "PERFORMANCE" "High memory usage: ${mem_usage}%"
    fi
    
    # Check response time
    local response_time
    response_time=$(curl -s -w "%{time_total}" -o /dev/null "http://localhost:${WEB_APP_PORT:-7777}" 2>/dev/null || echo "timeout")
    if [[ "$response_time" != "timeout" ]]; then
        log "Response time: ${response_time}s"
        if (( $(echo "$response_time > 2.0" | bc -l) )); then
            add_issue "WARNING" "PERFORMANCE" "Slow response time: ${response_time}s"
        fi
    else
        add_issue "WARNING" "PERFORMANCE" "Application not responding"
    fi
    
    # Check for memory leaks (simplified)
    local mem_trend
    mem_trend=$(docker stats --no-stream --format "{{.MemUsage}}" "$CONTAINER_NAME" 2>/dev/null)
    log "Current memory usage: $mem_trend"
}

# Registry connectivity check
check_registry() {
    header "Docker Registry Connectivity"
    
    # Test registry authentication
    log "Testing registry authentication..."
    if echo "${DOCKER_PASSWORD:-}" | docker login "$DOCKER_REGISTRY" -u "${DOCKER_USERNAME:-}" --password-stdin &> /dev/null; then
        success "Registry authentication successful"
        docker logout "$DOCKER_REGISTRY" &> /dev/null
    else
        add_issue "ERROR" "REGISTRY" "Registry authentication failed"
    fi
    
    # Test image pull
    log "Testing image pull..."
    if docker pull "$DOCKER_REGISTRY/$DOCKER_IMAGE_NAME:latest" &> /dev/null; then
        success "Image pull successful"
    else
        add_issue "WARNING" "REGISTRY" "Cannot pull image from registry"
    fi
}

# Generate summary report
generate_summary() {
    header "Troubleshooting Summary"
    
    if [[ $ISSUES_FOUND -eq 0 ]]; then
        success "No issues found! System appears to be healthy."
    else
        warning "Found $ISSUES_FOUND issues"
        if [[ $ISSUES_FIXED -gt 0 ]]; then
            success "Automatically fixed $ISSUES_FIXED issues"
        fi
        
        local remaining=$((ISSUES_FOUND - ISSUES_FIXED))
        if [[ $remaining -gt 0 ]]; then
            warning "$remaining issues require manual attention"
        fi
    fi
    
    # Provide next steps
    echo -e "\n${CYAN}Recommended Next Steps:${NC}"
    if [[ $ISSUES_FOUND -gt 0 ]]; then
        echo "1. Review the issues above and apply suggested fixes"
        echo "2. Re-run troubleshooting after fixes: $0"
        echo "3. Check application logs: docker logs $CONTAINER_NAME"
        echo "4. Restart services if needed: ./scripts/deploy.sh restart"
    else
        echo "1. Monitor system performance: docker stats $CONTAINER_NAME"
        echo "2. Check application health: curl http://localhost:${WEB_APP_PORT:-7777}/api/health"
        echo "3. Review logs periodically: docker logs $CONTAINER_NAME"
    fi
}

# Main execution
main() {
    log "FortiGate Nextrade Troubleshooting Script"
    log "Checks to run: ${CHECKS[*]}"
    
    init_report
    
    for check in "${CHECKS[@]}"; do
        case "$check" in
            all)
                check_system
                check_docker
                check_network
                check_container
                check_logs
                check_config
                check_permissions
                check_services
                check_performance
                check_registry
                ;;
            system)
                check_system
                ;;
            docker)
                check_docker
                ;;
            network)
                check_network
                ;;
            container)
                check_container
                ;;
            logs)
                check_logs
                ;;
            config)
                check_config
                ;;
            permissions)
                check_permissions
                ;;
            services)
                check_services
                ;;
            performance)
                check_performance
                ;;
            registry)
                check_registry
                ;;
            *)
                error "Unknown check: $check"
                exit 1
                ;;
        esac
    done
    
    generate_summary
    
    # Exit with error code if issues found
    if [[ $ISSUES_FOUND -gt 0 ]]; then
        exit 1
    fi
}

# Execute main function
main "$@"