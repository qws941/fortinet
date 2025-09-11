#!/bin/bash
# FortiGate Nextrade - Deployment Validation Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
PORTAINER_URL="${PORTAINER_URL:-https://portainer.jclee.me}"
PORTAINER_API_KEY="${PORTAINER_API_KEY}"
MAIN_PORT="${WEB_APP_PORT_MAIN:-7777}"
BACKUP_PORT="${WEB_APP_PORT_BACKUP:-7778}"
DEV_PORT="${WEB_APP_PORT_DEV:-7779}"
DEPLOYMENT_HOST="${DEPLOYMENT_HOST:-192.168.50.110}"

echo "🔍 FortiGate Nextrade Deployment Validation"
echo "============================================"

# Function to check container health
check_container_health() {
    local CONTAINER_NAME=$1
    local EXPECTED_PORT=$2
    
    echo "🔍 Checking container: $CONTAINER_NAME"
    
    if [ -n "$PORTAINER_API_KEY" ]; then
        # Check via Portainer API
        CONTAINER_STATUS=$(curl -s "$PORTAINER_URL/api/endpoints/1/docker/containers/json" \
            -H "X-API-Key: $PORTAINER_API_KEY" | \
            jq -r --arg name "$CONTAINER_NAME" '.[] | select(.Names[] | contains($name)) | .State')
        
        if [ "$CONTAINER_STATUS" = "running" ]; then
            echo "✅ Container $CONTAINER_NAME is running"
            
            # Check health endpoint if port is available
            if [ -n "$EXPECTED_PORT" ]; then
                if curl -f -s --max-time 10 "http://$DEPLOYMENT_HOST:$EXPECTED_PORT/api/health" > /dev/null; then
                    echo "✅ Health check passed for port $EXPECTED_PORT"
                else
                    echo "⚠️ Health check failed for port $EXPECTED_PORT"
                    return 1
                fi
            fi
        else
            echo "❌ Container $CONTAINER_NAME is not running (Status: $CONTAINER_STATUS)"
            return 1
        fi
    else
        echo "⚠️ PORTAINER_API_KEY not set, skipping container check"
        return 1
    fi
}

# Function to check network connectivity
check_network_connectivity() {
    echo "🌐 Checking network connectivity..."
    
    # Check main application ports
    for PORT in $MAIN_PORT $BACKUP_PORT $DEV_PORT; do
        if nc -z "$DEPLOYMENT_HOST" "$PORT" 2>/dev/null; then
            echo "✅ Port $PORT is accessible"
        else
            echo "❌ Port $PORT is not accessible"
        fi
    done
}

# Function to validate volumes
validate_volumes() {
    echo "💾 Validating volumes..."
    
    if [ -n "$PORTAINER_API_KEY" ]; then
        VOLUMES=$(curl -s "$PORTAINER_URL/api/endpoints/1/docker/volumes" \
            -H "X-API-Key: $PORTAINER_API_KEY" | \
            jq -r '.Volumes[] | select(.Name | contains("fortinet")) | .Name')
        
        EXPECTED_VOLUMES=(
            "fortinet-postgres-data"
            "fortinet-redis-data"
            "fortinet-app-uploads"
            "fortinet-app-logs"
            "fortinet-app-cache"
            "fortinet-app-backup-logs"
            "fortinet-app-dev-logs"
        )
        
        for EXPECTED_VOLUME in "${EXPECTED_VOLUMES[@]}"; do
            if echo "$VOLUMES" | grep -q "$EXPECTED_VOLUME"; then
                echo "✅ Volume $EXPECTED_VOLUME exists"
            else
                echo "⚠️ Volume $EXPECTED_VOLUME is missing"
            fi
        done
    else
        echo "⚠️ Cannot validate volumes without PORTAINER_API_KEY"
    fi
}

# Function to check API endpoints
check_api_endpoints() {
    echo "🔌 Checking API endpoints..."
    
    ENDPOINTS=(
        "/api/health"
        "/api/status"
        "/api/version"
    )
    
    for PORT in $MAIN_PORT $BACKUP_PORT; do
        echo "Testing port $PORT:"
        for ENDPOINT in "${ENDPOINTS[@]}"; do
            if curl -f -s --max-time 10 "http://$DEPLOYMENT_HOST:$PORT$ENDPOINT" > /dev/null; then
                echo "  ✅ $ENDPOINT"
            else
                echo "  ❌ $ENDPOINT"
            fi
        done
    done
}

# Main validation sequence
main() {
    echo "Starting deployment validation..."
    
    # Check container health
    check_container_health "fortinet-postgres"
    check_container_health "fortinet-redis"  
    check_container_health "fortinet-app" "$MAIN_PORT"
    check_container_health "fortinet-app-backup" "$BACKUP_PORT"
    check_container_health "fortinet-app-dev" "$DEV_PORT"
    
    # Check network connectivity
    check_network_connectivity
    
    # Validate volumes
    validate_volumes
    
    # Check API endpoints
    check_api_endpoints
    
    echo ""
    echo "🎉 Validation completed!"
    echo "Main Application: http://$DEPLOYMENT_HOST:$MAIN_PORT"
    echo "Backup Application: http://$DEPLOYMENT_HOST:$BACKUP_PORT"
    echo "Development Application: http://$DEPLOYMENT_HOST:$DEV_PORT"
}

# Run main function
main "$@"