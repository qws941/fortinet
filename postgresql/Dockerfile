# FortiGate Nextrade - PostgreSQL Database
FROM postgres:15-alpine

LABEL maintainer="FortiGate Nextrade Team"
LABEL service="postgresql"

# 환경 변수 설정
ENV POSTGRES_DB=fortinet
ENV POSTGRES_USER=fortinet
ENV POSTGRES_PASSWORD=fortinet123

# PostgreSQL 설정 파일 복사
COPY postgresql.conf /etc/postgresql/postgresql.conf

# 초기화 스크립트 복사
COPY init.sql /docker-entrypoint-initdb.d/

# 포트 노출
EXPOSE 5432

# 헬스체크
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U $POSTGRES_USER -d $POSTGRES_DB || exit 1

# PostgreSQL 시작 (기본 entrypoint 사용)