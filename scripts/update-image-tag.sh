#!/bin/bash

# GitOps 이미지 태그 자동 업데이트 스크립트
# Kustomize와 ArgoCD를 위한 이미지 태그 관리

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# 설정
REGISTRY="registry.jclee.me"
IMAGE_NAME="fortinet"
KUSTOMIZE_PATH="k8s/overlays/production/kustomization.yaml"
HELM_VALUES="charts/fortinet/values.yaml"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      GitOps 이미지 태그 업데이트           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# 1. 현재 Git 정보 수집
echo -e "${GREEN}1. Git 정보 수집...${NC}"
GIT_BRANCH=$(git branch --show-current)
GIT_COMMIT=$(git rev-parse --short HEAD)
GIT_COMMIT_FULL=$(git rev-parse HEAD)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "  📌 브랜치: $GIT_BRANCH"
echo "  📌 커밋: $GIT_COMMIT ($GIT_COMMIT_FULL)"
echo "  📌 타임스탬프: $TIMESTAMP"

# 2. 이미지 태그 생성
echo -e "${GREEN}2. 이미지 태그 생성...${NC}"

# 태그 형식 선택
if [ "$1" == "--semantic" ]; then
    # Semantic versioning
    VERSION=$(grep "^version:" charts/fortinet/Chart.yaml | awk '{print $2}')
    IMAGE_TAG="v${VERSION}"
    echo "  🏷️ Semantic 태그: $IMAGE_TAG"
elif [ "$1" == "--timestamp" ]; then
    # Timestamp 기반
    IMAGE_TAG="${GIT_BRANCH}-${TIMESTAMP}"
    echo "  🏷️ Timestamp 태그: $IMAGE_TAG"
elif [ "$1" == "--commit" ]; then
    # Commit SHA 기반
    IMAGE_TAG="${GIT_COMMIT}"
    echo "  🏷️ Commit 태그: $IMAGE_TAG"
else
    # 기본: Branch-Commit 형식
    IMAGE_TAG="${GIT_BRANCH}-${GIT_COMMIT}"
    echo "  🏷️ 기본 태그: $IMAGE_TAG"
fi

# 추가 태그
LATEST_TAG="latest"
IMMUTABLE_TAG="${GIT_COMMIT_FULL}"

echo "  🏷️ 추가 태그: latest, $IMMUTABLE_TAG"

# 3. Kustomize 업데이트
echo -e "${GREEN}3. Kustomize 설정 업데이트...${NC}"

if [ -f "$KUSTOMIZE_PATH" ]; then
    # 현재 태그 백업
    OLD_TAG=$(grep "newTag:" $KUSTOMIZE_PATH | awk '{print $2}')
    echo "  📌 현재 태그: $OLD_TAG"
    
    # 새 태그로 업데이트
    sed -i "s/newTag:.*/newTag: $IMAGE_TAG/" $KUSTOMIZE_PATH
    
    # immutable 태그 업데이트 (annotation)
    sed -i "s/gitops.immutable-tag:.*/gitops.immutable-tag: \"$IMMUTABLE_TAG\"/" $KUSTOMIZE_PATH
    
    echo "  ✅ Kustomize 업데이트 완료: $IMAGE_TAG"
else
    echo -e "  ${YELLOW}⚠️ Kustomize 파일이 없습니다: $KUSTOMIZE_PATH${NC}"
fi

# 4. Helm values 업데이트
echo -e "${GREEN}4. Helm values 업데이트...${NC}"

if [ -f "$HELM_VALUES" ]; then
    # 이미지 태그 업데이트
    sed -i "s/tag:.*/tag: \"$IMAGE_TAG\"/" $HELM_VALUES
    echo "  ✅ Helm values 업데이트 완료: $IMAGE_TAG"
else
    echo -e "  ${YELLOW}⚠️ Helm values 파일이 없습니다: $HELM_VALUES${NC}"
fi

