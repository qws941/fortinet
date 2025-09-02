# FortiGate Nextrade - Main Application
FROM python:3.11-slim

LABEL maintainer="FortiGate Nextrade Team"
LABEL service="app"

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY ../config/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . /app/src/

# 포트 노출
EXPOSE 7777

# 헬스체크
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7777/api/health || exit 1

# 실행 명령어
CMD ["python", "/app/src/main.py", "--web"]