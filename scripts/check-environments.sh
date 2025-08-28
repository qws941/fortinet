#!/bin/bash
# check-environments.sh - 모든 환경 상태 확인 스크립트

set -euo pipefail

# 색깔 출력을 위한 함수
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 환경 설정
declare -A ENVIRONMENTS=(
    ["production"]="30777"
    ["staging"]="30881"
    ["development"]="30880"
)

declare -A ENV_NAMESPACES=(
    ["production"]="fortinet"
    ["staging"]="fortinet-staging"
    ["development"]="fortinet-dev"
)

declare -A ARGOCD_APPS=(
    ["production"]="fortinet"
    ["staging"]="fortinet-staging"
    ["development"]="fortinet-development"
)

check_health_endpoint() {
    local env=$1
    local port=$2
    local url="http://192.168.50.110:${port}/api/health"
    
    log_info "Checking $env environment health ($url)..."
    
    if response=$(curl -s --connect-timeout 10 --max-time 30 "$url" 2>/dev/null); then
        if echo "$response" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
            environment=$(echo "$response" | jq -r '.environment // "unknown"')
            uptime=$(echo "$response" | jq -r '.uptime_human // "unknown"')
            log_success "$env: ✅ HEALTHY (Environment: $environment, Uptime: $uptime)"
            return 0
        else
            log_warning "$env: ⚠️  RESPONDING but not healthy"
            echo "$response" | jq . 2>/dev/null || echo "$response"
            return 1
        fi
    else
        log_error "$env: ❌ NOT RESPONDING"
        return 1
    fi
}

check_argocd_status() {
    local env=$1
    local app_name=$2
    
    log_info "Checking ArgoCD application status for $env ($app_name)..."
    
    if argocd app get "$app_name" --output json >/dev/null 2>&1; then
        local status=$(argocd app get "$app_name" --output json | jq -r '.status.sync.status // "Unknown"')
        local health=$(argocd app get "$app_name" --output json | jq -r '.status.health.status // "Unknown"')
        
        case "$status" in
            "Synced")
                if [ "$health" = "Healthy" ]; then
                    log_success "$env ArgoCD: ✅ SYNCED & HEALTHY"
                else
                    log_warning "$env ArgoCD: ⚠️  SYNCED but $health"
                fi
                ;;
            "OutOfSync")
                log_warning "$env ArgoCD: 🔄 OUT OF SYNC ($health)"
                ;;
            *)
                log_error "$env ArgoCD: ❌ $status ($health)"
                ;;
        esac
    else
        log_error "$env ArgoCD: ❌ APPLICATION NOT FOUND"
        return 1
    fi
}

check_kubernetes_resources() {
    local env=$1
    local namespace=$2
    
    log_info "Checking Kubernetes resources in $namespace..."
    
    # Check deployments
    local deployments=$(kubectl get deployments -n "$namespace" --no-headers 2>/dev/null | wc -l || echo "0")
    local ready_deployments=$(kubectl get deployments -n "$namespace" --no-headers 2>/dev/null | awk '$2 == $4 {print $1}' | wc -l || echo "0")
    
    # Check services
    local services=$(kubectl get services -n "$namespace" --no-headers 2>/dev/null | wc -l || echo "0")
    
    # Check pods
    local pods=$(kubectl get pods -n "$namespace" --no-headers 2>/dev/null | wc -l || echo "0")
    local running_pods=$(kubectl get pods -n "$namespace" --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l || echo "0")
    
    echo "  📦 Deployments: $ready_deployments/$deployments ready"
    echo "  🌐 Services: $services"
    echo "  🚀 Pods: $running_pods/$pods running"
    
    if [ "$ready_deployments" = "$deployments" ] && [ "$running_pods" = "$pods" ] && [ "$pods" -gt 0 ]; then
        log_success "$env K8s Resources: ✅ ALL READY"
        return 0
    else
        log_warning "$env K8s Resources: ⚠️  NOT ALL READY"
        
        # Show pod status for debugging
        echo "  Pod Status:"
        kubectl get pods -n "$namespace" --no-headers 2>/dev/null | while read line; do
            echo "    $line"
        done
        
        return 1
    fi
}

main() {
    log_info "🔍 Checking all environment statuses..."
    echo ""
    
    local overall_status=0
    local health_status=0
    local argocd_status=0
    local k8s_status=0
    
    # Check each environment
    for env in "${!ENVIRONMENTS[@]}"; do
        local port=${ENVIRONMENTS[$env]}
        local namespace=${ENV_NAMESPACES[$env]}
        local app_name=${ARGOCD_APPS[$env]}
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🚀 $env Environment (Port: $port, Namespace: $namespace)"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Health check
        if check_health_endpoint "$env" "$port"; then
            ((health_status += 1))
        fi
        
        echo ""
        
        # ArgoCD status
        if check_argocd_status "$env" "$app_name"; then
            ((argocd_status += 1))
        fi
        
        echo ""
        
        # Kubernetes resources
        if check_kubernetes_resources "$env" "$namespace"; then
            ((k8s_status += 1))
        fi
        
        echo ""
    done
    
    # Summary
    local total_envs=${#ENVIRONMENTS[@]}
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 DEPLOYMENT STATUS SUMMARY"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🏥 Health Endpoints:    $health_status/$total_envs environments healthy"
    echo "🔄 ArgoCD Applications: $argocd_status/$total_envs applications ready"
    echo "☸️  Kubernetes Resources: $k8s_status/$total_envs environments ready"
    echo ""
    
    if [ "$health_status" = "$total_envs" ] && [ "$argocd_status" = "$total_envs" ] && [ "$k8s_status" = "$total_envs" ]; then
        log_success "🎉 ALL ENVIRONMENTS ARE FULLY OPERATIONAL!"
        echo ""
        echo "🔗 Environment URLs:"
        echo "  📈 Production: https://fortinet.jclee.me (NodePort: 30777)"
        echo "  🧪 Staging: https://fortinet-staging.jclee.me (NodePort: 30779)"
        echo "  🔧 Development: https://fortinet-development.jclee.me (NodePort: 30778)"
        echo ""
        echo "🎯 Management URLs:"
        echo "  🚀 ArgoCD: https://argo.jclee.me/applications"
        echo "  🐳 Registry: https://registry.jclee.me"
        echo "  📊 Charts: https://charts.jclee.me"
        overall_status=0
    else
        log_warning "⚠️  SOME ENVIRONMENTS NEED ATTENTION"
        echo ""
        echo "🔧 Troubleshooting:"
        echo "  - Check pod logs: kubectl logs -n <namespace> -l app=fortinet --tail=100"
        echo "  - Force ArgoCD sync: argocd app sync <app-name> --prune --force"
        echo "  - Check deployment status: kubectl get deployments -n <namespace>"
        overall_status=1
    fi
    
    echo ""
    log_info "Check completed at $(date)"
    
    exit $overall_status
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi