# Phase 6: Create Dependencies - Summary

**Date**: October 15, 2025  
**Status**: ✅ COMPLETE

---

## Files Created

### 1. `requirements.txt` ✅
**Location**: `/home/mike/projects/rag/chroma/requirements.txt`

**Contents**:
- **Vector Database**: chromadb==1.1.1
- **AI/ML Services**: openai==2.3.0, sentence-transformers==5.1.1
- **Configuration**: python-dotenv==1.1.1
- **PDF Processing**: docling==2.55.1 (+ dependencies)
- **Optional**: PyMuPDF==1.26.4, pymupdf4llm==0.0.27

**Version Strategy**: Pinned to exact versions currently in use for reproducibility

---

### 2. `requirements-dev.txt` ✅
**Location**: `/home/mike/projects/rag/chroma/requirements-dev.txt`

**Contents**:
- **Testing**: pytest>=7.4.0, pytest-cov>=4.1.0
- **Formatting**: black>=23.0.0
- **Linting**: flake8>=6.1.0
- **Development**: ipython>=8.15.0, mypy>=1.5.0, pip-tools>=7.3.0

**Version Strategy**: Minimum versions (>=) for flexibility

---

### 3. `scripts/setup_venv.sh` ✅
**Location**: `/home/mike/projects/rag/chroma/scripts/setup_venv.sh`

**Features**:
- ✅ Python version check (requires 3.10+)
- ✅ Checks if venv already exists (asks to recreate)
- ✅ Creates virtual environment
- ✅ Upgrades pip
- ✅ Installs core dependencies from requirements.txt
- ✅ Prompts for optional dev dependencies
- ✅ Shows summary of installed packages
- ✅ Executable permissions set

---

## How to Use

### Install Dependencies in Existing Environment

```bash
# Activate your virtual environment first
source venv/bin/activate

# Install core dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

---

### Create Fresh Environment with Script

```bash
# From project root
./scripts/setup_venv.sh
```

**The script will:**
1. Check Python version (3.10+ required)
2. Check if venv exists (ask to recreate if it does)
3. Create virtual environment at `./venv/`
4. Upgrade pip
5. Install core dependencies
6. Ask if you want dev dependencies
7. Show summary

---

## Dependency Details

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| chromadb | 1.1.1 | Vector database for embeddings |
| openai | 2.3.0 | OpenAI API client for LLM |
| sentence-transformers | 5.1.1 | Embedding model (all-mpnet-base-v2) |
| python-dotenv | 1.1.1 | Load .env file configuration |
| docling | 2.55.1 | High-quality PDF to Markdown conversion |
| docling-core | 2.48.4 | Docling core functionality |
| docling-ibm-models | 3.9.1 | Docling IBM model implementations |
| docling-parse | 4.5.0 | Docling parsing utilities |
| PyMuPDF | 1.26.4 | Alternative PDF processing (experimental) |
| pymupdf4llm | 0.0.27 | PyMuPDF for LLM applications |

### Development Dependencies

| Package | Min Version | Purpose |
|---------|-------------|---------|
| pytest | 7.4.0 | Unit testing framework |
| pytest-cov | 4.1.0 | Test coverage reporting |
| black | 23.0.0 | Code formatting |
| flake8 | 6.1.0 | Code linting |
| ipython | 8.15.0 | Enhanced Python shell |
| mypy | 1.5.0 | Static type checking |
| pip-tools | 7.3.0 | Dependency management |

---

## Python Version Requirement

**Minimum**: Python 3.10

**Rationale**:
- Modern typing features used in codebase
- Better performance
- Required by some dependencies (e.g., docling)

**Current Environment**: Python 3.12.3 ✅

---

## Version Pinning Strategy

### Core Dependencies (requirements.txt)
- **Pinned to exact versions** (==)
- Ensures reproducible builds
- Matches currently working environment
- Update manually when needed

### Dev Dependencies (requirements-dev.txt)
- **Minimum versions** (>=)
- Allows flexibility for development tools
- Won't break if newer versions available
- Less critical for reproducibility

---

## Next Steps

### Verify Installation

To test that all dependencies are correctly installed:

```bash
# Activate venv
source venv/bin/activate

# Check Python version
python --version  # Should be 3.10+

# Verify core packages
python -c "import chromadb; print('chromadb:', chromadb.__version__)"
python -c "import openai; print('openai:', openai.__version__)"
python -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers: OK')"
python -c "from docling.document_converter import DocumentConverter; print('docling: OK')"

# Quick test
python src/query/docling_query.py --help
```

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'X'`  
**Solution**: Make sure virtual environment is activated: `source venv/bin/activate`

**Issue**: Python version too old  
**Solution**: Install Python 3.10+ and recreate venv: `python3.10 -m venv venv`

**Issue**: pip install fails  
**Solution**: Upgrade pip: `pip install --upgrade pip`

**Issue**: Docling installation fails  
**Solution**: May need system dependencies. Check Docling documentation.

---

## Phase 6 Checklist

- [x] Create `requirements.txt` with exact versions
- [x] Create `requirements-dev.txt` with development tools
- [x] Create `scripts/setup_venv.sh` automation script
- [x] Make setup script executable
- [x] Verify all files created correctly
- [x] Document usage and troubleshooting

---

## Phase 6 Status: ✅ COMPLETE

All dependency files created successfully!

**Next**: Phase 7 (Documentation)
