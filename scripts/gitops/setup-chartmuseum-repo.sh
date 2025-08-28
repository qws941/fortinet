#!/bin/bash

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ArgoCD ChartMuseum Repository 설정 ===${NC}"

# ChartMuseum 정보
CHARTMUSEUM_URL="https://charts.jclee.me"
REPO_NAME="chartmuseum"

echo -e "${BLUE}1. Kubectl을 통한 Repository 추가${NC}"

# Repository Secret 생성
kubectl create secret generic chartmuseum-repo \
  --from-literal=type=helm \
  --from-literal=url=${CHARTMUSEUM_URL} \
  --from-literal=name=${REPO_NAME} \
  --from-literal=username=admin \
  --from-literal=password=admin123 \
  --from-literal=insecure=true \
  -n argocd \
  --dry-run=client -o yaml | kubectl apply -f -

# Repository 리소스 생성
cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: chartmuseum-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
type: Opaque
stringData:
  type: helm
  name: chartmuseum
  url: ${CHARTMUSEUM_URL}
  username: admin
  password: admin123
  insecure-skip-server-verification: "true"
EOF

echo -e "${GREEN}✅ ChartMuseum repository 설정 완료${NC}"

# Repository 확인
echo -e "\n${BLUE}2. Repository 확인${NC}"
kubectl get secrets -n argocd -l argocd.argoproj.io/secret-type=repository

echo -e "\n${BLUE}3. ChartMuseum 기반 ArgoCD 애플리케이션 적용${NC}"
kubectl apply -f argocd/applications/fortinet.yaml

echo -e "\n${GREEN}✅ ChartMuseum 기반 ArgoCD 설정 완료!${NC}"