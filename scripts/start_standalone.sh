#!/bin/bash
set -e

echo "=== FortiGate Nextrade Standalone Mode ==="
echo "No external dependencies required"
echo "All configurations embedded"
echo ""

# Initialize directories if they don't exist
mkdir -p /app/logs /app/temp 2>/dev/null || true

# Set secure permissions
chmod 755 /app/src 2>/dev/null || true
chmod 777 /app/logs /app/temp 2>/dev/null || true

# Generate runtime secret key if not set
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
    echo "Generated runtime secret key"
fi

# Start embedded mock server in background (if needed)
if [ "$APP_MODE" = "test" ] || [ "$ENABLE_MOCK_SERVER" = "true" ]; then
    echo "Starting embedded mock server..."
    python /app/src/utils/mock_server.py &
    MOCK_PID=$!
    echo "Mock server started with PID: $MOCK_PID"
fi

# Health check before starting
echo "Running pre-flight checks..."
cd /app/src
if python -c "import sys; sys.path.insert(0, '/app/src'); from web_app import create_app; app = create_app(); print('✅ Application ready')"; then
    echo "✅ Pre-flight checks passed"
else
    echo "❌ Pre-flight checks failed"
    exit 1
fi

# Start the application
echo "Starting application on port $WEB_APP_PORT..."
cd /app/src

# For production, use gunicorn
if [ "$APP_MODE" = "production" ]; then
    exec gunicorn \
        --bind $WEB_APP_HOST:$WEB_APP_PORT \
        --workers $WORKERS \
        --worker-class $WORKER_CLASS \
        --timeout $TIMEOUT \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        "web_app:create_app()"
else
    # For development/test, use Flask directly
    exec python main.py --web
fi