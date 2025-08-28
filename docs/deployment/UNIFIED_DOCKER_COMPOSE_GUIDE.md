# Unified Docker Compose Configuration Guide

## Overview

The FortiGate Nextrade project has been unified into a single, comprehensive `docker-compose.yml` file that supports all deployment modes through environment variables and Docker Compose profiles. This approach eliminates the need for multiple separate Docker Compose files and provides a streamlined deployment experience.

## Key Features

- **Single Configuration File**: One `docker-compose.yml` supports all deployment modes
- **Environment-Driven**: All configuration through `.env` files
- **Profile-Based**: Use Docker Compose profiles to activate specific service sets
- **Secure by Default**: Security best practices built into all configurations
- **Backward Compatible**: Maintains compatibility with existing deployment workflows

## Deployment Modes

### 1. Default Mode (`default`)
Standard deployment with main application and Redis cache.

**Services**: `fortinet`, `redis`

```bash
# Set profile in .env
COMPOSE_PROFILES=default

# Deploy
docker-compose up -d
```

### 2. Development Mode (`dev`)
Development environment with monitoring tools.

**Services**: `fortinet`, `redis`, `prometheus`

```bash
# Switch to dev mode
./switch-deployment-mode.sh dev --template --restart
```

### 3. Microservices Architecture (`msa`)
Full MSA deployment with service mesh, API gateway, and message queue.

**Services**: 
- Infrastructure: `kong-database`, `kong-migrations`, `kong`, `consul`, `rabbitmq`, `redis`
- Microservices: `auth-service`, `fortimanager-service`, `itsm-service`, `monitoring-service`, `analysis-service`, `config-service`
- Main App: `fortinet`

```bash
# Switch to MSA mode
./switch-deployment-mode.sh msa --template --restart
```

### 4. Secure Mode (`secure`)
Security-hardened deployment with full monitoring stack and enhanced security features.

**Services**: All MSA services plus `mongodb`, `security-service`, `influxdb`, `grafana`

```bash
# Switch to secure mode (requires setting passwords)
./switch-deployment-mode.sh secure --template
# Edit .env to set secure passwords
docker-compose --profile secure up -d
```

### 5. Standalone Mode (`standalone`)
Single container deployment with no external dependencies.

**Services**: `fortinet` only (with embedded services)

```bash
# Switch to standalone mode
./switch-deployment-mode.sh standalone --template --restart
```

### 6. Verification Mode (`verify`)
Version verification and health checking.

**Services**: `fortinet`, `redis`, `version-check`

### 7. Watchtower Mode (`watchtower`)
Auto-update enabled deployment.

**Services**: Standard services plus `watchtower`

## Environment Configuration

### Main Configuration File (`.env`)

The main `.env` file contains all possible configuration options with sensible defaults. Key sections include:

- **Deployment Mode**: `COMPOSE_PROFILES`
- **Application Config**: `APP_MODE`, `DEBUG`, `LOG_LEVEL`
- **Network Config**: Ports, hostnames, networks
- **Volume Config**: Named volumes and mount options
- **Security Config**: Keys, certificates, access controls
- **Service Config**: MSA service settings
- **Monitoring Config**: InfluxDB, Grafana, Prometheus

### Environment-Specific Templates

Template files are provided for easy mode switching:

- `.env.local.example` - Local development
- `.env.production.example` - Production deployment
- `.env.msa.example` - Microservices architecture
- `.env.secure.example` - Security-hardened deployment
- `.env.standalone.example` - Standalone deployment

## Quick Start

### 1. Choose Deployment Mode

```bash
# List available modes
./switch-deployment-mode.sh --list

# Check current status
./switch-deployment-mode.sh --status
```

### 2. Configure Environment

```bash
# Switch to desired mode with template
./switch-deployment-mode.sh <mode> --template

# Edit .env file to customize settings
nano .env
```

### 3. Deploy

```bash
# Start services
docker-compose up -d

# Or use the switcher with auto-restart
./switch-deployment-mode.sh <mode> --restart
```

### 4. Verify Deployment

```bash
# Check configuration
./switch-deployment-mode.sh --check

# Check running services
docker-compose ps

# View logs
docker-compose logs -f
```

## Advanced Configuration

### Custom Volume Mounting

Change volume types from named volumes to bind mounts:

```bash
# In .env file, change volume types to absolute paths
DATA_VOLUME_TYPE=/host/path/to/data
LOGS_VOLUME_TYPE=/host/path/to/logs
```

### Service Scaling

Scale individual services:

```bash
# Scale main application
docker-compose up -d --scale fortinet=3

# Scale MSA services
docker-compose up -d --scale auth-service=2 --scale itsm-service=2
```

### Resource Limits

Adjust resource limits in `.env`:

```bash
MEMORY_LIMIT=2G
CPU_LIMIT=2.0
MEMORY_RESERVATION=1G
CPU_RESERVATION=1.0
```

### Network Configuration

Customize network settings:

```bash
NETWORK_SUBNET=172.21.0.0/16
BRIDGE_NAME=fortinet-custom-bridge
```

## Security Configuration

### Required Security Settings for Production

#### Default/MSA Modes
```bash
SECRET_KEY=<secure-256-bit-key>
REDIS_PASSWORD=<secure-password>
```

#### Secure Mode (Additional)
```bash
JWT_SECRET_KEY=<secure-jwt-key>
INTER_SERVICE_AUTH_KEY=<secure-service-key>
KONG_DB_PASSWORD=<secure-password>
RABBITMQ_PASSWORD=<secure-password>
RABBITMQ_ERLANG_COOKIE=<secure-cookie>
MONGODB_ROOT_PASSWORD=<secure-password>
INFLUXDB_PASSWORD=<secure-password>
GRAFANA_ADMIN_PASSWORD=<secure-password>
```

### Security Best Practices

1. **Use Strong Passwords**: Generate secure random passwords for all services
2. **Enable SSL Verification**: Set `*_VERIFY_SSL=true` for external services
3. **Network Isolation**: Use custom networks for service isolation
4. **Resource Limits**: Set appropriate memory and CPU limits
5. **Security Contexts**: All containers run with `no-new-privileges:true`
6. **User Restrictions**: Services run as non-root users where possible

## Monitoring and Logging

### Available Monitoring Stacks

#### Development (Dev Profile)
- **Prometheus**: Metrics collection and alerting

#### Secure Profile
- **InfluxDB**: Time-series metrics storage
- **Grafana**: Visualization and dashboards
- **Prometheus**: Metrics collection

### Log Management

Logs are automatically collected via Docker logging drivers:

```bash
# View application logs
docker-compose logs fortinet

# View all service logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs for specific profile
docker-compose --profile msa logs -f
```

### Health Monitoring

All services include health checks:

```bash
# Check service health
docker-compose ps

# View health check details
docker inspect <container_name> | jq '.[0].State.Health'
```

## Troubleshooting

### Common Issues

#### 1. Port Conflicts
If ports are already in use, modify port mappings in `.env`:

```bash
WEB_APP_PORT=7778
REDIS_PORT=6380
```

#### 2. Volume Permission Issues
If using bind mounts, ensure proper permissions:

```bash
# Create directories with correct permissions
sudo mkdir -p /host/path/to/data
sudo chown -R $USER:$USER /host/path/to/data
```

#### 3. Service Dependency Issues
If services fail to start due to dependencies:

```bash
# Stop all services
docker-compose down

# Start with fresh state
docker-compose up -d
```

#### 4. Configuration Validation
Use the built-in validation:

```bash
# Validate current configuration
./switch-deployment-mode.sh --check

# Test Docker Compose configuration
docker-compose config
```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# In .env file
DEBUG=true
LOG_LEVEL=debug

# Restart services
docker-compose restart
```

## Migration from Old Setup

### From Multiple Docker Compose Files

1. **Backup Old Configuration**:
   ```bash
   # Old files are automatically backed up to backup/docker-compose-files/
   ls backup/docker-compose-files/
   ```

2. **Identify Current Mode**:
   ```bash
   # Check which docker-compose file you were using
   # Map to new profile:
   # docker-compose.msa.yml -> msa profile
   # docker-compose.standalone.yml -> standalone profile
   # etc.
   ```

3. **Switch to Equivalent Mode**:
   ```bash
   ./switch-deployment-mode.sh <equivalent-mode> --template
   ```

### From Environment Files

Old environment files are preserved in `backup/docker-compose-files/`. You can reference them to migrate settings to the new unified `.env` file.

## Best Practices

### Development Workflow

1. **Local Development**:
   ```bash
   ./switch-deployment-mode.sh dev --template
   # Edit .env for local settings
   docker-compose up -d
   ```

2. **Testing MSA Locally**:
   ```bash
   ./switch-deployment-mode.sh msa --template
   # Set minimal passwords for local testing
   docker-compose up -d
   ```

3. **Production Deployment**:
   ```bash
   ./switch-deployment-mode.sh default --template
   # Configure production settings
   # Set secure passwords
   docker-compose up -d
   ```

### CI/CD Integration

The unified configuration works seamlessly with existing CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Deploy to Production
  run: |
    ./switch-deployment-mode.sh default
    docker-compose up -d
```

### Backup and Recovery

Regular backup of configuration and data:

```bash
# Backup configuration
cp .env .env.backup.$(date +%Y%m%d)

# Backup volumes
docker run --rm -v fortinet-data:/data -v $(pwd):/backup alpine tar czf /backup/data-backup.tar.gz -C /data .
```

## Support and Updates

### Getting Help

1. **Check Status**: `./switch-deployment-mode.sh --status`
2. **Validate Config**: `./switch-deployment-mode.sh --check`
3. **View Logs**: `docker-compose logs`
4. **Check Documentation**: This guide and Docker Compose docs

### Updates

The unified system is designed to be forward-compatible. New features and services can be added without breaking existing deployments by using additional profiles and environment variables.

---

For more detailed information, see:
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FortiGate API Documentation](docs/api/)
- [Security Configuration Guide](docs/security/)
- [Monitoring Setup Guide](docs/monitoring/)