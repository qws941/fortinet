FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY services/auth/ ./auth/
COPY src/core/auth_manager.py ./shared/
COPY src/utils/unified_logger.py ./shared/
COPY src/utils/security.py ./shared/

# 환경 변수 설정 - 독립 실행을 위한 기본값 포함
ENV PYTHONPATH=/app \
    SERVICE_NAME=auth-service \
    SERVICE_PORT=8081 \
    # 독립 실행을 위한 기본 설정
    REDIS_HOST="" \
    RABBITMQ_URL="" \
    CONSUL_URL="" \
    JWT_SECRET_KEY=standalone-jwt-secret \
    OFFLINE_MODE=true \
    STANDALONE_MODE=true

# 독립 실행 스크립트 생성
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Auth Service in standalone mode..."\n\
echo "Port: $SERVICE_PORT"\n\
echo "Mode: Standalone (no external dependencies)"\n\
\n\
# 독립 실행시 필요한 디렉토리 생성\n\
mkdir -p /app/data /app/logs\n\
\n\
# 서비스 시작\n\
exec python /app/auth/main.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# 포트 노출
EXPOSE 8081

# 서비스 시작 - ENTRYPOINT와 CMD 분리
ENTRYPOINT ["/app/start.sh"]
CMD []