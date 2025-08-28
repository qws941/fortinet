# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FortiGate Nextrade is a comprehensive network monitoring and analysis platform that integrates with FortiGate firewalls, FortiManager, and ITSM systems. Designed for closed network (offline) environments with both monolithic and microservices architecture support.

**Key Features:**
- Mock FortiGate subsystem for hardware-free development
- FortiManager Advanced Hub with AI-driven policy orchestration
- Real-time packet capture and analysis
- Offline-first design with comprehensive fallback mechanisms
- Dual architecture: Monolithic (legacy) + MSA (microservices)
- GitOps CI/CD with Helm charts, Harbor Registry, ChartMuseum, and ArgoCD

## Technology Stack
- **Backend**: Flask + Blueprint architecture (Python 3.11)
- **Frontend**: Bootstrap 5 + Vanilla JS (no React/Vue)
- **Database**: Redis (cache) + JSON file storage
- **Container**: Docker with multi-stage builds
- **Orchestration**: Kubernetes + ArgoCD GitOps
- **CI/CD**: GitHub Actions (self-hosted runners) → Harbor Registry → ChartMuseum → ArgoCD
- **Ingress**: Traefik (not NGINX)
- **MSA Infrastructure**: Kong Gateway, Consul, RabbitMQ

## Development Commands

### Local Development
```bash
# Install dependencies (supports pyproject.toml)
pip install -r requirements.txt
# OR with development dependencies
pip install -e ".[dev]"

# Run application (monolithic mode)
cd src && python main.py --web

# Run with mock mode (activates simple mock server on port 6666)
APP_MODE=test python src/main.py --web

# Run specific test categories
pytest -m "unit" -v                        # Unit tests only
pytest -m "integration" -v                 # Integration tests only
pytest -m "not slow" -v                    # Skip slow tests
pytest tests/manual/ -v                    # Manual testing suite (26 files)
pytest tests/functional/ -v                # Feature validation tests
pytest --cov=src --cov-report=html -v      # With coverage

# Code quality (configured in pyproject.toml)
black src/ && isort src/ && flake8 src/ --max-line-length=120 --ignore=E203,W503

# Alternative: Use pyproject.toml configured tools
python -m black src/
python -m isort src/
python -m flake8 src/

# Run feature test (validates 10 core features)
pytest tests/functional/test_features.py -v
```

### MSA Development
```bash
# Start full MSA stack
docker-compose -f docker-compose.msa.yml up -d

# Configure Kong Gateway routes
./scripts/setup-kong-routes.sh

# Check service status
docker-compose -f docker-compose.msa.yml ps

# Access MSA endpoints
# Kong Gateway: http://localhost:8000
# Consul UI: http://localhost:8500
# RabbitMQ UI: http://localhost:15672
```

### Docker Development
```bash
# Build production image (multi-stage build)
docker build -f Dockerfile.production -t fortigate-nextrade:latest .

# Run with mock mode (uses start.sh for production startup)
docker run -d --name fortigate-nextrade \
  -p 7777:7777 \
  -e APP_MODE=test \
  -e OFFLINE_MODE=true \
  -e WEB_APP_PORT=7777 \
  fortigate-nextrade:latest

# Development with simple mock server
docker run -d --name fortinet-debug \
  -p 7777:7777 \
  -v $(pwd)/dev-tools:/app/dev-tools \
  python:3.11-slim python /app/dev-tools/simple-mock-server.py
```

### Deployment & Monitoring
```bash
# Check deployment status
curl http://192.168.50.110:30777/api/health  # Current NodePort
curl http://fortinet.jclee.me/api/health     # Domain (needs /etc/hosts entry)

# Monitor ArgoCD deployment
argocd app get fortinet
argocd app sync fortinet

# Check pods
kubectl get pods -n fortinet
kubectl logs -l app=fortinet -n fortinet -f
```

## Commands Workflow

The project supports Claude Code's intelligent automation commands for streamlined development and deployment. These commands integrate seamlessly with the existing FortiGate Nextrade development pipeline.

### Available Commands

#### `/main` - Complete Automation Pipeline
**Purpose**: Execute the full development-to-deployment automation chain
**Process**:
1. **Test Phase**: Runs comprehensive test suite (unit, integration, functional)
2. **Quality Phase**: Code formatting with black/isort, linting with flake8
3. **Security Phase**: Security scans with bandit and safety
4. **Build Phase**: Docker image build and registry push
5. **Deploy Phase**: Helm chart package and ArgoCD deployment
6. **Verify Phase**: Health checks and deployment validation

**Best Use Cases**:
- Feature completion ready for production
- Release candidate preparation
- Full CI/CD pipeline validation

