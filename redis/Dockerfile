# FortiGate Nextrade - Redis Cache
FROM redis:7-alpine

LABEL maintainer="FortiGate Nextrade Team"
LABEL service="redis"

# Redis 설정 파일 복사 (선택적)
# COPY redis.conf /usr/local/etc/redis/redis.conf

# 포트 노출
EXPOSE 6379

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD redis-cli ping || exit 1

# Redis 서버 시작 (기본 설정 사용)
CMD ["redis-server"]