#!/bin/bash
# FortiGate Nextrade 통합 설치 스크립트
# Version: 2.0.0
# Date: 2025-06-04

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 변수 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TAR_FILE="fortinet-offline-deploy-20250604_182511.tar.gz"
IMAGE_NAME="fortigate-nextrade:latest"
CONTAINER_NAME="fortigate-nextrade"
PORT=7777

# 함수: 메시지 출력
print_message() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# 함수: 도움말 표시
show_help() {
    cat << EOF
FortiGate Nextrade 통합 설치 및 관리 도구

사용법: $0 [명령]

명령:
  install     - 오프라인 패키지 설치 및 서비스 시작
  start       - 서비스 시작
  stop        - 서비스 중지
  restart     - 서비스 재시작
  status      - 서비스 상태 확인
  logs        - 서비스 로그 확인
  config      - FortiManager 연결 설정
  uninstall   - 서비스 제거
  help        - 이 도움말 표시

예제:
  $0 install   # 최초 설치
  $0 config    # FortiManager 설정
  $0 status    # 상태 확인

EOF
}

# 함수: Docker 확인
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_message "Docker가 설치되어 있지 않습니다. Docker를 먼저 설치해주세요." "$RED"
        exit 1
    fi
    
    if ! docker ps &> /dev/null; then
        print_message "Docker 데몬이 실행되고 있지 않습니다. Docker를 시작해주세요." "$RED"
        exit 1
    fi
}