#### `/test` - Intelligent Test Management
**Purpose**: Run comprehensive test suite with automatic issue resolution
**Capabilities**:
- **Smart Test Discovery**: Automatically detects and runs relevant tests based on code changes
- **Coverage Analysis**: Targets minimum 5% coverage with detailed reporting
- **Auto-Fix Mode**: Attempts to fix common test failures (import errors, mock issues)
- **Performance Testing**: Includes slow test detection and optimization suggestions
- **Parallel Execution**: Runs unit and integration tests in parallel for speed

**Test Categories Executed**:
```bash
# Unit tests - Fast, isolated component testing
pytest -m "unit" --maxfail=5 -x

# Integration tests - API endpoint validation (70+ endpoints)
pytest -m "integration" --timeout=30

# Functional tests - Core feature validation (10 features)
pytest tests/functional/test_features.py

# MSA tests - Microservice architecture validation
pytest tests/msa/ --timeout=60

# Manual tests - Complex scenario validation (26 test files)
pytest tests/manual/ --capture=no
```

#### `/clean` - Intelligent Code Optimization
**Purpose**: Comprehensive codebase cleanup and optimization
**Operations**:
- **Code Formatting**: black with 120-character line limit
- **Import Optimization**: isort with profile compatibility for Django/Flask
- **Duplicate Detection**: Identifies and removes code duplication
- **Dead Code Removal**: Removes unused imports and functions
- **Security Fixes**: Applies automated security patches
- **Performance Optimization**: Suggests and applies performance improvements

**Configuration Integration**:
```toml
# pyproject.toml configuration used
[tool.black]
line-length = 120
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 120
known_first_party = ["src"]

[tool.flake8]
max-line-length = 120
ignore = ["E203", "W503"]
```

#### `/deploy` - GitOps Deployment Automation
**Purpose**: Automated deployment via GitOps CI/CD pipeline
**Deployment Flow**:
1. **Pre-Deploy Validation**: Ensures tests pass and code quality standards met
2. **Git Operations**: Automated commit with semantic versioning
3. **CI/CD Trigger**: Pushes to GitHub, triggering GitHub Actions workflow
4. **Image Build**: Multi-stage Docker build optimized for production
5. **Registry Push**: Secure push to Harbor Registry (registry.jclee.me)
6. **Helm Package**: Chart packaging and upload to ChartMuseum
7. **ArgoCD Sync**: Automated Kubernetes deployment via ArgoCD
8. **Health Verification**: Post-deployment health checks on NodePort 30777

**Deployment Targets**:
- **Monolithic Mode**: Single container deployment
- **MSA Mode**: 7-service microservice deployment
- **Offline Mode**: Air-gapped environment deployment

#### `/init` - Project Documentation Management
**Purpose**: Initialize and maintain comprehensive project documentation
**Documentation Scope**:
- API documentation generation from OpenAPI specs
- Architecture diagrams and component maps
- Development workflow documentation
- Deployment runbooks and troubleshooting guides
- Security and compliance documentation

### Advanced Workflow Patterns

#### Development Workflow Automation
```bash
# Feature development cycle
/test          # Validate current state
# Make changes
/test          # Verify changes work
/clean         # Optimize code quality
/deploy        # Deploy to staging

# Hotfix workflow
/test --fast   # Quick validation
# Apply fix
/main          # Full pipeline for critical fixes

# Release preparation
/clean         # Comprehensive cleanup
/test --full   # All test categories
/deploy --prod # Production deployment
```

#### Continuous Integration Patterns
```bash
# Pre-commit automation
/clean && /test  # Local validation before commit

# Branch validation
/test --branch   # Test only changed components

# Release candidate
/main --rc       # Full pipeline with release candidate tagging
```

### Performance Optimization Integration

#### Test Performance Optimization
- **Parallel Test Execution**: Automatically detects CPU cores and runs tests in parallel
- **Test Dependency Caching**: Caches test dependencies and fixtures for faster execution
- **Smart Test Selection**: Only runs tests affected by code changes
- **Performance Profiling**: Identifies slow tests and suggests optimizations

#### Build Performance Optimization
- **Docker Layer Caching**: Optimizes Docker build cache utilization
- **Multi-stage Build Optimization**: Minimizes final image size
- **Dependency Caching**: Caches Python packages and requirements

#### Deployment Performance
- **Progressive Deployment**: Blue-green deployment patterns
- **Health Check Optimization**: Fast health check endpoints for quick validation
- **Resource Optimization**: Container resource limits and requests optimization

### Integration with Existing Commands

