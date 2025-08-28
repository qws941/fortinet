#!/bin/bash

# ArgoCD 애플리케이션 동기화 스크립트
# GitOps 파이프라인 자동 동기화

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 설정
APP_NAME="fortinet"
NAMESPACE="argocd"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      ArgoCD 애플리케이션 동기화            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# 1. 애플리케이션 상태 확인
echo -e "${GREEN}1. 애플리케이션 상태 확인...${NC}"
APP_STATUS=$(kubectl get application -n $NAMESPACE $APP_NAME -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
HEALTH_STATUS=$(kubectl get application -n $NAMESPACE $APP_NAME -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")

echo "  📊 동기화 상태: $APP_STATUS"
echo "  🏥 헬스 상태: $HEALTH_STATUS"

# 2. kubectl을 통한 동기화 (ArgoCD CLI 없이)
echo -e "${GREEN}2. 애플리케이션 동기화 시작...${NC}"

# Sync 리소스 생성을 위한 패치
kubectl patch application $APP_NAME -n $NAMESPACE --type merge -p '{
  "operation": {
    "sync": {
      "revision": "HEAD",
      "prune": true,
      "syncOptions": ["CreateNamespace=true"]
    }
  }
}' 2>/dev/null || true

# 대안: 수동으로 sync 트리거
echo "  🔄 동기화 트리거..."
kubectl patch application $APP_NAME -n $NAMESPACE --type merge -p '{
  "metadata": {
    "annotations": {
      "argocd.argoproj.io/refresh": "normal"
    }
  }
}' 2>/dev/null || true

# 3. 동기화 대기
echo -e "${GREEN}3. 동기화 진행 중...${NC}"
MAX_WAIT=60
WAIT_TIME=0

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    SYNC_STATUS=$(kubectl get application -n $NAMESPACE $APP_NAME -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
    
    if [ "$SYNC_STATUS" == "Synced" ]; then
        echo "  ✅ 동기화 완료!"
        break
    fi
    
    echo "  ⏳ 동기화 대기 중... ($WAIT_TIME/$MAX_WAIT 초)"
    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
done

# 4. 최종 상태 확인
echo -e "${GREEN}4. 최종 상태 확인...${NC}"
kubectl get application -n $NAMESPACE $APP_NAME -o wide

# 5. 리소스 상태 확인
echo -e "${GREEN}5. 배포된 리소스 확인...${NC}"
echo "  📦 Deployments:"
kubectl get deployments -n fortinet 2>/dev/null || echo "    No deployments found"
echo ""
echo "  🔗 Services:"
kubectl get svc -n fortinet 2>/dev/null || echo "    No services found"
echo ""
echo "  🏃 Pods:"
kubectl get pods -n fortinet 2>/dev/null || echo "    No pods found"

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           동기화 요약                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

if [ "$SYNC_STATUS" == "Synced" ]; then
    echo -e "${GREEN}✅ ArgoCD 애플리케이션 동기화 성공!${NC}"
else
    echo -e "${YELLOW}⚠️ 동기화가 완료되지 않았습니다.${NC}"
    echo "   수동 동기화가 필요할 수 있습니다:"
    echo "   1. ArgoCD UI에서 수동 동기화"
    echo "   2. argocd app sync $APP_NAME 명령 실행"
fi

echo ""
echo "🔗 ArgoCD UI: https://argo.jclee.me"
echo "📊 애플리케이션: https://argo.jclee.me/applications/$APP_NAME"