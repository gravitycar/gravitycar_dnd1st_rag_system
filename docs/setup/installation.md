# Installation Guide

Complete setup instructions for the GravityCar D&D 1st Edition RAG System.

---

## System Requirements

### Hardware

**Minimum**:
- CPU: 4 cores
- RAM: 8 GB
- Disk: 10 GB free space

**Recommended**:
- CPU: 8+ cores (AMD Ryzen 9 / Intel i7 or better)
- RAM: 16 GB
- Disk: 20 GB SSD
- GPU: NVIDIA GPU with CUDA support (optional, 3-5x faster embedding)

### Software

- **Operating System**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows 10+ with WSL2
- **Python**: 3.10+ (tested with Python 3.12.3)
- **Git**: For cloning repository (optional)
- **Docker**: For ChromaDB (optional, can use pip install)
- **curl**: For testing ChromaDB connection

---

## Quick Start (Automated)

The fastest way to get started is using the automated setup script:

```bash
# 1. Navigate to project directory
cd /path/to/chroma

# 2. Run automated setup
./scripts/setup_venv.sh

# 3. Activate virtual environment
source venv/bin/activate

# 4. Verify installation
python --version       # Should be 3.10+
pip list | grep chroma # Should show chromadb 1.1.1
```

**That's it!** The script automatically:
- Checks Python version
- Creates virtual environment
- Installs all dependencies
- Verifies installation

---

## Manual Installation

If you prefer manual setup or need more control:

### Step 1: Verify Python Version

```bash
python3 --version
```

**Expected**: Python 3.10.0 or higher

If your Python is too old:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# macOS (using Homebrew)
brew install python@3.11

# Verify
python3.11 --version
```

### Step 2: Create Virtual Environment

```bash
# Navigate to project directory
cd /home/mike/projects/rag/chroma

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

**Verify activation**:
```bash
which python
# Should show: /path/to/chroma/venv/bin/python
```

### Step 3: Install Core Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt
```

**This installs**:
- `chromadb==1.1.1` - Vector database
- `openai==2.3.0` - OpenAI API client
- `sentence-transformers==5.1.1` - Embedding models
- `python-dotenv==1.1.1` - Environment variable management
- `docling==2.55.1` - PDF to markdown conversion

**Verify installation**:
```bash
pip list

# Should show:
# chromadb                 1.1.1
# openai                   2.3.0
# sentence-transformers    5.1.1
# ...
```

### Step 4: Install Development Tools (Optional)

For development and testing:

```bash
pip install -r requirements-dev.txt
```

**This installs**:
- `pytest>=8.3.4` - Testing framework
- `black>=25.1.0` - Code formatter
- `flake8>=7.1.2` - Linter
- `ipython>=8.32.0` - Interactive shell
- `mypy>=1.14.1` - Type checker

### Step 5: Download Embedding Model

The embedding model will download automatically on first use, but you can pre-download it:

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"
```

**Size**: ~420 MB  
**Location**: `~/.cache/torch/sentence_transformers/`

---

## Configuration

### Step 1: Create .env File

Create a `.env` file in the project root:

```bash
cd /home/mike/projects/rag/chroma
touch .env
```

### Step 2: Add Configuration

Edit `.env` with your configuration:

```bash
# OpenAI API Configuration (REQUIRED)
OPENAI_API_KEY=sk-your-api-key-here

# ChromaDB Configuration (OPTIONAL, defaults shown)
CHROMA_HOST=localhost
CHROMA_PORT=8060
```

