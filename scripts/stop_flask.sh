#!/usr/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

FLASK_PORT=${FLASK_PORT:-5000}

# Check if Flask is running
if ! curl -s http://localhost:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "Flask is not running"
    exit 0
fi

# Stop Flask
echo "Stopping Flask server..."
pkill -f "flask run"

# Wait a moment and verify
sleep 1

if curl -s http://localhost:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "✗ Failed to stop Flask (still responding)"
    exit 1
else
    echo "✓ Flask stopped successfully"
fi
