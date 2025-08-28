# =============================================================================
# FortiGate Nextrade - Optimized Production Dockerfile
# Multi-stage build with security best practices (2025 standards)
# =============================================================================

# Stage 1: Base image with minimal dependencies
FROM python:3.11-slim as base

# Security: Set non-root user early
ARG UID=10001
ARG GID=10001

# Build arguments
ARG BUILD_DATE
ARG VERSION=1.0.0
ARG COMMIT_SHA
ARG SERVICE_TYPE=fortinet

# Security best practice: Create non-root user first
RUN groupadd -g ${GID} fortinet && \
    useradd -r -u ${UID} -g fortinet -m -s /sbin/nologin fortinet

# Stage 2: Build dependencies (separate for better caching)
FROM base as build-deps

# Install build dependencies only
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 3: Python dependencies (separate for layer caching)
FROM build-deps as python-deps

WORKDIR /app

# Copy only requirements first for better caching
COPY --chown=fortinet:fortinet requirements.txt .

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn gevent prometheus-client

# Stage 4: Application build
FROM python-deps as builder

# Copy application code
COPY --chown=fortinet:fortinet . /app/

# Compile Python bytecode for faster startup
RUN python -m compileall /app/src -b -q

# Remove unnecessary files
RUN find /app -type f -name "*.py" -delete && \
    find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /app/tests /app/docs /app/.git /app/.github

# Stage 5: Final production image (minimal)
FROM python:3.11-slim as production

# Security: Create non-root user in final stage
ARG UID=10001
ARG GID=10001

RUN groupadd -g ${GID} fortinet && \
    useradd -r -u ${UID} -g fortinet -m -s /sbin/nologin fortinet

# Install only runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy Python packages from builder
COPY --from=python-deps --chown=fortinet:fortinet /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps --chown=fortinet:fortinet /usr/local/bin /usr/local/bin

# Copy compiled application from builder
COPY --from=builder --chown=fortinet:fortinet /app /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs && \
    chown -R fortinet:fortinet /app && \
    chmod 750 /app && \
    chmod 770 /app/data /app/logs

# Environment setup (minimal for security)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    SERVICE_TYPE=${SERVICE_TYPE} \
    APP_MODE=production \
    WEB_APP_HOST=0.0.0.0 \
    WEB_APP_PORT=7777 \
    PATH="/app/.local/bin:${PATH}"

# Security: Set secure defaults
ENV OFFLINE_MODE=true \
    SECRET_KEY="" \
    FORTIGATE_HOST="" \
    FORTIMANAGER_HOST="" \
    ITSM_BASE_URL=""

# Metadata labels
LABEL maintainer="FortiGate Nextrade Team" \
      version="${VERSION}" \
      description="FortiGate Nextrade ${SERVICE_TYPE} Service" \
      build-date="${BUILD_DATE}" \
      org.opencontainers.image.source="https://github.com/fortinet/nextrade" \
      org.opencontainers.image.vendor="FortiGate" \
      org.opencontainers.image.title="FortiGate Nextrade" \
      org.opencontainers.image.description="Production-ready FortiGate monitoring platform" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${COMMIT_SHA}"

# Create optimized startup script
RUN cat > /app/start.sh << 'EOF'
#!/bin/bash
set -e

# Security: Validate required environment variables
if [ "$APP_MODE" = "production" ]; then
    if [ -z "$SECRET_KEY" ]; then
        echo "ERROR: SECRET_KEY must be set in production mode"
        exit 1
    fi
fi

SERVICE_TYPE=${SERVICE_TYPE:-fortinet}
echo "Starting $SERVICE_TYPE service..."

# Health check function
health_check() {
    local host=$1
    local port=$2
    local service=$3
    local timeout=${4:-30}
    
    echo "Waiting for $service..."
    local count=0
    while ! nc -z "$host" "$port" 2>/dev/null; do
        count=$((count+1))
        if [ $count -ge $timeout ]; then
            echo "ERROR: $service not available after ${timeout}s"
            return 1
        fi
        sleep 1
    done
    echo "$service is ready"
}

# Wait for dependencies
if [ -n "$REDIS_HOST" ] && [ "$REDIS_HOST" != "mock" ]; then
    health_check "$REDIS_HOST" "${REDIS_PORT:-6379}" "Redis"
fi

if [ -n "$POSTGRES_HOST" ] && [ "$POSTGRES_HOST" != "mock" ]; then
    health_check "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}" "PostgreSQL"
fi

cd /app/src

# Start application with proper worker configuration
exec gunicorn \
    --bind ${WEB_APP_HOST}:${WEB_APP_PORT} \
    --workers ${WORKERS:-2} \
    --worker-class ${WORKER_CLASS:-gevent} \
    --timeout ${TIMEOUT:-120} \
    --keep-alive ${KEEPALIVE:-5} \
    --max-requests ${MAX_REQUESTS:-1000} \
    --max-requests-jitter ${MAX_REQUESTS_JITTER:-50} \
    --preload \
    --access-logfile - \
    --error-logfile - \
    --log-level ${LOG_LEVEL:-info} \
    "web_app:create_app()"
EOF

RUN chmod 755 /app/start.sh

# Security: Set user before exposing ports
USER fortinet
WORKDIR /app

# Health check with proper timeout and retry configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${WEB_APP_PORT}/api/health || exit 1

# Expose only necessary port
EXPOSE 7777

# Volume for persistent data (optional, mounted at runtime)
VOLUME ["/app/data"]

# Use exec form for proper signal handling
ENTRYPOINT ["/app/start.sh"]

# Stage 6: Development image (optional, for debugging)
FROM production as development

USER root

# Install development tools
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    vim \
    less \
    procps \
    net-tools \
    iputils-ping \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    ipython \
    pytest \
    black \
    flake8 \
    pytest-cov

USER fortinet

# Stage 7: Security scanner (optional, for CI/CD)
FROM production as security-scan

USER root

# Install security scanning tools
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
    safety \
    bandit \
    pip-audit

# Run security scans
RUN safety check --json || true && \
    bandit -r /app/src -f json || true && \
    pip-audit --desc || true

USER fortinet