#### Seamless Tool Integration
- **Pytest Integration**: Uses `python -m pytest` for module-based testing
- **Poetry/Pip Compatibility**: Works with both traditional pip and modern pyproject.toml
- **Docker Integration**: Leverages existing Dockerfile.production and docker-compose files
- **Kubernetes Integration**: Uses existing Helm charts and ArgoCD configurations

#### Environment Compatibility
- **Local Development**: Full feature support in local development environment
- **CI/CD Integration**: Native GitHub Actions integration
- **Offline Mode**: Full functionality in air-gapped environments
- **MSA Support**: Complete microservice architecture support

#### Configuration Harmony
- **pyproject.toml**: Uses existing tool configurations
- **Environment Variables**: Respects all existing environment variable patterns
- **Git Integration**: Works with existing branching strategies and commit patterns
- **Security Integration**: Leverages existing security scanning and compliance tools

### Command Monitoring and Feedback

#### Real-time Progress Tracking
- **Progress Indicators**: Real-time progress bars for long-running operations
- **Stage Completion**: Clear indication of completed and remaining stages
- **Error Detection**: Immediate error reporting with suggested fixes
- **Performance Metrics**: Execution time tracking and optimization suggestions

#### Result Reporting
- **Comprehensive Reports**: Detailed reports for all operations
- **Success/Failure Indicators**: Clear success/failure status
- **Action Recommendations**: Suggested next steps based on results
- **Trend Analysis**: Historical performance and quality trends

## Critical Architecture Patterns

### 1. API Client Session Management
**CRITICAL**: All API clients MUST initialize a requests session:
```python
class SomeAPIClient(BaseAPIClient):
    def __init__(self):
        super().__init__()  # REQUIRED - handles session initialization
```

### 2. Blueprint URL Namespacing
Templates MUST use blueprint namespaces:
```html
{{ url_for('main.dashboard') }}      <!-- Correct -->
{{ url_for('dashboard') }}            <!-- Wrong -->
```

### 3. Configuration Hierarchy
1. `data/config.json` - Runtime configuration (highest priority)
2. Environment variables
3. `src/config/unified_settings.py` - Default values

### 4. Mock System Activation
```python
# Automatic when APP_MODE=test
if os.getenv('APP_MODE', 'production').lower() == 'test':
    # Uses mock_fortigate and Postman-based mock server
```

### 5. Import Path Structure
**CRITICAL**: All imports within src/ must use relative paths:
```python
# Correct - relative imports from src/
from utils.unified_logger import get_logger
from api.clients.fortigate_api_client import FortiGateAPIClient

# Wrong - absolute imports cause ModuleNotFoundError
from src.utils.unified_logger import get_logger
```

## Key Components

### Flask Application Factory Pattern
The system uses a sophisticated Flask application factory with blueprint modularity:
```python
def create_app():
    app = Flask(__name__)
    # Security configurations
    # Blueprint registration
    # Cache manager initialization
    return app
```
- 8 blueprints handle domain-specific routing
- Unified security headers and CSRF protection
- Dynamic SocketIO integration based on OFFLINE_MODE

### FortiManager Advanced Hub
Four specialized modules accessible via:
```python
hub = FortiManagerAdvancedHub(api_client)
```

1. **Policy Orchestrator**: `hub.policy_orchestrator` - AI-driven policy management
2. **Compliance Framework**: `hub.compliance_framework` - Automated compliance checks
3. **Security Fabric**: `hub.security_fabric` - Integrated security management
4. **Analytics Engine**: `hub.analytics_engine` - Advanced analytics and reporting

### Connection Pool Management
Located in `src/core/connection_pool.py`:
- **connection_pool_manager**: Global connection pool for API clients
- **Session reuse**: Prevents connection exhaustion
- **Thread-safe**: Supports concurrent requests
- **Auto-cleanup**: Handles connection lifecycle

### Packet Sniffer System
Located in `src/security/packet_sniffer/`:
- **Analyzers**: Protocol-specific analysis (DNS, HTTP, TLS, FortiManager)
- **Filters**: BPF and advanced packet filtering
- **Exporters**: Multiple format support (CSV, JSON, PCAP, Reports)
- **Inspectors**: Deep packet inspection capabilities
- **Session Management**: Stateful packet tracking

### ITSM Integration
Located in `src/itsm/`:
- **Ticket Automation**: Automated ticket creation/updates
- **Policy Requests**: Firewall policy request workflows
- **Approval Workflows**: Multi-level approval processes
- **ServiceNow Integration**: API client for ServiceNow

## Testing Framework

### Pytest Configuration
- **Markers**: `slow`, `integration`, `unit`, `fortimanager`, `monitoring`
- **Coverage target**: 5% minimum (configurable in pytest.ini)
- **Test discovery**: `tests/` directory

