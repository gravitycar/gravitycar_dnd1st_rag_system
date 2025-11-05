#!/usr/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Set defaults if not in .env
FLASK_HOST=${FLASK_HOST:-0.0.0.0}
FLASK_PORT=${FLASK_PORT:-5000}
FLASK_ENV=${FLASK_ENV:-development}
LOG_FILE="flask.log"

# Check if Flask is already running
if curl -s http://localhost:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "Flask is already running on ${FLASK_HOST}:${FLASK_PORT}"
    exit 0
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "✗ Virtual environment not found. Run ./scripts/setup_venv.sh first"
    exit 1
fi

source venv/bin/activate

# Set Flask app location
export FLASK_APP=src/api.py

# Start Flask as background process
echo "Starting Flask server..."
echo "  Host: ${FLASK_HOST}"
echo "  Port: ${FLASK_PORT}"
echo "  Environment: ${FLASK_ENV}"
echo "  App: ${FLASK_APP}"
nohup flask run --host ${FLASK_HOST} --port ${FLASK_PORT} > ${LOG_FILE} 2>&1 &

# Wait for startup (give it 3 seconds)
sleep 3

# Verify it started
if curl -s http://localhost:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "✓ Flask started successfully on ${FLASK_HOST}:${FLASK_PORT}"
    echo "  Logs: ${LOG_FILE}"
    echo "  Health: http://localhost:${FLASK_PORT}/health"
else
    echo "✗ Failed to start Flask"
    echo "  Check logs: ${LOG_FILE}"
    exit 1
fi
