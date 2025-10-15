#!/bin/bash
# Setup virtual environment for GravityCar D&D 1st Edition RAG System
#
# This script creates a Python virtual environment and installs all dependencies.
# Run from the project root directory.
#
# Usage:
#   ./scripts/setup_venv.sh

set -e  # Exit on error

echo "========================================"
echo "Virtual Environment Setup"
echo "GravityCar D&D 1st Edition RAG System"
echo "========================================"
echo

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found!"
    echo "   Please run this script from the project root directory."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "📍 Detected Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "❌ Error: Python 3.10 or higher is required!"
    echo "   You have Python $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python version OK"
echo

# Check if venv already exists
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists at ./venv/"
    read -p "   Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing venv..."
        rm -rf venv
    else
        echo "   Keeping existing venv."
        echo "   To use it: source venv/bin/activate"
        exit 0
    fi
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
echo "✅ Virtual environment created"
echo

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ pip upgraded"
echo

# Install core dependencies
echo "📚 Installing core dependencies from requirements.txt..."
pip install -r requirements.txt
echo "✅ Core dependencies installed"
echo

# Ask about dev dependencies
read -p "📦 Install development dependencies? (pytest, black, flake8, etc.) (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📚 Installing development dependencies from requirements-dev.txt..."
    pip install -r requirements-dev.txt
    echo "✅ Development dependencies installed"
else
    echo "⏭️  Skipping development dependencies"
fi
echo

# Summary
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo
echo "Virtual environment created at: ./venv/"
echo
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo
echo "To deactivate:"
echo "  deactivate"
echo
echo "Installed packages:"
pip list --format=columns | head -n 20
echo "  ... (run 'pip list' to see all)"
echo
