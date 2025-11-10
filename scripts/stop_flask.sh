#!/usr/bin/bash

# Load environment variables from .env.dndchat file
# Try production path first (/home/gravityc/.env.dndchat), then local path (.env.dndchat)
if [ -f ~/.env.dndchat ]; then
    set -a
    source ~/.env.dndchat
    set +a
elif [ -f .env.dndchat ]; then
    set -a
    source .env.dndchat
    set +a
fi

FLASK_PORT=${FLASK_PORT:-5000}

# Check if Flask is running (try both HTTP and HTTPS)
if ! curl -s http://${FLASK_HOST}:${FLASK_PORT}/health > /dev/null 2>&1 && \
   ! curl -sk https://${FLASK_HOST}:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "Flask is not running"
    exit 0
fi

# Stop Flask (both flask run and gunicorn)
echo "Stopping Flask server..."
pkill -f "flask run" 2>/dev/null || true
pkill -f "gunicorn.*src.api:app" 2>/dev/null || true

# Wait a moment and verify
sleep 2

if curl -s http://${FLASK_HOST}:${FLASK_PORT}/health > /dev/null 2>&1 || \
   curl -sk https://${FLASK_HOST}:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "✗ Failed to stop Flask (still responding)"
    exit 1
else
    echo "✓ Flask stopped successfully"
fi
