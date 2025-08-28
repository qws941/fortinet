#!/bin/bash
# =============================================================================
# FortiGate Nextrade - 볼륨 마이그레이션 스크립트
# 바인드 마운트에서 Docker 명명된 볼륨으로 데이터 마이그레이션
# =============================================================================

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 프로젝트 디렉토리
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 마이그레이션 대상 정의
declare -A VOLUME_MAPPINGS=(
    ["fortinet-data"]="./data"
    ["fortinet-logs"]="./logs"
    ["fortinet-temp"]="./temp"
    ["fortinet-config"]="./config"
    ["fortinet-cache"]="./cache"
    ["fortinet-static"]="./static"
    ["fortinet-uploads"]="./uploads"
)

# 백업 디렉토리
BACKUP_DIR="./backups/migration_$(date +%Y%m%d_%H%M%S)"

# 도움말
show_help() {
    cat << EOF
FortiGate Nextrade - 볼륨 마이그레이션 도구

이 스크립트는 기존 바인드 마운트 디렉토리의 데이터를
Docker 명명된 볼륨으로 마이그레이션합니다.

사용법: $0 [옵션]

옵션:
  -h, --help       도움말 표시
  -b, --backup     마이그레이션 전 백업 생성
  -f, --force      확인 없이 진행
  -d, --dry-run    실제 작업 없이 시뮬레이션만 수행

마이그레이션 대상:
  ./data     -> fortinet-data
  ./logs     -> fortinet-logs
  ./temp     -> fortinet-temp
  ./config   -> fortinet-config
  ./cache    -> fortinet-cache
  ./static   -> fortinet-static
  ./uploads  -> fortinet-uploads
EOF
}

# 옵션 파싱
BACKUP=false
FORCE=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -b|--backup)
            BACKUP=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            error "알 수 없는 옵션: $1"
            show_help
            exit 1
            ;;
    esac
done

# 확인 메시지
if [[ "$FORCE" != true ]] && [[ "$DRY_RUN" != true ]]; then
    warning "이 스크립트는 기존 디렉토리의 데이터를 Docker 볼륨으로 마이그레이션합니다."
    warning "계속하시겠습니까? (y/N)"
    read -r confirm
    if [[ "$confirm" != "y" ]]; then
        log "취소되었습니다."
        exit 0
    fi
fi

# 컨테이너 상태 확인
check_containers() {
    if docker-compose ps -q | grep -q .; then
        error "실행 중인 컨테이너가 있습니다. 먼저 중지하세요:"
        error "  docker-compose down"
        exit 1
    fi
}

# 백업 생성
create_backup() {
    if [[ "$BACKUP" == true ]] && [[ "$DRY_RUN" != true ]]; then
        log "백업을 생성합니다: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
        
        for volume in "${!VOLUME_MAPPINGS[@]}"; do
            local src_dir="${VOLUME_MAPPINGS[$volume]}"
            if [[ -d "$src_dir" ]] && [[ -n "$(ls -A "$src_dir" 2>/dev/null)" ]]; then
                log "백업 중: $src_dir"
                tar czf "$BACKUP_DIR/${volume}.tar.gz" -C "$src_dir" .
            fi
        done
        success "백업 완료"
    fi
}

# 볼륨 생성
create_volumes() {
    log "Docker 볼륨을 생성합니다..."
    
    for volume in "${!VOLUME_MAPPINGS[@]}"; do
        if [[ "$DRY_RUN" == true ]]; then
            log "[DRY RUN] 볼륨 생성: $volume"
        else
            if ! docker volume inspect "$volume" &>/dev/null; then
                docker volume create "$volume"
                log "볼륨 생성됨: $volume"
            else
                log "볼륨 이미 존재: $volume"
            fi
        fi
    done
}

# 데이터 마이그레이션
migrate_data() {
    log "데이터를 마이그레이션합니다..."
    
    for volume in "${!VOLUME_MAPPINGS[@]}"; do
        local src_dir="${VOLUME_MAPPINGS[$volume]}"
        
        if [[ ! -d "$src_dir" ]]; then
            warning "디렉토리가 없습니다: $src_dir (건너뜀)"
            continue
        fi
        
        if [[ -z "$(ls -A "$src_dir" 2>/dev/null)" ]]; then
            warning "디렉토리가 비어있습니다: $src_dir (건너뜀)"
            continue
        fi
        
        if [[ "$DRY_RUN" == true ]]; then
            log "[DRY RUN] 마이그레이션: $src_dir -> $volume"
            log "[DRY RUN] 데이터 크기: $(du -sh "$src_dir" | cut -f1)"
        else
            log "마이그레이션 중: $src_dir -> $volume"
            
            # 임시 컨테이너를 사용하여 데이터 복사
            docker run --rm \
                -v "$volume:/dest" \
                -v "$(realpath "$src_dir"):/src:ro" \
                alpine sh -c "cp -av /src/. /dest/"
            
            success "완료: $volume"
        fi
    done
}

# 마이그레이션 검증
verify_migration() {
    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    
    log "마이그레이션을 검증합니다..."
    
    local all_success=true
    
    for volume in "${!VOLUME_MAPPINGS[@]}"; do
        local src_dir="${VOLUME_MAPPINGS[$volume]}"
        
        if [[ ! -d "$src_dir" ]] || [[ -z "$(ls -A "$src_dir" 2>/dev/null)" ]]; then
            continue
        fi
        
        # 원본 파일 수 계산
        local src_count=$(find "$src_dir" -type f | wc -l)
        
        # 볼륨 파일 수 계산
        local vol_count=$(docker run --rm -v "$volume:/data:ro" alpine find /data -type f | wc -l)
        
        if [[ "$src_count" -eq "$vol_count" ]]; then
            success "검증 성공: $volume (파일 수: $vol_count)"
        else
            error "검증 실패: $volume (원본: $src_count, 볼륨: $vol_count)"
            all_success=false
        fi
    done
    
    if [[ "$all_success" == true ]]; then
        success "모든 볼륨 검증 완료"
    else
        error "일부 볼륨 검증 실패"
        exit 1
    fi
}

# 정리 옵션 제공
cleanup_old_dirs() {
    if [[ "$DRY_RUN" == true ]]; then
        return
    fi
    
    warning "마이그레이션이 완료되었습니다."
    warning "기존 디렉토리를 삭제하시겠습니까? (백업이 있는 경우에만 권장)"
    warning "삭제할 디렉토리: ${!VOLUME_MAPPINGS[@]}"
    warning "계속하시겠습니까? (y/N)"
    
    read -r confirm
    if [[ "$confirm" == "y" ]]; then
        for src_dir in "${VOLUME_MAPPINGS[@]}"; do
            if [[ -d "$src_dir" ]]; then
                rm -rf "$src_dir"
                log "삭제됨: $src_dir"
            fi
        done
        success "기존 디렉토리 삭제 완료"
    else
        log "기존 디렉토리를 유지합니다."
    fi
}

# 마이그레이션 요약
show_summary() {
    echo ""
    echo "====================================="
    echo "마이그레이션 요약"
    echo "====================================="
    
    for volume in "${!VOLUME_MAPPINGS[@]}"; do
        local src_dir="${VOLUME_MAPPINGS[$volume]}"
        if [[ -d "$src_dir" ]] && [[ -n "$(ls -A "$src_dir" 2>/dev/null)" ]]; then
            local size=$(du -sh "$src_dir" 2>/dev/null | cut -f1 || echo "N/A")
            echo "$src_dir -> $volume (크기: $size)"
        fi
    done
    
    if [[ "$BACKUP" == true ]]; then
        echo ""
        echo "백업 위치: $BACKUP_DIR"
    fi
    
    echo "====================================="
}

# 메인 실행
main() {
    log "FortiGate Nextrade 볼륨 마이그레이션 시작"
    
    # 사전 검사
    check_containers
    
    # 요약 표시
    show_summary
    
    # 백업 생성
    create_backup
    
    # 볼륨 생성
    create_volumes
    
    # 데이터 마이그레이션
    migrate_data
    
    # 검증
    verify_migration
    
    # 정리
    cleanup_old_dirs
    
    if [[ "$DRY_RUN" == true ]]; then
        warning "DRY RUN 모드로 실행되었습니다. 실제 변경사항은 없습니다."
    else
        success "마이그레이션이 완료되었습니다!"
        log "이제 'docker-compose up -d'로 컨테이너를 시작할 수 있습니다."
    fi
}

# 실행
main