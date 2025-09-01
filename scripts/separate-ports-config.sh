#!/bin/bash
# =============================================================================
# FortiGate Nextrade - 각 이미지별 포트 분리 설정
# Redis: 7777, PostgreSQL: 7778, Fortinet-App: 7779
# =============================================================================

set -e

# 각 이미지별 포트 설정
REDIS_PORT=7777
POSTGRESQL_PORT=7778
FORTINET_PORT=7779

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

echo_info "🔧 각 이미지별 포트 분리 설정..."

# 포트 확인 및 정리
cleanup_ports() {
    echo_info "🧹 기존 포트 사용 정리..."
    
    for port in $REDIS_PORT $POSTGRESQL_PORT $FORTINET_PORT; do
        if lsof -i:$port > /dev/null 2>&1; then
            echo_warning "포트 $port 사용 중 - 프로세스 확인:"
            lsof -i:$port
            read -p "포트 $port 를 사용하는 프로세스를 종료하시겠습니까? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo lsof -ti:$port | xargs kill -9 2>/dev/null || true
                echo_success "포트 $port 정리 완료"
            fi
        fi
    done
}

# 개별 서비스 실행 스크립트 생성
generate_individual_scripts() {
    echo_info "📝 개별 서비스 실행 스크립트 생성..."
    
    mkdir -p scripts/individual-services
    
    # Redis 실행 스크립트
    cat > scripts/individual-services/run-redis.sh << EOF
#!/bin/bash
echo "🔴 Redis 서비스 시작 (포트: $REDIS_PORT)..."

docker run -d \\
    --name fortinet-redis-$REDIS_PORT \\
    --restart unless-stopped \\
    -p $REDIS_PORT:6379 \\
    -e REDIS_PORT=6379 \\
    -e REDIS_MAXMEMORY=256mb \\
    -e REDIS_MAXMEMORY_POLICY=allkeys-lru \\
    -e REDIS_APPENDONLY=yes \\
    --label "service.port=$REDIS_PORT" \\
    --label "service.type=redis" \\
    --label "com.centurylinklabs.watchtower.enable=true" \\
    registry.jclee.me/fortinet-redis:latest

echo "✅ Redis 서비스 시작됨 - http://localhost:$REDIS_PORT"
EOF

    # PostgreSQL 실행 스크립트
    cat > scripts/individual-services/run-postgresql.sh << EOF
#!/bin/bash
echo "🟢 PostgreSQL 서비스 시작 (포트: $POSTGRESQL_PORT)..."

docker run -d \\
    --name fortinet-postgresql-$POSTGRESQL_PORT \\
    --restart unless-stopped \\
    -p $POSTGRESQL_PORT:5432 \\
    -e POSTGRES_USER=fortinet \\
    -e POSTGRES_PASSWORD=fortinet123 \\
    -e POSTGRES_DB=fortinet_db \\
    -e PGDATA=/var/lib/postgresql/data \\
    --label "service.port=$POSTGRESQL_PORT" \\
    --label "service.type=postgresql" \\
    --label "com.centurylinklabs.watchtower.enable=true" \\
    registry.jclee.me/fortinet-postgresql:latest

echo "✅ PostgreSQL 서비스 시작됨 - localhost:$POSTGRESQL_PORT"
EOF

    # Fortinet App 실행 스크립트
    cat > scripts/individual-services/run-fortinet.sh << EOF
#!/bin/bash
echo "🔵 Fortinet 애플리케이션 시작 (포트: $FORTINET_PORT)..."

docker run -d \\
    --name fortinet-app-$FORTINET_PORT \\
    --restart unless-stopped \\
    -p $FORTINET_PORT:7777 \\
    -e APP_MODE=production \\
    -e WEB_APP_HOST=0.0.0.0 \\
    -e WEB_APP_PORT=7777 \\
    -e DATABASE_URL=postgresql://fortinet:fortinet123@host.docker.internal:$POSTGRESQL_PORT/fortinet_db \\
    -e REDIS_URL=redis://host.docker.internal:$REDIS_PORT/0 \\
    -e SECRET_KEY=fortinet-secret-key-2024 \\
    -e LOG_LEVEL=INFO \\
    --add-host=host.docker.internal:host-gateway \\
    --label "service.port=$FORTINET_PORT" \\
    --label "service.type=fortinet" \\
    --label "com.centurylinklabs.watchtower.enable=true" \\
    registry.jclee.me/fortinet:latest

echo "✅ Fortinet 애플리케이션 시작됨 - http://localhost:$FORTINET_PORT"
echo "🔍 Health Check: curl http://localhost:$FORTINET_PORT/api/health"
EOF

    # 실행 권한 부여
    chmod +x scripts/individual-services/*.sh
    echo_success "개별 서비스 스크립트 생성 완료"
}

# 통합 실행 스크립트
generate_unified_script() {
    echo_info "🚀 통합 실행 스크립트 생성..."
    
    cat > scripts/run-all-separated.sh << EOF
#!/bin/bash
# 모든 서비스를 각 포트별로 분리 실행

set -e

echo "🎯 FortiGate 서비스 분리 실행 시작..."
echo "  Redis: 포트 $REDIS_PORT"
echo "  PostgreSQL: 포트 $POSTGRESQL_PORT" 
echo "  Fortinet: 포트 $FORTINET_PORT"
echo

# 기존 컨테이너 정리
echo "🧹 기존 컨테이너 정리..."
docker stop fortinet-redis-$REDIS_PORT fortinet-postgresql-$POSTGRESQL_PORT fortinet-app-$FORTINET_PORT 2>/dev/null || true
docker rm fortinet-redis-$REDIS_PORT fortinet-postgresql-$POSTGRESQL_PORT fortinet-app-$FORTINET_PORT 2>/dev/null || true

# 볼륨 생성
echo "💾 볼륨 생성..."
docker volume create redis-data-$REDIS_PORT 2>/dev/null || true
docker volume create postgresql-data-$POSTGRESQL_PORT 2>/dev/null || true
docker volume create fortinet-logs-$FORTINET_PORT 2>/dev/null || true

# 순차적 서비스 시작
echo "▶️  Redis 시작 (포트 $REDIS_PORT)..."
./scripts/individual-services/run-redis.sh

echo "⏳ Redis 준비 대기..."
sleep 10

echo "▶️  PostgreSQL 시작 (포트 $POSTGRESQL_PORT)..."
./scripts/individual-services/run-postgresql.sh

echo "⏳ PostgreSQL 준비 대기..."
sleep 20

echo "▶️  Fortinet 애플리케이션 시작 (포트 $FORTINET_PORT)..."
./scripts/individual-services/run-fortinet.sh

echo "⏳ 애플리케이션 초기화 대기..."
sleep 30

# 상태 확인
echo "📊 서비스 상태 확인..."
echo "----------------------------------------"
echo "Redis ($REDIS_PORT):"
docker logs fortinet-redis-$REDIS_PORT --tail 3

echo "----------------------------------------"
echo "PostgreSQL ($POSTGRESQL_PORT):"
docker logs fortinet-postgresql-$POSTGRESQL_PORT --tail 3

echo "----------------------------------------" 
echo "Fortinet ($FORTINET_PORT):"
docker logs fortinet-app-$FORTINET_PORT --tail 5

echo "----------------------------------------"
echo "✅ 모든 서비스 시작 완료!"
echo
echo "📍 접속 정보:"
echo "  🔴 Redis: localhost:$REDIS_PORT"
echo "  🟢 PostgreSQL: localhost:$POSTGRESQL_PORT"
echo "  🔵 Fortinet App: http://localhost:$FORTINET_PORT"
echo
echo "🔍 Health Check:"
echo "  curl http://localhost:$FORTINET_PORT/api/health"
EOF

    chmod +x scripts/run-all-separated.sh
    echo_success "통합 실행 스크립트 완료"
}

# 서비스 모니터링 스크립트
generate_monitoring_script() {
    echo_info "📊 서비스 모니터링 스크립트 생성..."
    
    cat > scripts/monitor-separated-services.sh << 'EOF'
#!/bin/bash
# 분리된 서비스들의 상태 모니터링

REDIS_PORT=7777
POSTGRESQL_PORT=7778
FORTINET_PORT=7779

echo "📊 FortiGate 분리 서비스 모니터링 대시보드"
echo "=========================================="
echo "날짜: $(date)"
echo

# 컨테이너 상태
echo "🐳 컨테이너 상태:"
docker ps --filter "label=service.port" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "실행 중인 서비스 없음"
echo

# 포트 상태 확인
echo "🌐 포트 상태:"
for port in $REDIS_PORT $POSTGRESQL_PORT $FORTINET_PORT; do
    if nc -z localhost $port 2>/dev/null; then
        echo "  ✅ 포트 $port: 활성"
    else
        echo "  ❌ 포트 $port: 비활성"
    fi
done
echo

# Health Check
echo "💊 Health Check:"
if curl -s -f "http://localhost:$FORTINET_PORT/api/health" > /dev/null 2>&1; then
    echo "  ✅ Fortinet App: 정상"
    curl -s "http://localhost:$FORTINET_PORT/api/health" | head -3
else
    echo "  ❌ Fortinet App: 오류"
fi
echo

# 리소스 사용량
echo "📈 리소스 사용량:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    fortinet-redis-$REDIS_PORT fortinet-postgresql-$POSTGRESQL_PORT fortinet-app-$FORTINET_PORT 2>/dev/null || echo "통계 없음"
echo

# 최근 로그
echo "📝 최근 로그 (각 서비스별 마지막 2줄):"
echo "--- Redis ---"
docker logs fortinet-redis-$REDIS_PORT --tail 2 2>/dev/null || echo "Redis 로그 없음"
echo "--- PostgreSQL ---"
docker logs fortinet-postgresql-$POSTGRESQL_PORT --tail 2 2>/dev/null || echo "PostgreSQL 로그 없음"  
echo "--- Fortinet ---"
docker logs fortinet-app-$FORTINET_PORT --tail 2 2>/dev/null || echo "Fortinet 로그 없음"
echo

echo "🔄 실시간 모니터링을 보려면: watch -n 5 ./scripts/monitor-separated-services.sh"
EOF

    chmod +x scripts/monitor-separated-services.sh
    echo_success "모니터링 스크립트 완료"
}

# 실행
cleanup_ports
generate_individual_scripts
generate_unified_script
generate_monitoring_script

echo_success "🎉 각 이미지별 포트 분리 설정 완료!"
echo
echo "📍 포트 할당:"
echo "  🔴 Redis: $REDIS_PORT"
echo "  🟢 PostgreSQL: $POSTGRESQL_PORT"
echo "  🔵 Fortinet App: $FORTINET_PORT"
echo
echo "🚀 실행 방법:"
echo "  ./scripts/run-all-separated.sh"
echo
echo "📊 모니터링:"
echo "  ./scripts/monitor-separated-services.sh"