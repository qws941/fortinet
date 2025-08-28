#!/bin/bash

# =============================================================================
# FortiGate Nextrade - Docker Compose + Watchtower 배포 스크립트
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 환경 변수 확인
check_env() {
    log_info "환경 변수 확인 중..."
    
    if [ ! -f .env ]; then
        log_warning ".env 파일이 없습니다. 기본값으로 생성합니다..."
        cat > .env << EOF
# Docker Registry
DOCKER_REGISTRY=registry.jclee.me
DOCKER_IMAGE_NAME=fortinet
DOCKER_TAG=latest

# Application
APP_MODE=production
WEB_APP_PORT=7777
SECRET_KEY=$(openssl rand -hex 32)

# FortiGate
FORTIGATE_HOST=192.168.50.100
FORTIGATE_API_TOKEN=your-api-token

# FortiManager  
FORTIMANAGER_HOST=192.168.50.5
FORTIMANAGER_USERNAME=admin
FORTIMANAGER_PASSWORD=your-password

# Watchtower
WATCHTOWER_API_TOKEN=$(openssl rand -hex 32)

# Registry Credentials
REGISTRY_USERNAME=admin
REGISTRY_PASSWORD=your-registry-password
EOF
        log_success ".env 파일 생성 완료"
    fi
    
    source .env
}

# Docker 로그인
docker_login() {
    log_info "Docker Registry 로그인 중..."
    
    echo "${REGISTRY_PASSWORD}" | docker login ${DOCKER_REGISTRY} \
        --username ${REGISTRY_USERNAME} \
        --password-stdin || {
        log_error "Docker Registry 로그인 실패"
        exit 1
    }
    
    log_success "Docker Registry 로그인 성공"
}

# 이미지 빌드 및 푸시
build_and_push() {
    log_info "Docker 이미지 빌드 중..."
    
    # 프로덕션 이미지 빌드
    docker build \
        -f Dockerfile.production \
        -t ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG} \
        -t ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest \
        . || {
        log_error "Docker 이미지 빌드 실패"
        exit 1
    }
    
    log_success "Docker 이미지 빌드 완료"
    
    # 이미지 푸시
    log_info "Docker 이미지 푸시 중..."
    docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}
    docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest
    
    log_success "Docker 이미지 푸시 완료"
}

# 컨테이너 배포
deploy_containers() {
    log_info "컨테이너 배포 시작..."
    
    # 기존 컨테이너 정지 및 제거
    docker-compose down --remove-orphans 2>/dev/null || true
    
    # 메인 애플리케이션 시작
    docker-compose up -d || {
        log_error "메인 애플리케이션 배포 실패"
        exit 1
    }
    
    log_success "메인 애플리케이션 배포 완료"
    
    # Watchtower 시작
    log_info "Watchtower 서비스 시작..."
    docker-compose -f docker-compose.watchtower.yml up -d || {
        log_error "Watchtower 배포 실패"
        exit 1
    }
    
    log_success "Watchtower 서비스 시작 완료"
}

# 헬스체크
health_check() {
    log_info "헬스체크 수행 중..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s http://localhost:${WEB_APP_PORT}/api/health > /dev/null; then
            log_success "애플리케이션 헬스체크 성공"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "헬스체크 대기 중... ($attempt/$max_attempts)"
        sleep 2
    done
    
    log_error "헬스체크 실패"
    return 1
}

# 배포 상태 확인
check_deployment() {
    log_info "배포 상태 확인..."
    
    echo -e "\n${BLUE}=== 실행 중인 컨테이너 ===${NC}"
    docker-compose ps
    
    echo -e "\n${BLUE}=== Watchtower 상태 ===${NC}"
    docker-compose -f docker-compose.watchtower.yml ps
    
    echo -e "\n${BLUE}=== 최근 로그 ===${NC}"
    docker-compose logs --tail=20 fortinet
    
    echo -e "\n${GREEN}=== 배포 정보 ===${NC}"
    echo "🌐 애플리케이션 URL: http://localhost:${WEB_APP_PORT}"
    echo "📊 Watchtower API: http://localhost:8080"
    echo "🔄 자동 업데이트: 5분마다 체크"
    echo "📦 레지스트리: ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"
}

# 메인 실행
main() {
    log_info "FortiGate Nextrade 배포 시작"
    
    check_env
    docker_login
    build_and_push
    deploy_containers
    
    if health_check; then
        check_deployment
        log_success "✅ 배포 완료! Watchtower가 자동으로 업데이트를 관리합니다."
    else
        log_error "❌ 배포 실패. 로그를 확인하세요."
        docker-compose logs --tail=50
        exit 1
    fi
}

# 스크립트 실행
main "$@"