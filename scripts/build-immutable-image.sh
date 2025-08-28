#!/bin/bash
# =============================================================================
# FortiGate Nextrade - GitOps 불변 이미지 빌드 스크립트
# GitOps 4원칙 준수: 불변 인프라 (Immutable Infrastructure)
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GitOps Immutable Image Build System${NC}"
echo "=================================================="

# 환경 변수 기본값 설정
REGISTRY_URL="${REGISTRY_URL:-registry.jclee.me}"
NAMESPACE="${NAMESPACE:-fortinet}"
ENVIRONMENT="${ENVIRONMENT:-development}"
VERSION="${VERSION:-1.1.5}"

# GitOps 4원칙 준수: 불변 태그 생성 로직
echo -e "${YELLOW}📋 Generating Immutable Tag...${NC}"

# 타임스탬프 생성 (UTC)
BUILD_TIMESTAMP=$(date -u +'%Y%m%d-%H%M%S')
BUILD_DATE=$(date -u +'%Y-%m-%d %H:%M:%S UTC')

# Git 정보 수집
if [ -d ".git" ]; then
    GIT_COMMIT=$(git rev-parse HEAD)
    GIT_SHA=$(git rev-parse --short HEAD)
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    GIT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
    
    # Git 상태 확인
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "${YELLOW}⚠️  Warning: Working directory has uncommitted changes${NC}"
        GIT_SHA="${GIT_SHA}-dirty"
    fi
    
    echo -e "  Git Commit: ${GREEN}${GIT_COMMIT}${NC}"
    echo -e "  Git SHA: ${GREEN}${GIT_SHA}${NC}"
    echo -e "  Git Branch: ${GREEN}${GIT_BRANCH}${NC}"
    [ -n "$GIT_TAG" ] && echo -e "  Git Tag: ${GREEN}${GIT_TAG}${NC}"
else
    echo -e "${RED}❌ Error: Not a git repository${NC}"
    exit 1
fi

# 불변 태그 형식: {environment}-{timestamp}-{sha}[-{suffix}]
if [ -n "$GIT_TAG" ]; then
    # 태그가 있는 경우 사용
    IMMUTABLE_TAG="${ENVIRONMENT}-${BUILD_TIMESTAMP}-${GIT_TAG}-${GIT_SHA}"
else
    # 일반적인 경우
    IMMUTABLE_TAG="${ENVIRONMENT}-${BUILD_TIMESTAMP}-${GIT_SHA}"
fi

# 추가 태그들
LATEST_TAG="${ENVIRONMENT}-latest"
FULL_IMAGE="${REGISTRY_URL}/${NAMESPACE}:${IMMUTABLE_TAG}"
LATEST_IMAGE="${REGISTRY_URL}/${NAMESPACE}:${LATEST_TAG}"

echo -e "${GREEN}✅ Immutable Tag Generated${NC}"
echo -e "  Full Image: ${BLUE}${FULL_IMAGE}${NC}"
echo -e "  Latest Alias: ${BLUE}${LATEST_IMAGE}${NC}"
echo ""

# Docker 빌드 인수 준비
BUILD_ARGS=(
    --build-arg "BUILD_DATE=${BUILD_DATE}"
    --build-arg "BUILD_TIMESTAMP=${BUILD_TIMESTAMP}"
    --build-arg "GIT_COMMIT=${GIT_COMMIT}"
    --build-arg "GIT_SHA=${GIT_SHA}"
    --build-arg "GIT_BRANCH=${GIT_BRANCH}"
    --build-arg "VERSION=${VERSION}"
    --build-arg "IMMUTABLE_TAG=${IMMUTABLE_TAG}"
    --build-arg "REGISTRY_URL=${REGISTRY_URL}"
)

# Docker 이미지 빌드
echo -e "${YELLOW}🔨 Building Docker Image...${NC}"
echo -e "  Environment: ${GREEN}${ENVIRONMENT}${NC}"
echo -e "  Registry: ${GREEN}${REGISTRY_URL}${NC}"
echo -e "  Namespace: ${GREEN}${NAMESPACE}${NC}"
echo ""

# 멀티 플랫폼 빌드 (선택사항)
if [ "${MULTI_PLATFORM:-false}" = "true" ]; then
    echo -e "${YELLOW}🌐 Multi-platform build enabled${NC}"
    PLATFORM_ARGS="--platform linux/amd64,linux/arm64"
