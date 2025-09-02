#!/bin/bash

# =============================================================================
# FortiGate Nextrade - 수정된 이미지 빌드 및 푸시 스크립트
# =============================================================================

set -e

# 색상 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 변수 설정
REGISTRY="registry.jclee.me"
VERSION=$(cat VERSION 2>/dev/null || echo "v1.0.0")
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

log_info "🏗️  FortiGate Nextrade 이미지 빌드 및 푸시"
echo "📦 버전: $VERSION"
echo "📅 빌드 날짜: $BUILD_DATE"
echo "📝 커밋: $VCS_REF"
echo ""

# 1. 메인 Fortinet 앱 이미지 빌드 (이름 수정: fortinet-app -> fortinet)
log_info "🔨 메인 Fortinet 앱 이미지 빌드 중..."
docker build \
    -f Dockerfile.fortinet \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -t "$REGISTRY/fortinet:latest" \
    -t "$REGISTRY/fortinet:$VERSION" \
    .

log_success "✅ Fortinet 앱 이미지 빌드 완료"

# 2. Redis 이미지 빌드 (기존)
log_info "🔨 Redis 이미지 빌드 중..."
docker build \
    -f Dockerfile.redis \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -t "$REGISTRY/fortinet-redis:latest" \
    -t "$REGISTRY/fortinet-redis:$VERSION" \
    .

log_success "✅ Redis 이미지 빌드 완료"

# 3. PostgreSQL 이미지 빌드 (기존)
log_info "🔨 PostgreSQL 이미지 빌드 중..."
docker build \
    -f Dockerfile.postgresql \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -t "$REGISTRY/fortinet-postgresql:latest" \
    -t "$REGISTRY/fortinet-postgresql:$VERSION" \
    .

log_success "✅ PostgreSQL 이미지 빌드 완료"

# 4. 이미지 정보 출력
log_info "📋 빌드된 이미지 목록:"
docker images | grep "$REGISTRY/fortinet"

# 5. Registry 로그인 확인
log_info "🔐 Registry 로그인 상태 확인..."
if docker system info | grep -q "Username:"; then
    log_success "✅ Registry에 로그인되어 있습니다"
else
    log_warning "⚠️  Registry 로그인이 필요할 수 있습니다"
    echo "로그인 명령: docker login $REGISTRY"
fi

# 6. 이미지 푸시
log_info "📤 이미지 푸시 시작..."

# Fortinet 앱 푸시 (수정된 이름)
log_info "📤 Fortinet 앱 이미지 푸시 중..."
docker push "$REGISTRY/fortinet:latest"
docker push "$REGISTRY/fortinet:$VERSION"
log_success "✅ Fortinet 앱 이미지 푸시 완료"

# Redis 푸시
log_info "📤 Redis 이미지 푸시 중..."
docker push "$REGISTRY/fortinet-redis:latest"
docker push "$REGISTRY/fortinet-redis:$VERSION"
log_success "✅ Redis 이미지 푸시 완료"

# PostgreSQL 푸시
log_info "📤 PostgreSQL 이미지 푸시 중..."
docker push "$REGISTRY/fortinet-postgresql:latest"
docker push "$REGISTRY/fortinet-postgresql:$VERSION"
log_success "✅ PostgreSQL 이미지 푸시 완료"

# 7. 완료 메시지
echo ""
log_success "🎉 모든 이미지 빌드 및 푸시가 완료되었습니다!"
echo ""
log_info "📋 배포된 이미지:"
echo "  • $REGISTRY/fortinet:latest (메인 앱 - 이름 수정됨)"
echo "  • $REGISTRY/fortinet-redis:latest"
echo "  • $REGISTRY/fortinet-postgresql:latest"
echo ""
log_info "🚀 테스트 실행:"
echo "  ./test-integrated-deployment.sh"
echo ""
log_info "🐳 독립 배포 시작:"
echo "  docker-compose -f docker-compose-independent.yml up -d"