### Custom Rust-Style Testing Framework
```python
from src.utils.integration_test_framework import test_framework

@test_framework.test("Test description")
def test_something():
    with test_framework.test_app() as (app, client):
        response = client.get('/')
        test_framework.assert_eq(response.status_code, 200)
```

### Master Integration Test Suite
```bash
python src/utils/test_master_integration_suite.py
# Features: Phase-based execution, parallel testing, comprehensive results
```

## Environment Variables

### Core Settings
- `APP_MODE`: `production` | `test` | `development`
- `OFFLINE_MODE`: `true` | `false`
- `WEB_APP_PORT`: Default `7777`
- `SECRET_KEY`: Required for production

### API Configuration
- `FORTIMANAGER_HOST`, `FORTIMANAGER_API_KEY`
- `FORTIGATE_HOST`, `FORTIGATE_API_KEY`
- `ITSM_BASE_URL`, `ITSM_API_KEY`

### MSA Configuration
- `CONSUL_URL`: Service discovery
- `RABBITMQ_URL`: Message queue
- `REDIS_URL`: Cache backend
- `KONG_ADMIN_URL`: API Gateway admin

## MSA Service Architecture

### Service Ports
- **Kong Gateway**: 8000 (proxy), 8001 (admin), 8002 (GUI)
- **Auth Service**: 8081
- **FortiManager Service**: 8082
- **ITSM Service**: 8083
- **Monitoring Service**: 8084
- **Security Service**: 8085
- **Analysis Service**: 8086
- **Configuration Service**: 8087
- **Consul**: 8500
- **RabbitMQ**: 5672 (AMQP), 15672 (Management)

### Service Communication
- All external requests go through Kong Gateway
- Services discover each other via Consul
- Async messaging via RabbitMQ
- Shared cache via Redis

## CI/CD Pipeline

### GitHub Actions Workflow (gitops-pipeline.yml)
1. **Test Stage**: pytest, flake8, safety, bandit (parallel)
2. **Build Stage**: Docker buildx → Harbor Registry
3. **Helm Deploy**: Package → ChartMuseum upload → ArgoCD sync
4. **Verify Stage**: Health checks on NodePort 30777

### Required GitHub Secrets
- `REGISTRY_URL`: registry.jclee.me
- `REGISTRY_USERNAME`, `REGISTRY_PASSWORD`
- `CHARTMUSEUM_URL`: https://charts.jclee.me
- `CHARTMUSEUM_USERNAME`, `CHARTMUSEUM_PASSWORD`
- `APP_NAME`: fortinet
- `DEPLOYMENT_HOST`: 192.168.50.110
- `DEPLOYMENT_PORT`: 30777

## Project Structure
```
fortinet/
├── src/                      # Monolithic application (139 Python files)
│   ├── web_app.py           # Flask factory (8 blueprints)
│   ├── main.py              # Entry point
│   ├── routes/              # Blueprint routes (8 modules)
│   ├── api/clients/         # External API clients (4)
│   ├── fortimanager/        # Advanced features (5 modules)
│   ├── itsm/                # ITSM integration (7 modules)
│   ├── security/            # Security components
│   │   └── packet_sniffer/  # Packet capture system
│   ├── monitoring/          # Monitoring system
│   ├── analysis/            # Analysis engines
│   ├── utils/               # Utilities (17 modules)
│   └── templates/           # Jinja2 templates (20)
├── services/                # MSA microservices
│   ├── auth/                # Authentication service (8081)
│   ├── fortimanager/        # FortiManager service (8082)
│   ├── itsm/                # ITSM service (8083)
│   ├── monitoring/          # Monitoring service (8084)
│   ├── security/            # Security service (8085)
│   ├── analysis/            # Analysis service (8086)
│   └── config/              # Configuration service (8087)
├── tests/                   # Test suite (62 files)
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests (70+ endpoints)
│   ├── manual/              # Manual test suite (26 files)
│   └── msa/                 # MSA-specific tests
├── charts/fortinet/         # Helm chart (Traefik ingress)
├── docker-compose.msa.yml   # MSA development stack
├── .github/workflows/       # CI/CD (self-hosted runners)
└── requirements.txt         # Python dependencies
```

## Key API Endpoints

### Core APIs (Monolithic)
- `GET /api/health` - Health check
- `GET/POST /api/settings` - Settings management

### FortiManager APIs
- `POST /api/fortimanager/analyze-packet-path` - Packet path analysis
- `GET /api/fortimanager/devices` - List devices
- `POST /api/fortimanager/policies` - Get policies
- `GET /api/fortimanager/compliance` - Compliance status

