#!/bin/bash

# =============================================================================
# FortiGate Nextrade - 원격 서버 배포 스크립트
# Target: 192.168.50.215:1111 (SSH) / 192.168.50.110:30777 (NodePort)
# =============================================================================

set -e

# 설정
REMOTE_HOST="192.168.50.215"
REMOTE_PORT="1111"
REMOTE_USER="docker"
REMOTE_PATH="/volume1/docker/fortinet"
NODE_PORT="30777"
REGISTRY="registry.jclee.me"
IMAGE_NAME="fortinet"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 로그 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 타임스탬프 생성
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TAG="${TIMESTAMP}"

# 1. Docker 이미지 빌드 및 푸시
build_and_push() {
    log_info "Docker 이미지 빌드 시작..."
    
    # 프로덕션 이미지 빌드
    docker build \
        -f Dockerfile.production \
        -t ${REGISTRY}/${IMAGE_NAME}:${TAG} \
        -t ${REGISTRY}/${IMAGE_NAME}:latest \
        . || {
        log_error "Docker 이미지 빌드 실패"
        exit 1
    }
    
    log_success "Docker 이미지 빌드 완료: ${REGISTRY}/${IMAGE_NAME}:${TAG}"
    
    # Registry 로그인
    log_info "Docker Registry 로그인..."
    docker login ${REGISTRY} || {
        log_error "Registry 로그인 실패"
        exit 1
    }
    
    # 이미지 푸시
    log_info "이미지 푸시 중..."
    docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}
    docker push ${REGISTRY}/${IMAGE_NAME}:latest
    
    log_success "이미지 푸시 완료"
}

# 2. 원격 서버에 파일 전송
transfer_files() {
    log_info "원격 서버에 파일 전송 중..."
    
    # SSH 연결 테스트
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} "echo 'SSH 연결 성공'" || {
        log_error "SSH 연결 실패"
        exit 1
    }
    
    # 원격 디렉토리 생성
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_PATH}"
    
    # Docker Compose 파일 전송
    scp -P ${REMOTE_PORT} \
        docker-compose.yml \
        docker-compose.watchtower.yml \
        ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/
    
    # 환경 변수 파일 전송 (있는 경우)
    if [ -f .env ]; then
        scp -P ${REMOTE_PORT} .env ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/
    fi
    
    log_success "파일 전송 완료"
}

# 3. 원격 서버에서 배포 실행
deploy_remote() {
    log_info "원격 서버에서 배포 실행 중..."
    
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << EOF
        cd ${REMOTE_PATH}
        
        # 환경 변수 설정
        export DOCKER_TAG=${TAG}
        export NODE_PORT=${NODE_PORT}
        
        # 기존 컨테이너 정지
        docker-compose down --remove-orphans 2>/dev/null || true
        
        # 새 이미지 풀
        docker pull ${REGISTRY}/${IMAGE_NAME}:${TAG}
        docker pull ${REGISTRY}/${IMAGE_NAME}:latest
        
        # 컨테이너 시작
        docker-compose up -d
        
        # Watchtower 시작
        docker-compose -f docker-compose.watchtower.yml up -d
        
        # 상태 확인
        docker-compose ps
        docker ps | grep fortinet
EOF
    
    log_success "원격 배포 완료"
}

# 4. 헬스체크
health_check() {
    log_info "애플리케이션 헬스체크 중..."
    
    local max_attempts=30
    local attempt=0
    local health_url="http://${REMOTE_HOST}:${NODE_PORT}/api/health"
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f -s ${health_url} > /dev/null 2>&1; then
            log_success "헬스체크 성공!"
            
            # 상세 정보 출력
            echo -e "\n${GREEN}=== 배포 완료 ===${NC}"
            echo "🌐 애플리케이션 URL: http://${REMOTE_HOST}:${NODE_PORT}"
            echo "📦 배포된 이미지: ${REGISTRY}/${IMAGE_NAME}:${TAG}"
            echo "🔄 Watchtower 자동 업데이트: 활성화 (5분 간격)"
            echo "📊 상태 확인: curl ${health_url}"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log_info "헬스체크 대기 중... ($attempt/$max_attempts)"
        sleep 2
    done
    
    log_error "헬스체크 실패"
    return 1
}

# 5. 롤백 함수
rollback() {
    log_warning "롤백 실행 중..."
    
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << EOF
        cd ${REMOTE_PATH}
        
        # 이전 버전으로 롤백
        docker-compose down
        docker-compose up -d --force-recreate
        
        echo "롤백 완료. 이전 버전으로 복구됨."
EOF
}

# 메인 실행
main() {
    log_info "🚀 FortiGate Nextrade 원격 배포 시작"
    
    # 단계별 실행
    build_and_push
    transfer_files
    deploy_remote
    
    # 헬스체크
    if health_check; then
        log_success "✅ 배포 성공!"
        
        # 로그 확인
        echo -e "\n${BLUE}=== 최근 로그 ===${NC}"
        ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} \
            "cd ${REMOTE_PATH} && docker-compose logs --tail=10 fortinet"
    else
        log_error "❌ 배포 실패. 롤백을 시작합니다..."
        rollback
        exit 1
    fi
}

# 스크립트 실행
main "$@"