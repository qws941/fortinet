#!/bin/bash
# deploy-parallel.sh - 병렬 배포 스크립트

set -euo pipefail

# 색깔 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

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

log_deploy() {
    echo -e "${PURPLE}[DEPLOY]${NC} $1"
}

# 설정
REGISTRY="registry.jclee.me"
IMAGE_NAME="fortinet"
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_USERNAME="admin"
ARGOCD_PASSWORD="bingogo1"

# 환경별 설정
declare -A ENV_APPS=(
    ["production"]="fortinet"
    ["staging"]="fortinet-staging"
    ["development"]="fortinet-development"
)

declare -A ENV_URLS=(
    ["production"]="https://fortinet.jclee.me"
    ["staging"]="https://fortinet-staging.jclee.me"
    ["development"]="https://fortinet-development.jclee.me"
)

declare -A ENV_NODEPORTS=(
    ["production"]="30777"
    ["staging"]="30779"  
    ["development"]="30778"
)

# 사용법 표시
show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS] [ENVIRONMENTS...]

병렬 배포 스크립트 - 여러 환경에 동시 배포

OPTIONS:
    -h, --help          이 도움말 표시
    -t, --tag TAG       특정 이미지 태그 사용 (기본값: latest)
    -f, --force         강제 동기화 (기존 상태 무시)
    -w, --wait          배포 완료까지 대기
    -c, --check         배포 후 헬스체크 수행
    -d, --dry-run       실제 배포 없이 시뮬레이션만 수행
    --no-parallel       순차적 배포 (병렬 비활성화)

ENVIRONMENTS:
    production          프로덕션 환경 (기본값)
    staging             스테이징 환경
    development         개발 환경
    all                 모든 환경

예제:
    $0                                    # 프로덕션에 배포
    $0 staging development               # 스테이징과 개발 환경에 병렬 배포
    $0 all --tag v2.0.123 --wait        # 모든 환경에 특정 태그로 배포 후 대기
    $0 production --force --check       # 프로덕션에 강제 배포 후 헬스체크
    $0 --dry-run all                     # 모든 환경에 대한 배포 시뮬레이션
EOF
}

# ArgoCD CLI 설치 확인
check_argocd_cli() {
    if ! command -v argocd &> /dev/null; then
        log_info "Installing ArgoCD CLI..."
        curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
        chmod +x /tmp/argocd
        sudo mv /tmp/argocd /usr/local/bin/argocd
        log_success "ArgoCD CLI installed"
    fi
}

# ArgoCD 로그인
login_argocd() {
    log_info "Logging in to ArgoCD..."
    argocd login "$ARGOCD_SERVER" \
        --username "$ARGOCD_USERNAME" \
        --password "$ARGOCD_PASSWORD" \
        --insecure \
        --grpc-web
    log_success "ArgoCD login successful"
}

# 단일 환경 배포 함수
deploy_environment() {
    local env=$1
    local image_tag=${2:-latest}
    local force=${3:-false}
    local wait=${4:-false}
    local dry_run=${5:-false}
    
    local app_name=${ENV_APPS[$env]}
    local env_url=${ENV_URLS[$env]}
    local nodeport=${ENV_NODEPORTS[$env]}
    
    log_deploy "Starting deployment to $env environment..."
    log_deploy "  App: $app_name"
    log_deploy "  Image: $REGISTRY/$IMAGE_NAME:$image_tag"
    log_deploy "  URL: $env_url"
    log_deploy "  NodePort: 192.168.50.110:$nodeport"
    
    if [ "$dry_run" = "true" ]; then
        log_info "DRY RUN: Would deploy $app_name with image $REGISTRY/$IMAGE_NAME:$image_tag"
        return 0
    fi
    
    # 애플리케이션 상태 확인
    if ! argocd app get "$app_name" >/dev/null 2>&1; then
        log_error "Application $app_name not found in ArgoCD"
        return 1
    fi
    
    # 이미지 태그 업데이트 (매니페스트 수정)
    if [ "$image_tag" != "latest" ]; then
        log_info "Updating image tag in manifests..."
        sed -i "s|image: ${REGISTRY}/${IMAGE_NAME}:.*|image: ${REGISTRY}/${IMAGE_NAME}:${image_tag}|" \
            "../k8s/manifests/deployment.yaml"
    fi
    
    # 애플리케이션 새로고침
    log_info "Refreshing application $app_name..."
    argocd app get "$app_name" --refresh >/dev/null
    
    # 동기화 옵션 설정
    local sync_args="--prune --timeout 300"
    if [ "$force" = "true" ]; then
        sync_args="$sync_args --force"
        log_warning "Force sync enabled for $app_name"
    fi
    
    # 동기화 실행
    log_info "Syncing application $app_name..."
    if argocd app sync "$app_name" $sync_args; then
        log_success "Sync initiated for $app_name"
        
        # 완료 대기
        if [ "$wait" = "true" ]; then
            log_info "Waiting for sync completion..."
            if argocd app wait "$app_name" --timeout 300; then
                log_success "Deployment completed for $app_name"
            else
                log_error "Deployment timeout for $app_name"
                return 1
            fi
        fi
        
        return 0
    else
        log_error "Sync failed for $app_name"
        return 1
    fi
}

# 헬스체크 함수
health_check() {
    local env=$1
    local env_url=${ENV_URLS[$env]}
    local nodeport=${ENV_NODEPORTS[$env]}
    local fallback_url="http://192.168.50.110:$nodeport/api/health"
    
    log_info "Performing health check for $env environment..."
    
    # 잠시 대기 (배포 완료 후 서비스 준비 시간)
    sleep 30
    
    # Primary URL 체크
    if curl -s --max-time 10 "$env_url/api/health" | grep -q "healthy"; then
        log_success "Health check passed: $env_url"
        return 0
    fi
    
    # Fallback URL 체크
    if curl -s --max-time 10 "$fallback_url" | grep -q "healthy"; then
        log_success "Health check passed (NodePort): $fallback_url"
        return 0
    fi
    
    log_error "Health check failed for $env environment"
    return 1
}

