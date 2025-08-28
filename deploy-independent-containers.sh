#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Independent Container Deployment Script
# 완전 독립 컨테이너 배포 + Watchtower 자동 업데이트 설정
# =============================================================================

set -e

# 설정 변수
REGISTRY="registry.jclee.me"
REGISTRY_USER="admin"
REGISTRY_PASS="bingogo1"
VERSION="latest"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# 색상 출력 함수
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[정보]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[성공]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[경고]${NC} $1"
}

log_error() {
    echo -e "${RED}[오류]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[단계]${NC} $1"
}

# 전제조건 확인
log_step "1️⃣ 전제조건 확인"
if ! command -v docker &> /dev/null; then
    log_error "Docker가 설치되지 않았거나 PATH에 없습니다"
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Docker 데몬이 실행되지 않고 있습니다"
    exit 1
fi

log_info "Docker 환경 확인 완료"

# 레지스트리 인증
log_step "2️⃣ 레지스트리 인증"
echo "$REGISTRY_PASS" | docker login $REGISTRY --username $REGISTRY_USER --password-stdin
if [ $? -eq 0 ]; then
    log_success "레지스트리 인증 성공"
else
    log_error "레지스트리 인증 실패"
    exit 1
fi

# 이미지 빌드 및 푸시 함수
build_and_push() {
    local SERVICE=$1
    local DOCKERFILE=$2
    local IMAGE_NAME=$3
    
    log_info "🏗️ $SERVICE 이미지 빌드 중..."
    
    docker build \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        -f "$DOCKERFILE" \
        -t "$REGISTRY/$IMAGE_NAME:$VERSION" \
        -t "$REGISTRY/$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)" \
        .
    
    if [ $? -eq 0 ]; then
        log_success "$SERVICE 이미지 빌드 완료"
        
        log_info "📤 $SERVICE 이미지 레지스트리 업로드..."
        docker push "$REGISTRY/$IMAGE_NAME:$VERSION"
        docker push "$REGISTRY/$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)"
        log_success "$SERVICE 이미지 업로드 완료"
        
        # 매니페스트 검증
        if docker manifest inspect "$REGISTRY/$IMAGE_NAME:$VERSION" > /dev/null 2>&1; then
            log_success "$SERVICE 이미지 레지스트리 검증 완료"
        else
            log_warning "$SERVICE 이미지 레지스트리 검증 실패"
        fi
    else
        log_error "$SERVICE 이미지 빌드 실패"
        return 1
    fi
}

# Redis 이미지 빌드 및 푸시
log_step "3️⃣ Redis 서비스 이미지 처리"
build_and_push "Redis" "Dockerfile.redis" "fortinet-redis"

# PostgreSQL 이미지 빌드 및 푸시  
log_step "4️⃣ PostgreSQL 서비스 이미지 처리"
build_and_push "PostgreSQL" "Dockerfile.postgresql" "fortinet-postgresql"

# 메인 애플리케이션 이미지 빌드 및 푸시
log_step "5️⃣ FortiGate 애플리케이션 이미지 처리"
build_and_push "FortiGate App" "Dockerfile.fortinet" "fortinet"

# Watchtower 설정을 포함한 독립 배포 매니페스트 생성
log_step "6️⃣ 독립 배포 매니페스트 생성"
cat > docker-compose-independent-watchtower.yml << EOF
# =============================================================================
# FortiGate Nextrade - Independent Container Deployment with Watchtower
# 완전 독립 실행 + 자동 업데이트 + 컨테이너 격리
# =============================================================================

version: '3.8'

services:
  # Watchtower - 자동 이미지 업데이트 서비스
  watchtower:
    image: containrrr/watchtower:latest
    container_name: fortinet-watchtower
    restart: unless-stopped
    environment:
      - WATCHTOWER_POLL_INTERVAL=300  # 5분마다 확인
      - WATCHTOWER_CLEANUP=true       # 이전 이미지 정리
      - WATCHTOWER_INCLUDE_STOPPED=true
      - WATCHTOWER_REVIVE_STOPPED=false
      - WATCHTOWER_LABEL_ENABLE=true  # 라벨이 있는 컨테이너만 업데이트
      - WATCHTOWER_DEBUG=true
      - TZ=Asia/Seoul
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - fortinet-network
    labels:
      - "com.centurylinklabs.watchtower.enable=false"  # 자기 자신은 업데이트 안함

  # Redis Cache Service - 독립 실행
  fortinet-redis:
    image: $REGISTRY/fortinet-redis:latest
    container_name: fortinet-redis
    hostname: fortinet-redis
    restart: unless-stopped
    ports:
      - "30778:6379"
    volumes:
      - redis-data:/data
      - redis-logs:/var/log/redis
    networks:
      - fortinet-network
    environment:
      - TZ=Asia/Seoul
      - REDIS_PORT=6379
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
      - "com.centurylinklabs.watchtower.stop-signal=SIGTERM"

  # PostgreSQL Database Service - 독립 실행
  fortinet-postgresql:
    image: $REGISTRY/fortinet-postgresql:latest
    container_name: fortinet-postgresql
    hostname: fortinet-postgresql
    restart: unless-stopped
    ports:
      - "30779:5432"
    environment:
      - TZ=Asia/Seoul
      - POSTGRES_DB=fortinet_db
      - POSTGRES_USER=fortinet
      - POSTGRES_PASSWORD=fortinet123
      - POSTGRES_INITDB_ARGS=--encoding=UTF8 --locale=en_US.utf8
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - postgres-logs:/var/log/postgresql
    networks:
      - fortinet-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fortinet"]
      interval: 30s
      timeout: 10s
      start_period: 30s
      retries: 3
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
      - "com.centurylinklabs.watchtower.stop-signal=SIGTERM"

  # Main FortiGate Application - 독립 실행
  fortinet:
    image: $REGISTRY/fortinet:latest
    container_name: fortinet
    hostname: fortinet
    restart: unless-stopped
    ports:
      - "30777:7777"
    environment:
      # 기본 설정
      - TZ=Asia/Seoul
      - APP_MODE=production
      - WEB_APP_PORT=7777
      - PYTHONPATH=/app/src
      - PYTHONDONTWRITEBYTECODE=1
      - PYTHONUNBUFFERED=1
      
      # 데이터베이스 연결 (독립 설정)
      - DATABASE_URL=postgresql://fortinet:fortinet123@fortinet-postgresql:5432/fortinet_db
      - POSTGRES_HOST=fortinet-postgresql
      - POSTGRES_PORT=5432
      - POSTGRES_USER=fortinet
      - POSTGRES_PASSWORD=fortinet123
      - POSTGRES_DB=fortinet_db
      
      # Redis 연결 (독립 설정) 
      - REDIS_URL=redis://fortinet-redis:6379/0
      - REDIS_HOST=fortinet-redis
      - REDIS_PORT=6379
      - REDIS_DB=0
      
      # 보안 설정
      - SECRET_KEY=\${SECRET_KEY:-fortinet-independent-secret-2024}
      - JWT_SECRET_KEY=\${JWT_SECRET_KEY:-jwt-fortinet-independent-2024}
      
      # 성능 설정
      - WORKERS=4
      - WORKER_CLASS=gevent
      - TIMEOUT=120
      
      # 로깅 설정
      - LOG_LEVEL=INFO
      - STRUCTURED_LOGGING=true
      
    volumes:
      - fortinet-data:/app/data
      - fortinet-logs:/app/logs
    networks:
      - fortinet-network
    depends_on:
      - fortinet-redis
      - fortinet-postgresql
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7777/api/health"]
      interval: 30s
      timeout: 10s
      start_period: 60s
      retries: 3
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
      - "com.centurylinklabs.watchtower.stop-signal=SIGTERM"
      # Traefik 라벨 (선택사항)
      - "traefik.enable=true"
      - "traefik.http.routers.fortinet.rule=Host(\`fortinet.jclee.me\`)"
      - "traefik.http.routers.fortinet.entrypoints=websecure"
      - "traefik.http.services.fortinet.loadbalancer.server.port=7777"

networks:
  fortinet-network:
    name: fortinet-network
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16

volumes:
  redis-data:
    name: fortinet-redis-data
    driver: local
  redis-logs:
    name: fortinet-redis-logs
    driver: local
  postgres-data:
    name: fortinet-postgres-data
    driver: local
  postgres-logs:
    name: fortinet-postgres-logs
    driver: local
  fortinet-data:
    name: fortinet-data
    driver: local
  fortinet-logs:
    name: fortinet-logs
    driver: local
EOF

log_success "독립 배포 매니페스트 생성 완료: docker-compose-independent-watchtower.yml"

# 배포 실행
log_step "7️⃣ 독립 컨테이너 배포 시작"
log_info "기존 컨테이너 정리..."
docker-compose -f docker-compose-independent-watchtower.yml down --remove-orphans 2>/dev/null || true

log_info "새로운 독립 컨테이너 배포..."
docker-compose -f docker-compose-independent-watchtower.yml up -d

if [ $? -eq 0 ]; then
    log_success "독립 컨테이너 배포 완료"
else
    log_error "독립 컨테이너 배포 실패"
    exit 1
fi

# 배포 상태 확인
log_step "8️⃣ 배포 상태 확인"
sleep 10
docker-compose -f docker-compose-independent-watchtower.yml ps

# 건강 상태 확인
log_info "건강 상태 확인 중..."
for i in {1..30}; do
    if curl -f --max-time 5 http://localhost:30777/api/health > /dev/null 2>&1; then
        log_success "FortiGate 애플리케이션 건강 확인 완료 (응답시간: ${i}초)"
        break
    elif [ $i -eq 30 ]; then
        log_warning "건강 확인 시간 초과 (30초)"
        break
    else
        echo -n "."
        sleep 1
    fi
done

# Redis 상태 확인
if redis-cli -h localhost -p 30778 ping > /dev/null 2>&1; then
    log_success "Redis 서비스 연결 확인 완료"
else
    log_warning "Redis 서비스 연결 확인 실패"
fi

# PostgreSQL 상태 확인
if pg_isready -h localhost -p 30779 -U fortinet > /dev/null 2>&1; then
    log_success "PostgreSQL 서비스 연결 확인 완료"
else
    log_warning "PostgreSQL 서비스 연결 확인 실패"
fi

# 배포 정보 출력
log_step "9️⃣ 배포 정보"
echo ""
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│                    독립 컨테이너 배포 완료                        │"
echo "├─────────────────────────────────────────────────────────────────┤"
echo "│ 서비스                   │ 포트      │ 상태                      │"
echo "├─────────────────────────────────────────────────────────────────┤"
echo "│ FortiGate 애플리케이션    │ :30777   │ http://localhost:30777    │"
echo "│ Redis 캐시 서비스         │ :30778   │ 독립 실행                  │"
echo "│ PostgreSQL 데이터베이스   │ :30779   │ 독립 실행                  │"
echo "│ Watchtower 자동 업데이트  │ -        │ 5분 간격 모니터링           │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""

log_step "🔄 자동 업데이트 설정"
echo "• Watchtower가 5분마다 이미지 업데이트 확인"
echo "• 새 버전 감지시 자동으로 컨테이너 재시작"  
echo "• 이전 이미지는 자동으로 정리"
echo ""

log_step "📋 관리 명령어"
echo "• 상태 확인: docker-compose -f docker-compose-independent-watchtower.yml ps"
echo "• 로그 확인: docker-compose -f docker-compose-independent-watchtower.yml logs -f"
echo "• 서비스 중지: docker-compose -f docker-compose-independent-watchtower.yml down"
echo "• 강제 업데이트: docker exec fortinet-watchtower /watchtower --run-once"
echo ""

log_step "🏥 건강 확인 엔드포인트"
echo "• 애플리케이션: curl http://localhost:30777/api/health"
echo "• Redis: redis-cli -h localhost -p 30778 ping"  
echo "• PostgreSQL: pg_isready -h localhost -p 30779 -U fortinet"
echo ""

log_success "🎉 FortiGate Nextrade 독립 컨테이너 배포가 성공적으로 완료되었습니다!"
log_info "💡 Watchtower가 자동으로 이미지 업데이트를 모니터링합니다."

# 선택적 이미지 정리
echo ""
read -p "🧹 로컬 빌드 캐시를 정리하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "로컬 이미지 캐시 정리 중..."
    docker system prune -f
    log_success "로컬 이미지 캐시 정리 완료"
fi

echo ""
log_success "🚀 배포 스크립트 실행 완료!"