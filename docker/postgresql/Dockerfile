# PostgreSQL for FortiGate Nextrade
FROM postgres:15-alpine

# Set environment defaults
ENV POSTGRES_DB=fortinet \
    POSTGRES_USER=fortinet \
    LANG=en_US.utf8 \
    PGDATA=/var/lib/postgresql/data/pgdata

# Install additional packages if needed
RUN apk add --no-cache \
    curl \
    ca-certificates

# Copy initialization scripts
COPY init/*.sql /docker-entrypoint-initdb.d/
COPY init/*.sh /docker-entrypoint-initdb.d/

# Create custom PostgreSQL configuration
RUN mkdir -p /etc/postgresql
COPY postgresql.conf /etc/postgresql/postgresql.conf

# Health check script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Expose PostgreSQL port
EXPOSE 5432

# Set up volume for data persistence
VOLUME ["/var/lib/postgresql/data"]

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD /usr/local/bin/healthcheck.sh

# Use the default entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]