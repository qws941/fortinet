#!/bin/bash
# K8s 이미지 자동 업데이트 스크립트
# 이 스크립트를 cron에 등록하여 주기적으로 실행할 수 있습니다

set -e

# 설정
NAMESPACE="fortinet"
DEPLOYMENT="fortinet"
REGISTRY="registry.jclee.me"
IMAGE="fortinet"
LOG_FILE="/home/jclee/app/fortinet/logs/k8s-update.log"

# 로그 함수
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 현재 실행 중인 이미지 확인
get_current_image() {
    kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}'
}

# 최신 이미지 확인
check_latest_image() {
    # Docker registry API를 사용하여 최신 이미지 태그 확인
    # 또는 GitHub API를 사용하여 최신 커밋 확인
    curl -s "https://$REGISTRY/v2/$IMAGE/tags/list" | jq -r '.tags[]' | grep -E '^latest$|^[0-9a-f]{40}$' | sort -r | head -1
}

# 메인 업데이트 함수
update_deployment() {
    log "🔍 Checking for updates..."
    
    CURRENT_IMAGE=$(get_current_image)
    log "Current image: $CURRENT_IMAGE"
    
    # 강제로 최신 이미지 pull
    log "🔄 Forcing deployment restart to pull latest image..."
    kubectl rollout restart deployment/$DEPLOYMENT -n $NAMESPACE
    
    # 롤아웃 상태 확인
    log "⏳ Waiting for rollout to complete..."
    if kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=5m; then
        log "✅ Deployment updated successfully!"
        
        # Pod 상태 확인
        kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT
        
        # 헬스 체크
        sleep 30
        if curl -s https://fortinet.jclee.me/api/health > /dev/null; then
            log "✅ Health check passed!"
        else
            log "⚠️ Health check failed!"
        fi
    else
        log "❌ Rollout failed!"
        exit 1
    fi
}

# 스크립트 실행
main() {
    log "======================================"
    log "🚀 Starting K8s auto-update check"
    
    # kubectl 사용 가능 여부 확인
    if ! command -v kubectl &> /dev/null; then
        log "❌ kubectl not found!"
        exit 1
    fi
    
    # 네임스페이스 존재 여부 확인
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        log "❌ Namespace $NAMESPACE not found!"
        exit 1
    fi
    
    # 업데이트 실행
    update_deployment
    
    log "🎯 Auto-update check completed"
    log "======================================"
}

# 스크립트 실행
main "$@"