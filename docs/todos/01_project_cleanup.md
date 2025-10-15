# Project Cleanup TODO List

**Created**: October 15, 2025  
**Status**: Planning Phase  
**Priority**: High - Foundation for future development

---

## 1. File Organization & Directory Structure

### 1.1 Identify Files to Archive

**Current Issues:**
- Multiple experimental scripts from early development
- Mixed source files, data files, and documentation in root
- Obsolete conversion methods (pymupdf)

**Files to Archive:**

#### Obsolete Python Scripts (move to `archive/`):
- [ ] `chunk_monster_manual_docling.py` - **Superseded by**: `chunk_monster_encyclopedia.py`
- [ ] `embed_and_store_markdown.py` - **Superseded by**: `embed_docling.py`
- [ ] `embed_and_store_semantic.py` - **Superseded by**: `embed_docling.py`

#### Directories to Remove:
- [ ] `dndmarkdown/pymupdf/` - **Reason**: Docling produces better results, pymupdf was experimental

**Notes:**
- Archive directory already created at `archive/`
- Keep archived scripts for reference (they may be useful later)
- ChromaDB GUID directories will stay in root (see below)

#### ChromaDB GUID Directories:
These are ChromaDB's internal data storage directories. Each represents a collection.

**Strategy**: Leave GUID directories in place
- Project will eventually move to its own directory
- ChromaDB data will remain in `/home/mike/projects/rag/chroma/`
- This allows multiple projects to share the same ChromaDB instance

**Current GUID directories found:**
```
1601c5cc-29c5-4f3d-9e8f-cf135413dcc1/
236eaf52-b485-4724-92e1-f4cb859e9102/
34be7083-2abe-4d7f-8e6b-902746d651cb/
689d9343-c398-4b8e-b689-670607433655/
a2266aa9-97f0-4930-a682-3ec636da6232/
a282ad38-ffaf-4a0e-b9fa-1fc490d05d72/
cd83bf05-0793-4204-be31-60234f432ef3/
f8d76a4d-058b-4451-b1a3-d66b02f00645/
```

- [ ] Use `list_chromadb_collections.py` to identify which collections are in use
- [ ] Optionally clean up obsolete collections later (not part of this cleanup)

**Command to check collections:**
```bash
python list_chromadb_collections.py
```

#### Other Files to Keep:
- [ ] `README_DOCLING.md` - Will be integrated into main README (see Section 2.3)
- [ ] `.vscode/` - Keep (editor settings)
- [ ] `.github/` - Keep (if present)
- [ ] `.env` - Keep (contains API keys)
- [ ] `chroma.sqlite3` - Keep (ChromaDB metadata database)

---

### 1.2 Proposed Directory Structure

**Goal**: Organize source code, data, and documentation within current directory

**Current Working Directory**: `/home/mike/projects/rag/chroma/`

**Strategy**:
- Organize project files in place (eventually will move to new directory)
- Leave ChromaDB data in `/home/mike/projects/rag/chroma/` (shared resource)
- Clean separation of concerns: source, scripts, data, docs

