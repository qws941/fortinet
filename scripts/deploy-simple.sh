#!/bin/bash
# 간단한 배포 스크립트

set -e

# 색상 코드
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 FortiGate Nextrade 배포 시작${NC}"

# Git 변경사항 확인
if [[ -n $(git status -s) ]]; then
    echo -e "${YELLOW}⚠️  커밋되지 않은 변경사항이 있습니다${NC}"
    read -p "계속하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 현재 브랜치 확인
BRANCH=$(git branch --show-current)
echo -e "📌 현재 브랜치: ${YELLOW}$BRANCH${NC}"

# main/master 브랜치가 아닌 경우 경고
if [[ "$BRANCH" != "main" && "$BRANCH" != "master" ]]; then
    echo -e "${YELLOW}⚠️  프로덕션 브랜치가 아닙니다${NC}"
    read -p "계속하시겠습니까? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Push to GitHub
echo -e "${GREEN}📤 GitHub에 푸시 중...${NC}"
git push origin $BRANCH

echo -e "${GREEN}✅ 배포가 시작되었습니다!${NC}"
echo ""
echo "모니터링:"
echo "  • GitHub Actions: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:\/]\(.*\)\.git/\1/')/actions"
echo "  • ArgoCD: https://argo.jclee.me/applications/fortinet"
echo "  • 애플리케이션: https://fortinet.jclee.me"
echo ""
echo "ArgoCD는 3분 이내에 자동으로 동기화됩니다."