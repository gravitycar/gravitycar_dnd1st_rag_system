#!/bin/bash
# Quick setup script for D&D RAG system

echo "=================================="
echo "D&D RAG System - Package Installer"
echo "=================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install packages
echo ""
echo "Installing required packages..."
echo ""

pip install sentence-transformers chromadb-client openai python-dotenv

echo ""
echo "=================================="
echo "Verifying installation..."
echo "=================================="
echo ""

# Test imports
python3 << 'EOF'
try:
    import sentence_transformers
    print("✓ sentence-transformers installed")
except ImportError:
    print("✗ sentence-transformers NOT installed")

try:
    import chromadb
    print("✓ chromadb installed")
except ImportError:
    print("✗ chromadb NOT installed")

try:
    import openai
    print("✓ openai installed")
except ImportError:
    print("✗ openai NOT installed")

try:
    import dotenv
    print("✓ python-dotenv installed")
except ImportError:
    print("✗ python-dotenv NOT installed")
EOF

echo ""
echo "=================================="
echo "Checking ChromaDB connection..."
echo "=================================="

# Check ChromaDB
if curl -s http://localhost:8060/api/v1/heartbeat > /dev/null 2>&1; then
    echo "✓ ChromaDB is running on localhost:8060"
else
    echo "✗ ChromaDB is NOT running"
    echo ""
    echo "To start ChromaDB, run:"
    echo "  docker run -p 8060:8000 chromadb/chroma"
    echo ""
fi

echo ""
echo "=================================="
echo "Checking .env file..."
echo "=================================="

if [ -f ".env" ]; then
    if grep -q "gravitycar_openai_api_key" .env; then
        echo "✓ .env file exists with OpenAI API key"
    else
        echo "✗ .env file exists but OpenAI key not found"
    fi
else
    echo "✗ .env file not found"
fi

echo ""
echo "=================================="
echo "Setup complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. python chunk_players_handbook_docling.py dndmarkdown/docling/good_pdfs/Players_Handbook_(1e).md"
echo "  2. python embed_docling.py chunks_players_handbook.json dnd_players_handbook"
echo "  3. python query_docling.py dnd_players_handbook --test"
echo ""
