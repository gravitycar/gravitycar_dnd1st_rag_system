#!/usr/bin/bash

echo "================================================================================"
echo "Stopping D&D RAG System"
echo "================================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR"

# Stop Flask
echo "Step 1: Stopping Flask API..."
./scripts/stop_flask.sh
echo ""

# Stop ChromaDB
echo "Step 2: Stopping ChromaDB..."
pkill -f "chroma run"
sleep 1

# Verify ChromaDB stopped
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi
CHROMA_HOST_URL=${chroma_host_url:-http://localhost}
CHROMA_PORT=${chroma_host_port:-8060}

if curl -s ${CHROMA_HOST_URL}:${CHROMA_PORT}/api/v2/heartbeat > /dev/null 2>&1; then
    echo "✗ Failed to stop ChromaDB (still responding)"
else
    echo "✓ ChromaDB stopped successfully"
fi

echo ""
echo "================================================================================"
echo "✓ D&D RAG System stopped"
echo "================================================================================"
