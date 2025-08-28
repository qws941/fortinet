# Redis for FortiGate Nextrade
FROM redis:7-alpine

# Install additional packages
RUN apk add --no-cache \
    curl \
    ca-certificates

# Copy Redis configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Health check script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Create data directory
RUN mkdir -p /data && chown redis:redis /data

# Expose Redis port
EXPOSE 6379

# Set up volume for data persistence
VOLUME ["/data"]

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD /usr/local/bin/healthcheck.sh

# Switch to redis user
USER redis

# Start Redis with custom configuration
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]