# 5. Docker 이미지 빌드 (옵션)
if [ "$2" == "--build" ]; then
    echo -e "${GREEN}5. Docker 이미지 빌드...${NC}"
    
    if [ -f "Dockerfile.production" ]; then
        echo "  🐳 Production 이미지 빌드 중..."
        docker build \
            -f Dockerfile.production \
            -t $REGISTRY/$IMAGE_NAME:$IMAGE_TAG \
            -t $REGISTRY/$IMAGE_NAME:$LATEST_TAG \
            -t $REGISTRY/$IMAGE_NAME:$IMMUTABLE_TAG \
            --build-arg GIT_COMMIT=$GIT_COMMIT_FULL \
            --build-arg GIT_BRANCH=$GIT_BRANCH \
            --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
            --build-arg VERSION=$VERSION \
            .
        
        echo "  ✅ Docker 이미지 빌드 완료"
    else
        echo -e "  ${YELLOW}⚠️ Dockerfile.production이 없습니다${NC}"
    fi
fi

# 6. Registry 푸시 (옵션)
if [ "$2" == "--push" ] || [ "$3" == "--push" ]; then
    echo -e "${GREEN}6. Registry 푸시...${NC}"
    
    # Registry 로그인 확인
    if docker login $REGISTRY --username admin --password-stdin <<< "$REGISTRY_PASSWORD" &> /dev/null; then
        echo "  ✅ Registry 로그인 성공"
        
        # 이미지 푸시
        echo "  📤 이미지 푸시 중..."
        docker push $REGISTRY/$IMAGE_NAME:$IMAGE_TAG
        docker push $REGISTRY/$IMAGE_NAME:$LATEST_TAG
        docker push $REGISTRY/$IMAGE_NAME:$IMMUTABLE_TAG
        
        echo "  ✅ Registry 푸시 완료"
    else
        echo -e "  ${RED}❌ Registry 로그인 실패${NC}"
        echo "  REGISTRY_PASSWORD 환경 변수를 확인하세요"
    fi
fi

# 7. Git 커밋 (옵션)
if [ "$2" == "--commit" ] || [ "$3" == "--commit" ] || [ "$4" == "--commit" ]; then
    echo -e "${GREEN}7. Git 커밋...${NC}"
    
    git add $KUSTOMIZE_PATH $HELM_VALUES 2>/dev/null || true
    
    if git diff --staged --quiet; then
        echo "  ⚠️ 변경사항이 없습니다"
    else
        git commit -m "🏷️ Update image tag to $IMAGE_TAG

- Kustomize: $IMAGE_TAG
- Helm: $IMAGE_TAG
- Immutable: $IMMUTABLE_TAG
- Branch: $GIT_BRANCH
- Commit: $GIT_COMMIT_FULL

[skip ci]" 
        
        echo "  ✅ Git 커밋 완료"
        
        # Push (옵션)
        if [ "$5" == "--push-git" ]; then
            git push origin $GIT_BRANCH
            echo "  ✅ Git 푸시 완료"
        fi
    fi
fi

# 8. ArgoCD 동기화 (옵션)
if [ "$2" == "--sync" ] || [ "$3" == "--sync" ] || [ "$4" == "--sync" ] || [ "$5" == "--sync" ]; then
    echo -e "${GREEN}8. ArgoCD 동기화...${NC}"
    
    if command -v argocd &> /dev/null; then
        if argocd app sync fortinet --prune 2>/dev/null; then
            echo "  ✅ ArgoCD 동기화 시작됨"
        else
            echo -e "  ${YELLOW}⚠️ ArgoCD 동기화 실패 (수동 동기화 필요)${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠️ ArgoCD CLI가 설치되지 않았습니다${NC}"
    fi
fi

# 9. 요약
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           업데이트 요약                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "📋 업데이트 정보:"
echo "  - 이미지 태그: $IMAGE_TAG"
echo "  - Immutable 태그: $IMMUTABLE_TAG"
echo "  - Registry: $REGISTRY/$IMAGE_NAME"
echo ""
echo "📝 업데이트된 파일:"
[ -f "$KUSTOMIZE_PATH" ] && echo "  - $KUSTOMIZE_PATH"
[ -f "$HELM_VALUES" ] && echo "  - $HELM_VALUES"
echo ""
echo "🔗 다음 단계:"
echo "  1. git push origin $GIT_BRANCH"
echo "  2. GitHub Actions 파이프라인 확인"
echo "  3. ArgoCD 동기화 상태 확인"
echo "  4. 애플리케이션 헬스체크"
echo ""
echo "✅ 이미지 태그 업데이트 완료!"