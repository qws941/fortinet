#!/bin/bash
# ArgoCD 배포 완료 감지 및 오프라인 TAR 생성 트리거

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ArgoCD 상태 모니터링
monitor_deployment() {
    local APP_NAME="fortinet"
    local MAX_WAIT=300  # 5분 대기
    local CHECK_INTERVAL=10
    local ELAPSED=0
    
    echo -e "${BLUE}🔍 ArgoCD 배포 상태 모니터링 시작${NC}"
    
    while [ $ELAPSED -lt $MAX_WAIT ]; do
        # ArgoCD CLI로 상태 확인
        SYNC_STATUS=$(argocd app get $APP_NAME -o json 2>/dev/null | jq -r '.status.sync.status' || echo "Unknown")
        HEALTH_STATUS=$(argocd app get $APP_NAME -o json 2>/dev/null | jq -r '.status.health.status' || echo "Unknown")
        
        echo -e "⏱️  경과 시간: ${ELAPSED}초 | Sync: $SYNC_STATUS | Health: $HEALTH_STATUS"
        
        if [[ "$SYNC_STATUS" == "Synced" && "$HEALTH_STATUS" == "Healthy" ]]; then
            echo -e "${GREEN}✅ 배포 완료 확인!${NC}"
            
            # 현재 배포된 이미지 태그 가져오기
            IMAGE_TAG=$(argocd app get $APP_NAME -o json | \
                jq -r '.status.summary.images[0]' | \
                grep -oP '(?<=:)[a-f0-9]{40}$' || echo "latest")
            
            echo -e "${BLUE}📦 배포된 이미지 태그: $IMAGE_TAG${NC}"
            
            # GitHub Actions 워크플로우 트리거
            trigger_offline_build "$IMAGE_TAG"
            return 0
        fi
        
        sleep $CHECK_INTERVAL
        ELAPSED=$((ELAPSED + CHECK_INTERVAL))
    done
    
    echo -e "${YELLOW}⚠️  타임아웃: 배포가 완료되지 않았습니다${NC}"
    return 1
}

# GitHub Actions 오프라인 빌드 트리거
trigger_offline_build() {
    local IMAGE_TAG=$1
    
    echo -e "${BLUE}🚀 오프라인 TAR 생성 워크플로우 트리거${NC}"
    
    # GitHub API를 통한 workflow dispatch
    curl -X POST \
        -H "Authorization: token ${GITHUB_TOKEN}" \
        -H "Accept: application/vnd.github.v3+json" \
        https://api.github.com/repos/JCLEE94/fortinet/actions/workflows/offline-tar.yml/dispatches \
        -d "{\"ref\":\"master\",\"inputs\":{\"image_tag\":\"$IMAGE_TAG\"}}"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 오프라인 빌드 워크플로우 시작됨${NC}"
        echo -e "📊 진행 상황: https://github.com/JCLEE94/fortinet/actions"
    else
        echo -e "${YELLOW}❌ 워크플로우 트리거 실패${NC}"
        return 1
    fi
}

# 메인 실행
main() {
    # GitHub Token 확인
    if [ -z "$GITHUB_TOKEN" ]; then
        echo -e "${YELLOW}⚠️  GITHUB_TOKEN이 설정되지 않았습니다${NC}"
        echo "export GITHUB_TOKEN=your-github-token"
        exit 1
    fi
    
    # ArgoCD 로그인 확인
    if ! argocd app list &>/dev/null; then
        echo -e "${YELLOW}⚠️  ArgoCD에 로그인되지 않았습니다${NC}"
        echo "argocd login argo.jclee.me --username admin --password <password>"
        exit 1
    fi
    
    # 배포 모니터링 시작
    monitor_deployment
}

# 스크립트 실행
main "$@"