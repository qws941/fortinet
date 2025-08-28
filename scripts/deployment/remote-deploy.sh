#!/bin/bash
# FortiGate Nextrade 원격 배포 스크립트
# Docker Registry를 통한 원격 서버 배포 시스템

set -e
export TZ=Asia/Seoul

# 기본 설정
PROJECT_NAME="fortigate-nextrade"
BUILD_TIME=$(date +"%Y-%m-%d %H:%M:%S KST")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config/deploy-config.json"
DEFAULT_CONFIG_FILE="${SCRIPT_DIR}/config/deploy-config-example.json"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
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

# 도움말 표시
show_help() {
    cat << EOF
FortiGate Nextrade 원격 배포 스크립트

사용법:
  $0 [환경] [옵션]

환경:
  production    운영 환경 배포
  staging       스테이징 환경 배포
  development   개발 환경 배포

옵션:
  --registry-push     Docker Registry에 이미지 푸시
  --parallel          병렬 배포 (여러 서버 동시 배포)
  --no-backup         백업 생성 건너뛰기
  --dry-run           실제 배포 없이 테스트
  --rollback          이전 버전으로 롤백
  --config FILE       설정 파일 경로 지정
  --help              도움말 표시

예제:
  $0 production --registry-push
  $0 staging --parallel --no-backup
  $0 development --dry-run

환경 변수:
  DOCKER_REGISTRY_URL    Docker Registry URL
  DEPLOY_SSH_KEY         SSH 키 경로
  SLACK_WEBHOOK_URL      Slack 알림 웹훅
  
EOF
}

# 설정 파일 로드
load_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        if [[ -f "$DEFAULT_CONFIG_FILE" ]]; then
            log_warning "설정 파일이 없습니다. 예제 파일을 복사합니다."
            cp "$DEFAULT_CONFIG_FILE" "$CONFIG_FILE"
            log_warning "config/deploy-config.json을 환경에 맞게 수정하세요."
            exit 1
        else
            log_error "설정 파일을 찾을 수 없습니다: $CONFIG_FILE"
            exit 1
        fi
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq가 설치되지 않았습니다. 설치해주세요: sudo apt install jq"
        exit 1
    fi
}

# 환경별 서버 목록 조회
get_servers() {
    local env=$1
    echo $(jq -r ".servers.${env}[] | .host" "$CONFIG_FILE" 2>/dev/null)
}

# 서버 정보 조회
get_server_info() {
    local env=$1
    local host=$2
    local field=$3
    echo $(jq -r ".servers.${env}[] | select(.host==\"${host}\") | .${field}" "$CONFIG_FILE" 2>/dev/null)
}

# Docker Registry 설정
setup_registry() {
    export DOCKER_REGISTRY_URL=${DOCKER_REGISTRY_URL:-"localhost:5000"}
    
    if [[ "$REGISTRY_PUSH" == "true" ]]; then
        log_info "Docker Registry 설정: $DOCKER_REGISTRY_URL"
        
        # Registry 연결 테스트
        if ! curl -s "http://${DOCKER_REGISTRY_URL}/v2/" > /dev/null; then
            log_warning "Docker Registry에 연결할 수 없습니다: $DOCKER_REGISTRY_URL"
            log_info "로컬 Registry를 시작하시겠습니까? (y/n)"
            read -r answer
            if [[ "$answer" == "y" ]]; then
                docker run -d -p 5000:5000 --name registry registry:2 || true
                sleep 5
            fi
        fi
    fi
}

# Docker 이미지 빌드 및 푸시
build_and_push() {
    local image_tag="${DOCKER_REGISTRY_URL}/${PROJECT_NAME}:${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
    local latest_tag="${DOCKER_REGISTRY_URL}/${PROJECT_NAME}:${ENVIRONMENT}-latest"
    
    log_info "Docker 이미지 빌드 중..."
    docker build \
        --build-arg BUILD_TIME="$BUILD_TIME" \
        --build-arg TZ="$TZ" \
        --build-arg ENVIRONMENT="$ENVIRONMENT" \
        -f Dockerfile.offline \
        -t "$image_tag" \
        -t "$latest_tag" .
    
    if [[ "$REGISTRY_PUSH" == "true" ]]; then
        log_info "Docker Registry에 이미지 푸시 중..."
        docker push "$image_tag"
        docker push "$latest_tag"
        
        # 푸시된 이미지 정보 저장
        echo "$latest_tag" > .last_deployed_image
    fi
    
    export DOCKER_IMAGE="$latest_tag"
}

# SSH 연결 테스트
test_ssh_connection() {
    local host=$1
    local user=$2
    local port=$3
    local ssh_key=${DEPLOY_SSH_KEY:-~/.ssh/id_rsa}
    
    log_info "SSH 연결 테스트: ${user}@${host}:${port}"
    
    if ssh -i "$ssh_key" -p "$port" -o ConnectTimeout=10 -o BatchMode=yes \
        "${user}@${host}" "echo 'SSH 연결 성공'" >/dev/null 2>&1; then
        return 0
    else
        log_error "SSH 연결 실패: ${user}@${host}:${port}"
        return 1
    fi
}

# 원격 서버에서 백업 생성
create_backup() {
    local host=$1
    local user=$2
    local port=$3
    local deploy_path=$4
    local ssh_key=${DEPLOY_SSH_KEY:-~/.ssh/id_rsa}
    
    if [[ "$NO_BACKUP" == "true" ]]; then
        log_warning "백업 생성을 건너뜁니다."
        return 0
    fi
    
    log_info "백업 생성 중: ${host}"
    
    local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="${deploy_path}/../backups/${backup_name}"
    
    ssh -i "$ssh_key" -p "$port" "${user}@${host}" "
        mkdir -p ${deploy_path}/../backups
        if [[ -d ${deploy_path} ]]; then
            cp -r ${deploy_path} ${backup_path}
            echo '백업 생성 완료: ${backup_path}'
        else
            echo '배포 디렉토리가 없습니다: ${deploy_path}'
        fi
        
        # 오래된 백업 정리
        cd ${deploy_path}/../backups
        ls -t | tail -n +6 | xargs -r rm -rf
    "
}

# 원격 서버에 배포
deploy_to_server() {
    local host=$1
    local user=$2
    local port=$3
    local deploy_path=$4
    local service_name=$5
    local ssh_key=${DEPLOY_SSH_KEY:-~/.ssh/id_rsa}
    
    log_info "배포 시작: ${host}"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] 실제 배포는 수행하지 않습니다."
        return 0
    fi
    
    # 환경별 설정 생성
    local env_config=$(jq -r ".environments.${ENVIRONMENT}" "$CONFIG_FILE")
    
    ssh -i "$ssh_key" -p "$port" "${user}@${host}" "
        # 배포 디렉토리 생성
        mkdir -p ${deploy_path}
        cd ${deploy_path}
        
        # 기존 서비스 중지
        docker stop ${service_name} 2>/dev/null || true
        docker rm ${service_name} 2>/dev/null || true
        
        # 새 이미지 풀
        docker pull ${DOCKER_IMAGE}
        
        # 환경 설정 파일 생성
        cat > .env << 'ENV_EOF'
APP_MODE=${ENVIRONMENT}
FLASK_ENV=${ENVIRONMENT}
TZ=Asia/Seoul
BUILD_TIME=${BUILD_TIME}
DOCKER_IMAGE=${DOCKER_IMAGE}
$(echo '$env_config' | jq -r 'to_entries[] | \"\\(.key)=\\(.value)\"')
ENV_EOF
        
        # Docker Compose 파일 생성
        cat > docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'
services:
  app:
    image: \${DOCKER_IMAGE}
    container_name: ${service_name}
    restart: unless-stopped
    ports:
      - \"7777:7777\"
    environment:
      - APP_MODE=\${APP_MODE}
      - FLASK_ENV=\${FLASK_ENV}
      - TZ=\${TZ}
      - BUILD_TIME=\${BUILD_TIME}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    healthcheck:
      test: [\"CMD\", \"python3\", \"-c\", \"import urllib.request; urllib.request.urlopen('http://localhost:7777/api/health', timeout=5).read()\"]
      interval: 30s
      timeout: 10s
      start_period: 40s
      retries: 3
COMPOSE_EOF
        
        # 데이터 디렉토리 생성
        mkdir -p data logs
        
        # 서비스 시작
        docker-compose up -d
        
        echo '배포 완료: ${host}'
    "
}

# 헬스체크
health_check() {
    local host=$1
    local port=${2:-7777}
    local max_retries=10
    local retry_count=0
    
    log_info "헬스체크 시작: ${host}:${port}"
    
    while [[ $retry_count -lt $max_retries ]]; do
        if curl -s "http://${host}:${port}/api/health" >/dev/null 2>&1; then
            log_success "헬스체크 성공: ${host}:${port}"
            return 0
        else
            retry_count=$((retry_count + 1))
            log_warning "헬스체크 재시도 (${retry_count}/${max_retries}): ${host}:${port}"
            sleep 10
        fi
    done
    
    log_error "헬스체크 실패: ${host}:${port}"
    return 1
}

# 롤백
rollback() {
    local host=$1
    local user=$2
    local port=$3
    local deploy_path=$4
    local ssh_key=${DEPLOY_SSH_KEY:-~/.ssh/id_rsa}
    
    log_warning "롤백 시작: ${host}"
    
    ssh -i "$ssh_key" -p "$port" "${user}@${host}" "
        cd ${deploy_path}/../backups
        latest_backup=\$(ls -t | head -n 1)
        if [[ -n \"\$latest_backup\" ]]; then
            cd ${deploy_path}/..
            rm -rf ${deploy_path}
            mv backups/\$latest_backup ${deploy_path}
            cd ${deploy_path}
            docker-compose down
            docker-compose up -d
            echo '롤백 완료: \$latest_backup'
        else
            echo '백업이 없습니다.'
            exit 1
        fi
    "
}

# Slack 알림
send_slack_notification() {
    local message=$1
    local color=${2:-"good"}
    
    if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"$color\",\"text\":\"$message\"}]}" \
            "$SLACK_WEBHOOK_URL" >/dev/null || true
    fi
}

# 메인 배포 로직
main() {
    local env=${1:-"development"}
    
    # 유효한 환경인지 확인
    if [[ ! "$env" =~ ^(production|staging|development)$ ]]; then
        log_error "유효하지 않은 환경: $env"
        show_help
        exit 1
    fi
    
    export ENVIRONMENT=$env
    
    log_info "🚀 FortiGate Nextrade 원격 배포 시작"
    log_info "📅 빌드 시간: $BUILD_TIME"
    log_info "🌍 환경: $ENVIRONMENT"
    log_info "🌏 타임존: $TZ"
    echo ""
    
    # 설정 로드
    load_config
    
    # Docker Registry 설정
    setup_registry
    
    # 이미지 빌드 및 푸시
    if [[ "$REGISTRY_PUSH" == "true" ]] || [[ "$ENVIRONMENT" != "development" ]]; then
        build_and_push
    else
        export DOCKER_IMAGE="${PROJECT_NAME}:latest"
    fi
    
    # 서버 목록 조회
    servers=($(get_servers "$ENVIRONMENT"))
    
    if [[ ${#servers[@]} -eq 0 ]]; then
        log_error "환경 '${ENVIRONMENT}'에 대한 서버가 설정되지 않았습니다."
        exit 1
    fi
    
    log_info "배포 대상 서버: ${servers[*]}"
    
    # 배포 시작 알림
    send_slack_notification "🚀 FortiGate Nextrade ${ENVIRONMENT} 배포 시작\\n서버: ${servers[*]}"
    
    # 병렬 배포 vs 순차 배포
    if [[ "$PARALLEL" == "true" ]]; then
        log_info "병렬 배포 모드"
        
        # 백그라운드로 모든 서버에 배포
        pids=()
        for server in "${servers[@]}"; do
            (
                user=$(get_server_info "$ENVIRONMENT" "$server" "user")
                port=$(get_server_info "$ENVIRONMENT" "$server" "port")
                deploy_path=$(get_server_info "$ENVIRONMENT" "$server" "deploy_path")
                service_name=$(get_server_info "$ENVIRONMENT" "$server" "service_name")
                
                if test_ssh_connection "$server" "$user" "$port"; then
                    create_backup "$server" "$user" "$port" "$deploy_path"
                    deploy_to_server "$server" "$user" "$port" "$deploy_path" "$service_name"
                    health_check "$server"
                fi
            ) &
            pids+=($!)
        done
        
        # 모든 배포 완료 대기
        for pid in "${pids[@]}"; do
            wait $pid
        done
    else
        log_info "순차 배포 모드"
        
        # 순차적으로 서버에 배포
        for server in "${servers[@]}"; do
            user=$(get_server_info "$ENVIRONMENT" "$server" "user")
            port=$(get_server_info "$ENVIRONMENT" "$server" "port")
            deploy_path=$(get_server_info "$ENVIRONMENT" "$server" "deploy_path")
            service_name=$(get_server_info "$ENVIRONMENT" "$server" "service_name")
            
            if test_ssh_connection "$server" "$user" "$port"; then
                create_backup "$server" "$user" "$port" "$deploy_path"
                
                if deploy_to_server "$server" "$user" "$port" "$deploy_path" "$service_name"; then
                    if health_check "$server"; then
                        log_success "서버 배포 성공: $server"
                    else
                        log_error "헬스체크 실패: $server"
                        if [[ "$ROLLBACK_ON_FAILURE" == "true" ]]; then
                            rollback "$server" "$user" "$port" "$deploy_path"
                        fi
                        exit 1
                    fi
                else
                    log_error "배포 실패: $server"
                    exit 1
                fi
            else
                log_error "SSH 연결 실패로 배포 중단: $server"
                exit 1
            fi
        done
    fi
    
    # 배포 완료
    log_success "🎉 모든 서버 배포 완료!"
    log_info "📊 배포 정보:"
    log_info "  - 환경: $ENVIRONMENT"
    log_info "  - 이미지: $DOCKER_IMAGE"
    log_info "  - 서버 수: ${#servers[@]}"
    log_info "  - 빌드 시간: $BUILD_TIME"
    
    # 성공 알림
    send_slack_notification "✅ FortiGate Nextrade ${ENVIRONMENT} 배포 완료\\n서버: ${servers[*]}\\n이미지: ${DOCKER_IMAGE}"
    
    echo ""
    log_info "🌐 접속 정보:"
    for server in "${servers[@]}"; do
        log_info "  - http://${server}:7777"
    done
}

# 인자 파싱
ENVIRONMENT=""
REGISTRY_PUSH=false
PARALLEL=false
NO_BACKUP=false
DRY_RUN=false
ROLLBACK=false
ROLLBACK_ON_FAILURE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        production|staging|development)
            ENVIRONMENT=$1
            shift
            ;;
        --registry-push)
            REGISTRY_PUSH=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --no-backup)
            NO_BACKUP=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
done

# 환경이 지정되지 않은 경우 기본값 설정
if [[ -z "$ENVIRONMENT" ]]; then
    ENVIRONMENT="development"
fi

# 메인 함수 실행
main "$ENVIRONMENT"