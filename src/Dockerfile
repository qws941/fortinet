# FortiGate Nextrade - Main Application
FROM python:3.11-slim

LABEL maintainer="FortiGate Nextrade Team"
LABEL service="app"
LABEL version="2.0.0"

WORKDIR /app

# Create non-root user for security
RUN groupadd -r fortinet && useradd -r -g fortinet fortinet

# Install system packages
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for volumes
RUN mkdir -p /app/data /app/logs /app/uploads /app/cache && \
    chown -R fortinet:fortinet /app

# Copy application code
COPY . /app/src/

# Set proper permissions
RUN chown -R fortinet:fortinet /app/src

# Declare volumes for persistent data
VOLUME ["/app/data"]
VOLUME ["/app/logs"] 
VOLUME ["/app/uploads"]
VOLUME ["/app/cache"]

# Switch to non-root user
USER fortinet

# Expose port (configurable via environment variable)
EXPOSE 7777

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${WEB_APP_PORT:-7777}/api/health || exit 1

# Start application
CMD ["python", "/app/src/main.py", "--web"]