```
/home/mike/projects/rag/chroma/              # Current location (ChromaDB host)
├── [GUID directories...]                     # ChromaDB collection data (stays here)
├── chroma.sqlite3                            # ChromaDB metadata (stays here)
├── .env                                      # Shared ChromaDB config (stays here)
│
├── src/                                      # Python package (will move with project)
│   ├── __init__.py
│   ├── chunkers/                             # Document chunking modules
│   │   ├── __init__.py
│   │   ├── monster_encyclopedia.py           # From: chunk_monster_encyclopedia.py
│   │   └── players_handbook.py               # From: chunk_players_handbook_docling.py
│   ├── embedders/                            # Embedding modules
│   │   ├── __init__.py
│   │   └── docling_embedder.py               # From: embed_docling.py
│   ├── query/                                # Query/RAG modules
│   │   ├── __init__.py
│   │   └── docling_query.py                  # From: query_docling.py
│   ├── converters/                           # PDF conversion utilities
│   │   ├── __init__.py
│   │   └── pdf_converter.py                  # From: convert_pdfs_to_markdown.py
│   └── utils/                                # General utilities
│       └── __init__.py
│
├── scripts/                                  # Executable scripts
│   ├── benchmark_models.py                   # From: root
│   ├── list_chromadb_collections.py          # From: root
│   ├── start_chroma.sh                       # From: root (rename)
│   ├── setup_docling.sh                      # From: root
│   └── setup_venv.sh                         # NEW - create virtual environment
│
├── data/                                     # All data files
│   ├── source_pdfs/                          # Original PDF files
│   ├── markdown/                             # Converted markdown from dndmarkdown/docling/
│   └── chunks/                               # Chunked JSON files from chunk_files/
│
├── docs/                                     # Documentation
│   ├── README.md                             # Documentation index
│   ├── implementation_notes/                 # Existing implementation docs
│   ├── early_notes/                          # Existing historical notes
│   ├── questions/                            # Existing questions log
│   ├── todos/                                # This file and related TODOs
│   ├── setup/                                # NEW - Setup guides
│   │   ├── installation.md
│   │   └── chromadb_setup.md
│   └── implementations/                      # NEW - Detailed implementation docs
│       ├── MonsterEncyclopediaChunker.md
│       ├── DoclingEmbedder.md
│       ├── DnDRAG.md
│       └── adaptive_filtering.md
│
├── tests/                                    # Test files (empty for now)
│   └── __init__.py
│
├── archive/                                  # Archived/obsolete code
│   ├── chunk_monster_manual_docling.py       # Superseded by chunk_monster_encyclopedia.py
│   ├── embed_and_store_markdown.py           # Superseded by embed_docling.py
│   └── embed_and_store_semantic.py           # Superseded by embed_docling.py
│
├── venv/                                     # Virtual environment (existing)
├── README.md                                 # NEW - Main project README
└── requirements.txt                          # NEW - Python dependencies
```

**Implementation Steps:**
- [ ] Create `src/` package structure with `__init__.py` files
- [ ] Move Python source files to `src/` (see section 3)
- [ ] Move scripts to `scripts/` directory
- [ ] Move `dndmarkdown/docling/` → `data/markdown/`
- [ ] Move `chunk_files/` → `data/chunks/`
- [ ] Move obsolete scripts to `archive/`
- [ ] Remove `dndmarkdown/pymupdf/` directory
- [ ] Create new documentation files
- [ ] Update all import paths in source files

---

## 2. Documentation Updates

### 2.1 Create Implementation Documentation

**Purpose**: Document each major class/module with usage examples

#### Files to Create in `docs/implementations/`:

- [ ] **MonsterEncyclopediaChunker.md**
  - Purpose and design philosophy
  - Monster vs Category detection algorithm
  - Statistics extraction strategy
  - Nested monster handling
  - Usage examples and CLI
  - Known limitations

- [ ] **PlayersHandbookChunker.md**
  - Table detection and extraction
  - Multi-column handling
  - Section hierarchy
  - Usage examples
  - (Create this when we implement it)

- [ ] **DoclingEmbedder.md**
  - Embedding model selection rationale (all-mpnet-base-v2)
  - Statistics prepending strategy
  - Metadata flattening
  - ChromaDB collection management
  - Usage examples

- [ ] **DnDRAG.md**
  - Query pipeline architecture
  - Entity-aware retrieval algorithm
  - Adaptive gap detection (distance threshold)
  - Context formatting strategies
  - OpenAI integration
  - Usage examples and CLI options

- [ ] **adaptive_filtering.md**
  - Gap detection algorithm explanation
  - Why skip first gap?
  - Distance threshold fallback
  - Constraint application (min 2, max k)
  - Performance examples with real queries
  - Tuning recommendations

---

### 2.3 Create Main README.md

**Purpose**: Project landing page with quick start and overview

**Special Note**: Integrate content from `README_DOCLING.md` into this main README

**Sections:**
- [ ] Project title and tagline
- [ ] What is this? (Brief description)
- [ ] Key features (include Docling conversion quality notes from README_DOCLING.md)
- [ ] Quick start guide
- [ ] Architecture overview (high-level)
- [ ] Technologies used (highlight Docling for PDF conversion)
- [ ] Project structure
- [ ] Usage examples (incorporate examples from README_DOCLING.md)
- [ ] Development setup
- [ ] ChromaDB connection info

**Content to Merge from README_DOCLING.md:**
- Docling conversion approach and benefits
- Quality comparison with other methods
- Specific usage examples for chunking and embedding
- Any troubleshooting notes

