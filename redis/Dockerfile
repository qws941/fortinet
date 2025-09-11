# FortiGate Nextrade - Redis Cache
FROM redis:7-alpine

LABEL maintainer="FortiGate Nextrade Team"
LABEL service="redis"
LABEL version="2.0.0"

# Copy Redis configuration (optional)
COPY redis.conf /usr/local/etc/redis/redis.conf

# Create data directory
RUN mkdir -p /data && \
    chown redis:redis /data

# Declare volume for persistent data
VOLUME ["/data"]

# Expose Redis port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD redis-cli ping || exit 1

# Switch to redis user for security
USER redis

# Start Redis server with custom configuration
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]