### ITSM APIs
- `GET/POST /api/itsm/tickets` - Ticket management
- `POST /api/itsm/policy-requests` - Policy request automation
- `GET /api/itsm/approvals` - Approval workflows

### Monitoring APIs
- `GET /api/logs/stream` - Real-time log streaming (SSE)
- `GET /api/logs/container` - Container logs
- `GET /api/monitoring/metrics` - System metrics
- `GET /api/monitoring/alerts` - Alert management

### Security APIs
- `POST /api/security/scan` - Security scanning
- `GET /api/security/packets` - Packet analysis results
- `GET /api/security/threats` - Threat detection

## Troubleshooting Guide

### Common Issues & Solutions

#### Application Startup Issues

##### Port 7777 in Use
```bash
# Check what's using the port
sudo lsof -i:7777

# Kill process using port 7777
sudo lsof -ti:7777 | xargs kill -9

# Alternative: Use different port
WEB_APP_PORT=7778 python src/main.py --web
```

##### Import Errors
**Root Cause**: Running from wrong directory causing Python path issues
```bash
# Correct approach - run from src directory
cd src && python main.py --web

# Wrong approach - causes ModuleNotFoundError
python src/main.py --web

# Debug import issues
cd src && python -c "import sys; print('\n'.join(sys.path))"
```

##### Mock Mode Not Working
**Symptoms**: Real API calls attempted instead of mock responses
```bash
# Verify environment variable
echo $APP_MODE

# Set explicitly
export APP_MODE=test
python src/main.py --web

# Verify mock server startup
curl http://localhost:6666/api/health
```

#### Network and Connectivity Issues

##### Domain Access Issues
**Problem**: Cannot access fortinet.jclee.me
```bash
# Add to hosts file
echo "192.168.50.110 fortinet.jclee.me" | sudo tee -a /etc/hosts

# Verify DNS resolution
nslookup fortinet.jclee.me

# Test direct IP access
curl http://192.168.50.110:30777/api/health
```

##### API Connection Timeouts
**Symptoms**: FortiManager/FortiGate API calls timeout
```bash
# Test network connectivity
ping $FORTIMANAGER_HOST

# Test API endpoint accessibility
curl -k https://$FORTIMANAGER_HOST/jsonrpc

# Check firewall rules
sudo iptables -L | grep $FORTIMANAGER_HOST
```

#### Docker and Container Issues

##### Docker Build Failures
```bash
# Clean Docker cache
docker system prune -a

# Build with no cache
docker build --no-cache -f Dockerfile.production -t fortigate-nextrade:latest .

# Check disk space
df -h

# Inspect build logs
docker build -f Dockerfile.production -t fortigate-nextrade:latest . 2>&1 | tee build.log
```

##### Container Health Check Failures
```bash
# Check container logs
docker logs fortigate-nextrade -f

# Enter container for debugging
docker exec -it fortigate-nextrade /bin/bash

# Check application status inside container
docker exec fortigate-nextrade curl localhost:7777/api/health
```

#### Kubernetes and Deployment Issues

##### ArgoCD Sync Issues
```bash
# Check ArgoCD application status
argocd app get fortinet

# View detailed sync status
argocd app sync fortinet --dry-run

# Create image pull secret
kubectl create secret docker-registry harbor-registry \
  --docker-server=registry.jclee.me \
  --docker-username=admin \
  --docker-password=$PASSWORD \
  -n fortinet

# Force sync with prune
argocd app sync fortinet --prune

# Check for resource conflicts
kubectl get events -n fortinet --sort-by='.lastTimestamp'
```

##### Pod Startup Issues
```bash
# Check pod status
kubectl get pods -n fortinet -o wide

# Describe problematic pods
kubectl describe pod -l app=fortinet -n fortinet

# Check pod logs
kubectl logs -l app=fortinet -n fortinet -f

# Check resource limits
kubectl top pods -n fortinet
```

##### Service and Ingress Issues
```bash
# Check service endpoints
kubectl get svc -n fortinet

# Test service connectivity
kubectl port-forward svc/fortinet 8080:7777 -n fortinet

# Check ingress status
kubectl get ingress -n fortinet

# Test ingress connectivity
curl -H "Host: fortinet.jclee.me" http://192.168.50.110:30777/api/health
```

#### Database and Storage Issues

##### Redis Connection Issues
```bash
# Test Redis connectivity
redis-cli ping

# Check Redis configuration
redis-cli config get "*"

# Monitor Redis operations
redis-cli monitor
```

##### JSON File Storage Issues
```bash
# Check data directory permissions
ls -la data/

# Verify JSON file integrity
python -m json.tool data/config.json

# Check disk space
df -h data/
```

#### Test and Development Issues

##### Test Failures
```bash
# Run tests with verbose output
pytest -v --tb=long

# Run specific failing test
pytest tests/specific_test.py::test_function -v

# Check test dependencies
pip check

# Clear pytest cache
rm -rf .pytest_cache __pycache__
```

##### Performance Issues
```bash
# Profile application startup
time python src/main.py --web

# Monitor resource usage
htop

# Check memory usage
free -m

# Monitor network connections
netstat -tulpn | grep python
```

### Advanced Troubleshooting

#### Debug Mode Configuration
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=1

# Run with enhanced logging
python src/main.py --web --debug
```

#### Network Traffic Analysis
```bash
# Monitor network traffic
sudo tcpdump -i any host $FORTIMANAGER_HOST

# Check SSL/TLS issues
openssl s_client -connect $FORTIMANAGER_HOST:443

# Test API endpoints manually
curl -X POST https://$FORTIMANAGER_HOST/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"method":"get","params":[{"url":"/sys/status"}],"id":1}'
```

#### Performance Profiling
```bash
# Profile Python application
python -m cProfile -o profile.stats src/main.py --web

# Analyze profile results
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('time').print_stats(20)"

# Memory profiling
pip install memory_profiler
python -m memory_profiler src/main.py --web
```

## Automated CI/CD Monitoring

### GitHub Actions Monitoring

#### Pipeline Status Monitoring
```bash
# Check workflow status via GitHub CLI
gh workflow list
gh run list --workflow=gitops-pipeline.yml

# Monitor specific run
gh run view $RUN_ID

# Download logs for failed runs
gh run download $RUN_ID
```

#### Pipeline Performance Metrics
- **Test Stage**: Target < 5 minutes for full test suite
- **Build Stage**: Target < 10 minutes for Docker build and push
- **Deploy Stage**: Target < 3 minutes for Helm package and deploy
- **Verify Stage**: Target < 2 minutes for health checks

#### Automated Failure Notifications
```yaml
# GitHub Actions notification configuration
- name: Notify on Failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Harbor Registry Monitoring

#### Image Management
```bash
# List images in Harbor
curl -u admin:$PASSWORD https://registry.jclee.me/api/v2.0/projects/fortinet/repositories

# Check image vulnerabilities
curl -u admin:$PASSWORD https://registry.jclee.me/api/v2.0/projects/fortinet/repositories/fortinet/artifacts/latest/scan

# Monitor registry storage
curl -u admin:$PASSWORD https://registry.jclee.me/api/v2.0/statistics
```

#### Automated Image Cleanup
```bash
# Script to clean old images (retention policy)
#!/bin/bash
# Clean images older than 30 days
curl -X DELETE -u admin:$PASSWORD \
  "https://registry.jclee.me/api/v2.0/projects/fortinet/repositories/fortinet/artifacts?q=push_time%3C$(date -d '30 days ago' +%s)"
```

### ArgoCD Deployment Monitoring

#### Application Health Monitoring
```bash
# Monitor application sync status
argocd app wait fortinet --timeout 300

# Check application health
argocd app get fortinet -o json | jq '.status.health.status'

# Monitor sync waves and hooks
argocd app get fortinet -o json | jq '.status.operationState'
```

#### Automated Rollback Configuration
```yaml
# ArgoCD automated rollback policy
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
    - PrunePropagationPolicy=foreground
    retry:
      limit: 3
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

### Kubernetes Cluster Monitoring

#### Resource Usage Monitoring
```bash
# Monitor node resources
kubectl top nodes

# Monitor namespace resources
kubectl top pods -n fortinet

# Check resource quotas
kubectl describe quota -n fortinet
```

#### Automated Health Checks
```bash
# Health check script
#!/bin/bash
HEALTH_URL="http://192.168.50.110:30777/api/health"
TIMEOUT=10

# Check application health
if curl -f --max-time $TIMEOUT $HEALTH_URL > /dev/null 2>&1; then
    echo "✅ Application healthy"
    exit 0
else
    echo "❌ Application unhealthy"
    # Send alert
    curl -X POST $SLACK_WEBHOOK -H 'Content-type: application/json' \
         --data '{"text":"🚨 FortiGate Nextrade health check failed"}'
    exit 1
fi
```

### Monitoring Dashboard Integration

#### Prometheus Metrics Collection
```yaml
# Add to deployment for metrics collection
apiVersion: v1
kind: Service
metadata:
  name: fortinet-metrics
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "7777"
    prometheus.io/path: "/metrics"
