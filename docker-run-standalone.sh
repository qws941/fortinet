#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Docker 독립 실행 스크립트
# docker-compose 없이 단독 컨테이너로 실행
# =============================================================================

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본 설정
IMAGE_NAME="fortigate-nextrade"
CONTAINER_NAME="fortinet-standalone"
DEFAULT_PORT=7777
REGISTRY="registry.jclee.me/fortinet"

# 함수: 사용법 출력
usage() {
    echo -e "${BLUE}사용법:${NC}"
    echo "  $0 [옵션]"
    echo ""
    echo -e "${YELLOW}옵션:${NC}"
    echo "  -p PORT       포트 번호 (기본: 7777)"
    echo "  -n NAME       컨테이너 이름 (기본: fortinet-standalone)"
    echo "  -m MODE       실행 모드 (production|development|test)"
    echo "  -b            이미지 빌드"
    echo "  -r            레지스트리에서 pull"
    echo "  -d            백그라운드 실행 (detached)"
    echo "  -s            컨테이너 중지"
    echo "  -c            컨테이너 제거"
    echo "  -l            로그 확인"
    echo "  -h            도움말"
    echo ""
    echo -e "${GREEN}예제:${NC}"
    echo "  # 로컬 빌드 후 실행"
    echo "  $0 -b -p 8080"
    echo ""
    echo "  # 레지스트리에서 pull 후 실행"
    echo "  $0 -r -d"
    echo ""
    echo "  # 개발 모드로 실행"
    echo "  $0 -m development"
    exit 0
}

# 함수: 이미지 빌드
build_image() {
    echo -e "${BLUE}🔨 Docker 이미지 빌드 중...${NC}"
    
    # Dockerfile 선택
    if [ -f "Dockerfile.standalone" ]; then
        DOCKERFILE="Dockerfile.standalone"
        echo -e "${GREEN}✓ Standalone Dockerfile 사용${NC}"
    else
        DOCKERFILE="Dockerfile"
        echo -e "${YELLOW}⚠ 기본 Dockerfile 사용${NC}"
    fi
    
    # 빌드 실행
    docker build \
        -f $DOCKERFILE \
        -t ${IMAGE_NAME}:latest \
        -t ${IMAGE_NAME}:$(date +%Y%m%d-%H%M%S) \
        --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
        --build-arg VERSION=standalone-1.0 \
        .
    
    echo -e "${GREEN}✅ 이미지 빌드 완료${NC}"
}

# 함수: 레지스트리에서 pull
pull_image() {
    echo -e "${BLUE}📦 레지스트리에서 이미지 pull 중...${NC}"
    docker pull ${REGISTRY}/${IMAGE_NAME}:latest
    docker tag ${REGISTRY}/${IMAGE_NAME}:latest ${IMAGE_NAME}:latest
    echo -e "${GREEN}✅ 이미지 pull 완료${NC}"
}

# 함수: 컨테이너 실행
run_container() {
    local PORT=${1:-$DEFAULT_PORT}
    local MODE=${2:-production}
    local DETACHED=${3:-}
    
    echo -e "${BLUE}🚀 컨테이너 실행 중...${NC}"
    echo -e "  포트: ${GREEN}${PORT}${NC}"
    echo -e "  모드: ${GREEN}${MODE}${NC}"
    echo -e "  이름: ${GREEN}${CONTAINER_NAME}${NC}"
    
    # 기존 컨테이너 중지 및 제거
    if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
        echo -e "${YELLOW}⚠ 기존 컨테이너 중지 및 제거${NC}"
        docker stop ${CONTAINER_NAME} 2>/dev/null || true
        docker rm ${CONTAINER_NAME} 2>/dev/null || true
    fi
    
    # 실행 옵션 설정
    RUN_OPTS=""
    if [ "$DETACHED" = "true" ]; then
        RUN_OPTS="-d"
    else
        RUN_OPTS="-it"
    fi
    
    # 컨테이너 실행
    docker run $RUN_OPTS \
        --name ${CONTAINER_NAME} \
        -p ${PORT}:7777 \
        -e APP_MODE=${MODE} \
        -e WEB_APP_PORT=7777 \
        -e OFFLINE_MODE=true \
        -e SELF_CONTAINED=true \
        -e SECRET_KEY=$(openssl rand -hex 32) \
        -e TZ=Asia/Seoul \
        --restart unless-stopped \
        --health-cmd="curl -f http://localhost:7777/api/health || exit 1" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-start-period=60s \
        --health-retries=3 \
        ${IMAGE_NAME}:latest
    
    if [ "$DETACHED" = "true" ]; then
        echo -e "${GREEN}✅ 컨테이너가 백그라운드에서 실행 중입니다${NC}"
        echo -e "${BLUE}💡 로그 확인: docker logs -f ${CONTAINER_NAME}${NC}"
        echo -e "${BLUE}💡 접속 URL: http://localhost:${PORT}${NC}"
    fi
}

