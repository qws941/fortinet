#!/bin/bash
# =============================================================================
# FortiGate Nextrade - 외부 포트 로드밸런서 설정
# App 7777 포트 순차적 뷰 라우팅 구성
# =============================================================================

set -e

# Configuration
EXTERNAL_PORT="${EXTERNAL_PORT:-80}"
INTERNAL_PORT="7777"
APP_INSTANCES="${APP_INSTANCES:-3}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-30}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
echo_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
echo_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Traefik 로드밸런서 설정 생성
generate_traefik_config() {
    echo_info "🔧 Traefik 로드밸런서 설정 생성 중..."
    
    mkdir -p config/traefik
    
    cat > config/traefik/traefik.yml << EOF
# Traefik 동적 설정
global:
  checkNewVersion: false
  sendAnonymousUsage: false

serversTransport:
  insecureSkipVerify: true

api:
  dashboard: true
  insecure: true

entryPoints:
  web:
    address: ":${EXTERNAL_PORT}"
  websecure:
    address: ":443"
  traefik:
    address: ":8080"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: fortinet-network
  file:
    filename: /etc/traefik/dynamic.yml
    watch: true

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@jclee.me
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

log:
  level: INFO
  format: json

accessLog:
  format: json
  fields:
    defaultMode: keep
    names:
      ClientUsername: drop
    headers:
      defaultMode: keep
      names:
        User-Agent: keep
        Authorization: drop
        Content-Type: keep

metrics:
  prometheus:
    addEntryPointsLabels: true
    addServicesLabels: true
EOF

    # 동적 설정 파일
    cat > config/traefik/dynamic.yml << EOF
# Traefik 동적 라우팅 설정
http:
  routers:
    fortinet-app:
      rule: "Host(\`fortinet.jclee.me\`) || Host(\`localhost\`)"
      service: fortinet-service
      entrypoints:
        - web
        - websecure
      tls:
        certResolver: letsencrypt
      middlewares:
        - fortinet-auth
        - fortinet-ratelimit
        - fortinet-headers

    fortinet-api:
      rule: "Host(\`fortinet.jclee.me\`) && PathPrefix(\`/api\`)"
      service: fortinet-api-service
      entrypoints:
        - web
        - websecure
      tls:
        certResolver: letsencrypt
      middlewares:
        - fortinet-api-ratelimit
        - fortinet-headers

  services:
    fortinet-service:
      loadBalancer:
        healthCheck:
          path: /api/health
          interval: ${HEALTH_CHECK_INTERVAL}s
          timeout: 10s
        sticky:
          cookie:
            name: fortinet-server
            secure: true
            httpOnly: true
        servers:
EOF

    # 순차적 서버 추가
    for i in $(seq 1 $APP_INSTANCES); do
        port=$((30776 + i))
        cat >> config/traefik/dynamic.yml << EOF
          - url: "http://172.20.0.3${i}:7777"
            weight: 1
EOF
    done

    cat >> config/traefik/dynamic.yml << EOF

    fortinet-api-service:
      loadBalancer:
        healthCheck:
          path: /api/health
          interval: 10s
          timeout: 5s
        servers:
EOF

    # API 전용 서버 설정
    for i in $(seq 1 $APP_INSTANCES); do
        cat >> config/traefik/dynamic.yml << EOF
          - url: "http://172.20.0.3${i}:7777"
            weight: 1
EOF
    done

    cat >> config/traefik/dynamic.yml << EOF

  middlewares:
    fortinet-auth:
      basicAuth:
        users:
          - "admin:{\$2a\$10\$XYZ123456789..." # bcrypt hash

    fortinet-ratelimit:
      rateLimit:
        burst: 100
        period: 1m
        average: 50

    fortinet-api-ratelimit:
      rateLimit:
        burst: 200
        period: 1m
        average: 100

    fortinet-headers:
      headers:
        customRequestHeaders:
          X-Forwarded-Proto: "https"
          X-Real-IP: ""
        customResponseHeaders:
          X-Frame-Options: "DENY"
          X-Content-Type-Options: "nosniff"
          X-XSS-Protection: "1; mode=block"
          Strict-Transport-Security: "max-age=31536000; includeSubDomains"

tls:
  options:
    default:
      sslProtocols:
        - "TLSv1.2"
        - "TLSv1.3"
      cipherSuites:
        - "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
        - "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305"
        - "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
EOF

    echo_success "Traefik 설정 생성 완료"
}

