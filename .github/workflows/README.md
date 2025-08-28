# GitHub Actions Self-Hosted Runner Optimization Guide

## Overview

This optimized GitHub Actions workflow leverages self-hosted runners for enhanced performance, advanced caching strategies, matrix builds, and comprehensive security scanning. The workflow is designed specifically for the FortiGate Nextrade project with multi-service container support and registry.jclee.me integration.

## 📋 Workflow Overview

### **main-deploy.yml** - Main Deploy Pipeline
- **Purpose**: Comprehensive CI/CD with multi-service deployment and Watchtower integration
- **Triggers**: 
  - Push to main/master (excluding docs)
  - Manual dispatch
  - Weekly security scans (Sundays 2 AM UTC)
- **Key Features**:
  - Self-hosted runners for optimized builds
  - Matrix-based parallel testing (unit, integration, security, lint)
  - Multi-service container builds (Redis, PostgreSQL, Fortinet)
  - Registry.jclee.me integration for all images
  - Watchtower deployment automation
  - Enhanced GitOps deployment with ArgoCD
  - Comprehensive security scanning with Trivy
  - Real-time monitoring and verification

## Key Optimizations

### 1. Self-Hosted Runner Configuration

#### Runner Setup
```bash
# Download and configure GitHub Actions runner
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Configure runner with repository
./config.sh --url https://github.com/YOUR_USERNAME/fortinet --token YOUR_TOKEN

# Install as systemd service
sudo ./svc.sh install
sudo ./svc.sh start
```

#### Runner Labels
The workflow uses these specific labels:
- `self-hosted`: Basic self-hosted runner identification
- `linux`: Linux operating system
- `x64`: x86_64 architecture

#### Prerequisites for Self-Hosted Runners
```bash
# Docker and BuildKit
sudo apt-get update
sudo apt-get install docker.io docker-buildx-plugin
sudo usermod -aG docker $USER

# Python and development tools
sudo apt-get install python3.11 python3.11-venv python3-pip
sudo apt-get install build-essential git curl jq bc

# Helm
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
sudo mv linux-amd64/helm /usr/local/bin/

# Additional tools
sudo apt-get install postgresql-client redis-tools
```

### 2. Advanced Caching Strategy

#### Multi-Level Caching
1. **Python Dependencies**: Uses `actions/cache` with dependency file hashing
2. **Docker BuildKit**: Multi-platform layer caching with GitHub Actions cache
3. **Helm Charts**: Cached Helm dependencies and chart packages
4. **Registry Cache**: Docker registry-based caching for cross-platform builds

### 3. Matrix Build Strategy

#### Test Matrix
Parallel execution of:
- **Unit Tests**: Fast, isolated component testing
- **Integration Tests**: API endpoint validation with timeout controls
- **Security Tests**: Bandit source code analysis and Safety dependency scanning
- **Lint Tests**: Code formatting and style validation

#### Build Matrix
Multi-platform container builds:
- **linux/amd64**: Standard x86_64 architecture
- **linux/arm64**: ARM64 architecture for modern processors

## 🔧 Environment Configuration

### Repository Variables
```yaml
REGISTRY: registry.jclee.me
IMAGE_NAME: fortinet
CHARTMUSEUM_URL: https://charts.jclee.me
APP_NAME: fortinet
DEPLOYMENT_HOST: 192.168.50.110
DEPLOYMENT_PORT: 30777
PYTHON_VERSION: '3.11'
NODE_VERSION: '18'
CACHE_VERSION: v2
```

### Required GitHub Secrets
```yaml
REGISTRY_USERNAME: Harbor registry username
REGISTRY_PASSWORD: Harbor registry password
CHARTMUSEUM_USERNAME: ChartMuseum username
CHARTMUSEUM_PASSWORD: ChartMuseum password
ARGOCD_TOKEN: ArgoCD API token for deployments
WATCHTOWER_WEBHOOK_URL: Watchtower webhook endpoint for deployment triggers
WATCHTOWER_TOKEN: Authentication token for Watchtower webhook
GITHUB_TOKEN: Automatically provided by GitHub
```

## 🚀 Pipeline Phases

### Phase 1: Pre-flight Checks
- Duplicate action detection with `fkirc/skip-duplicate-actions`
- Security dependency validation with Safety
- Dynamic cache key generation based on dependency files
- Initial health verification

### Phase 2: Parallel Test Matrix
```yaml
strategy:
  fail-fast: false
  matrix:
    test-type: [unit, integration, security, lint]
```

- **Unit Tests**: Fast component testing with pytest
- **Integration Tests**: API endpoint validation with 60s timeout
- **Security Tests**: Bandit source analysis + Safety dependency scanning
- **Lint Tests**: Black formatting + isort imports + flake8 style