else
    PLATFORM_ARGS=""
fi

# Docker 빌드 실행
docker buildx build \
    ${PLATFORM_ARGS} \
    "${BUILD_ARGS[@]}" \
    --tag "${FULL_IMAGE}" \
    --tag "${LATEST_IMAGE}" \
    --file Dockerfile.production \
    --progress=plain \
    --no-cache \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker Build Successful${NC}"
else
    echo -e "${RED}❌ Docker Build Failed${NC}"
    exit 1
fi

# 이미지 정보 표시
echo ""
echo -e "${BLUE}📊 Built Image Information${NC}"
echo "=================================================="
docker images | grep "${NAMESPACE}" | head -5

# 이미지 메타데이터 검증
echo ""
echo -e "${YELLOW}🔍 Verifying Image Metadata...${NC}"
docker inspect "${FULL_IMAGE}" --format '{{json .Config.Labels}}' | python3 -m json.tool

# 레지스트리 푸시 (선택사항)
if [ "${PUSH:-false}" = "true" ]; then
    echo ""
    echo -e "${YELLOW}📤 Pushing to Registry...${NC}"
    
    # 불변 태그 푸시
    docker push "${FULL_IMAGE}"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Pushed: ${FULL_IMAGE}${NC}"
    else
        echo -e "${RED}❌ Failed to push: ${FULL_IMAGE}${NC}"
        exit 1
    fi
    
    # Latest 태그 푸시 (환경별)
    docker push "${LATEST_IMAGE}"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Pushed: ${LATEST_IMAGE}${NC}"
    else
        echo -e "${RED}❌ Failed to push: ${LATEST_IMAGE}${NC}"
        exit 1
    fi
fi

# 빌드 정보 저장 (CI/CD에서 활용)
echo ""
echo -e "${YELLOW}💾 Saving Build Information...${NC}"
BUILD_INFO_FILE="build-info-${BUILD_TIMESTAMP}.json"

cat > "${BUILD_INFO_FILE}" << EOF
{
  "gitops": {
    "principles": ["declarative", "git-source", "pull-based", "immutable"],
    "managed_by": "argocd",
    "immutable": true
  },
  "build": {
    "date": "${BUILD_DATE}",
    "timestamp": "${BUILD_TIMESTAMP}",
    "version": "${VERSION}",
    "immutable_tag": "${IMMUTABLE_TAG}",
    "environment": "${ENVIRONMENT}"
  },
  "git": {
    "commit": "${GIT_COMMIT}",
    "sha": "${GIT_SHA}",
    "branch": "${GIT_BRANCH}",
    "tag": "${GIT_TAG}",
    "repository": "https://github.com/JCLEE94/fortinet"
  },
  "registry": {
    "url": "${REGISTRY_URL}",
    "namespace": "${NAMESPACE}",
    "full_image": "${FULL_IMAGE}",
    "latest_alias": "${LATEST_IMAGE}"
  },
  "docker": {
    "dockerfile": "Dockerfile.production",
    "multi_platform": ${MULTI_PLATFORM:-false},
    "pushed": ${PUSH:-false}
  }
}
EOF

echo -e "${GREEN}✅ Build information saved: ${BUILD_INFO_FILE}${NC}"

# 완료 메시지
echo ""
echo -e "${GREEN}🎉 GitOps Immutable Build Complete!${NC}"
echo "=================================================="
echo -e "Immutable Tag: ${BLUE}${IMMUTABLE_TAG}${NC}"
echo -e "Full Image: ${BLUE}${FULL_IMAGE}${NC}"
echo -e "Build Info: ${YELLOW}${BUILD_INFO_FILE}${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update kustomization.yaml with new immutable tag"
echo "2. Commit and push to trigger ArgoCD sync"
echo "3. Monitor deployment through ArgoCD UI"
echo ""

# 환경 변수 내보내기 (CI/CD에서 활용)
echo "# Export these variables in your CI/CD pipeline:"
echo "export IMMUTABLE_TAG='${IMMUTABLE_TAG}'"
echo "export FULL_IMAGE='${FULL_IMAGE}'"
echo "export BUILD_TIMESTAMP='${BUILD_TIMESTAMP}'"
echo "export GIT_SHA='${GIT_SHA}'"