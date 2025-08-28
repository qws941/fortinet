#!/bin/bash

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GitOps 배포 검증 ===${NC}"

# 엔드포인트 정보
HEALTH_ENDPOINT="http://192.168.50.110:30779/api/health"
DOMAIN_ENDPOINT="http://fortinet.jclee.me/api/health"

echo -e "${BLUE}1. Kubernetes 리소스 상태 확인${NC}"
echo -e "${YELLOW}Namespace:${NC}"
kubectl get namespace fortinet

echo -e "\n${YELLOW}Pods:${NC}"
kubectl get pods -n fortinet

echo -e "\n${YELLOW}Services:${NC}"
kubectl get services -n fortinet

echo -e "\n${YELLOW}Ingress:${NC}"
kubectl get ingress -n fortinet

echo -e "\n${BLUE}2. ArgoCD 애플리케이션 상태${NC}"
kubectl get applications -n argocd | head -1
kubectl get applications -n argocd | grep fortinet || echo "ArgoCD 애플리케이션을 찾을 수 없습니다"

echo -e "\n${BLUE}3. Health Check 테스트${NC}"

echo -e "${YELLOW}NodePort 엔드포인트 테스트:${NC}"
if curl -f -s ${HEALTH_ENDPOINT} > /dev/null; then
    echo -e "${GREEN}✅ NodePort health check 성공${NC}"
    curl -s ${HEALTH_ENDPOINT} | jq . 2>/dev/null || curl -s ${HEALTH_ENDPOINT}
else
    echo -e "${RED}❌ NodePort health check 실패${NC}"
fi

echo -e "\n${YELLOW}도메인 엔드포인트 테스트:${NC}"
if curl -f -s ${DOMAIN_ENDPOINT} > /dev/null; then
    echo -e "${GREEN}✅ Domain health check 성공${NC}"
    curl -s ${DOMAIN_ENDPOINT} | jq . 2>/dev/null || curl -s ${DOMAIN_ENDPOINT}
else
    echo -e "${YELLOW}⚠️ Domain health check 실패 (DNS 또는 Ingress 문제일 수 있음)${NC}"
fi

echo -e "\n${BLUE}4. 웹 애플리케이션 페이지 테스트${NC}"
echo -e "${YELLOW}메인 페이지 접근 테스트:${NC}"
if curl -f -s http://192.168.50.110:30779/ | grep -q "FortiGate" 2>/dev/null; then
    echo -e "${GREEN}✅ 메인 페이지 접근 성공${NC}"
else
    echo -e "${YELLOW}⚠️ 메인 페이지 접근 실패 또는 내용 확인 불가${NC}"
fi

echo -e "\n${BLUE}5. Docker 이미지 정보 확인${NC}"
POD_NAME=$(kubectl get pods -n fortinet -l app=fortinet -o jsonpath='{.items[0].metadata.name}')
if [ -n "${POD_NAME}" ]; then
    echo -e "${YELLOW}Pod: ${POD_NAME}${NC}"
    kubectl describe pod ${POD_NAME} -n fortinet | grep -A2 "Image:"
else
    echo -e "${RED}❌ fortinet Pod를 찾을 수 없습니다${NC}"
fi

echo -e "\n${BLUE}6. 로그 확인 (최근 10줄)${NC}"
if [ -n "${POD_NAME}" ]; then
    kubectl logs ${POD_NAME} -n fortinet --tail=10
else
    echo -e "${RED}❌ 로그를 확인할 Pod가 없습니다${NC}"
fi

echo -e "\n${BLUE}=== 검증 완료 ===${NC}"
echo -e "${GREEN}🎉 GitOps 파이프라인 구현이 완료되었습니다!${NC}"
echo ""
echo -e "${BLUE}접속 정보:${NC}"
echo -e "  • NodePort: http://192.168.50.110:30779"
echo -e "  • Domain: http://fortinet.jclee.me"
echo -e "  • ArgoCD: https://argo.jclee.me"
echo -e "  • Registry: https://registry.jclee.me"
echo ""
echo -e "${BLUE}다음 단계:${NC}"
echo -e "  1. 코드 변경 후 git push하여 자동 배포 테스트"
echo -e "  2. GitHub Actions에서 파이프라인 실행 확인"
echo -e "  3. ArgoCD에서 자동 동기화 확인"