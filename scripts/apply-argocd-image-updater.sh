#!/bin/bash
# ArgoCD Image Updater 설정 적용 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 ArgoCD Image Updater 설정 시작${NC}"

# ArgoCD 로그인 확인
echo -e "${BLUE}1️⃣ ArgoCD 연결 확인${NC}"
if ! argocd app list &>/dev/null; then
    echo -e "${YELLOW}ArgoCD에 로그인이 필요합니다${NC}"
    echo "argocd login argo.jclee.me --username admin --password <password> --insecure --grpc-web"
    exit 1
fi
echo -e "${GREEN}✅ ArgoCD 연결 확인됨${NC}"

# Image Updater 설치 확인
echo -e "${BLUE}2️⃣ ArgoCD Image Updater 설치 확인${NC}"
if kubectl -n argocd get deployment argocd-image-updater &>/dev/null; then
    echo -e "${GREEN}✅ Image Updater가 이미 설치되어 있습니다${NC}"
else
    echo -e "${YELLOW}Image Updater 설치 중...${NC}"
    kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj-labs/argocd-image-updater/stable/manifests/install.yaml
    
    # 설치 대기
    kubectl -n argocd wait --for=condition=available --timeout=300s deployment/argocd-image-updater
    echo -e "${GREEN}✅ Image Updater 설치 완료${NC}"
fi

# Registry 설정 적용
echo -e "${BLUE}3️⃣ Registry 설정 적용${NC}"
if [ -f "argocd/image-updater-config.yaml" ]; then
    kubectl apply -f argocd/image-updater-config.yaml
    echo -e "${GREEN}✅ Registry 설정 적용 완료${NC}"
else
    echo -e "${YELLOW}⚠️  argocd/image-updater-config.yaml 파일이 없습니다${NC}"
fi

# 기존 앱 확인
echo -e "${BLUE}4️⃣ 기존 ArgoCD Application 확인${NC}"
if argocd app get fortinet &>/dev/null; then
    echo -e "${YELLOW}기존 fortinet 앱이 존재합니다${NC}"
    read -p "기존 앱을 삭제하고 새로 생성하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        argocd app delete fortinet --cascade -y
        echo -e "${GREEN}✅ 기존 앱 삭제 완료${NC}"
        sleep 5
    else
        echo -e "${YELLOW}기존 앱을 유지합니다${NC}"
        exit 0
    fi
fi

# 새 앱 생성
echo -e "${BLUE}5️⃣ Image Updater가 설정된 새 Application 생성${NC}"
kubectl apply -f argocd/fortinet-app.yaml
echo -e "${GREEN}✅ Application 생성 완료${NC}"

# 앱 동기화
echo -e "${BLUE}6️⃣ 초기 동기화 실행${NC}"
sleep 5
argocd app sync fortinet
echo -e "${GREEN}✅ 동기화 완료${NC}"

# Image Updater 로그 확인
echo -e "${BLUE}7️⃣ Image Updater 상태 확인${NC}"
echo -e "${YELLOW}Image Updater 로그 (최근 10줄):${NC}"
kubectl -n argocd logs -l app.kubernetes.io/name=argocd-image-updater --tail=10

# 최종 안내
echo -e "${GREEN}🎉 ArgoCD Image Updater 설정 완료!${NC}"
echo ""
echo -e "${BLUE}다음 단계:${NC}"
echo "1. 코드를 push하면 자동으로 이미지가 빌드됩니다"
echo "2. Image Updater가 새 이미지를 감지하고 자동 배포합니다"
echo "3. 배포 완료 후 오프라인 TAR가 자동 생성됩니다"
echo ""
echo -e "${BLUE}모니터링:${NC}"
echo "• ArgoCD UI: https://argo.jclee.me/applications/fortinet"
echo "• Image Updater 로그: kubectl -n argocd logs -l app.kubernetes.io/name=argocd-image-updater -f"
echo "• GitHub Actions: https://github.com/JCLEE94/fortinet/actions"