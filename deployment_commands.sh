#!/bin/bash

# =============================================================================
# FortiGate Nextrade 배포 명령어 스크립트
# 보안 개선 및 코드 품질 향상 반영된 운영 배포용
# =============================================================================

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 헤더 출력
print_header() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

# 환경 변수 설정
setup_environment() {
    print_header "🔧 운영 환경 변수 설정"
    
    # 필수 환경 변수 (보안 강화)
    export APP_MODE=production
    export WEB_APP_PORT=7777
    export WEB_APP_HOST=0.0.0.0
    export OFFLINE_MODE=false
    
    # 보안 설정 (운영 필수)
    export VERIFY_SSL=true
    export SESSION_COOKIE_SECURE=true
    export SESSION_COOKIE_HTTPONLY=true
    export SESSION_COOKIE_SAMESITE=Lax
    export PERMANENT_SESSION_LIFETIME=900
    
    # JWT 보안 설정
    export JWT_EXPIRES_IN=900
    export JWT_ALGORITHM=HS256
    export JWT_ISSUER=fortinet-app
    export JWT_AUDIENCE=fortinet-api
    
    # API 보안
    export API_RATE_LIMIT_MAX=100
    export API_RATE_LIMIT_WINDOW=60
    export API_TIMEOUT=30
    
    # 로깅 설정
    export LOG_LEVEL=INFO
    export DISABLE_DEBUG_LOGS=true
    export MASK_SENSITIVE_DATA=true
    
    # GitOps 메타데이터
    export GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    export GIT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
    export GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "master")
    export VERSION="v1.0.9-fix-redis"
    export BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    export BUILD_TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
    export IMMUTABLE_TAG="${VERSION}-${GIT_SHA}"
    export REGISTRY_URL="registry.jclee.me"
    
    print_success "환경 변수 설정 완료"
    print_info "GitOps 태그: ${IMMUTABLE_TAG}"
    print_info "레지스트리: ${REGISTRY_URL}/fortinet:${IMMUTABLE_TAG}"
}

# SECRET_KEY 생성 (보안 강화)
generate_secret_key() {
    print_header "🔐 보안 키 생성"
    
    if [ -z "$SECRET_KEY" ]; then
        print_info "새로운 SECRET_KEY 생성 중..."
        export SECRET_KEY=$(openssl rand -hex 32)
        print_success "SECRET_KEY 생성 완료 (32바이트)"
        print_warning "SECRET_KEY를 안전한 곳에 저장하세요!"
        echo "export SECRET_KEY=\"$SECRET_KEY\"" > .env.production
        chmod 600 .env.production
    else
        print_success "기존 SECRET_KEY 사용"
    fi
}

# 배포 전 검증
validate_deployment() {
    print_header "🔍 배포 전 검증"
    
    # 배포 검증 스크립트 실행
    if [ -f "deployment_validation.py" ]; then
        print_info "배포 검증 스크립트 실행 중..."
        python3 deployment_validation.py
        
        if [ $? -eq 0 ]; then
            print_success "배포 검증 통과"
        else
            print_error "배포 검증 실패"
            exit 1
        fi
    else
        print_warning "배포 검증 스크립트 없음 - 기본 검증 실행"
        
        # 기본 검증
        if [ ! -f "Dockerfile" ]; then
            print_error "Dockerfile 없음"
            exit 1
        fi
        
        if [ ! -f "requirements.txt" ]; then
            print_error "requirements.txt 없음"
            exit 1
        fi
        
        if [ ! -d "charts/fortinet" ]; then
            print_error "Helm 차트 없음"
            exit 1
        fi
        
        print_success "기본 검증 통과"
    fi
}

# Docker 이미지 빌드
build_docker_image() {
    print_header "🐳 Docker 이미지 빌드"
    
    local image_tag="${REGISTRY_URL}/fortinet:${IMMUTABLE_TAG}"
    local latest_tag="${REGISTRY_URL}/fortinet:latest"
    
    print_info "이미지 빌드 시작: ${image_tag}"
    
    docker build \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg BUILD_TIMESTAMP="${BUILD_TIMESTAMP}" \
        --build-arg GIT_COMMIT="${GIT_COMMIT}" \
        --build-arg GIT_SHA="${GIT_SHA}" \
        --build-arg GIT_BRANCH="${GIT_BRANCH}" \
        --build-arg VERSION="${VERSION}" \
        --build-arg IMMUTABLE_TAG="${IMMUTABLE_TAG}" \
        --build-arg REGISTRY_URL="${REGISTRY_URL}" \
        -t "${image_tag}" \
        -t "${latest_tag}" \
        .
    
    if [ $? -eq 0 ]; then
        print_success "Docker 이미지 빌드 완료"
        print_info "이미지 태그: ${image_tag}"
        print_info "최신 태그: ${latest_tag}"
    else
        print_error "Docker 이미지 빌드 실패"
        exit 1
    fi
}

# 레지스트리에 푸시
push_to_registry() {
    print_header "📤 레지스트리 푸시"
    
    local image_tag="${REGISTRY_URL}/fortinet:${IMMUTABLE_TAG}"
    local latest_tag="${REGISTRY_URL}/fortinet:latest"
    
    print_info "이미지 푸시 시작..."
    
    # Harbor 레지스트리 로그인 (환경변수 필요)
    if [ -n "$REGISTRY_USERNAME" ] && [ -n "$REGISTRY_PASSWORD" ]; then
        echo "$REGISTRY_PASSWORD" | docker login "$REGISTRY_URL" -u "$REGISTRY_USERNAME" --password-stdin
        
        if [ $? -ne 0 ]; then
            print_error "레지스트리 로그인 실패"
            exit 1
        fi
        
        print_success "레지스트리 로그인 성공"
    else
        print_warning "레지스트리 인증 정보 없음 - 수동 로그인 필요"
    fi
    
    # 이미지 푸시
    docker push "${image_tag}"
    docker push "${latest_tag}"
    
    if [ $? -eq 0 ]; then
        print_success "이미지 푸시 완료"
        print_info "레지스트리 URL: https://${REGISTRY_URL}/harbor/projects"
    else
        print_error "이미지 푸시 실패"
        exit 1
    fi
}

# Helm 차트 업데이트
update_helm_chart() {
    print_header "⚙️  Helm 차트 업데이트"
    
    local chart_path="charts/fortinet"
    local values_file="${chart_path}/values.yaml"
    
    if [ -f "$values_file" ]; then
        print_info "values.yaml 업데이트 중..."
        
        # 이미지 태그 업데이트
        sed -i "s/tag: .*/tag: \"${IMMUTABLE_TAG}\"/" "$values_file"
        
        # GitOps 메타데이터 업데이트
        sed -i "s/GIT_SHA: .*/GIT_SHA: \"${GIT_SHA}\"/" "$values_file"
        sed -i "s/GIT_COMMIT: .*/GIT_COMMIT: \"${GIT_COMMIT}\"/" "$values_file"
        sed -i "s/VERSION: .*/VERSION: \"${VERSION}\"/" "$values_file"
        sed -i "s/BUILD_DATE: .*/BUILD_DATE: \"${BUILD_DATE}\"/" "$values_file"
        
        print_success "Helm 차트 업데이트 완료"
        print_info "이미지 태그: ${IMMUTABLE_TAG}"
    else
        print_error "values.yaml 파일 없음"
        exit 1
    fi
}

# ArgoCD 배포
deploy_with_argocd() {
    print_header "🚀 ArgoCD 배포"
    
    # Git 커밋 및 푸시 (GitOps)
    print_info "Git 변경사항 커밋 중..."
    git add charts/fortinet/values.yaml
    git commit -m "deploy: update to ${IMMUTABLE_TAG} with security improvements

🔐 Security Enhancements:
- Updated cryptography to 44.0.1 (Critical vulnerabilities fixed)
- Enhanced SSL verification settings
- Improved container security (non-root user)
- Added security manager and automated fixes

⚙️ Configuration Updates:
- Image tag: ${IMMUTABLE_TAG}
- Registry: ${REGISTRY_URL}
- Build date: ${BUILD_DATE}

🤖 Generated with Claude Code (https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
    
    git push origin master
    
    if [ $? -eq 0 ]; then
        print_success "Git 푸시 완료 - GitOps 파이프라인 트리거됨"
    else
        print_error "Git 푸시 실패"
        exit 1
    fi
    
    # ArgoCD 동기화 (선택사항)
    if command -v argocd &> /dev/null; then
        print_info "ArgoCD 수동 동기화 중..."
        argocd app sync fortinet
        argocd app wait fortinet --timeout 300
        
        if [ $? -eq 0 ]; then
            print_success "ArgoCD 동기화 완료"
        else
            print_warning "ArgoCD 동기화 실패 - 수동 확인 필요"
        fi
    else
        print_info "ArgoCD CLI 없음 - GitHub Actions 자동 배포 대기"
    fi
}

# 배포 후 검증
verify_deployment() {
    print_header "✅ 배포 후 검증"
    
    local health_url="http://192.168.50.110:30777/api/health"
    local domain_url="http://fortinet.jclee.me/api/health"
    
    print_info "배포 완료 대기 중... (60초)"
    sleep 60
    
    # NodePort 접속 확인
    print_info "NodePort 헬스체크 중..."
    response=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null || echo "000")
    
    if [ "$response" = "200" ]; then
        print_success "NodePort 접속 성공 (${health_url})"
    else
        print_warning "NodePort 접속 실패 (응답 코드: ${response})"
    fi
    
    # 도메인 접속 확인 (hosts 파일 설정 필요)
    print_info "도메인 접속 확인 중..."
    domain_response=$(curl -s -o /dev/null -w "%{http_code}" "$domain_url" 2>/dev/null || echo "000")
    
    if [ "$domain_response" = "200" ]; then
        print_success "도메인 접속 성공 (${domain_url})"
    else
        print_warning "도메인 접속 실패 - hosts 파일 설정 확인 필요"
        print_info "설정 명령: echo '192.168.50.110 fortinet.jclee.me' | sudo tee -a /etc/hosts"
    fi
    
    # 헬스체크 상세 정보
    print_info "헬스체크 상세 정보:"
    curl -s "$health_url" 2>/dev/null | jq . 2>/dev/null || curl -s "$health_url"
}

