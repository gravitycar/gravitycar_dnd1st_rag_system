# Project Cleanup - Summary (UPDATED)

## What I've Created

I've created a comprehensive cleanup plan in `docs/todos/` with the following files:

### 1. Main TODO Document
**File**: `docs/todos/01_project_cleanup.md` (~5,200 lines, UPDATED)

**Sections**:
1. **File Organization & Directory Structure**
   - Identifies files to archive (not delete)
   - Proposes organized directory structure in current location
   - ChromaDB GUID directories stay in place (shared resource)
   
2. **Documentation Updates**
   - Implementation docs for each major class
   - Main README.md (integrating README_DOCLING.md)
   - Setup documentation guides
   - copilot_instructions.md (moved to Phase 9, Mike will handle)

3. **Move Python Source Files**
   - Complete dependency list
   - File-by-file reorganization plan with new locations
   - Package name: `gravitycar_dnd1st_rag_system`
   - Import path updates

4. **Priority Execution Order**
   - 9 phases (was 7)
   - 37 specific tasks in logical sequence
   - Phases ordered by risk (data → scripts → source code → docs)

5. **Questions Resolved**
   - All 5 original questions answered ✅
   - Package name, testing strategy, file status all clarified

### 2. Quick Checklist
**File**: `docs/todos/00_quick_checklist.md`

Condensed version for quick reference during implementation.

### 3. Helper Script
**File**: `list_chromadb_collections.py`

Script to:
- List all ChromaDB collections with UUIDs
- Identify which GUID directories are in use
- Mark obsolete directories for deletion

## Key Findings

### Python Dependencies Identified
```
Core:
- chromadb>=0.4.22
- openai>=1.3.0
- sentence-transformers>=2.2.0
- python-dotenv>=1.0.0

Data Processing:
- docling>=1.0.0
- pymupdf>=1.23.0 (optional/experimental)

Development:
- pytest, black, flake8
```

### Files to Archive (UPDATED)
- `chunk_monster_manual_docling.py` → `archive/` (superseded by `chunk_monster_encyclopedia.py`)
- `embed_and_store_markdown.py` → `archive/` (superseded by `embed_docling.py`)
- `embed_and_store_semantic.py` → `archive/` (superseded by `embed_docling.py`)
- `dndmarkdown/pymupdf/` → DELETE (docling produces better results)

### Files to Keep & Organize (UPDATED)
- `convert_pdfs_to_markdown.py` → `src/converters/` (still relevant for future books)
- `chunk_players_handbook_docling.py` → `src/chunkers/` (keep for future refactoring)
- `benchmark_models.py` → `scripts/` (useful utility)

### ChromaDB Strategy (UPDATED)
- **Leave GUID directories in place** in `/home/mike/projects/rag/chroma/`
- Project files will eventually move to their own directory
- ChromaDB remains as shared resource

### Proposed Directory Structure (UPDATED)
```
/home/mike/projects/rag/chroma/
├── [GUID directories...]  # ChromaDB data (stays here)
├── chroma.sqlite3         # ChromaDB metadata (stays here)
├── src/                   # Python package (will move with project)
│   ├── chunkers/
│   ├── embedders/
│   ├── query/
│   └── utils/
├── scripts/              # CLI wrappers & management
├── data/                 # PDFs, markdown, chunks
├── chroma_data/          # ChromaDB storage
├── docs/                 # All documentation
├── tests/                # Test files
├── archive/              # Obsolete code
└── venv/                 # Virtual environment
```

## Immediate Next Steps (UPDATED)

### All Questions Resolved ✅
All 5 original questions have been answered:
- ✅ Package name: `gravitycar_dnd1st_rag_system`
- ✅ ChromaDB collections: Leave GUID directories in place
- ✅ Script status: Archive obsolete, keep relevant
- ✅ Markdown data: Remove pymupdf, keep docling
- ✅ Testing: Empty tests/ directory created

### Ready to Implement:
Follow the 9 phases in priority order:
1. Create package structure (`__init__.py` files)
2. Move data files (low risk)
3. Move scripts (low risk)
4. Archive obsolete files
5. Move source code (update imports - higher risk)
6. Create dependencies (requirements.txt)
7. Documentation
8. Testing
9. Final tasks (copilot instructions - Mike handles)

## What I Did NOT Do (As Requested)

✅ Did not implement any cleanup  
✅ Did not delete any files  
✅ Did not move any files  
✅ Only created/updated planning documents

## Key Changes from Original Plan

1. **No Git** - Removed all git references (repo will be created after cleanup)
2. **ChromaDB in Place** - GUID directories stay in current location (shared resource)
3. **Package Name** - Decided on `gravitycar_dnd1st_rag_system`
4. **Archive, Don't Delete** - Obsolete files moved to `archive/`, not deleted
5. **Keep Converters** - `convert_pdfs_to_markdown.py` still relevant for future books
6. **Move benchmark_models.py** - Goes to `scripts/`, not `archive/`
7. **Copilot Instructions** - Moved to Phase 9, Mike will handle personally

## Recommendations

### Start With Phase 1:
1. Create `__init__.py` files in all `src/` subdirectories
2. Create `tests/__init__.py`
3. Verify directory structure

### Then Proceed:
- Follow phases 2-9 in order
- Test after each phase
- No need for git commits between phases (repo doesn't exist yet)

### Consider Later:
- Creating a `setup.py` for installable package
- Adding logging configuration
- Adding configuration file (YAML) for settings
- Docker support for deployment

### Priority:
- **High**: Directory structure, source organization, documentation
- **Medium**: Scripts, testing, cleanup
- **Low**: Advanced features (Docker, CI/CD)

---

**Questions?** Review `docs/todos/01_project_cleanup.md` for detailed notes on any topic.