# Docker Compose 확장 설정 생성
generate_loadbalancer_compose() {
    echo_info "🐳 로드밸런서 Docker Compose 설정 생성..."
    
    cat > docker-compose.loadbalancer.yml << EOF
version: '3.8'

networks:
  fortinet-network:
    external: true
  traefik-network:
    driver: bridge

volumes:
  traefik-letsencrypt:
    driver: local

services:
  # Traefik 로드밸런서
  traefik:
    image: traefik:v3.0
    container_name: fortinet-traefik
    hostname: fortinet-traefik
    restart: unless-stopped
    networks:
      - fortinet-network
      - traefik-network
    ports:
      - "${EXTERNAL_PORT}:80"
      - "443:443"
      - "8080:8080"  # Traefik Dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./config/traefik:/etc/traefik:ro
      - traefik-letsencrypt:/letsencrypt
    environment:
      - TRAEFIK_API=true
      - TRAEFIK_API_DASHBOARD=true
      - TRAEFIK_API_INSECURE=true
      - TRAEFIK_PROVIDERS_DOCKER=true
      - TRAEFIK_PROVIDERS_DOCKER_EXPOSEDBYDEFAULT=false
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik.rule=Host(\`traefik.jclee.me\`)"
      - "traefik.http.routers.traefik.entrypoints=websecure"
      - "traefik.http.routers.traefik.tls.certresolver=letsencrypt"
      - "traefik.http.routers.traefik.service=api@internal"
      - "com.centurylinklabs.watchtower.enable=false"

  # 앱 인스턴스 1
  fortinet-app-1:
    extends:
      file: docker-compose-separated.yml
      service: fortinet
    container_name: fortinet-app-1
    hostname: fortinet-app-1
    networks:
      fortinet-network:
        ipv4_address: 172.20.0.31
    ports:
      - "30777:7777"
    environment:
      - INSTANCE_ID=1
      - INSTANCE_NAME=fortinet-app-1
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app1.rule=Host(\`fortinet.jclee.me\`) && PathPrefix(\`/instance1\`)"
      - "traefik.http.services.app1.loadbalancer.server.port=7777"
      - "com.centurylinklabs.watchtower.scope=fortinet-app"

  # 앱 인스턴스 2  
  fortinet-app-2:
    extends:
      file: docker-compose-separated.yml
      service: fortinet
    container_name: fortinet-app-2
    hostname: fortinet-app-2
    networks:
      fortinet-network:
        ipv4_address: 172.20.0.32
    ports:
      - "30778:7777"
    environment:
      - INSTANCE_ID=2
      - INSTANCE_NAME=fortinet-app-2
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app2.rule=Host(\`fortinet.jclee.me\`) && PathPrefix(\`/instance2\`)"
      - "traefik.http.services.app2.loadbalancer.server.port=7777"
      - "com.centurylinklabs.watchtower.scope=fortinet-app"

  # 앱 인스턴스 3
  fortinet-app-3:
    extends:
      file: docker-compose-separated.yml
      service: fortinet
    container_name: fortinet-app-3
    hostname: fortinet-app-3
    networks:
      fortinet-network:
        ipv4_address: 172.20.0.33
    ports:
      - "30779:7777"
    environment:
      - INSTANCE_ID=3
      - INSTANCE_NAME=fortinet-app-3
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.app3.rule=Host(\`fortinet.jclee.me\`) && PathPrefix(\`/instance3\`)"
      - "traefik.http.services.app3.loadbalancer.server.port=7777"
      - "com.centurylinklabs.watchtower.scope=fortinet-app"
EOF

    echo_success "로드밸런서 Docker Compose 설정 완료"
}

# 순차적 뷰 라우팅 스크립트
generate_sequential_routing() {
    echo_info "🔄 순차적 뷰 라우팅 스크립트 생성..."
    
    cat > scripts/sequential-router.py << 'EOF'
#!/usr/bin/env python3
"""
FortiGate Nextrade - 순차적 뷰 라우팅 관리
외부 포트에서 내부 앱 인스턴스로 순차 분배
"""

import time
import json
import requests
import logging
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class AppInstance:
    id: int
    name: str
    url: str
    port: int
    healthy: bool = False
    last_check: float = 0
    response_time: float = 0

class SequentialRouter:
    def __init__(self, instances: List[Dict], health_check_interval: int = 30):
        self.instances = [AppInstance(**inst) for inst in instances]
        self.current_index = 0
        self.health_check_interval = health_check_interval
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger('SequentialRouter')

    def health_check(self, instance: AppInstance) -> bool:
        """개별 인스턴스 health check"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{instance.url}/api/health",
                timeout=10,
                headers={'User-Agent': 'SequentialRouter/1.0'}
            )
            instance.response_time = time.time() - start_time
            instance.last_check = time.time()
            
            if response.status_code == 200:
                instance.healthy = True
                self.logger.debug(f"✅ {instance.name} is healthy (response: {instance.response_time:.3f}s)")
                return True
            else:
                instance.healthy = False
                self.logger.warning(f"❌ {instance.name} unhealthy (status: {response.status_code})")
                return False
                
        except Exception as e:
            instance.healthy = False
            instance.last_check = time.time()
            self.logger.error(f"❌ {instance.name} health check failed: {e}")
            return False

    def check_all_instances(self):
        """모든 인스턴스 health check"""
        current_time = time.time()
        
        for instance in self.instances:
            if current_time - instance.last_check > self.health_check_interval:
                self.health_check(instance)

    def get_next_healthy_instance(self) -> AppInstance:
        """순차적으로 다음 healthy 인스턴스 반환"""
        self.check_all_instances()
        
        # 모든 인스턴스가 unhealthy인 경우
        healthy_instances = [inst for inst in self.instances if inst.healthy]
        if not healthy_instances:
            self.logger.error("🚨 모든 인스턴스가 unhealthy 상태입니다!")
            # 첫 번째 인스턴스라도 반환 (fallback)
            return self.instances[0]
        
        # 순차적 선택 (Round Robin)
        self.current_index = (self.current_index + 1) % len(healthy_instances)
        selected = healthy_instances[self.current_index]
        
        self.logger.info(f"🎯 Selected instance: {selected.name} (response_time: {selected.response_time:.3f}s)")
        return selected

    def get_status(self) -> Dict:
        """현재 상태 반환"""
        self.check_all_instances()
        
        return {
            'timestamp': time.time(),
            'total_instances': len(self.instances),
            'healthy_instances': len([inst for inst in self.instances if inst.healthy]),
            'current_index': self.current_index,
            'instances': [
                {
                    'id': inst.id,
                    'name': inst.name,
                    'url': inst.url,
                    'healthy': inst.healthy,
                    'response_time': inst.response_time,
                    'last_check': inst.last_check
                }
                for inst in self.instances
            ]
        }

# 설정 예제
if __name__ == "__main__":
    instances = [
        {'id': 1, 'name': 'fortinet-app-1', 'url': 'http://172.20.0.31:7777', 'port': 30777},
        {'id': 2, 'name': 'fortinet-app-2', 'url': 'http://172.20.0.32:7777', 'port': 30778}, 
        {'id': 3, 'name': 'fortinet-app-3', 'url': 'http://172.20.0.33:7777', 'port': 30779}
    ]
    
    router = SequentialRouter(instances)
    
    # 상태 모니터링
    while True:
        status = router.get_status()
        print(f"📊 Router Status: {status['healthy_instances']}/{status['total_instances']} healthy")
        
        # 다음 인스턴스 테스트
        next_instance = router.get_next_healthy_instance()
        print(f"➡️  Next: {next_instance.name}")
        
        time.sleep(10)
EOF

    chmod +x scripts/sequential-router.py
    echo_success "순차적 뷰 라우팅 스크립트 완료"
}

# 배포 스크립트
generate_deployment_script() {
    echo_info "🚀 로드밸런서 배포 스크립트 생성..."
    
    cat > scripts/deploy-loadbalancer.sh << 'EOF'
#!/bin/bash
# 로드밸런서 배포 스크립트

set -e

echo "🚀 FortiGate 로드밸런서 배포 시작..."

# 기존 서비스 중지
echo "⏹️ 기존 서비스 중지..."
docker-compose -f docker-compose-separated.yml down 2>/dev/null || true
docker-compose -f docker-compose.loadbalancer.yml down 2>/dev/null || true

# 네트워크 생성
echo "🌐 네트워크 설정..."
docker network create fortinet-network 2>/dev/null || true

# 서비스 시작 (의존성 순서)
echo "📦 Redis & PostgreSQL 시작..."
docker-compose -f docker-compose-separated.yml up -d redis postgresql

# Health check 대기
echo "⏳ 데이터베이스 서비스 준비 대기..."
sleep 30

# 앱 인스턴스들과 로드밸런서 시작
echo "🔧 앱 인스턴스 및 로드밸런서 시작..."
docker-compose -f docker-compose.loadbalancer.yml up -d

# 서비스 상태 확인
echo "🔍 서비스 상태 확인..."
sleep 15

docker ps --filter "label=traefik.enable=true" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "✅ 배포 완료!"
echo "📍 접속 정보:"
echo "  - 메인 애플리케이션: http://fortinet.jclee.me"
echo "  - Traefik 대시보드: http://traefik.jclee.me:8080"
echo "  - Health Check: http://fortinet.jclee.me/api/health"

# 순차 라우터 시작 옵션
read -p "순차 라우터를 시작하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 순차 라우터 시작..."
    python3 scripts/sequential-router.py &
    echo "✅ 순차 라우터가 백그라운드에서 실행 중입니다"
fi
EOF

    chmod +x scripts/deploy-loadbalancer.sh
    echo_success "배포 스크립트 완료"
}

# 실행
echo_info "🎯 외부 포트 로드밸런서 설정 시작..."
echo "외부 포트: $EXTERNAL_PORT"
echo "내부 포트: $INTERNAL_PORT" 
echo "앱 인스턴스: $APP_INSTANCES개"
echo

generate_traefik_config
generate_loadbalancer_compose
generate_sequential_routing
generate_deployment_script

echo_success "🎉 외부 포트 로드밸런서 설정 완료!"
echo_info "💡 배포 방법:"
echo "  ./scripts/deploy-loadbalancer.sh"