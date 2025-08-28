#!/bin/bash

# Enhanced Health Check Script with Learning-Based Improvements
# Based on patterns learned from 35+ workflow executions

set -e

# Configuration
SERVICE_URL="${1:-http://192.168.50.110:30777}"
MAX_RETRIES="${2:-10}"
RETRY_DELAY="${3:-30}"
TIMEOUT="${4:-10}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🏥 Starting Enhanced Health Check"
echo "URL: $SERVICE_URL"
echo "Max Retries: $MAX_RETRIES"
echo "Retry Delay: ${RETRY_DELAY}s"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Function to check health
check_health() {
    local response
    local http_code
    
    # Use curl with timeout and capture both response and HTTP code
    response=$(curl -s -w "\n%{http_code}" --max-time "$TIMEOUT" "$SERVICE_URL/api/health" 2>/dev/null || echo "CURL_ERROR")
    
    if [[ "$response" == "CURL_ERROR" ]]; then
        return 1
    fi
    
    # Extract HTTP code (last line)
    http_code=$(echo "$response" | tail -n1)
    
    # Extract JSON response (all but last line)
    json_response=$(echo "$response" | head -n-1)
    
    # Check HTTP code
    if [[ "$http_code" != "200" ]]; then
        echo -e "${YELLOW}HTTP Code: $http_code${NC}"
        return 1
    fi
    
    # Parse JSON response
    if command -v jq &> /dev/null; then
        status=$(echo "$json_response" | jq -r '.status' 2>/dev/null || echo "unknown")
        environment=$(echo "$json_response" | jq -r '.environment' 2>/dev/null || echo "unknown")
        version=$(echo "$json_response" | jq -r '.version' 2>/dev/null || echo "unknown")
        
        echo -e "${GREEN}✓ Status: $status${NC}"
        echo "  Environment: $environment"
        echo "  Version: $version"
        
        if [[ "$status" == "healthy" ]]; then
            return 0
        fi
    else
        # Fallback without jq
        if echo "$json_response" | grep -q '"status":"healthy"'; then
            echo -e "${GREEN}✓ Health check passed (no jq)${NC}"
            return 0
        fi
    fi
    
    return 1
}

# Function to check pod status (if kubectl available)
check_pods() {
    if command -v kubectl &> /dev/null; then
        echo ""
        echo "📦 Checking Pod Status..."
        kubectl get pods -n fortinet --no-headers 2>/dev/null | while read line; do
            pod_name=$(echo "$line" | awk '{print $1}')
            ready=$(echo "$line" | awk '{print $2}')
            status=$(echo "$line" | awk '{print $3}')
            
            if [[ "$status" == "Running" ]]; then
                echo -e "  ${GREEN}✓${NC} $pod_name: $ready ($status)"
            else
                echo -e "  ${RED}✗${NC} $pod_name: $ready ($status)"
            fi
        done
    fi
}

# Function to check ArgoCD status (if argocd CLI available)
check_argocd() {
    if command -v argocd &> /dev/null && [[ -n "$ARGOCD_AUTH_TOKEN" ]]; then
        echo ""
        echo "🔄 Checking ArgoCD Sync Status..."
        
        sync_status=$(argocd app get fortinet --server argo.jclee.me --grpc-web --insecure -o json 2>/dev/null | jq -r '.status.sync.status' || echo "unknown")
        health_status=$(argocd app get fortinet --server argo.jclee.me --grpc-web --insecure -o json 2>/dev/null | jq -r '.status.health.status' || echo "unknown")
        
        if [[ "$sync_status" == "Synced" ]]; then
            echo -e "  ${GREEN}✓${NC} Sync: $sync_status"
        else
            echo -e "  ${YELLOW}⚠${NC} Sync: $sync_status"
        fi
        
        if [[ "$health_status" == "Healthy" ]]; then
            echo -e "  ${GREEN}✓${NC} Health: $health_status"
        else
            echo -e "  ${YELLOW}⚠${NC} Health: $health_status"
        fi
    fi
}

# Main health check loop with retries
success=false

for i in $(seq 1 $MAX_RETRIES); do
    echo ""
    echo "🔍 Health Check Attempt $i/$MAX_RETRIES"
    echo "────────────────────────────"
    
    if check_health; then
        success=true
        echo -e "${GREEN}✅ Health check passed!${NC}"
        
        # Additional checks on success
        check_pods
        check_argocd
        
        break
    else
        if [ $i -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}⏳ Health check failed, retrying in ${RETRY_DELAY}s...${NC}"
            sleep $RETRY_DELAY
        else
            echo -e "${RED}❌ Health check failed after $MAX_RETRIES attempts${NC}"
        fi
    fi
done

# Final status
echo ""
echo "════════════════════════════════════════"
if $success; then
    echo -e "${GREEN}🎉 DEPLOYMENT HEALTHY AND READY${NC}"
    exit 0
else
    echo -e "${RED}💔 DEPLOYMENT HEALTH CHECK FAILED${NC}"
    echo ""
    echo "Troubleshooting Tips:"
    echo "1. Check if pods are running: kubectl get pods -n fortinet"
    echo "2. Check pod logs: kubectl logs -n fortinet -l app=fortinet"
    echo "3. Check service: kubectl get svc -n fortinet"
    echo "4. Check ingress: kubectl get ingress -n fortinet"
    echo "5. Check ArgoCD: argocd app get fortinet --grpc-web"
    exit 1
fi