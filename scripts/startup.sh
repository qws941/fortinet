#!/bin/bash
# =============================================================================
# FortiGate Nextrade - Container Startup Script
# =============================================================================

set -e

# Environment variables with defaults
export PYTHONPATH=${PYTHONPATH:-/app/src}
export PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-1}
export PYTHONDONTWRITEBYTECODE=${PYTHONDONTWRITEBYTECODE:-1}

# Application settings
export APP_MODE=${APP_MODE:-production}
export WEB_APP_HOST=${WEB_APP_HOST:-0.0.0.0}
export WEB_APP_PORT=${WEB_APP_PORT:-7777}

# Performance settings
export WORKERS=${WORKERS:-4}
export WORKER_CLASS=${WORKER_CLASS:-gevent}
export TIMEOUT=${TIMEOUT:-120}

echo "🚀 Starting FortiGate Nextrade Application"
echo "📍 Working Directory: $(pwd)"
echo "🐍 Python Path: $PYTHONPATH"
echo "🌐 Host: $WEB_APP_HOST:$WEB_APP_PORT"
echo "⚙️  Workers: $WORKERS ($WORKER_CLASS)"

# Wait for dependencies
echo "⏳ Waiting for dependencies..."
sleep 5

# Check if src directory exists
if [ ! -d "/app/src" ]; then
    echo "❌ Source directory not found: /app/src"
    exit 1
fi

# Check if web_app.py exists
if [ ! -f "/app/src/web_app.py" ]; then
    echo "❌ Main application file not found: /app/src/web_app.py"
    exit 1
fi

# Change to the src directory
cd /app/src

# Try to import the application first
echo "🔍 Testing application import..."
python3 -c "from web_app import create_app; app = create_app(); print('✅ Application import successful')" || {
    echo "❌ Application import failed"
    echo "📂 Available files in /app/src:"
    ls -la /app/src/ || true
    exit 1
}

# Start the application
echo "🎯 Starting Gunicorn server..."
exec gunicorn \
    --bind "$WEB_APP_HOST:$WEB_APP_PORT" \
    --workers "$WORKERS" \
    --worker-class "$WORKER_CLASS" \
    --timeout "$TIMEOUT" \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --capture-output \
    --preload \
    "web_app:create_app()"