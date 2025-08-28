#!/bin/bash
# FortiGate Nextrade Docker Compose Startup Script

set -e

echo "🚀 Starting FortiGate Nextrade with Docker Compose..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Login to private registry
echo "🔑 Logging into private registry..."
if [ -z "$REGISTRY_USERNAME" ] || [ -z "$REGISTRY_PASSWORD" ]; then
    echo "❌ REGISTRY_USERNAME and REGISTRY_PASSWORD environment variables must be set"
    echo "   Export them or add to .env file:"
    echo "   export REGISTRY_USERNAME=your_username"
    echo "   export REGISTRY_PASSWORD=your_password"
    exit 1
fi
echo "$REGISTRY_PASSWORD" | docker login ${REGISTRY:-registry.jclee.me} -u "$REGISTRY_USERNAME" --password-stdin

# Pull latest image
echo "📥 Pulling latest image..."
docker pull ${REGISTRY:-registry.jclee.me}/${IMAGE_NAME:-fortinet}:latest

# Start services
echo "🐳 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Service Status:"
docker-compose ps

# Show logs
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo "✅ FortiGate Nextrade is running!"
echo "🌐 Access at: http://localhost:7777"
echo "📊 Health check: http://localhost:7777/api/health"