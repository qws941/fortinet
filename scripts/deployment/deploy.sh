#!/bin/bash
set -euo pipefail

# FortiGate Nextrade 배포 스크립트
# registry.jclee.me에서 이미지를 가져와서 단일 컨테이너로 배포

REGISTRY="registry.jclee.me"
IMAGE_NAME="fortinet"
CONTAINER_NAME="fortinet-app"
APP_PORT="${APP_PORT:-7777}"
TAG="${TAG:-latest}"

echo "🚀 FortiGate Nextrade 배포 시작..."
echo "📦 Registry: $REGISTRY"
echo "🏷️  Image: $IMAGE_NAME:$TAG"
echo "🚪 Port: $APP_PORT"

# Docker 로그인
if [ -n "${REGISTRY_USERNAME:-}" ] && [ -n "${REGISTRY_PASSWORD:-}" ]; then
    echo "🔐 Registry 로그인 중..."
    echo "$REGISTRY_PASSWORD" | docker login $REGISTRY -u "$REGISTRY_USERNAME" --password-stdin
fi

# 최신 이미지 가져오기
echo "📥 최신 이미지 가져오는 중..."
docker pull $REGISTRY/$IMAGE_NAME:$TAG

# 기존 컨테이너 정지 및 제거
echo "🛑 기존 컨테이너 정리 중..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# 환경 변수 설정
ENV_VARS=(
    "-e APP_MODE=${APP_MODE:-production}"
    "-e FLASK_ENV=${FLASK_ENV:-production}"
    "-e LOG_LEVEL=${LOG_LEVEL:-INFO}"
    "-e TZ=${TZ:-Asia/Seoul}"
    "-e WEB_APP_PORT=$APP_PORT"
)

# FortiGate 설정 (선택사항)
if [ -n "${FORTIGATE_HOST:-}" ]; then
    ENV_VARS+=("-e FORTIGATE_HOST=$FORTIGATE_HOST")
fi

if [ -n "${FORTIGATE_TOKEN:-}" ]; then
    ENV_VARS+=("-e FORTIGATE_TOKEN=$FORTIGATE_TOKEN")
fi

if [ -n "${FORTIMANAGER_HOST:-}" ]; then
    ENV_VARS+=("-e FORTIMANAGER_HOST=$FORTIMANAGER_HOST")
fi

if [ -n "${FORTIMANAGER_USERNAME:-}" ]; then
    ENV_VARS+=("-e FORTIMANAGER_USERNAME=$FORTIMANAGER_USERNAME")
fi

if [ -n "${FORTIMANAGER_PASSWORD:-}" ]; then
    ENV_VARS+=("-e FORTIMANAGER_PASSWORD=$FORTIMANAGER_PASSWORD")
fi

# 새 컨테이너 실행
echo "🚢 새 컨테이너 실행 중..."
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p $APP_PORT:7777 \
    "${ENV_VARS[@]}" \
    $REGISTRY/$IMAGE_NAME:$TAG

# 컨테이너 시작 대기
echo "⏳ 컨테이너 시작 대기 중..."
sleep 10

# 배포 검증
echo "🔍 배포 상태 확인 중..."
if docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep -q $CONTAINER_NAME; then
    echo "✅ 배포 성공!"
    echo ""
    echo "📊 컨테이너 상태:"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "🌐 서비스 접속:"
    echo "   http://localhost:$APP_PORT"
    echo "   http://localhost:$APP_PORT/health (헬스 체크)"
    echo ""
    echo "📋 로그 확인:"
    echo "   docker logs $CONTAINER_NAME"
    echo ""
    echo "🎉 배포가 완료되었습니다!"
else
    echo "❌ 배포 실패!"
    echo ""
    echo "📋 컨테이너 로그:"
    docker logs $CONTAINER_NAME --tail=50 2>/dev/null || echo "로그를 가져올 수 없습니다."
    echo ""
    echo "🔍 문제 해결:"
    echo "1. 포트 $APP_PORT가 사용 중인지 확인: lsof -ti:$APP_PORT"
    echo "2. 이미지가 올바른지 확인: docker images | grep $IMAGE_NAME"
    echo "3. 환경 변수 확인: docker inspect $CONTAINER_NAME"
    exit 1
fi

# 사용하지 않는 이미지 정리 (선택사항)
if [ "${CLEANUP_IMAGES:-false}" = "true" ]; then
    echo "🧹 사용하지 않는 이미지 정리 중..."
    docker image prune -f
fi

echo ""
echo "🎯 배포 스크립트 완료!"