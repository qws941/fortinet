#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Deploy Separated Services
# =============================================================================

set -e

# Configuration
COMPOSE_FILE="docker-compose-separated.yml"
PROJECT_NAME="fortinet"
REGISTRY="registry.jclee.me"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check service health
check_health() {
    local service=$1
    local max_attempts=$2
    local attempt=1
    
    echo_info "⏳ Waiting for $service to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps $service | grep -q "healthy"; then
            echo_success "✅ $service is healthy"
            return 0
        fi
        
        echo_info "Attempt $attempt/$max_attempts - $service not ready yet..."
        sleep 10
        ((attempt++))
    done
    
    echo_error "❌ $service failed to become healthy"
    return 1
}

# Function to show service status
show_status() {
    echo_info "📊 Service Status:"
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps
    echo
    
    echo_info "🔍 Health Checks:"
    for service in redis postgresql fortinet; do
        status=$(docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME ps $service 2>/dev/null | tail -n +3 | awk '{print $4}' | head -1)
        if [ "$status" = "healthy" ]; then
            echo_success "✅ $service: $status"
        elif [ "$status" = "starting" ]; then
            echo_warning "⏳ $service: $status"
        else
            echo_error "❌ $service: $status"
        fi
    done
    echo
}

echo_info "🚀 Starting FortiGate Nextrade - Separated Services Deployment"

# Check prerequisites
echo_info "🔍 Checking prerequisites..."

if ! command -v docker-compose &> /dev/null; then
    echo_error "docker-compose is not installed"
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo_error "Compose file $COMPOSE_FILE not found"
    exit 1
fi

# Create data directory if it doesn't exist
if [ ! -d "./data" ]; then
    echo_info "📁 Creating data directory..."
    mkdir -p ./data
    echo "{ \"initialized\": true, \"timestamp\": \"$(date -u +'%Y-%m-%dT%H:%M:%SZ')\" }" > ./data/config.json
fi

# Set environment variables
export SECRET_KEY=${SECRET_KEY:-"fortinet-secret-key-2024-$(openssl rand -hex 16)"}
export JWT_SECRET_KEY=${JWT_SECRET_KEY:-"jwt-secret-fortinet-2024-$(openssl rand -hex 16)"}
export WEBHOOK_URL=${WEBHOOK_URL:-""}
export WATCHTOWER_TOKEN=${WATCHTOWER_TOKEN:-"fortinet-watchtower-2024-$(openssl rand -hex 8)"}

echo_info "🔐 Environment variables set"

# Pull latest images
echo_info "📥 Pulling latest images from registry..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME pull

# Stop any existing containers
echo_info "⏹️ Stopping existing containers..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down --remove-orphans

# Start services in order
echo_info "🔄 Starting services..."

# Start Redis first
echo_info "🔴 Starting Redis service..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d redis
check_health redis 6

# Start PostgreSQL
echo_info "🐘 Starting PostgreSQL service..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d postgresql
check_health postgresql 12

# Start main application
echo_info "🏗️ Starting Fortinet application..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d fortinet
check_health fortinet 18

# Start Watchtower
echo_info "👀 Starting Watchtower service..."
docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d watchtower

echo_success "🎉 All services started successfully!"

# Show final status
show_status

# Test application endpoints
echo_info "🧪 Testing application endpoints..."

# Wait for app to be fully ready
sleep 15

# Test health endpoint
if curl -f -s http://localhost:7777/api/health > /dev/null; then
    echo_success "✅ Health endpoint is responding"
else
    echo_warning "⚠️ Health endpoint test failed"
fi

# Test Redis connectivity
if docker exec fortinet-redis redis-cli ping > /dev/null 2>&1; then
    echo_success "✅ Redis connectivity test passed"
else
    echo_warning "⚠️ Redis connectivity test failed"
fi

# Test PostgreSQL connectivity
if docker exec fortinet-postgresql pg_isready -U fortinet -d fortinet_db > /dev/null 2>&1; then
    echo_success "✅ PostgreSQL connectivity test passed"
else
    echo_warning "⚠️ PostgreSQL connectivity test failed"
fi

# Display connection information
echo_info "📋 Connection Information:"
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ Service Endpoints                                           │"
echo "├─────────────────────────────────────────────────────────────┤"
echo "│ Fortinet Application: http://localhost:7777                │"
echo "│ Redis: localhost:6379                                      │"
echo "│ PostgreSQL: localhost:5432                                 │"
echo "│ Watchtower API: http://localhost:8080                      │"
echo "└─────────────────────────────────────────────────────────────┘"

echo_info "📊 Volume Information:"
docker volume ls | grep fortinet

echo_info "🔧 Management Commands:"
echo "  • View logs: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f [service]"
echo "  • Stop all: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME down"
echo "  • Restart: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME restart [service]"
echo "  • Scale app: docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME up -d --scale fortinet=3"

echo_success "🚀 Deployment completed successfully!"

# Optional: Follow logs
read -p "📋 Would you like to follow the logs? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo_info "📋 Following logs (Press Ctrl+C to exit)..."
    docker-compose -f $COMPOSE_FILE -p $PROJECT_NAME logs -f --tail=50
fi