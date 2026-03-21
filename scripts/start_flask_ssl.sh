#!/usr/bin/bash
################################################################################
# Start Flask with HTTPS support using gunicorn
################################################################################

# Load environment variables from .env file
if [ -f ~/.env.dndchat ]; then
    set -a
    source ~/.env.dndchat
    set +a
fi

# Set defaults if not in .env
FLASK_HOST=${FLASK_HOST:-0.0.0.0}
FLASK_PORT=${FLASK_PORT:-5000}
FLASK_ENV=${FLASK_ENV:-production}
LOG_FILE="flask.log"
WORKERS=${GUNICORN_WORKERS:-4}

# SSL Certificate paths (adjust these for Hurricane Electric)
SSL_CERT=${SSL_CERT_PATH:-"/etc/ssl/certs/www.gravitycar.com.cert.2025-09-19T04_50_28"}
SSL_KEY=${SSL_KEY_PATH:-"/home/gravityc/.certs/gravityc.pem"}

# Check if Flask is already running
# Use -k flag to skip SSL verification for self-signed certs
if curl -sk https://${FLASK_HOST}:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "Flask is already running on ${FLASK_HOST}:${FLASK_PORT}"
    exit 0
fi

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "✗ Virtual environment not found. Run ./scripts/setup_venv.sh first"
    exit 1
fi

source venv/bin/activate

# Check if SSL certificates exist
if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
    echo "⚠️  SSL certificates not found at:"
    echo "    Cert: $SSL_CERT"
    echo "    Key:  $SSL_KEY"    https://dndchat.gravitycar.com:5000/health
    echo ""
    echo "Running in HTTP mode (development only)"
    echo "To enable HTTPS, set SSL_CERT_PATH and SSL_KEY_PATH in .env"
    
    # Run without SSL
    nohup gunicorn \
        --bind ${FLASK_HOST}:${FLASK_PORT} \
        --workers ${WORKERS} \
        --timeout 120 \
        --access-logfile ${LOG_FILE} \
        --error-logfile ${LOG_FILE} \
        --log-level info \
        src.api:app > ${LOG_FILE} 2>&1 &
else
    echo "Starting Flask server with HTTPS..."
    echo "  Host: ${FLASK_HOST}"
    echo "  Port: ${FLASK_PORT}"
    echo "  Workers: ${WORKERS}"
    echo "  SSL Cert: ${SSL_CERT}"
    echo "  SSL Key: ${SSL_KEY}"
    
    # Run with SSL
    nohup gunicorn \
        --bind ${FLASK_HOST}:${FLASK_PORT} \
        --workers ${WORKERS} \
        --timeout 120 \
        --certfile ${SSL_CERT} \
        --keyfile ${SSL_KEY} \
        --access-logfile ${LOG_FILE} \
        --error-logfile ${LOG_FILE} \
        --log-level info \
        src.api:app > ${LOG_FILE} 2>&1 &
fi

# Wait for startup
sleep 3

# Verify it started (use hostname for health check since gunicorn binds to FLASK_HOST)
# Try HTTPS first (with -k to skip cert verification for self-signed certs)
if curl -sk https://${FLASK_HOST}:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "✓ Flask started successfully with HTTPS on ${FLASK_HOST}:${FLASK_PORT}"
    echo "  Logs: ${LOG_FILE}"
    echo "  Health: https://${FLASK_HOST}:${FLASK_PORT}/health"
# Fall back to HTTP
elif curl -s http://${FLASK_HOST}:${FLASK_PORT}/health > /dev/null 2>&1; then
    echo "✓ Flask started successfully with HTTP on ${FLASK_HOST}:${FLASK_PORT}"
    echo "  Logs: ${LOG_FILE}"
    echo "  Health: http://${FLASK_HOST}:${FLASK_PORT}/health"
else
    echo "✗ Failed to start Flask"
    echo "Check logs: tail -50 ${LOG_FILE}"
    exit 1
fi
