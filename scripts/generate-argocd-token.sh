#!/bin/bash

# ArgoCD 서버 정보
ARGOCD_SERVER="argo.jclee.me"
ARGOCD_USERNAME="admin"
ARGOCD_PASSWORD="bingogo1"

echo "🔐 ArgoCD API 토큰 생성 중..."

# 1. ArgoCD 로그인
echo "1️⃣ ArgoCD 로그인..."
argocd login $ARGOCD_SERVER \
    --username $ARGOCD_USERNAME \
    --password $ARGOCD_PASSWORD \
    --insecure \
    --grpc-web

# 2. 기존 토큰 확인
echo "2️⃣ 기존 토큰 확인..."
EXISTING_TOKEN=$(argocd account get-user-info --grpc-web | grep -A5 "fortinet-ci" || echo "")

if [ ! -z "$EXISTING_TOKEN" ]; then
    echo "   ⚠️ 기존 토큰이 있습니다. 삭제 후 재생성합니다."
    argocd account delete-token fortinet-ci --grpc-web 2>/dev/null || true
fi

# 3. 새 토큰 생성
echo "3️⃣ 새 API 토큰 생성..."
TOKEN=$(argocd account generate-token --grpc-web)

if [ -z "$TOKEN" ]; then
    echo "❌ 토큰 생성 실패!"
    exit 1
fi

echo "✅ ArgoCD API 토큰 생성 완료!"
echo ""
echo "📋 토큰 정보:"
echo "   이름: fortinet-ci"
echo "   토큰: $TOKEN"
echo ""
echo "🔧 GitHub Secrets에 추가하려면:"
echo "   gh secret set ARGOCD_AUTH_TOKEN --body=\"$TOKEN\""
echo ""
echo "🧪 토큰 테스트:"
echo "   ARGOCD_TOKEN='$TOKEN' python scripts/test-argocd-api.py"

# 토큰을 파일로 저장 (보안 주의!)
echo "$TOKEN" > .argocd-token
chmod 600 .argocd-token
echo ""
echo "💾 토큰이 .argocd-token 파일에 저장되었습니다 (보안 주의!)"