### Phase 3: Multi-Service Build Matrix
```yaml
strategy:
  fail-fast: false
  matrix:
    service: [redis, postgresql, fortinet]
```

- **Redis Service**: fortinet-redis container build
- **PostgreSQL Service**: fortinet-postgresql container build
- **Fortinet Service**: fortinet main application container build
- Docker BuildKit with advanced caching
- Security scanning with Trivy for each service
- Registry.jclee.me push for all images

### Phase 4: Watchtower Deployment
- Automatic deployment trigger via webhook
- Multi-service update coordination
- Deployment stabilization monitoring
- Registry propagation verification

### Phase 5: GitOps Deployment
- Enhanced Helm chart updates with metadata
- ChartMuseum upload with retry logic (3 attempts)
- GitOps commit with multi-service deployment details
- ArgoCD synchronization with monitoring

### Phase 6: Advanced Verification
- ArgoCD application health monitoring (20 attempts)
- Multi-endpoint health validation
- Performance response time verification
- Comprehensive service health checks

### Phase 7: Notification and Cleanup
- Multi-service deployment status reporting
- Automated Docker system cleanup
- Performance metrics collection

## 📝 Usage Examples

### Standard Development Workflow
```bash
# Make changes
git add .
git commit -m "feat: implement new FortiManager integration"
git push origin main

# Pipeline automatically triggers:
# 1. Pre-flight checks (30s)
# 2. Parallel tests (2-3 minutes)
# 3. Multi-service builds (6-8 minutes)
# 4. Watchtower deployment (2-3 minutes)
# 5. GitOps deployment (2-3 minutes)
# 6. Verification (2-3 minutes)
# Total: ~12-18 minutes with multi-service deployment
```

### Manual Pipeline Execution
```bash
# Navigate to GitHub Actions tab
# Select "Main Deploy Pipeline"
# Click "Run workflow"
# Optionally specify branch and parameters
```

### Security Scan Only
```bash
# Triggered automatically every Sunday at 2 AM UTC
# Or manually trigger for immediate security assessment
# Results visible in GitHub Security tab
```

## 🔍 Advanced Troubleshooting

### Self-Hosted Runner Issues
```bash
# Check runner status
sudo systemctl status actions.runner.YOUR_USERNAME-fortinet.YOUR_RUNNER_NAME

# View runner logs
sudo journalctl -u actions.runner.YOUR_USERNAME-fortinet.YOUR_RUNNER_NAME -f

# Restart runner service
sudo systemctl restart actions.runner.YOUR_USERNAME-fortinet.YOUR_RUNNER_NAME

# Update runner
cd ~/actions-runner
sudo ./svc.sh stop
./config.sh remove --token YOUR_TOKEN
# Download latest version and reconfigure
```

### Docker Build Issues
```bash
# Clean Docker system
docker system prune -a --volumes

# Reset BuildKit
docker buildx rm multiarch-builder
docker buildx create --name multiarch-builder --use --platform linux/amd64,linux/arm64

# Check BuildKit status
docker buildx ls
docker buildx inspect multiarch-builder
```

### Cache Issues
```bash
# Clear GitHub Actions cache
gh cache list --repo YOUR_USERNAME/fortinet
gh cache delete CACHE_KEY --repo YOUR_USERNAME/fortinet

# Clear local caches
rm -rf ~/.cache/pip
docker buildx prune --all
helm repo update
```

### Registry and Deployment Issues
```bash
# Test Harbor registry connectivity
curl -u $REGISTRY_USERNAME:$REGISTRY_PASSWORD https://registry.jclee.me/v2/_catalog

# Test ChartMuseum connectivity
curl -u $CHARTMUSEUM_USERNAME:$CHARTMUSEUM_PASSWORD $CHARTMUSEUM_URL/api/charts

# Test ArgoCD API
curl -H "Authorization: Bearer $ARGOCD_TOKEN" \
  "http://$DEPLOYMENT_HOST:31017/api/v1/applications/$APP_NAME"

# Manual deployment verification
curl "http://$DEPLOYMENT_HOST:$DEPLOYMENT_PORT/api/health"
```

## 📊 Performance Monitoring

### Build Performance Metrics
- **Typical execution times with self-hosted runners**:
  - Pre-flight: 30-60 seconds
  - Test Matrix (parallel): 2-4 minutes
  - Multi-Service Build Matrix (parallel): 6-8 minutes
  - Watchtower Deployment: 2-3 minutes
  - GitOps Deployment: 2-3 minutes
  - Verification: 2-3 minutes
  - **Total**: 14-20 minutes

- **Comparison with single-service deployment**:
  - Single-service: 12-15 minutes
  - Multi-service: 14-20 minutes
  - **Multi-service overhead**: 15-25% for comprehensive deployment

### Resource Utilization
```bash
# Monitor runner resource usage
htop
iotop
docker stats

# Monitor disk usage
df -h
docker system df

# Monitor network usage
iftop
nethogs
```

### Cache Hit Rates
```bash
# Monitor cache effectiveness
gh cache list --repo YOUR_USERNAME/fortinet
docker buildx du

# Optimize cache strategy based on hit rates
# Typical targets:
# - Python dependencies: >90% hit rate
# - Docker layers: >70% hit rate
# - Helm charts: >80% hit rate
```

## 🔒 Enhanced Security Features

### Security Scanning Integration
1. **Trivy Container Scanning**:
   - Vulnerability scanning with SARIF output
   - Critical and High severity focus
   - Platform-specific scanning (amd64, arm64)
   - Integration with GitHub Security tab

2. **Source Code Analysis**:
   - Bandit security linting for Python
   - Safety dependency vulnerability checking
   - Automated security report generation

3. **GitHub Security Integration**:
   - SARIF upload for vulnerability tracking
   - Security advisories integration
   - Automated security issue creation

### Security Best Practices
```bash
# Runner security hardening
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow from 192.168.0.0/16 to any port 80
sudo ufw allow from 192.168.0.0/16 to any port 443

# Docker security
echo '{"live-restore": true, "userland-proxy": false}' | sudo tee -a /etc/docker/daemon.json
sudo systemctl restart docker

# Regular security updates
sudo apt-get update && sudo apt-get upgrade -y
docker pull registry.jclee.me/fortinet:latest
```

## 🎯 Performance Optimization Tips

### Runner Optimization
```bash
# Increase Docker daemon limits
echo '{
  "max-concurrent-downloads": 10,
  "max-concurrent-uploads": 10,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}' | sudo tee /etc/docker/daemon.json

# Optimize filesystem for CI/CD
sudo mount -o remount,noatime /
echo "/dev/sda1 / ext4 defaults,noatime 0 1" | sudo tee -a /etc/fstab
```

### Pipeline Optimization
- **Test Optimization**: Profile slow tests and optimize or parallelize
- **Cache Tuning**: Monitor cache hit rates and adjust strategies
- **Resource Allocation**: Adjust runner resources based on workload
- **Network Optimization**: Use local package mirrors when possible

### Cost Optimization
- **Scheduled Cleanup**: Implement automated cleanup for old artifacts
- **Resource Monitoring**: Track and optimize resource usage patterns
- **Build Efficiency**: Optimize Docker layer ordering and dependencies

## 🔄 Migration Guide

### From GitHub-Hosted to Self-Hosted
1. **Infrastructure Setup**:
   ```bash
   # Provision runner infrastructure
   # Install and configure runners
   # Set up monitoring and alerting
   ```

2. **Workflow Migration**:
   ```yaml
   # Update runs-on values
   runs-on: [self-hosted, linux, x64]
   ```

3. **Testing and Validation**:
   ```bash
   # Test workflows with self-hosted infrastructure
   # Validate performance improvements
   # Verify security scanning integration
   ```

4. **Documentation and Training**:
   ```bash
   # Update team documentation
   # Train team on new infrastructure
   # Establish monitoring procedures
   ```

## ✅ Success Metrics

### Performance Improvements
- ✅ **Multi-Service Build**: Parallel builds for Redis, PostgreSQL, and Fortinet
- ✅ **Registry Integration**: All images pushed to registry.jclee.me
- ✅ **Parallel Execution**: 4x parallel test execution
- ✅ **Cache Efficiency**: >80% cache hit rate for dependencies

### Deployment Enhancements
- ✅ **Watchtower Integration**: Automated deployment via webhook triggers
- ✅ **GitOps Deployment**: ArgoCD sync with comprehensive metadata
- ✅ **Multi-Service Coordination**: Coordinated updates across all services
- ✅ **Registry Propagation**: Reliable image availability verification

### Security Enhancements
- ✅ **Multi-Service Scanning**: Trivy security scanning for all services
- ✅ **SARIF Integration**: Security findings in GitHub Security tab
- ✅ **Compliance**: Enhanced security compliance reporting
- ✅ **Service-Specific Security**: Individual vulnerability assessment per service

### Operational Excellence
- ✅ **Dual Deployment**: Both Watchtower and GitOps deployment methods
- ✅ **Comprehensive Monitoring**: Health checks for all services
- ✅ **Enhanced GitOps**: Multi-service deployment metadata tracking
- ✅ **Automated Cleanup**: Optimized artifact retention and cleanup

This enhanced GitHub Actions workflow provides comprehensive multi-service deployment capabilities with registry.jclee.me integration and dual deployment strategies for maximum reliability and operational flexibility.