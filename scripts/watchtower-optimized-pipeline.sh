#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Watchtower 최적화 파이프라인
# 3개 이미지 빌드/배포 안정화
# =============================================================================

set -e

# Configuration
REGISTRY="registry.jclee.me"
VERSION="${VERSION:-latest}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BRANCH_NAME=$(git branch --show-current 2>/dev/null || echo "main")

# Watchtower 최적화 설정
WATCHTOWER_POLL_INTERVAL="${WATCHTOWER_POLL_INTERVAL:-300}"  # 5분
WATCHTOWER_LIFECYCLE_HOOKS="${WATCHTOWER_LIFECYCLE_HOOKS:-true}"
WATCHTOWER_ROLLING_RESTART="${WATCHTOWER_ROLLING_RESTART:-true}"

# 이미지 정의
declare -A IMAGES=(
    ["redis"]="Dockerfile.redis"
    ["postgresql"]="Dockerfile.postgresql" 
    ["fortinet"]="Dockerfile.fortinet"
)

# 의존성 순서 (Redis -> PostgreSQL -> Fortinet)
BUILD_ORDER=("redis" "postgresql" "fortinet")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }
echo_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Pre-flight checks
preflight_checks() {
    echo_step "🔍 Watchtower 환경 사전 체크..."
    
    # Docker 환경 체크
    if ! command -v docker &> /dev/null; then
        echo_error "Docker가 설치되지 않았습니다"
        exit 1
    fi
    
    # Registry 접근 체크
    if ! docker login $REGISTRY --username admin --password-stdin <<< "$REGISTRY_PASSWORD" 2>/dev/null; then
        echo_warning "Registry 인증 실패 - 대화형 로그인 시도중..."
        docker login $REGISTRY || exit 1
    fi
    
    # 현재 실행중인 컨테이너 체크
    RUNNING_CONTAINERS=$(docker ps -q --filter "label=com.centurylinklabs.watchtower.enable=true")
    if [[ -n "$RUNNING_CONTAINERS" ]]; then
        echo_info "감지된 Watchtower 관리 컨테이너: $(echo $RUNNING_CONTAINERS | wc -w)개"
    fi
    
    echo_success "사전 체크 완료"
}

# 이미지 빌드 (Watchtower 최적화)
build_image() {
    local service=$1
    local dockerfile=${IMAGES[$service]}
    local image_name="$REGISTRY/fortinet-$service"
    local timestamp_tag=$(date +%Y%m%d-%H%M%S)
    
    echo_step "🏗️ $service 이미지 빌드 중..."
    
    # BuildKit 활성화로 빌드 성능 향상
    export DOCKER_BUILDKIT=1
    
    # 다중 태그 빌드 (latest + timestamp)
    docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        --label "com.centurylinklabs.watchtower.enable=true" \
        --label "com.centurylinklabs.watchtower.scope=fortinet" \
        --label "org.opencontainers.image.created=$BUILD_DATE" \
        --label "org.opencontainers.image.revision=$VCS_REF" \
        --label "org.opencontainers.image.version=$VERSION-$timestamp_tag" \
        --label "fortinet.deployment.branch=$BRANCH_NAME" \
        --label "fortinet.deployment.timestamp=$BUILD_DATE" \
        -f "$dockerfile" \
        -t "$image_name:latest" \
        -t "$image_name:$timestamp_tag" \
        -t "$image_name:$VCS_REF" \
        . || {
        echo_error "$service 이미지 빌드 실패"
        return 1
    }
    
    echo_success "$service 이미지 빌드 완료"
}

# 이미지 안정성 테스트
test_image_stability() {
    local service=$1
    local image_name="$REGISTRY/fortinet-$service:latest"
    
    echo_step "🧪 $service 이미지 안정성 테스트..."
    
    # 보안 스캔
    if command -v trivy &> /dev/null; then
        echo_info "Trivy 보안 스캔 실행 중..."
        if trivy image --severity HIGH,CRITICAL "$image_name" --exit-code 1; then
            echo_success "$service 보안 스캔 통과"
        else
            echo_warning "$service 보안 취약점 발견 - 계속 진행하시겠습니까?"
            read -p "Continue? (y/N): " -n 1 -r
            echo
            [[ ! $REPLY =~ ^[Yy]$ ]] && return 1
        fi
    fi
    
    # Health Check 테스트 (컨테이너 실행 없이 이미지 검사)
    docker run --rm --entrypoint="" "$image_name" sh -c 'command -v curl >/dev/null || command -v wget >/dev/null || command -v nc >/dev/null' || {
        echo_warning "$service 이미지에 health check 도구가 누락되었을 수 있습니다"
    }
    
    echo_success "$service 안정성 테스트 완료"
}

# Registry 푸시 (Watchtower 감지 최적화)
push_to_registry() {
    local service=$1
    local image_name="$REGISTRY/fortinet-$service"
    local timestamp_tag=$(date +%Y%m%d-%H%M%S)
    
    echo_step "📤 $service 이미지 Registry 푸시..."
    
    # 순차적 푸시로 Registry 부하 방지
    docker push "$image_name:$timestamp_tag" || return 1
    docker push "$image_name:$VCS_REF" || return 1
    
    # latest 태그는 마지막에 푸시 (Watchtower 트리거 최적화)
    docker push "$image_name:latest" || return 1
    
    # Registry에서 이미지 확인
    if docker manifest inspect "$image_name:latest" > /dev/null 2>&1; then
        echo_success "$service 이미지가 Registry에 확인됨"
    else
        echo_error "$service 이미지 Registry 검증 실패"
        return 1
    fi
}

# Watchtower 호환 Health Check 강화
enhance_health_checks() {
    echo_step "💊 Watchtower 호환 Health Check 구현..."
    
    # 개선된 startup 스크립트 생성
    cat > startup.sh << 'EOF'
#!/bin/bash
set -e

# Watchtower 신호 처리
trap 'echo "Received SIGTERM, shutting down gracefully..."; exit 0' SIGTERM
trap 'echo "Received SIGINT, shutting down gracefully..."; exit 0' SIGINT

# Health endpoint 활성화까지 대기
wait_for_health() {
    local max_attempts=60
    local attempt=1
    
    echo "Waiting for application health endpoint..."
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:7777/api/health > /dev/null 2>&1; then
            echo "✅ Health endpoint is ready"
            return 0
        fi
        echo "⏳ Attempt $attempt/$max_attempts - waiting for health endpoint..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ Health endpoint failed to become ready"
    exit 1
}

# 애플리케이션 시작
cd /app/src
python main.py --web &
APP_PID=$!

# Health check 대기
wait_for_health

# Watchtower 신호 대기
wait $APP_PID
EOF
    
    chmod +x startup.sh
    echo_success "Health Check 강화 완료"
}

# Rolling 업데이트 전략 구현
implement_rolling_strategy() {
    echo_step "🔄 Rolling 업데이트 전략 구현..."
    
    # docker-compose override 파일 생성
    cat > docker-compose.watchtower.yml << EOF
version: '3.8'

services:
  # Watchtower 전용 설정
  redis:
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
      - "com.centurylinklabs.watchtower.scope=fortinet"
      - "com.centurylinklabs.watchtower.monitor-only=false"
      - "com.centurylinklabs.watchtower.lifecycle.pre-update=redis-cli bgsave"
      - "com.centurylinklabs.watchtower.lifecycle.post-update=redis-cli ping"
      - "com.centurylinklabs.watchtower.stop-timeout=30s"
    deploy:
      restart_policy:
        condition: unless-stopped
        delay: 10s
        max_attempts: 3

  postgresql:
    labels:
      - "com.centurylinklabs.watchtower.enable=true" 
      - "com.centurylinklabs.watchtower.scope=fortinet"
      - "com.centurylinklabs.watchtower.monitor-only=false"
      - "com.centurylinklabs.watchtower.lifecycle.pre-update=pg_ctl stop -m fast"
      - "com.centurylinklabs.watchtower.lifecycle.post-update=pg_isready -U fortinet"
      - "com.centurylinklabs.watchtower.stop-timeout=60s"
    deploy:
      restart_policy:
        condition: unless-stopped
        delay: 15s
        max_attempts: 3

  fortinet:
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
      - "com.centurylinklabs.watchtower.scope=fortinet" 
      - "com.centurylinklabs.watchtower.monitor-only=false"
      - "com.centurylinklabs.watchtower.lifecycle.pre-update=curl -f http://localhost:7777/api/health"
      - "com.centurylinklabs.watchtower.lifecycle.post-update=curl -f http://localhost:7777/api/health"
      - "com.centurylinklabs.watchtower.stop-timeout=45s"
    deploy:
      restart_policy:
        condition: unless-stopped
        delay: 20s
        max_attempts: 3
    depends_on:
      - redis
      - postgresql
EOF

    echo_success "Rolling 업데이트 전략 구현 완료"
}

# 메인 빌드 프로세스
main_build_process() {
    echo_step "🚀 Watchtower 최적화 빌드 프로세스 시작..."
    
    # Health Check 강화
    enhance_health_checks
    
    # Rolling 전략 구현
    implement_rolling_strategy
    
    # 의존성 순서대로 빌드
    for service in "${BUILD_ORDER[@]}"; do
        echo_info "=== $service 서비스 처리 중 ==="
        
        build_image "$service" || {
            echo_error "$service 빌드 실패"
            exit 1
        }
        
        test_image_stability "$service" || {
            echo_error "$service 안정성 테스트 실패" 
            exit 1
        }
        
        push_to_registry "$service" || {
            echo_error "$service 푸시 실패"
            exit 1
        }
        
        # 서비스간 간격으로 Registry 부하 분산
        sleep 5
    done
}

# Watchtower 상태 모니터링
monitor_watchtower() {
    echo_step "📊 Watchtower 모니터링 설정..."
    
    cat > scripts/monitor-watchtower.sh << 'EOF'
#!/bin/bash
# Watchtower 상태 모니터링 스크립트

echo "=== Watchtower 모니터링 대시보드 ==="
echo "날짜: $(date)"
echo

# 컨테이너 상태 확인
echo "📦 관리 대상 컨테이너:"
docker ps --filter "label=com.centurylinklabs.watchtower.enable=true" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
echo

# Watchtower 로그 확인
if docker ps --filter "name=watchtower" -q > /dev/null; then
    echo "📋 최근 Watchtower 로그:"
    docker logs watchtower --tail 10
else
    echo "⚠️ Watchtower 컨테이너를 찾을 수 없습니다"
fi
echo

# Registry 이미지 확인
echo "🏭 Registry 이미지 태그:"
for service in redis postgresql fortinet; do
    echo "  fortinet-$service: $(docker run --rm registry.jclee.me/fortinet-$service:latest sh -c 'echo ${BUILD_DATE:-unknown}' 2>/dev/null || echo 'unknown')"
done
EOF

    chmod +x scripts/monitor-watchtower.sh
    echo_success "모니터링 설정 완료"
}

# 실행 함수들
preflight_checks
main_build_process
monitor_watchtower

echo_success "🎉 Watchtower 최적화 파이프라인 완료!"
echo_info "💡 다음 단계:"
echo "  1. Watchtower 실행: docker run -d --name watchtower -v /var/run/docker.sock:/var/run/docker.sock containrrr/watchtower --scope fortinet --interval $WATCHTOWER_POLL_INTERVAL"
echo "  2. 배포 확인: docker-compose -f docker-compose-separated.yml -f docker-compose.watchtower.yml up -d"
echo "  3. 모니터링: ./scripts/monitor-watchtower.sh"
echo
echo "📈 파이프라인 통계:"
echo "  빌드된 이미지: ${#BUILD_ORDER[@]}개"
echo "  빌드 시간: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
echo "  Git Commit: $VCS_REF"
echo "  Branch: $BRANCH_NAME"