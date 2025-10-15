# Project Cleanup Planning - Index

This directory contains all planning documents for reorganizing the D&D RAG System project.

## 📋 Documents in This Directory

### Quick Start
- **[SUMMARY.md](SUMMARY.md)** - Executive summary of the cleanup plan
- **[00_quick_checklist.md](00_quick_checklist.md)** - Condensed checklist for implementation

### Detailed Planning
- **[01_project_cleanup.md](01_project_cleanup.md)** - Complete cleanup plan with 27 tasks
- **[STRUCTURE_COMPARISON.md](STRUCTURE_COMPARISON.md)** - Visual before/after directory structures

### Helper Tools
- **[../../../list_chromadb_collections.py](../../../list_chromadb_collections.py)** - Script to identify active vs obsolete ChromaDB collections

---

## 🎯 Where to Start

### First Time Reading?
1. Read [SUMMARY.md](SUMMARY.md) - 5 minute overview
2. Review [STRUCTURE_COMPARISON.md](STRUCTURE_COMPARISON.md) - See the visual difference
3. Skim [01_project_cleanup.md](01_project_cleanup.md) - Full details

### Ready to Implement?
1. Use [00_quick_checklist.md](00_quick_checklist.md) as your task list
2. Reference [01_project_cleanup.md](01_project_cleanup.md) for detailed notes
3. Run `list_chromadb_collections.py` to identify obsolete files

---

## 📊 Quick Stats (UPDATED)

**Main TODO Document**:
- 5 major sections
- 37 actionable tasks (was 27)
- 9 implementation phases (was 7)
- All 5 questions resolved ✅

**Files to Move**:
- 5 Python source files → `src/`
- 4 scripts → `scripts/`
- Data files → `data/`
- ChromaDB GUID directories → STAY IN PLACE (shared resource)

**Files to Create**:
- `requirements.txt` and `requirements-dev.txt`
- `__init__.py` files in `src/` subdirectories
- 1 new management script (`setup_venv.sh`)
- 6+ documentation files
- Main README.md (integrating README_DOCLING.md)

**Files to Archive**:
- 3 obsolete Python scripts → `archive/`
- 1 directory to delete: `dndmarkdown/pymupdf/`

---

## 🗂️ Document Details

### SUMMARY.md
- What was created
- Key findings
- Immediate next steps
- What was NOT done (as requested)

### 00_quick_checklist.md
- Condensed task list
- Checkbox format for tracking
- Quick reference during implementation
- ~50 total items

### 01_project_cleanup.md
- **Section 1**: File organization & directory structure
  - Identify obsolete files
  - GUID directory analysis
  - Proposed structure
  
- **Section 2**: Documentation updates
  - copilot_instructions.md
  - Implementation docs (5 files)
  - Main README.md
  - Setup guides (2 files)
  
- **Section 3**: Move Python source files
  - Dependencies list
  - File-by-file reorganization
  - Virtual environment setup
  - ChromaDB management scripts
  - Import path updates
  
- **Section 4**: requirements.txt
  - Core dependencies
  - Development dependencies
  
- **Section 5**: Priority execution order
  - 7 phases
  - 27 tasks
  - Safety-first approach

### STRUCTURE_COMPARISON.md
- Side-by-side comparison
- Current structure (messy)
- Proposed structure (clean)
- Migration mapping
- Import examples
- Visual benefits explanation

---

## ✅ Questions Resolved

All 5 original questions have been answered:

1. **ChromaDB Collections**: ✅ **Leave GUID directories in place**
   - Project will move to its own directory eventually
   - ChromaDB stays in `/home/mike/projects/rag/chroma/` as shared resource

2. **Script Status**: ✅ **Archive obsolete, keep relevant**
   - Archive: `chunk_monster_manual_docling.py`, `embed_and_store_markdown.py`, `embed_and_store_semantic.py`
   - Keep: `chunk_monster_encyclopedia.py`, `chunk_players_handbook_docling.py`, `convert_pdfs_to_markdown.py`
   - Move to scripts: `benchmark_models.py`

3. **Markdown Data**: ✅ **Remove pymupdf, keep docling**
   - `docling/` is production quality → move to `data/markdown/`
   - `pymupdf/` was experimental → delete directory

4. **Testing**: ✅ **Create empty tests directory**
   - `tests/` directory created
   - Test strategy out of scope for this cleanup

5. **Package Name**: ✅ **gravitycar_dnd1st_rag_system**
   - Descriptive and unique

---

## 🚀 Implementation Phases (UPDATED)

See [01_project_cleanup.md](01_project_cleanup.md) for details.

### Phase 1: Create Package Structure
- Create `__init__.py` files in `src/` subdirectories
- Create `tests/__init__.py`
- Verify directory structure

### Phase 2: Move Data Files
- Move `dndmarkdown/docling/` → `data/markdown/`
- Move `chunk_files/` → `data/chunks/`
- Remove `dndmarkdown/pymupdf/` directory

### Phase 3: Move Scripts
- Move scripts to `scripts/` directory
- Make executable: `chmod +x scripts/*.sh`

### Phase 4: Archive Obsolete Files
- Move obsolete scripts to `archive/`

### Phase 5: Move Source Code
- Move Python files to `src/` subdirectories
- Update all import statements
- Test each moved file

### Phase 6: Create Dependencies
- Create `requirements.txt`
- Create `requirements-dev.txt`
- Create `scripts/setup_venv.sh`

### Phase 7: Documentation
- Integrate `README_DOCLING.md` into main `README.md`
- Create implementation docs
- Create setup guides

### Phase 8: Testing
- Test chunking pipeline
- Test embedding pipeline
- Test query pipeline
- Verify imports work

### Phase 9: Final Tasks (Mike's Responsibility)
- Create `docs/copilot_instructions.md` (Mike will handle)
- Review and consolidate documentation
- Initialize git repository (after cleanup)

---

## 📝 Notes (UPDATED)

### What These Documents Do NOT Do
✅ Do not implement any changes  
✅ Do not delete any files  
✅ Do not move any files  
✅ Only provide planning and organization

### Key Changes from Original Plan
1. **No Git** - Removed all git references (repo will be created after cleanup)
2. **ChromaDB in Place** - GUID directories stay in current location (shared resource)
3. **Package Name** - `gravitycar_dnd1st_rag_system`
4. **Archive Strategy** - Obsolete files moved to `archive/`, not deleted
5. **Keep Converters** - `convert_pdfs_to_markdown.py` still relevant for future books
6. **Move benchmark_models.py** - Goes to `scripts/`, not `archive/`
7. **Copilot Instructions** - Phase 9, Mike will handle personally

### Implementation Safety
- All changes are reversible (file moves, not deletions)
- Test after each phase
- No git commits needed between phases (repo doesn't exist yet)
- Can stop and resume at any phase boundary

### Future Enhancements Noted
- Installable Python package (`setup.py`)
- Logging configuration
- Configuration file (YAML/TOML)
- Docker support
- Web interface

---

## 🔄 Keeping These Docs Updated

As you implement changes:
1. Check off items in [00_quick_checklist.md](00_quick_checklist.md)
2. Add notes to [01_project_cleanup.md](01_project_cleanup.md)
3. Document deviations from plan
4. Add lessons learned

---

**Created**: October 15, 2025  
**Updated**: October 15, 2025  
**Status**: Planning complete, all questions resolved, ready for implementation  
**Next**: Begin Phase 1 (Create package structure)
