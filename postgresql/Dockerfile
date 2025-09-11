# FortiGate Nextrade - PostgreSQL Database
FROM postgres:15-alpine

LABEL maintainer="FortiGate Nextrade Team"
LABEL service="postgresql"
LABEL version="2.0.0"

# Environment variables (should be overridden in production)
ENV POSTGRES_DB=${POSTGRES_DB:-fortinet}
ENV POSTGRES_USER=${POSTGRES_USER:-fortinet}
ENV POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-change_me_in_production}

# Copy PostgreSQL configuration
COPY postgresql.conf /etc/postgresql/postgresql.conf

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/

# Create data directory with proper permissions
RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql/data && \
    chmod 0700 /var/lib/postgresql/data

# Declare volume for persistent data
VOLUME ["/var/lib/postgresql/data"]

# Expose PostgreSQL port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB} || exit 1

# Use default PostgreSQL entrypoint (runs as postgres user)