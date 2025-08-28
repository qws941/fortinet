#!/bin/bash

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Kubernetes 리소스 설정 ===${NC}"

# 네임스페이스 생성
NAMESPACE="fortinet"

echo -e "${BLUE}1. 네임스페이스 생성${NC}"
if kubectl get namespace ${NAMESPACE} &>/dev/null; then
    echo -e "${GREEN}✓ 네임스페이스 ${NAMESPACE}가 이미 존재합니다${NC}"
else
    kubectl create namespace ${NAMESPACE}
    echo -e "${GREEN}✓ 네임스페이스 ${NAMESPACE} 생성 완료${NC}"
fi

echo -e "\n${BLUE}2. Harbor Registry Secret 생성${NC}"
REGISTRY_URL="registry.jclee.me"
REGISTRY_USERNAME="admin"

# Harbor registry secret 확인 및 생성
if kubectl get secret harbor-registry -n ${NAMESPACE} &>/dev/null; then
    echo -e "${GREEN}✓ Harbor registry secret이 이미 존재합니다${NC}"
else
    echo -e "${YELLOW}Harbor registry 비밀번호를 입력하세요:${NC}"
    read -rs REGISTRY_PASSWORD
    
    kubectl create secret docker-registry harbor-registry \
        --docker-server=${REGISTRY_URL} \
        --docker-username=${REGISTRY_USERNAME} \
        --docker-password=${REGISTRY_PASSWORD} \
        --namespace=${NAMESPACE}
    
    echo -e "${GREEN}✓ Harbor registry secret 생성 완료${NC}"
fi

echo -e "\n${BLUE}3. ArgoCD 네임스페이스에도 registry secret 생성${NC}"
if kubectl get secret harbor-registry -n argocd &>/dev/null; then
    echo -e "${GREEN}✓ ArgoCD 네임스페이스에 Harbor registry secret이 이미 존재합니다${NC}"
else
    if [ -z "${REGISTRY_PASSWORD:-}" ]; then
        echo -e "${YELLOW}Harbor registry 비밀번호를 입력하세요:${NC}"
        read -rs REGISTRY_PASSWORD
    fi
    
    kubectl create secret docker-registry harbor-registry \
        --docker-server=${REGISTRY_URL} \
        --docker-username=${REGISTRY_USERNAME} \
        --docker-password=${REGISTRY_PASSWORD} \
        --namespace=argocd
    
    echo -e "${GREEN}✓ ArgoCD 네임스페이스에 Harbor registry secret 생성 완료${NC}"
fi

echo -e "\n${BLUE}4. 설정 확인${NC}"
echo -e "${YELLOW}네임스페이스:${NC}"
kubectl get namespace ${NAMESPACE}

echo -e "\n${YELLOW}Secrets in ${NAMESPACE}:${NC}"
kubectl get secrets -n ${NAMESPACE}

echo -e "\n${YELLOW}Secrets in argocd:${NC}"
kubectl get secrets -n argocd | grep harbor-registry || echo "No harbor-registry secret found"

echo -e "\n${GREEN}✅ Kubernetes 리소스 설정 완료!${NC}"
echo -e "${BLUE}다음 단계: ArgoCD 애플리케이션 생성${NC}"