# 병렬 배포 함수
deploy_parallel() {
    local environments=("$@")
    local pids=()
    local results=()
    
    log_info "Starting parallel deployment to ${#environments[@]} environments..."
    
    # 각 환경에 대해 백그라운드 프로세스로 배포 시작
    for env in "${environments[@]}"; do
        (
            deploy_environment "$env" "$IMAGE_TAG" "$FORCE" "$WAIT" "$DRY_RUN"
            echo $? > "/tmp/deploy_${env}_$$"
        ) &
        pids+=($!)
        log_info "Started deployment process for $env (PID: ${pids[-1]})"
    done
    
    # 모든 프로세스 완료 대기
    log_info "Waiting for all deployments to complete..."
    for i in "${!pids[@]}"; do
        wait "${pids[$i]}"
        local result=$(cat "/tmp/deploy_${environments[$i]}_$$")
        results+=("$result")
        rm -f "/tmp/deploy_${environments[$i]}_$$"
        
        if [ "$result" -eq 0 ]; then
            log_success "Deployment completed: ${environments[$i]}"
        else
            log_error "Deployment failed: ${environments[$i]}"
        fi
    done
    
    # 결과 요약
    local success_count=0
    local total_count=${#environments[@]}
    
    for result in "${results[@]}"; do
        if [ "$result" -eq 0 ]; then
            ((success_count++))
        fi
    done
    
    log_info "Deployment summary: $success_count/$total_count environments successful"
    
    # 헬스체크 (요청된 경우)
    if [ "$HEALTH_CHECK" = "true" ] && [ "$success_count" -gt 0 ]; then
        log_info "Performing health checks..."
        for i in "${!environments[@]}"; do
            if [ "${results[$i]}" -eq 0 ]; then
                health_check "${environments[$i]}"
            fi
        done
    fi
    
    return $([ "$success_count" -eq "$total_count" ] && echo 0 || echo 1)
}

# 순차 배포 함수
deploy_sequential() {
    local environments=("$@")
    local success_count=0
    local total_count=${#environments[@]}
    
    log_info "Starting sequential deployment to ${#environments[@]} environments..."
    
    for env in "${environments[@]}"; do
        if deploy_environment "$env" "$IMAGE_TAG" "$FORCE" "$WAIT" "$DRY_RUN"; then
            ((success_count++))
            
            # 헬스체크 (요청된 경우)
            if [ "$HEALTH_CHECK" = "true" ]; then
                health_check "$env"
            fi
        fi
    done
    
    log_info "Sequential deployment summary: $success_count/$total_count environments successful"
    return $([ "$success_count" -eq "$total_count" ] && echo 0 || echo 1)
}

# 메인 함수
main() {
    # 기본값 설정
    IMAGE_TAG="latest"
    FORCE=false
    WAIT=false
    HEALTH_CHECK=false
    DRY_RUN=false
    PARALLEL=true
    ENVIRONMENTS=()
    
    # 인수 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -w|--wait)
                WAIT=true
                shift
                ;;
            -c|--check)
                HEALTH_CHECK=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-parallel)
                PARALLEL=false
                shift
                ;;
            all)
                ENVIRONMENTS=(production staging development)
                shift
                ;;
            production|staging|development)
                ENVIRONMENTS+=("$1")
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # 환경이 지정되지 않은 경우 기본값
    if [ ${#ENVIRONMENTS[@]} -eq 0 ]; then
        ENVIRONMENTS=(production)
    fi
    
    # 환경 유효성 검증
    for env in "${ENVIRONMENTS[@]}"; do
        if [[ ! " production staging development " =~ " $env " ]]; then
            log_error "Invalid environment: $env"
            exit 1
        fi
    done
    
    log_info "🚀 Parallel Deployment Script"
    log_info "Environments: ${ENVIRONMENTS[*]}"
    log_info "Image Tag: $IMAGE_TAG"
    log_info "Force: $FORCE"
    log_info "Wait: $WAIT"
    log_info "Health Check: $HEALTH_CHECK"
    log_info "Dry Run: $DRY_RUN"
    log_info "Parallel: $PARALLEL"
    
    if [ "$DRY_RUN" = "false" ]; then
        # ArgoCD CLI 확인 및 로그인
        check_argocd_cli
        login_argocd
    fi
    
    # 배포 실행
    if [ "$PARALLEL" = "true" ] && [ ${#ENVIRONMENTS[@]} -gt 1 ]; then
        deploy_parallel "${ENVIRONMENTS[@]}"
    else
        deploy_sequential "${ENVIRONMENTS[@]}"
    fi
    
    local exit_code=$?
    
    if [ "$exit_code" -eq 0 ]; then
        log_success "🎉 All deployments completed successfully!"
        
        echo -e "\n🔗 Environment Access URLs:"
        for env in "${ENVIRONMENTS[@]}"; do
            echo "  $env: ${ENV_URLS[$env]} (NodePort: 192.168.50.110:${ENV_NODEPORTS[$env]})"
        done
        
        echo -e "\n📊 Management URLs:"
        echo "  ArgoCD: https://argo.jclee.me"
        echo "  Registry: https://registry.jclee.me"
        echo "  Charts: https://charts.jclee.me"
        
    else
        log_error "❌ Some deployments failed. Check the logs above for details."
        exit 1
    fi
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi