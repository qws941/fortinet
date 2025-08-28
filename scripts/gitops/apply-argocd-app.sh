#!/bin/bash

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ArgoCD 애플리케이션 매니페스트 적용 ===${NC}"

echo -e "${BLUE}1. Git 기반 ArgoCD 애플리케이션 적용${NC}"
if kubectl apply -f argocd/applications/fortinet-git.yaml; then
    echo -e "${GREEN}✓ Git 기반 ArgoCD 애플리케이션 적용 완료${NC}"
else
    echo -e "${RED}✗ Git 기반 ArgoCD 애플리케이션 적용 실패${NC}"
fi

echo -e "\n${BLUE}2. 애플리케이션 상태 확인${NC}"
sleep 5
kubectl get applications -n argocd | grep fortinet || echo "애플리케이션을 찾을 수 없습니다"

echo -e "\n${BLUE}3. Pods 상태 확인${NC}"
kubectl get pods -n fortinet

echo -e "\n${GREEN}✅ ArgoCD 애플리케이션 매니페스트 적용 완료!${NC}"
echo -e "${BLUE}ArgoCD 웹 UI에서 확인하세요: https://argo.jclee.me${NC}"
echo -e "${BLUE}애플리케이션 URL: http://192.168.50.110:30779${NC}"