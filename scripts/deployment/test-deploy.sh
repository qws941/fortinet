#!/bin/bash
# 로컬 원격 배포 테스트 스크립트

set -e
export TZ=Asia/Seoul

# 색상 코드
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

echo "🧪 FortiGate Nextrade 배포 시스템 테스트"
echo ""

# 1. 환경 변수 설정
log_info "환경 변수 설정..."
export DOCKER_REGISTRY_URL=localhost:5000
export PROJECT_NAME=fortigate-nextrade
export BUILD_TIME=$(date +"%Y-%m-%d %H:%M:%S KST")

# 2. Docker Registry 상태 확인
log_info "Docker Registry 상태 확인..."
if curl -s "http://localhost:5000/v2/" >/dev/null; then
    log_success "Docker Registry 연결 성공"
else
    log_error "Docker Registry 연결 실패"
    exit 1
fi

# 3. 로컬 이미지 빌드 테스트
log_info "Docker 이미지 빌드 테스트..."
docker build \
    --build-arg BUILD_TIME="$BUILD_TIME" \
    --build-arg TZ="$TZ" \
    -f Dockerfile.offline \
    -t "${PROJECT_NAME}:test" . >/dev/null 2>&1

if [[ $? -eq 0 ]]; then
    log_success "Docker 이미지 빌드 성공"
else
    log_error "Docker 이미지 빌드 실패"
    exit 1
fi

# 4. Registry 푸시 테스트
log_info "Registry 푸시 테스트..."
docker tag "${PROJECT_NAME}:test" "localhost:5000/${PROJECT_NAME}:test"
docker push "localhost:5000/${PROJECT_NAME}:test" >/dev/null 2>&1

if [[ $? -eq 0 ]]; then
    log_success "Registry 푸시 성공"
else
    log_error "Registry 푸시 실패"
    exit 1
fi

# 5. 이미지 풀 테스트
log_info "Registry 풀 테스트..."
docker rmi "localhost:5000/${PROJECT_NAME}:test" >/dev/null 2>&1 || true
docker pull "localhost:5000/${PROJECT_NAME}:test" >/dev/null 2>&1

if [[ $? -eq 0 ]]; then
    log_success "Registry 풀 성공"
else
    log_error "Registry 풀 실패"
    exit 1
fi

# 6. 컨테이너 실행 테스트
log_info "컨테이너 실행 테스트..."
docker stop fortigate-nextrade-test 2>/dev/null || true
docker rm fortigate-nextrade-test 2>/dev/null || true

docker run -d \
    --name fortigate-nextrade-test \
    -p 7778:7777 \
    -e APP_MODE=test \
    -e TZ="$TZ" \
    "localhost:5000/${PROJECT_NAME}:test"

# 7. 헬스체크 테스트
log_info "헬스체크 테스트..."
sleep 10

for i in {1..6}; do
    if curl -s "http://localhost:7778/api/health" >/dev/null 2>&1; then
        log_success "헬스체크 성공!"
        break
    else
        log_warning "헬스체크 재시도 ($i/6)..."
        sleep 5
    fi
    if [[ $i -eq 6 ]]; then
        log_error "헬스체크 실패!"
        docker logs fortigate-nextrade-test --tail=20
        exit 1
    fi
done

# 8. 로그 확인
log_info "컨테이너 로그 확인..."
docker logs fortigate-nextrade-test --tail=5

# 9. 정리
log_info "테스트 환경 정리..."
docker stop fortigate-nextrade-test
docker rm fortigate-nextrade-test
docker rmi "localhost:5000/${PROJECT_NAME}:test" || true
docker rmi "${PROJECT_NAME}:test" || true

# 10. 최종 결과
echo ""
log_success "🎉 모든 테스트 통과!"
echo ""
log_info "📋 테스트 결과 요약:"
log_info "  ✅ Docker Registry 연결"
log_info "  ✅ 이미지 빌드"
log_info "  ✅ Registry 푸시/풀"
log_info "  ✅ 컨테이너 실행"
log_info "  ✅ 헬스체크"
log_info "  ✅ 로그 확인"

echo ""
log_info "🚀 원격 배포 시스템 준비 완료!"
log_info ""
log_info "다음 단계:"
log_info "  1. SSH 키 설정: ./setup-ssh.sh generate-key"
log_info "  2. 원격 서버 설정: ./setup-ssh.sh setup-all --servers \"server1,server2\""
log_info "  3. 배포 설정 수정: config/deploy-config.json"
log_info "  4. 원격 배포 실행: ./remote-deploy.sh production --registry-push"