# 함수: 설치
install() {
    print_message "FortiGate Nextrade 설치를 시작합니다..." "$BLUE"
    
    # tar 파일 확인
    print_message "스크립트 디렉토리: $SCRIPT_DIR" "$BLUE"
    print_message "찾는 파일: $SCRIPT_DIR/$TAR_FILE" "$BLUE"
    
    if [ ! -f "$SCRIPT_DIR/$TAR_FILE" ]; then
        print_message "설치 파일을 찾을 수 없습니다: $TAR_FILE" "$RED"
        print_message "현재 디렉토리 파일 목록:" "$YELLOW"
        ls -la "$SCRIPT_DIR"/*.tar.gz 2>/dev/null || echo "tar.gz 파일이 없습니다"
        exit 1
    fi
    
    print_message "설치 파일 확인됨: $(ls -lh "$SCRIPT_DIR/$TAR_FILE" | awk '{print $5}')" "$GREEN"
    
    # Docker 이미지 추출 및 로드
    print_message "Docker 이미지를 추출하는 중..." "$YELLOW"
    tar -xzf "$SCRIPT_DIR/$TAR_FILE" -C "$SCRIPT_DIR" --strip-components=1
    
    print_message "Docker 이미지를 로드하는 중..." "$YELLOW"
    # 추출된 Docker 이미지 파일 찾기
    DOCKER_IMAGE_FILE=$(find "$SCRIPT_DIR" -name "*.tar" -not -name "$TAR_FILE" | head -1)
    if [ -f "$DOCKER_IMAGE_FILE" ]; then
        print_message "Docker 이미지 파일: $DOCKER_IMAGE_FILE" "$BLUE"
        docker load -i "$DOCKER_IMAGE_FILE"
    else
        print_message "Docker 이미지 파일을 찾을 수 없습니다" "$RED"
        exit 1
    fi
    
    # 필요한 디렉토리 생성
    mkdir -p "$SCRIPT_DIR/data" "$SCRIPT_DIR/logs" "$SCRIPT_DIR/ssl/certs"
    
    # docker-compose.yml 생성
    create_docker_compose
    
    # 서비스 시작
    start_service
    
    print_message "설치가 완료되었습니다!" "$GREEN"
    print_message "웹 인터페이스: http://localhost:$PORT" "$GREEN"
    print_message "FortiManager 설정: $0 config" "$YELLOW"
}

# 함수: docker-compose.yml 생성
create_docker_compose() {
    cat > "$SCRIPT_DIR/docker-compose.yml" << EOF
version: '3.8'

services:
  fortinet:
    image: $IMAGE_NAME
    container_name: $CONTAINER_NAME
    restart: unless-stopped
    network_mode: bridge
    dns:
      - 127.0.0.1
    ports:
      - "$PORT:$PORT"
    volumes:
      - ./data:/app/data:z
      - ./logs:/app/logs:z
    environment:
      - TZ=Asia/Seoul
      - PYTHONUNBUFFERED=1
      - FLASK_PORT=$PORT
      - FLASK_ENV=production
      - APP_MODE=production
      - HOST_IP=0.0.0.0
      - OFFLINE_MODE=true
      - NO_INTERNET=true
      - DISABLE_EXTERNAL_CALLS=true
      - FORTIMANAGER_HOST=\${FORTIMANAGER_HOST:-172.28.174.31}
      - FORTIMANAGER_USERNAME=\${FORTIMANAGER_USERNAME:-monitor}
      - FORTIMANAGER_PASSWORD=\${FORTIMANAGER_PASSWORD:-}
      - FORTIMANAGER_PORT=\${FORTIMANAGER_PORT:-443}
      - FORTIMANAGER_VERIFY_SSL=false
    healthcheck:
      test: ["CMD", "python3", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s
EOF
}

# 함수: FortiManager 설정
config_fortimanager() {
    print_message "FortiManager 연결 설정" "$BLUE"
    
    # 기존 설정 읽기
    if [ -f "$SCRIPT_DIR/.env" ]; then
        source "$SCRIPT_DIR/.env"
    fi
    
    # 사용자 입력
    read -p "FortiManager 호스트 주소 [$FORTIMANAGER_HOST]: " input_host
    FORTIMANAGER_HOST=${input_host:-$FORTIMANAGER_HOST}
    
    read -p "FortiManager 사용자명 [$FORTIMANAGER_USERNAME]: " input_user
    FORTIMANAGER_USERNAME=${input_user:-${FORTIMANAGER_USERNAME:-admin}}
    
    read -sp "FortiManager 비밀번호: " input_pass
    echo
    FORTIMANAGER_PASSWORD=${input_pass:-$FORTIMANAGER_PASSWORD}
    
    read -p "FortiManager 포트 [$FORTIMANAGER_PORT]: " input_port
    FORTIMANAGER_PORT=${input_port:-${FORTIMANAGER_PORT:-443}}
    
    # .env 파일 생성
    cat > "$SCRIPT_DIR/.env" << EOF
FORTIMANAGER_HOST=$FORTIMANAGER_HOST
FORTIMANAGER_USERNAME=$FORTIMANAGER_USERNAME
FORTIMANAGER_PASSWORD=$FORTIMANAGER_PASSWORD
FORTIMANAGER_PORT=$FORTIMANAGER_PORT
EOF
    
    print_message "설정이 저장되었습니다." "$GREEN"
    
    # 서비스 재시작 여부 확인
    if docker ps | grep -q $CONTAINER_NAME; then
        read -p "서비스를 재시작하시겠습니까? (y/N): " restart_confirm
        if [[ $restart_confirm =~ ^[Yy]$ ]]; then
            restart_service
        fi
    fi
}

# 함수: 서비스 시작
start_service() {
    print_message "서비스를 시작하는 중..." "$YELLOW"
    
    # .env 파일이 있으면 로드
    if [ -f "$SCRIPT_DIR/.env" ]; then
        export $(cat "$SCRIPT_DIR/.env" | xargs)
    fi
    
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
    
    # 컨테이너 시작 대기 (외부 연결 없이)
    print_message "서비스가 준비될 때까지 대기 중..." "$YELLOW"
    for i in {1..30}; do
        if docker ps | grep -q $CONTAINER_NAME; then
            if docker exec $CONTAINER_NAME python3 -c "import sys; sys.exit(0)" &> /dev/null; then
                print_message "서비스가 성공적으로 시작되었습니다!" "$GREEN"
                return 0
            fi
        fi
        sleep 2
        echo -n "."
    done
    echo
    print_message "서비스 시작 확인에 실패했습니다. 로그를 확인해주세요." "$RED"
}

# 함수: 서비스 중지
stop_service() {
    print_message "서비스를 중지하는 중..." "$YELLOW"
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" down
    print_message "서비스가 중지되었습니다." "$GREEN"
}

# 함수: 서비스 재시작
restart_service() {
    stop_service
    start_service
}

# 함수: 서비스 상태
show_status() {
    print_message "서비스 상태:" "$BLUE"
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" ps
    
    echo
    if docker ps | grep -q $CONTAINER_NAME && docker exec $CONTAINER_NAME python3 -c "import sys; sys.exit(0)" &> /dev/null; then
        print_message "웹 인터페이스 상태: 정상" "$GREEN"
        print_message "접속 URL: http://localhost:$PORT" "$GREEN"
    else
        print_message "웹 인터페이스 상태: 응답 없음" "$RED"
    fi
}

# 함수: 로그 보기
show_logs() {
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" logs -f --tail=100
}

# 함수: 제거
uninstall() {
    print_message "FortiGate Nextrade를 제거하시겠습니까?" "$YELLOW"
    read -p "모든 데이터가 삭제됩니다. 계속하시겠습니까? (y/N): " confirm
    
    if [[ $confirm =~ ^[Yy]$ ]]; then
        stop_service
        
        print_message "Docker 이미지를 제거하는 중..." "$YELLOW"
        docker rmi $IMAGE_NAME 2>/dev/null || true
        
        print_message "설치 파일을 정리하는 중..." "$YELLOW"
        rm -f "$SCRIPT_DIR/fortigate-nextrade-offline.tar"
        rm -f "$SCRIPT_DIR/docker-compose.yml"
        rm -f "$SCRIPT_DIR/.env"
        
        read -p "데이터와 로그도 삭제하시겠습니까? (y/N): " delete_data
        if [[ $delete_data =~ ^[Yy]$ ]]; then
            rm -rf "$SCRIPT_DIR/data" "$SCRIPT_DIR/logs" "$SCRIPT_DIR/ssl"
        fi
        
        print_message "제거가 완료되었습니다." "$GREEN"
    else
        print_message "제거가 취소되었습니다." "$YELLOW"
    fi
}

# 메인 실행
check_docker

case "${1:-help}" in
    install)
        install
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    config)
        config_fortimanager
        ;;
    uninstall)
        uninstall
        ;;
    *)
        show_help
        ;;
esac