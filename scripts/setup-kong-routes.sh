#!/bin/bash

# Kong API Gateway 라우팅 설정 스크립트
set -e

KONG_ADMIN_URL="http://localhost:8001"

echo "Kong API Gateway 라우팅 설정 시작..."

# 서비스 등록 및 라우트 설정 함수
setup_service_route() {
    local service_name=$1
    local service_host=$2
    local service_port=$3
    local route_path=$4
    
    echo "Setting up service: $service_name"
    
    # 서비스 등록
    curl -s -X POST ${KONG_ADMIN_URL}/services \
        --data name=$service_name \
        --data host=$service_host \
        --data port=$service_port \
        --data protocol=http
    
    # 라우트 등록
    curl -s -X POST ${KONG_ADMIN_URL}/services/$service_name/routes \
        --data paths[]=$route_path \
        --data methods[]=GET \
        --data methods[]=POST \
        --data methods[]=PUT \
        --data methods[]=DELETE \
        --data strip_path=false
    
    echo "✅ $service_name configured"
}

# 인증 서비스
setup_service_route "auth-service" "auth-service" 8081 "/auth"

# FortiManager 서비스
setup_service_route "fortimanager-service" "fortimanager-service" 8082 "/fortimanager"

# ITSM 서비스
setup_service_route "itsm-service" "itsm-service" 8083 "/itsm"

# 모니터링 서비스
setup_service_route "monitoring-service" "monitoring-service" 8084 "/monitoring"

# 보안 서비스
setup_service_route "security-service" "security-service" 8085 "/security"

# 분석 서비스
setup_service_route "analysis-service" "analysis-service" 8086 "/analysis"

# 설정 서비스
setup_service_route "config-service" "config-service" 8087 "/config"

echo ""
echo "🔒 JWT 인증 플러그인 설정..."

# JWT 플러그인 전역 설정
curl -s -X POST ${KONG_ADMIN_URL}/plugins \
    --data name=jwt \
    --data config.secret_is_base64=false \
    --data config.header_names[]=Authorization

echo "✅ JWT plugin configured"

echo ""
echo "⚡ Rate Limiting 플러그인 설정..."

# Rate Limiting 플러그인 설정
curl -s -X POST ${KONG_ADMIN_URL}/plugins \
    --data name=rate-limiting \
    --data config.minute=100 \
    --data config.hour=1000

echo "✅ Rate limiting plugin configured"

echo ""
echo "📝 로깅 플러그인 설정..."

# HTTP Log 플러그인 설정
curl -s -X POST ${KONG_ADMIN_URL}/plugins \
    --data name=http-log \
    --data config.http_endpoint=http://monitoring-service:8084/api/gateway-logs

echo "✅ HTTP log plugin configured"

echo ""
echo "🎯 CORS 플러그인 설정..."

# CORS 플러그인 설정
curl -s -X POST ${KONG_ADMIN_URL}/plugins \
    --data name=cors \
    --data config.origins="*" \
    --data config.methods=GET,POST,PUT,DELETE,OPTIONS \
    --data config.headers="Accept,Authorization,Content-Type,X-Requested-With" \
    --data config.credentials=true

echo "✅ CORS plugin configured"

echo ""
echo "🔍 Kong 설정 확인..."

# 설정된 서비스 확인
echo "Registered Services:"
curl -s ${KONG_ADMIN_URL}/services | jq -r '.data[].name' | sort

echo ""
echo "Registered Routes:"
curl -s ${KONG_ADMIN_URL}/routes | jq -r '.data[] | "\(.name // "unnamed"): \(.paths[])"' | sort

echo ""
echo "Installed Plugins:"
curl -s ${KONG_ADMIN_URL}/plugins | jq -r '.data[].name' | sort | uniq

echo ""
echo "🚀 Kong API Gateway 설정 완료!"
echo ""
echo "API Gateway 접근 URL:"
echo "  - Gateway: http://localhost:8000"
echo "  - Admin API: http://localhost:8001"
echo "  - Admin GUI: http://localhost:8002"
echo ""
echo "서비스 라우팅:"
echo "  - 인증: http://localhost:8000/auth/*"
echo "  - FortiManager: http://localhost:8000/fortimanager/*"
echo "  - ITSM: http://localhost:8000/itsm/*"
echo "  - 모니터링: http://localhost:8000/monitoring/*"
echo "  - 보안: http://localhost:8000/security/*"
echo "  - 분석: http://localhost:8000/analysis/*"
echo "  - 설정: http://localhost:8000/config/*"