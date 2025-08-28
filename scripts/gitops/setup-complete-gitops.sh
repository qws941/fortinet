#!/bin/bash

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}    GitOps CI/CD 완전 자동화 설정${NC}"
echo -e "${CYAN}========================================${NC}"

# 현재 디렉토리 확인
if [ ! -f "CLAUDE.md" ]; then
    echo -e "${RED}❌ CLAUDE.md 파일이 없습니다. 프로젝트 루트에서 실행하세요.${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 GitOps CI/CD 파이프라인 자동 설정을 시작합니다...${NC}"
echo ""

# 단계별 실행
STEPS=(
    "GitHub Secrets 설정"
    "Kubernetes 리소스 설정" 
    "ArgoCD 애플리케이션 적용"
    "배포 검증"
)

SCRIPTS=(
    "scripts/gitops/setup-github-secrets.sh"
    "scripts/gitops/setup-k8s-resources.sh"
    "scripts/gitops/apply-argocd-app.sh"
    "scripts/gitops/verify-deployment.sh"
)

for i in "${!STEPS[@]}"; do
    step=$((i + 1))
    echo -e "${BLUE}=== 단계 ${step}/4: ${STEPS[i]} ===${NC}"
    
    if [ -f "${SCRIPTS[i]}" ]; then
        if ./"${SCRIPTS[i]}"; then
            echo -e "${GREEN}✅ 단계 ${step} 완료${NC}"
        else
            echo -e "${RED}❌ 단계 ${step} 실패${NC}"
            echo -e "${YELLOW}수동으로 확인하세요: ${SCRIPTS[i]}${NC}"
        fi
    else
        echo -e "${RED}❌ 스크립트를 찾을 수 없습니다: ${SCRIPTS[i]}${NC}"
    fi
    
    echo ""
    
    # 다음 단계로 넘어가기 전 잠시 대기
    if [ $step -lt 4 ]; then
        echo -e "${YELLOW}다음 단계로 계속하려면 Enter를 누르세요...${NC}"
        read -r
    fi
done

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}         설정 완료 요약${NC}"
echo -e "${CYAN}========================================${NC}"

echo -e "${GREEN}🎉 GitOps CI/CD 파이프라인 설정이 완료되었습니다!${NC}"
echo ""

echo -e "${BLUE}📋 설정된 구성 요소:${NC}"
echo -e "  ✅ GitHub Actions 워크플로우"
echo -e "  ✅ Kubernetes 네임스페이스 및 시크릿"
echo -e "  ✅ ArgoCD 애플리케이션"
echo -e "  ✅ Helm 차트 구조"
echo -e "  ✅ Docker Registry 연동"
echo ""

echo -e "${BLUE}🔗 접속 정보:${NC}"
echo -e "  • 애플리케이션: http://192.168.50.110:30779"
echo -e "  • 도메인: http://fortinet.jclee.me"
echo -e "  • ArgoCD: https://argo.jclee.me"
echo -e "  • Harbor Registry: https://registry.jclee.me"
echo -e "  • ChartMuseum: https://charts.jclee.me"
echo ""

echo -e "${BLUE}🚀 파이프라인 테스트 방법:${NC}"
echo -e "  1. 코드 변경 후 커밋 & 푸시:"
echo -e "     ${CYAN}git add . && git commit -m \"feat: test gitops pipeline\" && git push origin master${NC}"
echo -e "  2. GitHub Actions 워크플로우 확인:"
echo -e "     ${CYAN}https://github.com/JCLEE94/fortinet/actions${NC}"
echo -e "  3. ArgoCD에서 자동 동기화 확인:"
echo -e "     ${CYAN}https://argo.jclee.me/applications/fortinet-git${NC}"
echo ""

echo -e "${BLUE}📁 생성된 파일들:${NC}"
echo -e "  • .github/workflows/gitops-pipeline.yml"
echo -e "  • argocd/applications/fortinet.yaml"
echo -e "  • argocd/applications/fortinet-git.yaml"
echo -e "  • scripts/gitops/setup-*.sh"
echo ""

echo -e "${YELLOW}⚠️  참고사항:${NC}"
echo -e "  • ArgoCD Image Updater가 설정되어 자동으로 이미지 업데이트됩니다"
echo -e "  • 마스터 브랜치에 푸시할 때마다 자동 배포됩니다"
echo -e "  • ChartMuseum 또는 Git 기반 Helm 배포 중 선택 가능합니다"
echo ""

echo -e "${GREEN}✨ GitOps 여정을 시작하세요! ✨${NC}"