**Example Structure:**
```markdown
# GravityCar D&D 1st Edition RAG System

Retrieval-Augmented Generation system for Advanced Dungeons & Dragons 1st Edition rulebooks.

## What Is This?

A semantic search and question-answering system that allows you to query AD&D 1st Edition rules using natural language. Powered by ChromaDB for vector storage, OpenAI for LLM responses, and custom chunking strategies optimized for D&D content structure.

## Key Features

- **Intelligent Chunking**: Custom chunkers for Monster Manual (category-aware) and Player's Handbook (table-aware)
- **High-Quality PDF Conversion**: Uses Docling for superior markdown conversion with table preservation
- **Entity-Aware Retrieval**: Automatically detects comparison queries ("X vs Y") and ensures both entities are retrieved
- **Adaptive Gap Detection**: Returns 2-10 results based on semantic similarity drop-offs, not arbitrary k values
- **Smart Category Context**: Nested monsters (e.g., specific demon types) automatically include parent category information
- **Statistics Integration**: Monster stats embedded in searchable text for LLM access

## Quick Start

[Installation, setup, basic usage examples]

## Architecture

[High-level diagram and explanation]
```

**After Merging:**
- [ ] Delete or archive `README_DOCLING.md`

---

### 2.4 Create Setup Documentation

**Files to Create in `docs/setup/`:**

- [ ] **installation.md**
  - Prerequisites (Python 3.10+, ChromaDB, OpenAI API key)
  - Virtual environment setup
  - Dependencies installation
  - ChromaDB installation and configuration
  - Environment variables (.env file)
  - Verification steps

- [ ] **chromadb_setup.md**
  - ChromaDB installation methods
  - Starting ChromaDB as background process
  - Connection configuration (shared ChromaDB instance)
  - Collection management
  - Backup and restore procedures
  - Troubleshooting

---

### 2.5 Create `copilot_instructions.md`

**Purpose**: Provide GitHub Copilot with comprehensive project context

**⚠️ NOTE**: This will be handled by Mike personally (move to end of task list)

**Content to Include:**
- [ ] Project overview and goals
- [ ] Key technologies: ChromaDB, OpenAI, Sentence Transformers, Docling
- [ ] Code architecture and module purposes
- [ ] Naming conventions and code style
- [ ] Common patterns used (RAG pipeline, chunking strategies, gap detection)
- [ ] Current active features (entity-aware retrieval, adaptive filtering)
- [ ] Development guidelines and best practices

**Location**: `docs/copilot_instructions.md`

**Reference existing implementation notes:**
- `docs/implementation_notes/` (review and incorporate)
- `docs/early_notes/` (historical context)

---

## 3. Move Python Source Files

### 3.1 Identify All Python Dependencies

**Current Dependencies** (based on imports in codebase):

**Core Dependencies:**
```
chromadb>=0.4.0           # Vector database
openai>=1.0.0             # OpenAI API client
sentence-transformers      # Embedding models
python-dotenv             # Environment variable management
```

**Data Processing:**
```
docling                   # PDF to Markdown conversion (best quality)
pymupdf                   # Alternative PDF parser (experimental)
```

**Standard Library Used** (no install needed):
```python
json, re, pathlib, os, sys, argparse
from typing import List, Dict, Any, Tuple, Optional
```

**Development/Testing** (optional):
```
pytest                    # Testing framework
black                     # Code formatting
flake8                    # Linting
```

- [ ] Create `requirements.txt` with all dependencies
- [ ] Create `requirements-dev.txt` for development dependencies
- [ ] Document minimum Python version (3.10+)

---

### 3.2 Python Files to Organize

**Production Source Files** (move to `src/`):

**Chunkers** → `src/chunkers/`:
- [ ] `chunk_monster_encyclopedia.py` → `monster_encyclopedia.py`
  - Rename class if needed
  - Update imports
  - Make module importable

- [ ] `chunk_players_handbook_docling.py` → `players_handbook.py`
  - Keep for future refactoring
  - Update imports
  - Make module importable

**Embedders** → `src/embedders/`:
- [ ] `embed_docling.py` → `docling_embedder.py`
  - Update imports
  - Make module importable