# 함수: 컨테이너 중지
stop_container() {
    echo -e "${YELLOW}⏹ 컨테이너 중지 중...${NC}"
    docker stop ${CONTAINER_NAME}
    echo -e "${GREEN}✅ 컨테이너 중지 완료${NC}"
}

# 함수: 컨테이너 제거
remove_container() {
    echo -e "${YELLOW}🗑 컨테이너 제거 중...${NC}"
    docker rm -f ${CONTAINER_NAME} 2>/dev/null || true
    echo -e "${GREEN}✅ 컨테이너 제거 완료${NC}"
}

# 함수: 로그 확인
show_logs() {
    echo -e "${BLUE}📋 컨테이너 로그:${NC}"
    docker logs -f ${CONTAINER_NAME}
}

# 함수: 헬스체크
health_check() {
    local PORT=${1:-$DEFAULT_PORT}
    echo -e "${BLUE}🏥 헬스체크 실행 중...${NC}"
    
    # 최대 30초 대기
    for i in {1..30}; do
        if curl -f http://localhost:${PORT}/api/health 2>/dev/null; then
            echo -e "\n${GREEN}✅ 애플리케이션이 정상 작동 중입니다${NC}"
            echo -e "${BLUE}🌐 접속 URL: http://localhost:${PORT}${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    echo -e "\n${RED}❌ 헬스체크 실패${NC}"
    return 1
}

# 메인 스크립트
main() {
    local PORT=$DEFAULT_PORT
    local MODE="production"
    local BUILD=false
    local PULL=false
    local DETACHED=false
    local STOP=false
    local REMOVE=false
    local LOGS=false
    
    # 옵션 파싱
    while getopts "p:n:m:brdscblh" opt; do
        case $opt in
            p) PORT=$OPTARG ;;
            n) CONTAINER_NAME=$OPTARG ;;
            m) MODE=$OPTARG ;;
            b) BUILD=true ;;
            r) PULL=true ;;
            d) DETACHED=true ;;
            s) STOP=true ;;
            c) REMOVE=true ;;
            l) LOGS=true ;;
            h) usage ;;
            *) usage ;;
        esac
    done
    
    # 작업 실행
    if [ "$STOP" = true ]; then
        stop_container
        exit 0
    fi
    
    if [ "$REMOVE" = true ]; then
        remove_container
        exit 0
    fi
    
    if [ "$LOGS" = true ]; then
        show_logs
        exit 0
    fi
    
    if [ "$BUILD" = true ]; then
        build_image
    elif [ "$PULL" = true ]; then
        pull_image
    else
        # 이미지 존재 확인
        if [[ "$(docker images -q ${IMAGE_NAME}:latest 2> /dev/null)" == "" ]]; then
            echo -e "${YELLOW}⚠ 이미지가 없습니다. 빌드를 시작합니다...${NC}"
            build_image
        fi
    fi
    
    # 컨테이너 실행
    run_container $PORT $MODE $DETACHED
    
    # 백그라운드 실행시 헬스체크
    if [ "$DETACHED" = true ]; then
        sleep 3
        health_check $PORT
    fi
}

# 스크립트 실행
main "$@"