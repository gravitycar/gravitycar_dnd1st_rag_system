# Project Cleanup - Quick Checklist

This is a condensed version of `01_project_cleanup.md` for quick reference.

**Package Name**: `gravitycar_dnd1st_rag_system`

## Phase 1: Create Package Structure
- [ ] Create `__init__.py` files in `src/` subdirectories
- [ ] Create `tests/__init__.py`
- [ ] Verify directory structure

## Phase 2: Move Data Files
- [ ] Move `dndmarkdown/docling/` → `data/markdown/`
- [ ] Move `chunk_files/` contents → `data/chunks/`
- [ ] Remove `dndmarkdown/pymupdf/` directory

## Phase 3: Move Scripts
- [ ] Move `benchmark_models.py` → `scripts/`
- [ ] Move `list_chromadb_collections.py` → `scripts/`
- [ ] Move `start_chroma.sh` → `scripts/`
- [ ] Move `setup_docling.sh` → `scripts/`
- [ ] Make scripts executable: `chmod +x scripts/*.sh`

## Phase 4: Archive Obsolete Files
- [ ] Move `chunk_monster_manual_docling.py` → `archive/`
- [ ] Move `embed_and_store_markdown.py` → `archive/`
- [ ] Move `embed_and_store_semantic.py` → `archive/`

## Phase 5: Move Source Code
- [ ] Move `convert_pdfs_to_markdown.py` → `src/converters/pdf_converter.py`
- [ ] Move `chunk_monster_encyclopedia.py` → `src/chunkers/monster_encyclopedia.py`
- [ ] Move `chunk_players_handbook_docling.py` → `src/chunkers/players_handbook.py`
- [ ] Move `embed_docling.py` → `src/embedders/docling_embedder.py`
- [ ] Move `query_docling.py` → `src/query/docling_query.py`
- [ ] Update all import statements
- [ ] Test each moved file

## Phase 6: Create Dependencies
- [ ] Create `requirements.txt`
- [ ] Create `requirements-dev.txt`
- [ ] Create `scripts/setup_venv.sh`

## Phase 7: Documentation
- [ ] Integrate `README_DOCLING.md` into main `README.md`
- [ ] Create `docs/implementations/MonsterEncyclopediaChunker.md`
- [ ] Create `docs/implementations/DoclingEmbedder.md`
- [ ] Create `docs/implementations/DnDRAG.md`
- [ ] Create `docs/implementations/adaptive_filtering.md`
- [ ] Create `docs/setup/installation.md`
- [ ] Create `docs/setup/chromadb_setup.md`
- [ ] Update `docs/README.md`

## Phase 8: Testing
- [ ] Test chunking pipeline
- [ ] Test embedding pipeline
- [ ] Test query pipeline
- [ ] Verify all imports work

## Phase 9: Final Tasks (Mike)
- [ ] Create `docs/copilot_instructions.md` (Mike handles personally)
- [ ] Review and consolidate documentation
- [ ] Initialize git repository (after cleanup)

---

See `01_project_cleanup.md` for detailed implementation notes.