**Query/RAG** → `src/query/`:
- [ ] `query_docling.py` → `docling_query.py`
  - Update imports
  - Ensure CLI still works

**Converters** → `src/converters/`:
- [ ] `convert_pdfs_to_markdown.py` → `pdf_converter.py`
  - Still relevant (more books will come)
  - Extract reusable functions
  - Make module importable

**Scripts** (move to `scripts/`):
- [ ] `benchmark_models.py` → `scripts/benchmark_models.py`
- [ ] `list_chromadb_collections.py` → `scripts/list_chromadb_collections.py`
- [ ] `start_chroma.sh` → `scripts/start_chroma.sh`
- [ ] `setup_docling.sh` → `scripts/setup_docling.sh`
- [ ] Create `scripts/setup_venv.sh` (new)

---

### 3.3 Create Virtual Environment Setup Script

**File**: `scripts/setup_venv.sh`

**Purpose**: Automate creation of virtual environment with all dependencies

```bash
#!/bin/bash
# Setup virtual environment for D&D RAG System

# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (optional)
read -p "Install development dependencies? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -r requirements-dev.txt
fi

echo "✅ Virtual environment setup complete!"
echo "To activate: source venv/bin/activate"
```

- [ ] Create `scripts/setup_venv.sh`
- [ ] Make executable: `chmod +x scripts/setup_venv.sh`
- [ ] Test on clean system

---

### 3.4 Update Existing ChromaDB Script

**Note**: `start_chroma.sh` already exists and will be moved to `scripts/`

**Tasks:**
- [ ] Move `start_chroma.sh` → `scripts/start_chroma.sh`
- [ ] Verify script uses correct paths for shared ChromaDB instance
- [ ] Update path references if needed (should point to `/home/mike/projects/rag/chroma/`)
- [ ] Make executable: `chmod +x scripts/*.sh`
- [ ] Document usage in `docs/setup/chromadb_setup.md`

---

### 3.5 Update Import Paths

**After moving files, update all imports:**

**Example transformation:**
```python
# OLD (before reorganization)
from embed_docling import DoclingEmbedder

# NEW (after reorganization)
from src.embedders.docling_embedder import DoclingEmbedder
```

**Files to Update:**
- [ ] All moved source files
- [ ] All script wrappers
- [ ] Any test files
- [ ] Documentation examples

**Strategy:**
- Use relative imports within package: `from ..embedders import DoclingEmbedder`
- Use absolute imports in scripts: `from src.embedders.docling_embedder import DoclingEmbedder`
- Add `src/` to Python path in scripts if needed

---

## 4. Create requirements.txt

**File**: `requirements.txt`

```
# Core dependencies
chromadb>=0.4.22
openai>=1.3.0
sentence-transformers>=2.2.2
python-dotenv>=1.0.0

# PDF processing
docling>=1.0.0

# Optional: Alternative PDF parser
pymupdf>=1.23.0
```

**File**: `requirements-dev.txt`

```
# Development dependencies
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.1.0
ipython>=8.15.0
```

- [ ] Create `requirements.txt`
- [ ] Create `requirements-dev.txt`
- [ ] Test installation: `pip install -r requirements.txt`
- [ ] Document any platform-specific requirements

---

## 5. Priority Order for Execution

**Phase 1: Create Package Structure** (Foundation)
1. [ ] Create `__init__.py` files in all `src/` subdirectories
2. [ ] Create empty `tests/__init__.py`
3. [ ] Verify directory structure is complete

**Phase 2: Move Data Files** (Low Risk)
4. [ ] Move `dndmarkdown/docling/` → `data/markdown/`
5. [ ] Move `chunk_files/` contents → `data/chunks/`
6. [ ] Remove `dndmarkdown/pymupdf/` directory
7. [ ] Verify data file locations

**Phase 3: Move Scripts** (Low Risk)
8. [ ] Move `benchmark_models.py` → `scripts/`
9. [ ] Move `list_chromadb_collections.py` → `scripts/`
10. [ ] Move `start_chroma.sh` → `scripts/`
11. [ ] Move `setup_docling.sh` → `scripts/`
12. [ ] Make all scripts executable: `chmod +x scripts/*.sh`

**Phase 4: Archive Obsolete Files**
13. [ ] Move `chunk_monster_manual_docling.py` → `archive/`
14. [ ] Move `embed_and_store_markdown.py` → `archive/`
15. [ ] Move `embed_and_store_semantic.py` → `archive/`

