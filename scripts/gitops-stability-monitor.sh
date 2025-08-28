#!/bin/bash
# GitOps Deployment Stability Monitor
# 배포 안정성 모니터링 및 자동 복구 스크립트

set -euo pipefail

# Configuration
NAMESPACE="fortinet"
APP_NAME="fortinet"
ARGOCD_SERVER="argo.jclee.me"
HEALTH_ENDPOINT="http://192.168.50.110:30777/api/health"
MAX_WAIT_TIME=600  # 10 minutes
CHECK_INTERVAL=30  # 30 seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Check if required commands are available
check_prerequisites() {
    log "Checking prerequisites..."
    
    local missing_commands=()
    
    for cmd in kubectl argocd curl jq; do
        if ! command -v $cmd &> /dev/null; then
            missing_commands+=($cmd)
        fi
    done
    
    if [ ${#missing_commands[@]} -ne 0 ]; then
        error "Missing required commands: ${missing_commands[*]}"
        return 1
    fi
    
    success "All prerequisites satisfied"
}

# Get current ArgoCD application status
get_argocd_status() {
    kubectl get app $APP_NAME -n argocd -o json 2>/dev/null | jq -r '{
        sync: .status.sync.status,
        health: .status.health.status,
        operationState: (.status.operationState.phase // "Unknown"),
        revision: .status.sync.revision
    }'
}

# Get Kubernetes deployment status
get_deployment_status() {
    kubectl get deployment $APP_NAME -n $NAMESPACE -o json 2>/dev/null | jq -r '{
        image: .spec.template.spec.containers[0].image,
        replicas: .spec.replicas,
        readyReplicas: (.status.readyReplicas // 0),
        availableReplicas: (.status.availableReplicas // 0),
        conditions: [.status.conditions[]? | select(.type=="Progressing" or .type=="Available")]
    }'
}

# Get GitHub Actions pipeline status
get_pipeline_status() {
    gh run list --limit 1 --json status,conclusion,createdAt,headSha 2>/dev/null || echo "[]"
}

# Check application health
check_health() {
    local response
    response=$(curl -s -f "$HEALTH_ENDPOINT" 2>/dev/null || echo '{"status":"unhealthy"}')
    echo "$response" | jq -r '.status // "unknown"'
}

# Trigger ArgoCD sync
trigger_sync() {
    log "Triggering ArgoCD sync..."
    
    if argocd app sync $APP_NAME --grpc-web --prune --force 2>/dev/null; then
        success "ArgoCD sync triggered successfully"
        return 0
    else
        error "Failed to trigger ArgoCD sync"
        return 1
    fi
}

# Wait for deployment rollout
wait_for_rollout() {
    local timeout=$1
    local start_time=$(date +%s)
    
    log "Waiting for deployment rollout (timeout: ${timeout}s)..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $timeout ]; then
            error "Deployment rollout timeout after ${timeout}s"
            return 1
        fi
        
        local deployment_status
        deployment_status=$(get_deployment_status)
        
        local replicas=$(echo "$deployment_status" | jq -r '.replicas')
        local ready_replicas=$(echo "$deployment_status" | jq -r '.readyReplicas')
        local available_replicas=$(echo "$deployment_status" | jq -r '.availableReplicas')
        
        if [ "$replicas" = "$ready_replicas" ] && [ "$replicas" = "$available_replicas" ]; then
            success "Deployment rollout completed successfully"
            return 0
        fi
        
        log "Rollout progress: $ready_replicas/$replicas ready, $available_replicas/$replicas available"
        sleep $CHECK_INTERVAL
    done
}

# Monitor deployment stability
monitor_stability() {
    local duration=${1:-300}  # Default 5 minutes
    local start_time=$(date +%s)
    local health_check_failures=0
    local max_health_failures=3
    
    log "Monitoring deployment stability for ${duration}s..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $duration ]; then
            success "Stability monitoring completed successfully"
            return 0
        fi
        
        # Check application health
        local health_status
        health_status=$(check_health)
        
        if [ "$health_status" = "healthy" ]; then
            health_check_failures=0
            log "Health check passed ($((duration - elapsed))s remaining)"
        else
            health_check_failures=$((health_check_failures + 1))
            warning "Health check failed (attempt $health_check_failures/$max_health_failures)"
            
            if [ $health_check_failures -ge $max_health_failures ]; then
                error "Too many health check failures, deployment unstable"
                return 1
            fi
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# Generate stability report
generate_report() {
    local report_file="/tmp/gitops-stability-report-$(date +%Y%m%d-%H%M%S).json"
    
    log "Generating stability report..."
    
    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "argocd_status": $(get_argocd_status),
    "deployment_status": $(get_deployment_status),
    "pipeline_status": $(get_pipeline_status | jq '.[0] // {}'),
    "health_status": "$(check_health)",
    "kubernetes_resources": {
        "pods": $(kubectl get pods -n $NAMESPACE -o json | jq '.items | length'),
        "services": $(kubectl get svc -n $NAMESPACE -o json | jq '.items | length'),
        "ingresses": $(kubectl get ing -n $NAMESPACE -o json | jq '.items | length')
    },
    "stability_score": {
        "argocd_sync": $([ "$(get_argocd_status | jq -r '.sync')" = "Synced" ] && echo "100" || echo "0"),
        "argocd_health": $([ "$(get_argocd_status | jq -r '.health')" = "Healthy" ] && echo "100" || echo "0"),
        "app_health": $([ "$(check_health)" = "healthy" ] && echo "100" || echo "0")
    }
}
EOF
    
    success "Report generated: $report_file"
    cat "$report_file" | jq '.'
}

# Main execution
main() {
    log "Starting GitOps Deployment Stability Monitor"
    echo "=================================================="
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Get initial status
    log "Current deployment status:"
    echo "ArgoCD Status: $(get_argocd_status)"
    echo "Deployment Status: $(get_deployment_status)"
    echo "Health Status: $(check_health)"
    
    # Check if sync is needed
    local argocd_status
    argocd_status=$(get_argocd_status)
    local sync_status=$(echo "$argocd_status" | jq -r '.sync')
    
    if [ "$sync_status" = "OutOfSync" ]; then
        warning "Application is OutOfSync, triggering sync..."
        if trigger_sync; then
            # Wait for rollout
            if wait_for_rollout $MAX_WAIT_TIME; then
                # Monitor stability
                monitor_stability 300  # 5 minutes
            else
                error "Rollout failed or timed out"
                generate_report
                exit 1
            fi
        else
            error "Failed to trigger sync"
            exit 1
        fi
    else
        success "Application is in sync, monitoring stability..."
        monitor_stability 180  # 3 minutes for already synced apps
    fi
    
    # Generate final report
    generate_report
    
    success "GitOps deployment stability monitoring completed"
}

# Execute main function if script is called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi