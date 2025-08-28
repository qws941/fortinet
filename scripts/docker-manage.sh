#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Docker 관리 스크립트
# 단일 컨테이너 운영 관리를 위한 통합 스크립트
# =============================================================================

set -euo pipefail

# 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
ENV_FILE="${ENV_FILE:-.env}"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로깅 함수
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# 도움말 함수
show_help() {
    cat << EOF
${MAGENTA}FortiGate Nextrade - Docker 관리 도구${NC}

${YELLOW}사용법:${NC} $0 [명령] [옵션]

${YELLOW}명령어:${NC}
  ${GREEN}up${NC}              컨테이너 시작 (백그라운드)
  ${GREEN}down${NC}            컨테이너 중지 및 제거
  ${GREEN}restart${NC}         컨테이너 재시작
  ${GREEN}logs${NC}            컨테이너 로그 보기
  ${GREEN}status${NC}          컨테이너 상태 확인
  ${GREEN}shell${NC}           컨테이너 쉘 접속
  ${GREEN}exec${NC}            컨테이너에서 명령 실행
  ${GREEN}build${NC}           이미지 빌드
  ${GREEN}pull${NC}            이미지 풀
  ${GREEN}push${NC}            이미지 푸시
  ${GREEN}ps${NC}              실행 중인 컨테이너 목록
  ${GREEN}images${NC}          이미지 목록
  ${GREEN}volumes${NC}         볼륨 목록 및 정보
  ${GREEN}volume-backup${NC}   볼륨 백업
  ${GREEN}volume-restore${NC}  볼륨 복원
  ${GREEN}clean${NC}           미사용 리소스 정리
  ${GREEN}update${NC}          컨테이너 업데이트
  ${GREEN}health${NC}          헬스체크 상태
  ${GREEN}stats${NC}           리소스 사용량 통계
  ${GREEN}config${NC}          설정 검증
  ${GREEN}init${NC}            환경 초기화

${YELLOW}옵션:${NC}
  -h, --help      도움말 표시
  -f, --file      Docker Compose 파일 지정
  -e, --env       환경 파일 지정
  -v, --verbose   상세 출력
  --follow        로그 실시간 추적

${YELLOW}예제:${NC}
  $0 up                    # 컨테이너 시작
  $0 logs --follow         # 실시간 로그 보기
  $0 exec python main.py   # 컨테이너에서 명령 실행
  $0 volume-backup data    # 데이터 볼륨 백업
  $0 update                # 최신 이미지로 업데이트

${YELLOW}볼륨 관리:${NC}
  fortinet-data      애플리케이션 데이터
  fortinet-logs      로그 파일
  fortinet-temp      임시 파일
  fortinet-config    설정 파일
  fortinet-cache     캐시 데이터
  fortinet-static    정적 파일
  fortinet-uploads   업로드 파일
EOF
}

# 디렉토리 변경
cd "$PROJECT_DIR"

# Docker Compose 명령 래퍼
compose() {
    if command -v docker-compose &> /dev/null; then
        docker-compose --file "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
    else
        docker compose --file "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"
    fi
}

# 컨테이너 시작
cmd_up() {
    log "컨테이너를 시작합니다..."
    compose up -d
    sleep 3
    cmd_status
    success "컨테이너가 시작되었습니다."
}

# 컨테이너 중지
cmd_down() {
    log "컨테이너를 중지합니다..."
    compose down
    success "컨테이너가 중지되었습니다."
}

# 컨테이너 재시작
cmd_restart() {
    log "컨테이너를 재시작합니다..."
    compose restart
    success "컨테이너가 재시작되었습니다."
}

# 로그 보기
cmd_logs() {
    local follow=""
    if [[ "${2:-}" == "--follow" ]] || [[ "${2:-}" == "-f" ]]; then
        follow="--follow"
    fi
    compose logs --tail=100 $follow
}

# 상태 확인
cmd_status() {
    info "컨테이너 상태:"
    compose ps
    
    echo ""
    info "헬스체크 상태:"
    local container_name=$(compose ps -q)
    if [[ -n "$container_name" ]]; then
        docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "헬스체크 없음"
    else
        warning "실행 중인 컨테이너가 없습니다."
    fi
}

# 쉘 접속
cmd_shell() {
    local container_name=$(compose ps -q)
    if [[ -z "$container_name" ]]; then
        error "실행 중인 컨테이너가 없습니다."
        exit 1
    fi
    docker exec -it "$container_name" /bin/bash
}

# 명령 실행
cmd_exec() {
    local container_name=$(compose ps -q)
    if [[ -z "$container_name" ]]; then
        error "실행 중인 컨테이너가 없습니다."
        exit 1
    fi
    shift # 'exec' 명령 제거
    docker exec "$container_name" "$@"
}

# 이미지 빌드
cmd_build() {
    log "이미지를 빌드합니다..."
    compose build --no-cache
    success "이미지 빌드가 완료되었습니다."
}

# 이미지 풀
cmd_pull() {
    log "이미지를 가져옵니다..."
    compose pull
    success "이미지를 가져왔습니다."
}

# 이미지 푸시
cmd_push() {
    log "이미지를 푸시합니다..."
    compose push
    success "이미지를 푸시했습니다."
}

# 컨테이너 목록
cmd_ps() {
    compose ps
}

# 이미지 목록
cmd_images() {
    docker images | grep -E "(fortinet|REPOSITORY)" || true
}

# 볼륨 목록
cmd_volumes() {
    info "FortiGate Nextrade 볼륨:"
    docker volume ls | grep -E "(fortinet|DRIVER)" || true
    
    echo ""
    info "볼륨 상세 정보:"
    for vol in fortinet-data fortinet-logs fortinet-temp fortinet-config fortinet-cache fortinet-static fortinet-uploads; do
        if docker volume inspect "$vol" &>/dev/null; then
            echo -e "\n${GREEN}$vol:${NC}"
            docker volume inspect "$vol" | jq -r '.[0] | "  크기: \(.Size // "N/A")\n  마운트포인트: \(.Mountpoint)\n  생성일: \(.CreatedAt)"' 2>/dev/null || echo "  정보 조회 실패"
        fi
    done
}

# 볼륨 백업
cmd_volume_backup() {
    local volume_name="${2:-}"
    if [[ -z "$volume_name" ]]; then
        error "볼륨 이름을 지정하세요. (예: fortinet-data)"
        exit 1
    fi
    
    local backup_dir="./backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${backup_dir}/${volume_name}_${timestamp}.tar.gz"
    
    mkdir -p "$backup_dir"
    
    log "볼륨 백업: $volume_name -> $backup_file"
    
    docker run --rm \
        -v "$volume_name:/data:ro" \
        -v "$(pwd)/$backup_dir:/backup" \
        alpine tar czf "/backup/$(basename "$backup_file")" -C /data .
    
    success "백업 완료: $backup_file"
}

# 볼륨 복원
cmd_volume_restore() {
    local volume_name="${2:-}"
    local backup_file="${3:-}"
    
    if [[ -z "$volume_name" ]] || [[ -z "$backup_file" ]]; then
        error "사용법: $0 volume-restore <볼륨명> <백업파일>"
        exit 1
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        error "백업 파일을 찾을 수 없습니다: $backup_file"
        exit 1
    fi
    
    warning "볼륨 복원: $volume_name <- $backup_file"
    warning "기존 데이터가 덮어씌워집니다. 계속하시겠습니까? (y/N)"
    read -r confirm
    
    if [[ "$confirm" != "y" ]]; then
        info "취소되었습니다."
        exit 0
    fi
    
    docker run --rm \
        -v "$volume_name:/data" \
        -v "$(realpath "$backup_file"):/backup.tar.gz:ro" \
        alpine sh -c "cd /data && tar xzf /backup.tar.gz"
    
    success "복원 완료"
}

# 정리
cmd_clean() {
    log "미사용 리소스를 정리합니다..."
    docker system prune -f
    docker volume prune -f
    success "정리가 완료되었습니다."
}

# 업데이트
cmd_update() {
    log "컨테이너를 업데이트합니다..."
    cmd_pull
    cmd_down
    cmd_up
    success "업데이트가 완료되었습니다."
}

# 헬스체크
cmd_health() {
    local container_name=$(compose ps -q)
    if [[ -z "$container_name" ]]; then
        error "실행 중인 컨테이너가 없습니다."
        exit 1
    fi
    
    info "헬스체크 상세 정보:"
    docker inspect --format='{{json .State.Health}}' "$container_name" | jq '.' 2>/dev/null || echo "헬스체크 정보 없음"
}

# 통계
cmd_stats() {
    info "리소스 사용량:"
    docker stats --no-stream $(compose ps -q) 2>/dev/null || warning "통계를 가져올 수 없습니다."
}

# 설정 검증
cmd_config() {
    info "Docker Compose 설정 검증:"
    compose config
}

# 환경 초기화
cmd_init() {
    log "환경을 초기화합니다..."
    
    # .env 파일 생성
    if [[ ! -f "$ENV_FILE" ]]; then
        if [[ -f ".env.example" ]]; then
            cp .env.example "$ENV_FILE"
            info ".env 파일이 생성되었습니다. 설정을 확인하세요."
        else
            warning ".env.example 파일을 찾을 수 없습니다."
        fi
    fi
    
    # 필요한 디렉토리 생성
    mkdir -p data logs temp config cache static uploads backups
    
    # 볼륨 생성
    for vol in fortinet-data fortinet-logs fortinet-temp fortinet-config fortinet-cache fortinet-static fortinet-uploads; do
        if ! docker volume inspect "$vol" &>/dev/null; then
            docker volume create "$vol"
            info "볼륨 생성: $vol"
        fi
    done
    
    success "환경 초기화가 완료되었습니다."
}

# 메인 함수
main() {
    local command="${1:-}"
    
    if [[ -z "$command" ]] || [[ "$command" == "-h" ]] || [[ "$command" == "--help" ]]; then
        show_help
        exit 0
    fi
    
    case "$command" in
        up) cmd_up ;;
        down) cmd_down ;;
        restart) cmd_restart ;;
        logs) cmd_logs "$@" ;;
        status) cmd_status ;;
        shell) cmd_shell ;;
        exec) cmd_exec "$@" ;;
        build) cmd_build ;;
        pull) cmd_pull ;;
        push) cmd_push ;;
        ps) cmd_ps ;;
        images) cmd_images ;;
        volumes) cmd_volumes ;;
        volume-backup) cmd_volume_backup "$@" ;;
        volume-restore) cmd_volume_restore "$@" ;;
        clean) cmd_clean ;;
        update) cmd_update ;;
        health) cmd_health ;;
        stats) cmd_stats ;;
        config) cmd_config ;;
        init) cmd_init ;;
        *)
            error "알 수 없는 명령: $command"
            show_help
            exit 1
            ;;
    esac
}

# 실행
main "$@"