**Phase 5: Move Source Code** (Higher Risk - Update Imports)
16. [ ] Move `convert_pdfs_to_markdown.py` → `src/converters/pdf_converter.py`
17. [ ] Move `chunk_monster_encyclopedia.py` → `src/chunkers/monster_encyclopedia.py`
18. [ ] Move `chunk_players_handbook_docling.py` → `src/chunkers/players_handbook.py`
19. [ ] Move `embed_docling.py` → `src/embedders/docling_embedder.py`
20. [ ] Move `query_docling.py` → `src/query/docling_query.py`
21. [ ] Update all import statements in moved files
22. [ ] Test each moved file after updating imports

**Phase 6: Create Dependencies**
23. [ ] Create `requirements.txt`
24. [ ] Create `requirements-dev.txt`
25. [ ] Create `scripts/setup_venv.sh`

**Phase 7: Documentation**
26. [ ] Integrate `README_DOCLING.md` into main `README.md`
27. [ ] Create implementation docs in `docs/implementations/`
28. [ ] Create setup guides in `docs/setup/`
29. [ ] Update `docs/README.md` with new structure

**Phase 8: Testing**
30. [ ] Test chunking pipeline: `python src/chunkers/monster_encyclopedia.py`
31. [ ] Test embedding pipeline: `python src/embedders/docling_embedder.py`
32. [ ] Test query pipeline: `python src/query/docling_query.py`
33. [ ] Verify all imports work correctly
34. [ ] Test scripts in `scripts/` directory

**Phase 9: Final Tasks** (Mike's Responsibility)
35. [ ] Create `docs/copilot_instructions.md` (Mike will handle personally)
36. [ ] Review and consolidate all documentation
37. [ ] Initialize git repository (after cleanup complete)

---

## Notes and Considerations

### Package Name
- **Package Name**: `gravitycar_dnd1st_rag_system`
- Use in `__init__.py` files and imports
- Future: Consider adding `setup.py` for installable package
  - Would allow: `pip install -e .` for development
  - Makes imports cleaner: `from gravitycar_dnd1st_rag_system import chunkers`

### ChromaDB Strategy
- **Keep GUID directories in current location** (`/home/mike/projects/rag/chroma/`)
- Project files will eventually move to their own directory
- ChromaDB remains as shared resource for multiple projects
- Connection string in `.env` should point to shared ChromaDB location

### Testing Strategy
- Tests directory created but empty
- Establishing comprehensive test strategy is out of scope
- Future: Add pytest, create test files as needed

### Backwards Compatibility
- Keep old scripts in `archive/` for reference
- Document changes in README
- No need for symlinks (clean break)

### Future Enhancements
- Add logging configuration
- Add configuration file (YAML/TOML) for settings
- Add Docker support for easy deployment
- Add web interface
- Create installable package with `setup.py`

---

## Questions Resolved ✅

1. **ChromaDB Collections**: ✅ **Leave GUID directories in place**
   - Project will move to its own directory eventually
   - ChromaDB data stays in `/home/mike/projects/rag/chroma/` as shared resource
   - Use `scripts/list_chromadb_collections.py` to identify collections

2. **Script Status**: ✅ **Archive obsolete, keep relevant**
   - Archive: `chunk_monster_manual_docling.py`, `embed_and_store_markdown.py`, `embed_and_store_semantic.py`
   - Keep: `chunk_monster_encyclopedia.py`, `chunk_players_handbook_docling.py`, `convert_pdfs_to_markdown.py`
   - Move: `benchmark_models.py` → `scripts/`

3. **Markdown Data**: ✅ **Remove pymupdf, keep docling**
   - `docling/` is production quality → move to `data/markdown/`
   - `pymupdf/` was experimental → delete directory

4. **Testing**: ✅ **Create empty tests directory**
   - `tests/` directory created
   - Test strategy out of scope for this cleanup
   - Add tests as needed in future

5. **Package Name**: ✅ **gravitycar_dnd1st_rag_system**
   - Descriptive and unique
   - Use in `__init__.py` files and documentation

---

**Last Updated**: October 15, 2025  
**Next Steps**: Review this plan, answer questions, begin Phase 1
