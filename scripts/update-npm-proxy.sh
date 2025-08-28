#!/bin/bash

# Nginx Proxy Manager 자동 업데이트 스크립트
# 이 스크립트는 Kubernetes 서비스의 포트 변경을 감지하고 NPM을 자동으로 업데이트합니다

set -e

# 설정
NPM_URL="http://your-npm-domain.com"  # NPM 주소
NPM_EMAIL="admin@example.com"         # NPM 관리자 이메일
NPM_PASSWORD="changeme"                # NPM 관리자 비밀번호
PROXY_HOST_ID=""                       # 업데이트할 Proxy Host ID (첫 실행 후 설정)

# Kubernetes 설정
K8S_NAMESPACE="fortinet"
K8S_SERVICE="fortinet-nodeport"
K8S_NODE_IP="192.168.50.110"          # Kubernetes 노드 IP

echo "🔄 Nginx Proxy Manager 자동 업데이트"
echo "===================================="

# 1. NPM 로그인
echo "1️⃣ NPM 로그인 중..."
TOKEN=$(curl -s -X POST "${NPM_URL}/api/tokens" \
  -H "Content-Type: application/json" \
  -d "{\"identity\":\"${NPM_EMAIL}\",\"secret\":\"${NPM_PASSWORD}\"}" \
  | jq -r '.token')

if [ -z "$TOKEN" ]; then
  echo "❌ NPM 로그인 실패"
  exit 1
fi

echo "✅ 로그인 성공"

# 2. Kubernetes에서 현재 NodePort 가져오기
echo "2️⃣ Kubernetes NodePort 확인 중..."
NODE_PORT=$(kubectl get service ${K8S_SERVICE} -n ${K8S_NAMESPACE} -o jsonpath='{.spec.ports[0].nodePort}')

if [ -z "$NODE_PORT" ]; then
  echo "❌ NodePort를 찾을 수 없습니다"
  exit 1
fi

echo "✅ 현재 NodePort: $NODE_PORT"

# 3. 기존 Proxy Host 찾기 또는 생성
if [ -z "$PROXY_HOST_ID" ]; then
  echo "3️⃣ Proxy Host 검색 중..."
  
  # 모든 proxy hosts 가져오기
  HOSTS=$(curl -s -X GET "${NPM_URL}/api/nginx/proxy-hosts" \
    -H "Authorization: Bearer ${TOKEN}")
  
  # fortinet 도메인 찾기
  PROXY_HOST_ID=$(echo "$HOSTS" | jq -r '.[] | select(.domain_names[] | contains("fortinet")) | .id' | head -1)
  
  if [ -z "$PROXY_HOST_ID" ]; then
    echo "4️⃣ 새 Proxy Host 생성 중..."
    # 새 proxy host 생성
    RESPONSE=$(curl -s -X POST "${NPM_URL}/api/nginx/proxy-hosts" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d '{
        "domain_names": ["fortinet.jclee.me"],
        "forward_scheme": "http",
        "forward_host": "'${K8S_NODE_IP}'",
        "forward_port": '${NODE_PORT}',
        "access_list_id": "0",
        "certificate_id": 0,
        "meta": {
          "letsencrypt_agree": false,
          "dns_challenge": false
        },
        "advanced_config": "",
        "locations": [],
        "block_exploits": true,
        "caching_enabled": false,
        "allow_websocket_upgrade": true,
        "http2_support": true,
        "hsts_enabled": false,
        "hsts_subdomains": false,
        "ssl_forced": false
      }')
    
    PROXY_HOST_ID=$(echo "$RESPONSE" | jq -r '.id')
    echo "✅ Proxy Host 생성됨 (ID: $PROXY_HOST_ID)"
    echo "⚠️  스크립트의 PROXY_HOST_ID를 업데이트하세요: $PROXY_HOST_ID"
  fi
fi

# 4. Proxy Host 업데이트
echo "4️⃣ Proxy Host 업데이트 중..."
UPDATE_RESPONSE=$(curl -s -X PUT "${NPM_URL}/api/nginx/proxy-hosts/${PROXY_HOST_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "forward_host": "'${K8S_NODE_IP}'",
    "forward_port": '${NODE_PORT}'
  }')

if [ $? -eq 0 ]; then
  echo "✅ Proxy Host 업데이트 완료"
  echo "   - Forward to: ${K8S_NODE_IP}:${NODE_PORT}"
else
  echo "❌ 업데이트 실패"
  exit 1
fi

echo ""
echo "🎉 완료!"
echo "Proxy Host ID: $PROXY_HOST_ID (다음 실행을 위해 저장하세요)"