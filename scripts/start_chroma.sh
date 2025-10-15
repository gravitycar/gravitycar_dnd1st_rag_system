#!/usr/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Set defaults if not in .env
CHROMA_HOST_URL=${chroma_host_url:-http://localhost}
CHROMA_PORT=${chroma_host_port:-8060}
CHROMA_PATH=${chroma_data_path:-.}
LOG_FILE="chroma.log"

# Extract just the host from URL (remove http:// or https://)
CHROMA_HOST=$(echo ${CHROMA_HOST_URL} | sed 's~http[s]*://~~')

# Check if ChromaDB is already running
if curl -s ${CHROMA_HOST_URL}:${CHROMA_PORT}/api/v2/heartbeat > /dev/null 2>&1; then
    echo "ChromaDB is already running on ${CHROMA_HOST}:${CHROMA_PORT}"
    exit 0
fi

# Start ChromaDB as background process
echo "Starting ChromaDB server..."
echo "  Host: ${CHROMA_HOST}"
echo "  Port: ${CHROMA_PORT}"
echo "  Data path: ${CHROMA_PATH}"
nohup chroma run --host ${CHROMA_HOST} --port ${CHROMA_PORT} --path ${CHROMA_PATH} > ${LOG_FILE} 2>&1 &

# Wait for startup (give it 5 seconds)
sleep 5

# Verify it started
if curl -s ${CHROMA_HOST_URL}:${CHROMA_PORT}/api/v2/heartbeat > /dev/null 2>&1; then
    echo "✓ ChromaDB started successfully on ${CHROMA_HOST}:${CHROMA_PORT}"
    echo "  Logs: ${LOG_FILE}"
else
    echo "✗ Failed to start ChromaDB"
    echo "  Check logs: ${LOG_FILE}"
    exit 1
fi