**Get OpenAI API Key**:
1. Go to [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create new secret key
3. Copy key (starts with `sk-`)
4. Paste into `.env` file

**Security Notes**:
- ⚠️ **Never commit `.env` to version control**
- ⚠️ Keep your API key secret
- ⚠️ Use `.gitignore` to exclude `.env`

### Step 3: Verify Configuration

```bash
# Check .env file exists
ls -la .env

# Check API key is set
grep OPENAI_API_KEY .env
# Should show: OPENAI_API_KEY=sk-...
```

---

## ChromaDB Setup

See **[chromadb_setup.md](chromadb_setup.md)** for detailed ChromaDB installation and configuration.

**Quick version**:

```bash
# Option 1: Using Docker (recommended)
docker run -p 8060:8000 chromadb/chroma

# Option 2: Using provided script
./scripts/start_chroma.sh

# Option 3: Using pip (if chromadb installed)
chroma run --path ./chroma_data --port 8060

# Verify connection
curl http://localhost:8060/api/v1/heartbeat
# Should return: {}
```

---

## Verification

### Test Installation

Run the verification script:

```bash
# Test ChromaDB connection
python scripts/list_chromadb_collections.py

# Expected output:
# Connected to ChromaDB at localhost:8060
# Collections: [list of collections]
```

### Test Pipeline

If you have data already processed:

```bash
# Test query
python src/query/docling_query.py "What is a beholder?"

# Expected: Answer with page citations
```

If you need to process data first:

```bash
# 1. Chunk a book (if markdown exists)
python src/chunkers/monster_encyclopedia.py data/markdown/Monster_Manual_(1e).md

# 2. Embed chunks
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Monster_Manual_(1e).json \
  dnd_monster_manual

# 3. Query
python src/query/docling_query.py "Tell me about owlbears"
```

---

## Troubleshooting

### "Python version too old" Error

**Solution**: Install Python 3.10+

```bash
# Check current version
python3 --version

# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv

# macOS
brew install python@3.11

# Create venv with specific version
python3.11 -m venv venv
```

### "pip: command not found" Error

**Solution**: Install pip

```bash
# Ubuntu/Debian
sudo apt install python3-pip

# macOS
python3 -m ensurepip
```

### "ModuleNotFoundError: No module named 'chromadb'"

**Solution**: Activate virtual environment

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "OpenAI API key not found" Error

**Solution**: Check `.env` file

```bash
# Verify .env exists
ls -la .env

# Verify API key is set
cat .env | grep OPENAI_API_KEY

# If missing, create .env:
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

### "Cannot connect to ChromaDB" Error

**Solution**: Start ChromaDB

```bash
# Check if running
curl http://localhost:8060/api/v1/heartbeat

# If not running, start it
./scripts/start_chroma.sh
```

### "ImportError: cannot import name 'SentenceTransformer'"

**Solution**: Reinstall sentence-transformers

```bash
pip uninstall sentence-transformers
pip install sentence-transformers==5.1.1
```

### Virtual Environment Not Activating

**Linux/macOS**:
```bash
source venv/bin/activate
```

**Windows**:
```bash
venv\Scripts\activate
```

**If still not working**:
```bash
# Delete and recreate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Updating

### Update Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Update all packages
pip install --upgrade -r requirements.txt

# Or update specific package
pip install --upgrade chromadb
```

### Update Embedding Model

```bash
# Delete cached model
rm -rf ~/.cache/torch/sentence_transformers/

# Re-download on next use
python src/embedders/docling_embedder.py [args]
```

---

## Uninstallation

### Remove Virtual Environment

```bash
# Deactivate (if activated)
deactivate

# Remove virtual environment
rm -rf venv
```

### Remove ChromaDB Data

```bash
# Remove ChromaDB GUID directories
rm -rf /home/mike/projects/rag/chroma/[GUID directories]

# Remove ChromaDB metadata
rm -f /home/mike/projects/rag/chroma/chroma.sqlite3
```

### Remove Cached Models

```bash
# Remove sentence-transformers cache
rm -rf ~/.cache/torch/sentence_transformers/

# Remove Hugging Face cache (if used)
rm -rf ~/.cache/huggingface/
```

---

## Next Steps

After successful installation:

1. **[ChromaDB Setup](chromadb_setup.md)**: Configure ChromaDB server
2. **[Main README](../../README.md)**: Usage examples and workflow
3. **[Implementation Docs](../implementations/)**: Deep dives into algorithms

---

## Platform-Specific Notes

### Linux

**Dependencies**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-dev python3-pip python3-venv build-essential

# Fedora/RHEL
sudo dnf install python3-devel python3-pip gcc-c++
```

### macOS

**Dependencies**:
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install build tools
xcode-select --install
```

### Windows (WSL2)

**Setup WSL2**:
```powershell
# In PowerShell (as Administrator)
wsl --install
wsl --set-default-version 2
wsl --install -d Ubuntu
```

**Inside WSL**:
```bash
# Update packages
sudo apt update && sudo apt upgrade

# Install Python
sudo apt install python3.11 python3.11-venv python3-pip

# Follow Linux instructions above
```

---

## Development Setup

For contributing or advanced development:

### 1. Install Dev Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Configure Git Hooks (Optional)

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install
```

### 3. Configure IDE

**VS Code** (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true
}
```

**PyCharm**:
1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Select: `/path/to/chroma/venv/bin/python`

---

## Support

For issues:
1. Check **[Troubleshooting](#troubleshooting)** section above
2. Review **[ChromaDB Setup](chromadb_setup.md)** for database issues
3. Check GitHub Issues (if applicable)

---

**Package Name**: `gravitycar_dnd1st_rag_system`  
**Minimum Python**: 3.10  
**Last Updated**: 2025-01-XX  
**Version**: 1.0
