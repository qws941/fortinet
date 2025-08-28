#!/bin/bash
# FortiGate Nextrade Docker Compose Stop Script

set -e

echo "🛑 Stopping FortiGate Nextrade..."

# Stop services gracefully
echo "📋 Current running services:"
docker-compose ps

echo "🔽 Stopping services..."
docker-compose down

# Optional: Remove volumes (uncomment if needed)
# echo "🗑️  Removing volumes..."
# docker-compose down -v

echo "✅ FortiGate Nextrade stopped successfully!"

# Show remaining containers (if any)
echo "📊 Remaining containers:"
docker ps --filter "name=fortinet" || echo "No fortinet containers running"