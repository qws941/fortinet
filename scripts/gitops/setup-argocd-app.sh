#!/bin/bash

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== ArgoCD 애플리케이션 설정 ===${NC}"

# ArgoCD 설정
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_USERNAME="admin"
ARGOCD_PASSWORD="bingogo1"

# 애플리케이션 정보
APP_NAME="fortinet"
NAMESPACE="fortinet"

echo -e "${BLUE}1. ArgoCD 로그인${NC}"
if argocd login ${ARGOCD_SERVER} \
    --username ${ARGOCD_USERNAME} \
    --password ${ARGOCD_PASSWORD} \
    --insecure \
    --grpc-web; then
    echo -e "${GREEN}✓ ArgoCD 로그인 성공${NC}"
else
    echo -e "${RED}✗ ArgoCD 로그인 실패${NC}"
    echo "ArgoCD CLI가 설치되어 있는지 확인하세요"
    exit 1
fi

echo -e "\n${BLUE}2. Helm Repository 추가 (ChartMuseum)${NC}"
# ArgoCD에 Helm repository 추가
REPO_NAME="chartmuseum"
REPO_URL="https://charts.jclee.me"

if argocd repo list | grep -q "${REPO_URL}"; then
    echo -e "${GREEN}✓ Helm repository가 이미 등록되어 있습니다${NC}"
else
    echo -e "${YELLOW}ChartMuseum 사용자명을 입력하세요 (기본값: admin):${NC}"
    read -r CHARTMUSEUM_USERNAME
    CHARTMUSEUM_USERNAME=${CHARTMUSEUM_USERNAME:-admin}
    
    echo -e "${YELLOW}ChartMuseum 비밀번호를 입력하세요:${NC}"
    read -rs CHARTMUSEUM_PASSWORD
    
    argocd repo add ${REPO_URL} \
        --type helm \
        --name ${REPO_NAME} \
        --username ${CHARTMUSEUM_USERNAME} \
        --password ${CHARTMUSEUM_PASSWORD} \
        --insecure-skip-server-verification
    
    echo -e "${GREEN}✓ Helm repository 추가 완료${NC}"
fi

echo -e "\n${BLUE}3. Git Repository 추가${NC}"
GIT_REPO="https://github.com/JCLEE94/fortinet.git"

if argocd repo list | grep -q "${GIT_REPO}"; then
    echo -e "${GREEN}✓ Git repository가 이미 등록되어 있습니다${NC}"
else
    argocd repo add ${GIT_REPO}
    echo -e "${GREEN}✓ Git repository 추가 완료${NC}"
fi

echo -e "\n${BLUE}4. ArgoCD 애플리케이션 생성${NC}"
# 기존 애플리케이션 확인
if argocd app get ${APP_NAME} &>/dev/null; then
    echo -e "${YELLOW}기존 애플리케이션을 삭제하고 다시 생성하시겠습니까? (y/N)${NC}"
    read -r CONFIRM
    if [[ "${CONFIRM}" =~ ^[Yy]$ ]]; then
        argocd app delete ${APP_NAME} --yes
        echo -e "${GREEN}✓ 기존 애플리케이션 삭제 완료${NC}"
    else
        echo -e "${YELLOW}기존 애플리케이션을 유지합니다${NC}"
        SKIP_CREATE=true
    fi
fi

if [ -z "${SKIP_CREATE:-}" ]; then
    echo -e "${YELLOW}어떤 방식으로 애플리케이션을 생성하시겠습니까?${NC}"
    echo "1) ChartMuseum에서 Helm 차트 사용"
    echo "2) Git 리포지토리에서 Helm 차트 사용"
    read -r CHOICE
    
    case ${CHOICE} in
        1)
            echo -e "${BLUE}ChartMuseum에서 애플리케이션 생성${NC}"
            kubectl apply -f argocd/applications/fortinet.yaml
            ;;
        2)
            echo -e "${BLUE}Git 리포지토리에서 애플리케이션 생성${NC}"
            kubectl apply -f argocd/applications/fortinet-git.yaml
            ;;
        *)
            echo -e "${BLUE}기본값: ChartMuseum에서 애플리케이션 생성${NC}"
            kubectl apply -f argocd/applications/fortinet.yaml
            ;;
    esac
    
    echo -e "${GREEN}✓ ArgoCD 애플리케이션 생성 완료${NC}"
fi

echo -e "\n${BLUE}5. 애플리케이션 동기화${NC}"
# 잠시 대기 후 동기화
sleep 5

if argocd app sync ${APP_NAME}; then
    echo -e "${GREEN}✓ 애플리케이션 동기화 성공${NC}"
else
    echo -e "${YELLOW}! 애플리케이션 동기화 실패 - 수동으로 확인하세요${NC}"
fi

echo -e "\n${BLUE}6. 애플리케이션 상태 확인${NC}"
argocd app get ${APP_NAME}

echo -e "\n${GREEN}✅ ArgoCD 애플리케이션 설정 완료!${NC}"
echo -e "${BLUE}ArgoCD 웹 UI에서 확인하세요: https://${ARGOCD_SERVER}${NC}"
echo -e "${BLUE}애플리케이션 URL: http://192.168.50.110:30779${NC}"