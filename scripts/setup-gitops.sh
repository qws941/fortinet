#!/bin/bash
set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 프로젝트 설정값
GITHUB_ORG="JCLEE94"
APP_NAME="fortinet"
NAMESPACE="fortinet"

# 기존 NodePort 사용 (이미 30777로 서비스 중)
NODEPORT="30777"

# 인증 정보
REGISTRY_URL="registry.jclee.me"
REGISTRY_USERNAME="admin"
REGISTRY_PASSWORD="bingogo1"
CHARTMUSEUM_URL="https://charts.jclee.me"
CHARTMUSEUM_USERNAME="admin"
CHARTMUSEUM_PASSWORD="bingogo1"

log_info "GitHub Secrets 설정 중..."
gh secret list | grep -q "REGISTRY_URL" || gh secret set REGISTRY_URL -b "${REGISTRY_URL}"
gh secret list | grep -q "REGISTRY_USERNAME" || gh secret set REGISTRY_USERNAME -b "${REGISTRY_USERNAME}"
gh secret list | grep -q "REGISTRY_PASSWORD" || gh secret set REGISTRY_PASSWORD -b "${REGISTRY_PASSWORD}"
gh secret list | grep -q "CHARTMUSEUM_URL" || gh secret set CHARTMUSEUM_URL -b "${CHARTMUSEUM_URL}"
gh secret list | grep -q "CHARTMUSEUM_USERNAME" || gh secret set CHARTMUSEUM_USERNAME -b "${CHARTMUSEUM_USERNAME}"
gh secret list | grep -q "CHARTMUSEUM_PASSWORD" || gh secret set CHARTMUSEUM_PASSWORD -b "${CHARTMUSEUM_PASSWORD}"

log_info "GitHub Variables 설정 중..."
gh variable list | grep -q "APP_NAME" || gh variable set APP_NAME -b "${APP_NAME}"
gh variable list | grep -q "NAMESPACE" || gh variable set NAMESPACE -b "${NAMESPACE}"
gh variable list | grep -q "NODEPORT" || gh variable set NODEPORT -b "${NODEPORT}"

log_info "✅ GitHub 환경 설정 완료"