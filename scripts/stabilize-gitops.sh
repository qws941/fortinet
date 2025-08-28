#!/bin/bash

# GitOps 상태 안정화 스크립트
# 시스템의 GitOps 상태를 점검하고 안정화합니다

set -e

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "============================================"
echo "   GitOps 상태 안정화 스크립트"
echo "============================================"
echo ""

# 1. Git 상태 확인
echo -e "${YELLOW}[1/8] Git 상태 확인${NC}"
if [ -z "$(git status --porcelain)" ]; then
    echo -e "${GREEN}✓ Git 작업 트리가 깨끗합니다${NC}"
else
    echo -e "${RED}✗ 커밋되지 않은 변경사항이 있습니다${NC}"
    git status --short
fi

# 2. 현재 브랜치 및 커밋 정보
echo -e "\n${YELLOW}[2/8] 현재 Git 정보${NC}"
CURRENT_BRANCH=$(git branch --show-current)
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "브랜치: $CURRENT_BRANCH"
echo "커밋: $CURRENT_COMMIT"
echo "태그: ${CURRENT_BRANCH}-${CURRENT_COMMIT}"

# 3. Kubernetes 연결 확인
echo -e "\n${YELLOW}[3/8] Kubernetes 클러스터 연결${NC}"
if kubectl cluster-info &>/dev/null; then
    echo -e "${GREEN}✓ Kubernetes 클러스터 연결 성공${NC}"
    kubectl version --short | head -n 2
else
    echo -e "${RED}✗ Kubernetes 클러스터 연결 실패${NC}"
    exit 1
fi

# 4. Namespace 확인
echo -e "\n${YELLOW}[4/8] Namespace 상태${NC}"
if kubectl get namespace fortinet &>/dev/null; then
    echo -e "${GREEN}✓ fortinet namespace 존재${NC}"
else
    echo -e "${YELLOW}! fortinet namespace 생성 중...${NC}"
    kubectl create namespace fortinet
fi

# 5. Deployment 상태
echo -e "\n${YELLOW}[5/8] Deployment 상태${NC}"
kubectl get deployment -n fortinet -o wide || true
REPLICAS=$(kubectl get deployment fortinet -n fortinet -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
DESIRED=$(kubectl get deployment fortinet -n fortinet -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")

if [ "$REPLICAS" = "$DESIRED" ] && [ "$REPLICAS" != "0" ]; then
    echo -e "${GREEN}✓ Deployment 정상 (${REPLICAS}/${DESIRED} replicas)${NC}"
else
    echo -e "${YELLOW}! Deployment 상태 이상 (${REPLICAS}/${DESIRED} replicas)${NC}"
fi

# 6. Pod 상태
echo -e "\n${YELLOW}[6/8] Pod 상태${NC}"
kubectl get pods -n fortinet -o wide
RUNNING_PODS=$(kubectl get pods -n fortinet --field-selector=status.phase=Running -o name | wc -l)
echo -e "실행 중인 Pod: ${RUNNING_PODS}개"

# 7. Service 상태
echo -e "\n${YELLOW}[7/8] Service 상태${NC}"
kubectl get svc -n fortinet
NODEPORT=$(kubectl get svc fortinet -n fortinet -o jsonpath='{.spec.ports[0].nodePort}' 2>/dev/null || echo "30777")
echo "NodePort: $NODEPORT"

# 8. 헬스체크
echo -e "\n${YELLOW}[8/8] 애플리케이션 헬스체크${NC}"
HEALTH_URL="http://192.168.50.110:${NODEPORT}/api/health"
if curl -s -f --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ 헬스체크 성공${NC}"
    echo "상세 정보:"
    curl -s "$HEALTH_URL" | jq -r '.status, .version, .build_info.immutable_tag' 2>/dev/null | while read line; do
        echo "  - $line"
    done
else
    echo -e "${RED}✗ 헬스체크 실패${NC}"
fi

# 9. 안정화 작업
echo -e "\n${YELLOW}=== 안정화 작업 ===${NC}"

# ConfigMap 업데이트
echo "ConfigMap 업데이트 중..."
cat <<EOF | kubectl apply -f - >/dev/null
apiVersion: v1
kind: ConfigMap
metadata:
  name: fortinet-config
  namespace: fortinet
data:
  GIT_BRANCH: "$CURRENT_BRANCH"
  GIT_SHA: "$CURRENT_COMMIT"
  IMMUTABLE_TAG: "${CURRENT_BRANCH}-${CURRENT_COMMIT}"
  LAST_STABLE: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EOF
echo -e "${GREEN}✓ ConfigMap 업데이트 완료${NC}"

# Image Pull Secret 확인
if kubectl get secret harbor-registry -n fortinet &>/dev/null; then
    echo -e "${GREEN}✓ Image Pull Secret 존재${NC}"
else
    echo -e "${YELLOW}! Image Pull Secret이 없습니다. 생성이 필요할 수 있습니다.${NC}"
fi

# 10. 최종 상태 요약
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}   GitOps 상태 안정화 완료${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "요약:"
echo "  - Git: ${CURRENT_BRANCH}-${CURRENT_COMMIT}"
echo "  - Deployment: ${REPLICAS}/${DESIRED} replicas"
echo "  - Pods: ${RUNNING_PODS}개 실행 중"
echo "  - Service: NodePort ${NODEPORT}"
echo "  - Health: ${HEALTH_URL}"
echo ""

# 추가 권장 사항
if [ "$REPLICAS" != "$DESIRED" ] || [ "$RUNNING_PODS" = "0" ]; then
    echo -e "${YELLOW}권장 사항:${NC}"
    echo "  1. Pod 로그 확인: kubectl logs -n fortinet -l app=fortinet"
    echo "  2. 이벤트 확인: kubectl get events -n fortinet --sort-by='.lastTimestamp'"
    echo "  3. 수동 재시작: kubectl rollout restart deployment/fortinet -n fortinet"
fi

echo ""
echo "완료!"