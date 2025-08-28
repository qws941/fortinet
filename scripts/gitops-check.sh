#!/bin/bash

# GitOps 전체 점검 스크립트

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        GitOps 전체 시스템 점검        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# 1. Git 상태
echo -e "${YELLOW}[1/7] Git Repository 상태${NC}"
BRANCH=$(git branch --show-current)
COMMIT=$(git rev-parse --short HEAD)
UNCOMMITTED=$(git status --porcelain | wc -l)

echo "  • Branch: ${BRANCH}"
echo "  • Commit: ${COMMIT}"
echo "  • Tag: ${BRANCH}-${COMMIT}"

if [ "$UNCOMMITTED" -eq 0 ]; then
    echo -e "  • ${GREEN}✓ 작업 트리 깨끗함${NC}"
else
    echo -e "  • ${YELLOW}⚠ 커밋되지 않은 변경사항: ${UNCOMMITTED}개${NC}"
fi
echo ""

# 2. ArgoCD 앱 목록
echo -e "${YELLOW}[2/7] ArgoCD Applications${NC}"
kubectl get application -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status --no-headers | while read name sync health; do
    if [ "$sync" = "Synced" ]; then
        sync_color="${GREEN}✓ ${sync}${NC}"
    else
        sync_color="${YELLOW}⚠ ${sync}${NC}"
    fi
    
    if [ "$health" = "Healthy" ]; then
        health_color="${GREEN}✓ ${health}${NC}"
    else
        health_color="${RED}✗ ${health}${NC}"
    fi
    
    echo -e "  • ${name}: ${sync_color} / ${health_color}"
done
echo ""

# 3. Fortinet 앱 상세
echo -e "${YELLOW}[3/7] Fortinet Application 상세${NC}"
SYNC_STATUS=$(kubectl get application fortinet -n argocd -o jsonpath='{.status.sync.status}')
HEALTH_STATUS=$(kubectl get application fortinet -n argocd -o jsonpath='{.status.health.status}')
REVISION=$(kubectl get application fortinet -n argocd -o jsonpath='{.status.sync.revision}' | cut -c1-7)
AUTO_SYNC=$(kubectl get application fortinet -n argocd -o jsonpath='{.spec.syncPolicy.automated}')

echo "  • Sync Status: ${SYNC_STATUS}"
echo "  • Health Status: ${HEALTH_STATUS}"
echo "  • Git Revision: ${REVISION}"

if [ -n "$AUTO_SYNC" ]; then
    echo -e "  • ${GREEN}✓ Auto-sync 활성화됨${NC}"
    echo "    - Prune: $(echo $AUTO_SYNC | jq -r '.prune // false')"
    echo "    - Self-heal: $(echo $AUTO_SYNC | jq -r '.selfHeal // false')"
else
    echo -e "  • ${YELLOW}⚠ Auto-sync 비활성화됨${NC}"
fi
echo ""

# 4. Kubernetes 리소스
echo -e "${YELLOW}[4/7] Kubernetes Resources (fortinet namespace)${NC}"
DEPLOY_READY=$(kubectl get deployment fortinet -n fortinet -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
DEPLOY_DESIRED=$(kubectl get deployment fortinet -n fortinet -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
POD_COUNT=$(kubectl get pods -n fortinet --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l)

echo "  • Deployment: ${DEPLOY_READY}/${DEPLOY_DESIRED} replicas ready"
echo "  • Running Pods: ${POD_COUNT}"

kubectl get pods -n fortinet --no-headers 2>/dev/null | while read name ready status restarts age; do
    if [ "$status" = "Running" ]; then
        echo -e "    - ${name}: ${GREEN}✓ ${status}${NC} (Restarts: ${restarts})"
    else
        echo -e "    - ${name}: ${RED}✗ ${status}${NC} (Restarts: ${restarts})"
    fi
done
echo ""

# 5. Service & Ingress
echo -e "${YELLOW}[5/7] Service & Ingress${NC}"
SVC_TYPE=$(kubectl get svc fortinet -n fortinet -o jsonpath='{.spec.type}' 2>/dev/null)
NODE_PORT=$(kubectl get svc fortinet -n fortinet -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null)
INGRESS_HOST=$(kubectl get ingress -n fortinet -o jsonpath='{.items[0].spec.rules[0].host}' 2>/dev/null)

echo "  • Service Type: ${SVC_TYPE}"
echo "  • NodePort: ${NODE_PORT}"
if [ -n "$INGRESS_HOST" ]; then
    echo "  • Ingress Host: ${INGRESS_HOST}"
fi
echo ""

# 6. 애플리케이션 헬스체크
echo -e "${YELLOW}[6/7] Application Health Check${NC}"
HEALTH_URL="http://192.168.50.110:30777/api/health"

if curl -s -f --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    HEALTH_DATA=$(curl -s "$HEALTH_URL")
    APP_STATUS=$(echo "$HEALTH_DATA" | jq -r '.status')
    APP_VERSION=$(echo "$HEALTH_DATA" | jq -r '.version')
    APP_TAG=$(echo "$HEALTH_DATA" | jq -r '.build_info.immutable_tag')
    APP_UPTIME=$(echo "$HEALTH_DATA" | jq -r '.uptime')
    
    echo -e "  • ${GREEN}✓ 헬스체크 성공${NC}"
    echo "    - Status: ${APP_STATUS}"
    echo "    - Version: ${APP_VERSION}"
    echo "    - Image Tag: ${APP_TAG}"
    echo "    - Uptime: ${APP_UPTIME}"
else
    echo -e "  • ${RED}✗ 헬스체크 실패${NC}"
    echo "    - URL: ${HEALTH_URL}"
fi
echo ""

# 7. GitOps 준수 상태
echo -e "${YELLOW}[7/7] GitOps Compliance${NC}"
COMPLIANCE_SCORE=0
TOTAL_CHECKS=6

# Check 1: Git clean
if [ "$UNCOMMITTED" -eq 0 ]; then
    echo -e "  ${GREEN}✓ Git 작업 트리 깨끗함${NC}"
    ((COMPLIANCE_SCORE++))
else
    echo -e "  ${YELLOW}⚠ 커밋되지 않은 변경사항 있음${NC}"
fi

# Check 2: ArgoCD sync
if [ "$SYNC_STATUS" = "Synced" ]; then
    echo -e "  ${GREEN}✓ ArgoCD 동기화 상태 정상${NC}"
    ((COMPLIANCE_SCORE++))
else
    echo -e "  ${YELLOW}⚠ ArgoCD 동기화 필요${NC}"
fi

# Check 3: Health status
if [ "$HEALTH_STATUS" = "Healthy" ]; then
    echo -e "  ${GREEN}✓ 애플리케이션 상태 정상${NC}"
    ((COMPLIANCE_SCORE++))
else
    echo -e "  ${RED}✗ 애플리케이션 상태 이상${NC}"
fi

# Check 4: Auto-sync enabled
if [ -n "$AUTO_SYNC" ]; then
    echo -e "  ${GREEN}✓ 자동 동기화 활성화${NC}"
    ((COMPLIANCE_SCORE++))
else
    echo -e "  ${YELLOW}⚠ 자동 동기화 비활성화${NC}"
fi

# Check 5: All pods running
if [ "$POD_COUNT" -gt 0 ] && [ "$DEPLOY_READY" = "$DEPLOY_DESIRED" ]; then
    echo -e "  ${GREEN}✓ 모든 Pod 실행 중${NC}"
    ((COMPLIANCE_SCORE++))
else
    echo -e "  ${RED}✗ Pod 상태 이상${NC}"
fi

# Check 6: Health endpoint responsive
if [ "$APP_STATUS" = "healthy" ]; then
    echo -e "  ${GREEN}✓ 헬스 엔드포인트 정상${NC}"
    ((COMPLIANCE_SCORE++))
else
    echo -e "  ${RED}✗ 헬스 엔드포인트 이상${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════${NC}"
PERCENTAGE=$((COMPLIANCE_SCORE * 100 / TOTAL_CHECKS))

if [ "$PERCENTAGE" -ge 90 ]; then
    echo -e "${GREEN}GitOps Compliance Score: ${COMPLIANCE_SCORE}/${TOTAL_CHECKS} (${PERCENTAGE}%) - EXCELLENT${NC}"
elif [ "$PERCENTAGE" -ge 70 ]; then
    echo -e "${YELLOW}GitOps Compliance Score: ${COMPLIANCE_SCORE}/${TOTAL_CHECKS} (${PERCENTAGE}%) - GOOD${NC}"
else
    echo -e "${RED}GitOps Compliance Score: ${COMPLIANCE_SCORE}/${TOTAL_CHECKS} (${PERCENTAGE}%) - NEEDS IMPROVEMENT${NC}"
fi
echo -e "${BLUE}════════════════════════════════════════${NC}"
echo ""

# 액션 아이템
if [ "$COMPLIANCE_SCORE" -lt "$TOTAL_CHECKS" ]; then
    echo -e "${YELLOW}권장 조치:${NC}"
    
    if [ "$UNCOMMITTED" -gt 0 ]; then
        echo "  • Git 변경사항 커밋: git add -A && git commit -m 'message'"
    fi
    
    if [ "$SYNC_STATUS" != "Synced" ]; then
        echo "  • ArgoCD 동기화: argocd app sync fortinet"
    fi
    
    if [ -z "$AUTO_SYNC" ]; then
        echo "  • 자동 동기화 활성화: kubectl patch application fortinet -n argocd --type merge -p '{\"spec\":{\"syncPolicy\":{\"automated\":{\"prune\":true,\"selfHeal\":true}}}}'"
    fi
    
    if [ "$POD_COUNT" -eq 0 ] || [ "$DEPLOY_READY" != "$DEPLOY_DESIRED" ]; then
        echo "  • Pod 재시작: kubectl rollout restart deployment/fortinet -n fortinet"
    fi
fi

echo ""
echo "점검 완료: $(date '+%Y-%m-%d %H:%M:%S')"