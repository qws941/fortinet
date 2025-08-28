#!/bin/bash

# FortiGate Nextrade Health Monitoring Script
# Continuously monitors the health of the deployed application

set -e

# Configuration
APP_URL="http://localhost:7777"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
CHECK_INTERVAL=60  # seconds
ERROR_THRESHOLD=3
CONTAINER_NAME="fortinet-prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
ERROR_COUNT=0
CHECK_COUNT=0

# Function to send alert
send_alert() {
    local message="$1"
    local severity="$2"
    
    echo -e "${RED}[ALERT] ${message}${NC}"
    
    # Send to webhook if configured
    if [ ! -z "$ALERT_WEBHOOK" ]; then
        curl -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"FortiNet Alert: ${message}\", \"severity\":\"${severity}\"}" \
            2>/dev/null || true
    fi
    
    # Log to file
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ${severity}: ${message}" >> /var/log/fortinet-monitor.log
}

# Function to check health endpoint
check_health() {
    local response=$(curl -s -w "\n%{http_code}" "$APP_URL/api/health" 2>/dev/null || echo "000")
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        local status=$(echo "$body" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$status" = "healthy" ]; then
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

# Function to check container status
check_container() {
    if docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
        return 0
    else
        return 1
    fi
}

# Function to check resource usage
check_resources() {
    local stats=$(docker stats --no-stream --format "{{.CPUPerc}} {{.MemPerc}}" "$CONTAINER_NAME" 2>/dev/null || echo "0% 0%")
    local cpu=$(echo "$stats" | awk '{print $1}' | sed 's/%//')
    local mem=$(echo "$stats" | awk '{print $2}' | sed 's/%//')
    
    if (( $(echo "$cpu > 80" | bc -l) )); then
        send_alert "High CPU usage: ${cpu}%" "warning"
    fi
    
    if (( $(echo "$mem > 90" | bc -l) )); then
        send_alert "High memory usage: ${mem}%" "warning"
    fi
}

# Function to perform comprehensive health check
perform_health_check() {
    CHECK_COUNT=$((CHECK_COUNT + 1))
    echo -e "\n${GREEN}[CHECK #${CHECK_COUNT}]${NC} $(date '+%Y-%m-%d %H:%M:%S')"
    
    # Check container
    if ! check_container; then
        ERROR_COUNT=$((ERROR_COUNT + 1))
        send_alert "Container $CONTAINER_NAME is not running" "critical"
        
        if [ $ERROR_COUNT -ge $ERROR_THRESHOLD ]; then
            echo -e "${RED}[CRITICAL]${NC} Attempting to restart container..."
            docker start "$CONTAINER_NAME" 2>/dev/null || docker run -d --name "$CONTAINER_NAME" -p 7777:7777 registry.jclee.me/fortinet:latest
            ERROR_COUNT=0
        fi
        return 1
    fi
    
    # Check health endpoint
    if ! check_health; then
        ERROR_COUNT=$((ERROR_COUNT + 1))
        send_alert "Health check failed" "warning"
        
        if [ $ERROR_COUNT -ge $ERROR_THRESHOLD ]; then
            send_alert "Health check failed $ERROR_THRESHOLD times consecutively" "critical"
        fi
    else
        if [ $ERROR_COUNT -gt 0 ]; then
            echo -e "${GREEN}[RECOVERED]${NC} Service is healthy again"
            ERROR_COUNT=0
        fi
        echo -e "${GREEN}✓${NC} Health check passed"
    fi
    
    # Check resources
    check_resources
    
    # Check specific endpoints
    for endpoint in "/api/settings" "/dashboard" "/devices"; do
        http_code=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL$endpoint" 2>/dev/null || echo "000")
        if [ "$http_code" = "200" ]; then
            echo -e "${GREEN}✓${NC} Endpoint $endpoint is responsive"
        else
            echo -e "${YELLOW}⚠${NC} Endpoint $endpoint returned $http_code"
        fi
    done
    
    # Display summary
    echo -e "${GREEN}Summary:${NC}"
    docker stats --no-stream "$CONTAINER_NAME" 2>/dev/null || echo "Container stats unavailable"
}

# Main monitoring loop
echo -e "${GREEN}Starting FortiGate Nextrade Health Monitor${NC}"
echo "Monitoring URL: $APP_URL"
echo "Container: $CONTAINER_NAME"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Error threshold: $ERROR_THRESHOLD"
echo "----------------------------------------"

# Create log file if it doesn't exist
touch /var/log/fortinet-monitor.log 2>/dev/null || true

# Trap to handle script termination
trap 'echo -e "\n${YELLOW}Monitoring stopped${NC}"; exit 0' INT TERM

# Main loop
while true; do
    perform_health_check
    sleep "$CHECK_INTERVAL"
done