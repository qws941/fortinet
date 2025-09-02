#!/bin/bash

# =============================================================================
# FortiGate Nextrade - Production Startup Script
# GitOps 운영 환경 최적화된 시작 스크립트
# =============================================================================

set -e  # 오류 발생 시 즉시 중단

# 환경 변수 기본값 설정
export APP_MODE=${APP_MODE:-production}
export WEB_APP_HOST=${WEB_APP_HOST:-0.0.0.0}
export WEB_APP_PORT=${WEB_APP_PORT:-7777}
export PYTHONPATH=${PYTHONPATH:-/app/src}
export WORKERS=${WORKERS:-4}
export WORKER_CLASS=${WORKER_CLASS:-gevent}
export WORKER_CONNECTIONS=${WORKER_CONNECTIONS:-1000}
export MAX_REQUESTS=${MAX_REQUESTS:-1000}
export MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}
export TIMEOUT=${TIMEOUT:-120}
export KEEPALIVE=${KEEPALIVE:-5}

echo "=== FortiGate Nextrade Production Startup ==="
echo "App Mode: $APP_MODE"
echo "Host: $WEB_APP_HOST"
echo "Port: $WEB_APP_PORT"
echo "Workers: $WORKERS"
echo "Worker Class: $WORKER_CLASS"
echo "Python Path: $PYTHONPATH"

# 빌드 정보 출력 (GitOps 추적성)
if [ -f "/app/build-info.txt" ]; then
    echo ""
    echo "=== GitOps Build Information ==="
    cat /app/build-info.txt
    echo ""
fi

# 디렉토리 및 권한 확인
echo "=== Directory and Permission Check ==="
# 디렉토리 생성 시도 (실패해도 계속 진행)
mkdir -p /app/logs /app/data /app/temp 2>/dev/null || true
# 권한 변경 시도 (실패해도 계속 진행)
chmod 755 /app/src /app/logs /app/data /app/temp 2>/dev/null || true

# 헬스체크 엔드포인트 사전 확인
echo "=== Pre-flight Health Check ==="
cd /app/src
if python -c "import sys; sys.path.insert(0, '/app/src'); from web_app import create_app; print('✅ App import successful')"; then
    echo "✅ Application import test passed"
else
    echo "❌ Application import test failed"
    exit 1
fi

# Gunicorn으로 프로덕션 서버 시작
echo "=== Starting Gunicorn Production Server ==="
cd /app/src

exec gunicorn \
    --bind $WEB_APP_HOST:$WEB_APP_PORT \
    --workers $WORKERS \
    --worker-class $WORKER_CLASS \
    --worker-connections $WORKER_CONNECTIONS \
    --max-requests $MAX_REQUESTS \
    --max-requests-jitter $MAX_REQUESTS_JITTER \
    --timeout $TIMEOUT \
    --keep-alive $KEEPALIVE \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    --enable-stdio-inheritance \
    "web_app:create_app()"