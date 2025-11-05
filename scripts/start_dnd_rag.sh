#!/usr/bin/bash

echo "================================================================================"
echo "Starting D&D RAG System"
echo "================================================================================"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR"

# Start ChromaDB
echo "Step 1: Starting ChromaDB..."
./scripts/start_chroma.sh
if [ $? -ne 0 ]; then
    echo "✗ Failed to start ChromaDB"
    exit 1
fi
echo ""

# Start Flask
echo "Step 2: Starting Flask API..."
./scripts/start_flask.sh
if [ $? -ne 0 ]; then
    echo "✗ Failed to start Flask"
    echo "  Stopping ChromaDB..."
    pkill -f "chroma run"
    exit 1
fi
echo ""

echo "================================================================================"
echo "✓ D&D RAG System started successfully"
echo "================================================================================"
echo ""
echo "Services:"
echo "  - ChromaDB: http://localhost:8060/api/v2/heartbeat"
echo "  - Flask API: http://localhost:5000/health"
echo ""
echo "Logs:"
echo "  - ChromaDB: chroma.log"
echo "  - Flask: flask.log"
echo ""
echo "To stop: ./scripts/stop_dnd_rag.sh"
echo "================================================================================"
