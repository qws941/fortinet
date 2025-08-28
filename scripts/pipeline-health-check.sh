#!/bin/bash
# CI/CD 파이프라인 헬스체크 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 헬퍼 함수
print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
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
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 시작
print_header "FortiGate Nextrade 파이프라인 헬스체크"

# 1. Git 상태 확인
print_header "Git 상태 확인"
if git status &>/dev/null; then
    BRANCH=$(git branch --show-current)
    print_success "Git 리포지토리: $(pwd)"
    print_info "현재 브랜치: $BRANCH"
    
    # Uncommitted changes 확인
    if [[ -n $(git status -s) ]]; then
        print_warning "커밋되지 않은 변경사항 있음"
        git status -s
    else
        print_success "작업 디렉토리 깨끗함"
    fi
else
    print_error "Git 리포지토리가 아닙니다"
    exit 1
fi

# 2. Registry 연결 확인
print_header "Registry 연결 확인"
if curl -f -s https://registry.jclee.me/v2/ > /dev/null; then
    print_success "registry.jclee.me 연결 성공"
    
    # 현재 이미지 확인
    REPOS=$(curl -s https://registry.jclee.me/v2/_catalog | jq -r '.repositories[]' 2>/dev/null || echo "")
    if [[ -n "$REPOS" ]]; then
        print_info "현재 레지스트리 이미지:"
        echo "$REPOS" | while read repo; do
            echo "  📦 $repo"
        done
    fi
    
    # fortinet 이미지 확인
    if echo "$REPOS" | grep -q "fortinet"; then
        TAGS=$(curl -s https://registry.jclee.me/v2/fortinet/tags/list | jq -r '.tags[]?' 2>/dev/null || echo "")
        if [[ -n "$TAGS" ]]; then
            print_success "fortinet 이미지 태그:"
            echo "$TAGS" | head -5 | while read tag; do
                echo "  🏷️  $tag"
            done
        fi
    else
        print_warning "fortinet 이미지가 아직 빌드되지 않음"
    fi
else
    print_error "registry.jclee.me에 연결할 수 없음"
fi

# 3. Dockerfile 확인
print_header "Dockerfile 확인"
if [[ -f "Dockerfile.production" ]]; then
    print_success "Dockerfile.production 존재"
elif [[ -f "Dockerfile" ]]; then
    print_warning "Dockerfile만 존재 (Dockerfile.production 권장)"
else
    print_error "Dockerfile이 없음"
fi

# 4. GitHub Actions 워크플로우 확인
print_header "GitHub Actions 워크플로우 확인"
if [[ -f ".github/workflows/build-deploy.yml" ]]; then
    print_success "build-deploy.yml 워크플로우 존재"
    
    # Workflow 구문 확인 (기본적인 체크)
    if grep -q "registry.jclee.me" .github/workflows/build-deploy.yml; then
        print_success "레지스트리 설정 확인됨"
    else
        print_error "레지스트리 설정 누락"
    fi
    
    if grep -q "insecure = true" .github/workflows/build-deploy.yml; then
        print_success "Insecure 레지스트리 설정 확인됨"
    else
        print_warning "Insecure 레지스트리 설정 확인 필요"
    fi
else
    print_error "GitHub Actions 워크플로우가 없음"
fi

# 5. Kubernetes 매니페스트 확인
print_header "Kubernetes 매니페스트 확인"
if [[ -d "k8s/manifests" ]]; then
    print_success "k8s/manifests 디렉토리 존재"
    
    if [[ -f "k8s/manifests/kustomization.yaml" ]]; then
        print_success "kustomization.yaml 존재"
        
        if grep -q "registry.jclee.me" k8s/manifests/kustomization.yaml; then
            print_success "레지스트리 이미지 설정 확인됨"
        else
            print_error "레지스트리 이미지 설정 누락"
        fi
    else
        print_error "kustomization.yaml 누락"
    fi
    
    if [[ -f "k8s/manifests/registry-noauth-secret.yaml" ]]; then
        print_success "레지스트리 시크릿 존재"
    else
        print_warning "레지스트리 시크릿 누락"
    fi
else
    print_error "k8s/manifests 디렉토리 누락"
fi

# 6. 의존성 파일 확인
print_header "의존성 파일 확인"
if [[ -f "requirements.txt" ]]; then
    print_success "requirements.txt 존재"
    DEPS=$(wc -l < requirements.txt)
    print_info "$DEPS개의 의존성 패키지"
else
    print_warning "requirements.txt 없음"
fi

# 7. ArgoCD 연결 확인 (선택적)
print_header "ArgoCD 연결 확인"
if command -v argocd > /dev/null; then
    if argocd version --client > /dev/null 2>&1; then
        print_success "ArgoCD CLI 설치됨"
        
        # ArgoCD 서버 연결 시도 (에러 무시)
        if argocd app list > /dev/null 2>&1; then
            print_success "ArgoCD 서버 연결 성공"
            
            if argocd app get fortinet > /dev/null 2>&1; then
                print_success "fortinet 애플리케이션 존재"
            else
                print_warning "fortinet 애플리케이션 없음"
            fi
        else
            print_warning "ArgoCD 서버에 연결할 수 없음 (로그인 필요할 수 있음)"
        fi
    else
        print_warning "ArgoCD CLI 설정 문제"
    fi
else
    print_info "ArgoCD CLI 설치되지 않음 (선택적)"
fi

# 8. 최근 커밋 확인
print_header "최근 커밋 확인"
RECENT_COMMITS=$(git log --oneline -5)
print_info "최근 5개 커밋:"
echo "$RECENT_COMMITS" | while read commit; do
    echo "  📝 $commit"
done

# 요약
print_header "헬스체크 요약"
echo ""
print_info "🔍 모니터링 링크:"
echo "  📊 GitHub Actions: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:\/]\(.*\)\.git/\1/')/actions"
echo "  🎯 ArgoCD: https://argo.jclee.me/applications/fortinet"
echo "  🗂️  Registry: https://registry.jclee.me/v2/_catalog"
echo "  🌐 Application: https://fortinet.jclee.me"
echo ""
print_info "🚀 배포 명령어:"
echo "  ./scripts/deploy-simple.sh"
echo "  git push origin $BRANCH"
echo ""

print_success "헬스체크 완료!"