# 배포 요약 출력
print_deployment_summary() {
    print_header "📊 배포 완료 요약"
    
    echo -e "${GREEN}🎉 FortiGate Nextrade 배포 완료!${NC}"
    echo
    echo -e "${CYAN}📦 배포 정보:${NC}"
    echo -e "  • 이미지: ${REGISTRY_URL}/fortinet:${IMMUTABLE_TAG}"
    echo -e "  • 버전: ${VERSION}"
    echo -e "  • 빌드: ${BUILD_DATE}"
    echo -e "  • 커밋: ${GIT_SHA}"
    echo
    echo -e "${CYAN}🌐 접속 URL:${NC}"
    echo -e "  • NodePort: http://192.168.50.110:30777"
    echo -e "  • 도메인: http://fortinet.jclee.me"
    echo -e "  • 헬스체크: http://192.168.50.110:30777/api/health"
    echo
    echo -e "${CYAN}🔧 모니터링:${NC}"
    echo -e "  • ArgoCD: http://192.168.50.110:31017/applications/fortinet"
    echo -e "  • Harbor: https://registry.jclee.me/harbor/projects"
    echo
    echo -e "${CYAN}📋 추가 명령어:${NC}"
    echo -e "  • 로그 확인: kubectl logs -l app=fortinet -n fortinet -f"
    echo -e "  • 팟 상태: kubectl get pods -n fortinet"
    echo -e "  • ArgoCD 동기화: argocd app sync fortinet"
}

# 메인 실행 함수
main() {
    print_header "🚀 FortiGate Nextrade 배포 시작"
    
    # 단계별 실행
    setup_environment
    generate_secret_key
    validate_deployment
    build_docker_image
    
    # 레지스트리 푸시 (인증 정보가 있는 경우)
    if [ -n "$REGISTRY_USERNAME" ] && [ -n "$REGISTRY_PASSWORD" ]; then
        push_to_registry
    else
        print_warning "레지스트리 인증 정보 없음 - 수동 푸시 필요"
        print_info "수동 푸시 명령: docker push ${REGISTRY_URL}/fortinet:${IMMUTABLE_TAG}"
    fi
    
    update_helm_chart
    deploy_with_argocd
    verify_deployment
    print_deployment_summary
    
    print_success "배포 프로세스 완료!"
}

# 사용법 출력
usage() {
    echo "사용법: $0 [옵션]"
    echo
    echo "옵션:"
    echo "  --build-only      Docker 이미지 빌드만 실행"
    echo "  --deploy-only     배포만 실행 (빌드 제외)"
    echo "  --verify-only     배포 후 검증만 실행"
    echo "  --help           이 도움말 출력"
    echo
    echo "환경변수:"
    echo "  REGISTRY_USERNAME  레지스트리 사용자명"
    echo "  REGISTRY_PASSWORD  레지스트리 비밀번호"
    echo "  SECRET_KEY         애플리케이션 시크릿 키"
    echo
    echo "예시:"
    echo "  # 전체 배포"
    echo "  ./deployment_commands.sh"
    echo
    echo "  # 빌드만 실행"
    echo "  ./deployment_commands.sh --build-only"
    echo
    echo "  # 인증 정보와 함께 배포"
    echo "  REGISTRY_USERNAME=admin REGISTRY_PASSWORD=password ./deployment_commands.sh"
}

# 명령행 인수 처리
case "${1:-}" in
    --build-only)
        setup_environment
        generate_secret_key
        validate_deployment
        build_docker_image
        print_success "빌드 완료!"
        ;;
    --deploy-only)
        setup_environment
        update_helm_chart
        deploy_with_argocd
        verify_deployment
        print_deployment_summary
        ;;
    --verify-only)
        verify_deployment
        ;;
    --help)
        usage
        ;;
    "")
        main
        ;;
    *)
        print_error "알 수 없는 옵션: $1"
        usage
        exit 1
        ;;
esac