```

#### Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "FortiGate Nextrade Monitoring",
    "panels": [
      {
        "title": "Application Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job='fortinet'}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "http_request_duration_seconds{job='fortinet'}"
          }
        ]
      }
    ]
  }
}
```

### Alert Management

#### Prometheus Alert Rules
```yaml
groups:
- name: fortinet.rules
  rules:
  - alert: FortinetDown
    expr: up{job="fortinet"} == 0
    for: 2m
    annotations:
      summary: "FortiGate Nextrade application is down"
      
  - alert: HighResponseTime
    expr: http_request_duration_seconds{job="fortinet"} > 5
    for: 5m
    annotations:
      summary: "High response time detected"
```

#### Automated Incident Response
```bash
# Automated restart script
#!/bin/bash
if ! curl -f http://192.168.50.110:30777/api/health; then
    echo "Restarting application..."
    kubectl rollout restart deployment/fortinet -n fortinet
    kubectl rollout status deployment/fortinet -n fortinet --timeout=300s
fi
```

## Performance Optimization Guide

### Application Performance

#### Memory Optimization
```bash
# Monitor memory usage during development
python -m memory_profiler src/main.py --web

# Optimize Python memory usage
export PYTHONDONTWRITEBYTECODE=1  # Reduce .pyc file creation
export PYTHONUNBUFFERED=1         # Improve logging performance

# Flask memory optimization
export FLASK_ENV=production       # Use production optimizations
```

#### Database Performance
```python
# Redis connection pool optimization
REDIS_CONNECTION_POOL_SIZE = 50
REDIS_CONNECTION_TIMEOUT = 5

# JSON file caching strategy
CACHE_TTL = 300  # 5 minutes cache for config files
```

#### API Client Performance
```python
# Session reuse for better performance
class OptimizedAPIClient(BaseAPIClient):
    def __init__(self):
        super().__init__()
        self.session.headers.update({'Connection': 'keep-alive'})
        
    # Connection pooling
    adapter = HTTPAdapter(
        pool_connections=20,
        pool_maxsize=50,
        max_retries=3
    )
    self.session.mount('http://', adapter)
    self.session.mount('https://', adapter)
```

### Docker Performance Optimization

#### Multi-Stage Build Optimization
```dockerfile
# Optimize layer caching
FROM python:3.11-slim as base
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Use specific tags for reproducible builds
FROM base as production
COPY src/ /app/src/
WORKDIR /app
```

#### Container Resource Limits
```yaml
# Kubernetes resource optimization
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Testing Performance

#### Parallel Test Execution
```bash
# Run tests in parallel
pytest -n auto tests/

# Optimize test database setup
pytest --reuse-db tests/

# Cache test dependencies
pip install pytest-cache
pytest --cache-clear tests/  # Clear when needed
```

#### Test Data Optimization
```python
# Use fixtures for expensive operations
@pytest.fixture(scope="session")
def api_client():
    return FortiGateAPIClient()

# Mock external calls for speed
@pytest.mark.unit
def test_fast_unit(mocker):
    mocker.patch('requests.get', return_value=mock_response)
```

### CI/CD Performance

#### Pipeline Optimization
```yaml
# GitHub Actions optimization
- name: Cache Dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: pip-${{ hashFiles('requirements.txt') }}

# Parallel job execution
strategy:
  matrix:
    test-type: [unit, integration, security]
```

#### Docker Build Cache
```bash
# Use BuildKit for better caching
export DOCKER_BUILDKIT=1

# Multi-platform build optimization
docker buildx build --cache-from=type=registry,ref=registry.jclee.me/fortinet/cache
```

### Network Performance

#### Connection Optimization
```python
# Async HTTP requests where appropriate
import aiohttp
import asyncio

async def fetch_multiple_endpoints():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_endpoint(session, url) for url in urls]
        return await asyncio.gather(*tasks)
```

#### DNS and Network Tuning
```bash
# Optimize DNS resolution
echo "options single-request-reopen" >> /etc/resolv.conf

# Network buffer tuning
echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' >> /etc/sysctl.conf
```

### Monitoring Performance

#### Efficient Logging
```python
# Structured logging for better performance
import structlog

logger = structlog.get_logger()
logger = logger.bind(component="api", version="1.0")

# Log sampling for high-volume endpoints
if random.random() < 0.1:  # Sample 10% of requests
    logger.info("Request processed", endpoint=endpoint)
```

#### Metrics Collection Optimization
```python
# Use efficient metrics collection
from prometheus_client import Counter, Histogram, start_http_server

# Counters for counting events
request_count = Counter('requests_total', 'Total requests')

# Histograms for measuring durations
request_duration = Histogram('request_duration_seconds', 'Request duration')

# Start metrics server on separate port
start_http_server(8080)
```

### Production Performance Tuning

#### Flask Configuration
```python
# Production Flask settings
app.config.update(
    DEBUG=False,
    TESTING=False,
    SECRET_KEY=os.environ['SECRET_KEY'],
    WTF_CSRF_TIME_LIMIT=None,  # Reduce CSRF overhead
    SEND_FILE_MAX_AGE_DEFAULT=31536000,  # 1 year cache
)

# Use production WSGI server
gunicorn_config = {
    'workers': multiprocessing.cpu_count() * 2 + 1,
    'worker_class': 'sync',
    'worker_connections': 1000,
    'max_requests': 1000,
    'preload_app': True
}
```

#### Database Connection Tuning
```python
# Redis optimization for production
REDIS_CONFIG = {
    'host': 'redis',
    'port': 6379,
    'db': 0,
    'decode_responses': True,
    'socket_connect_timeout': 5,
    'socket_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}
```

#### Kubernetes Performance
```yaml
# Pod disruption budget for availability
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: fortinet-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: fortinet

# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fortinet-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fortinet
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Development Guidelines

### Do's
- Always use `APP_MODE=test` for local development
- Use blueprint namespaces in templates: `{{ url_for('main.dashboard') }}`
- Call `super().__init__()` when extending API clients
- Run tests before committing: `pytest tests/ -v`
- Use environment variables instead of hardcoded values
- Run code quality checks: `black src/ && isort src/ && flake8 src/`
- Use the custom test framework for integration tests
- Implement connection pooling for API clients
- Use caching strategically for expensive operations
- Monitor resource usage in development and production

### Don'ts
- Don't use absolute imports within src/ directory
- Don't hardcode IPs, URLs, or credentials
- Don't bypass the mock system when `APP_MODE=test`
- Don't forget session management in API clients
- Don't use uppercase in Docker image names
- Don't commit without running the linter
- Don't ignore memory leaks in long-running processes
- Don't create new database connections for each request
- Don't disable caching without performance testing
- Don't ignore production performance metrics

### Testing Best Practices
- Mark tests appropriately: `@pytest.mark.unit`, `@pytest.mark.integration`
- Use fixtures for common test data (defined in `tests/conftest.py`)
- Mock external API calls in unit tests
- Use `APP_MODE=test` for integration tests
- Run the feature test to validate core functionality: `pytest tests/functional/test_features.py -v`
- Use custom Rust-style test framework: `@test_framework.test("description")`
- Implement parallel test execution for faster feedback
- Use test data caching for expensive setup operations
- Profile tests to identify performance bottlenecks
- Implement test timeout limits to prevent hanging tests

## High-Level Architecture

### Request Flow (Monolithic Mode)
1. **Entry Point**: `src/main.py --web` starts Flask app on port 7777
2. **Application Factory**: `src/web_app.py` creates Flask app with 8 blueprints
3. **Blueprint Routes**: Each blueprint handles specific domain (main, api, fortimanager, itsm, etc.)
4. **API Clients**: All clients extend `BaseAPIClient` for session management
5. **Cache Layer**: `UnifiedCacheManager` handles Redis/memory caching
6. **Data Layer**: JSON file storage for persistence in offline mode

### MSA Request Flow
1. **Kong Gateway** (8000): All external requests entry point
2. **Service Discovery**: Consul (8500) manages service registration
3. **Message Queue**: RabbitMQ (5672) for async communication
4. **Microservices**: 7 services (8081-8087) handle specific domains
5. **Shared Cache**: Redis for cross-service data sharing

### Offline-First Architecture
**CRITICAL**: System automatically detects and adapts to offline environments:
```python
OFFLINE_MODE = (
    os.getenv("OFFLINE_MODE", "false").lower() == "true"
    or os.getenv("NO_INTERNET", "false").lower() == "true"
    or os.getenv("DISABLE_EXTERNAL_CALLS", "false").lower() == "true"
)
```
- Disables SocketIO, updates, and telemetry
- Activates mock servers on port 6666
- Uses JSON file storage instead of external databases

### Configuration Hierarchy Pattern
Strict 3-tier configuration loading:
1. **data/config.json** (runtime configuration - highest priority)
2. **Environment variables** (deployment-specific)
3. **src/config/unified_settings.py** (application defaults)

### Security-First Design
Multiple security layers implemented:
- **Enhanced security**: `src/utils/enhanced_security.py`
- **Security fixes**: `src/utils/security_fixes.py` (critical import at line 210)
- **Security scanner**: `src/utils/security_scanner.py`
- **Rate limiting**: Built into Flask routes
- **CSRF protection**: Automatic token generation