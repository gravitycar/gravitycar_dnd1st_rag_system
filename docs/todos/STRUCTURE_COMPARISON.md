# Directory Structure: Current vs Proposed (UPDATED)

## Current Structure (Messy!)

```
/home/mike/projects/rag/chroma/           # ChromaDB install directory
├── .env                                  # Config
├── .vscode/                              # Editor settings
├── .github/                              # Git settings
├── venv/                                 # Virtual environment
│
├── chroma.sqlite3                        # ChromaDB metadata DB
├── 1601c5cc-29c5-4f3d-9e8f-cf135413dcc1/ # ChromaDB collection (UUID 1)
├── 236eaf52-b485-4724-92e1-f4cb859e9102/ # ChromaDB collection (UUID 2)
├── 34be7083-2abe-4d7f-8e6b-902746d651cb/ # ChromaDB collection (UUID 3)
├── 689d9343-c398-4b8e-b689-670607433655/ # ... 5 more GUID directories
├── a2266aa9-97f0-4930-a682-3ec636da6232/
├── a282ad38-ffaf-4a0e-b9fa-1fc490d05d72/
├── cd83bf05-0793-4204-be31-60234f432ef3/
├── f8d76a4d-058b-4451-b1a3-d66b02f00645/
│
├── chunk_monster_encyclopedia.py         # Source files mixed in root
├── chunk_monster_manual_docling.py       # (obsolete)
├── chunk_players_handbook_docling.py
├── embed_docling.py
├── embed_and_store_markdown.py           # (obsolete)
├── embed_and_store_semantic.py           # (obsolete)
├── query_docling.py
├── convert_pdfs_to_markdown.py
├── benchmark_models.py
├── list_chromadb_collections.py
├── start_chroma.sh
├── setup_docling.sh
├── README_DOCLING.md                     # Old readme
│
├── chunk_files/                          # Output data
│   └── chunks_Monster_Manual_(1e).json
│
├── dndmarkdown/                          # Source data
│   ├── docling/                          # Good conversions
│   │   └── good_pdfs/
│   │       ├── Monster_Manual_(1e).md
│   │       └── Monster_Manual_(1e).pdf
│   └── pymupdf/                          # Experimental (to be deleted)
│
├── src/                                  # ✅ CREATED
│   ├── chunkers/
│   ├── embedders/
│   ├── query/
│   ├── converters/
│   └── utils/
│
├── scripts/                              # ✅ CREATED (empty)
├── data/                                 # ✅ CREATED
│   ├── source_pdfs/
│   ├── markdown/
│   └── chunks/
│
├── archive/                              # ✅ CREATED (empty)
├── tests/                                # ✅ CREATED (empty)
│
└── docs/                                 # Documentation
    ├── early_notes/
    ├── implementation_notes/
    ├── questions/
    └── todos/

Problems:
❌ Source files, data files, and ChromaDB data all mixed in root
❌ Multiple obsolete scripts in root
❌ dndmarkdown/ directory needs reorganization
❌ chunk_files/ should move to data/
❌ No __init__.py files in src/ subdirectories yet
```

---

## Proposed Structure (Clean!)

**Package Name**: `gravitycar_dnd1st_rag_system`

```
/home/mike/projects/rag/chroma/           # ChromaDB host (stays here)
├── .env                                  # Config
├── .vscode/                              # Editor settings
├── .github/                              # Git settings (if present)
├── venv/                                 # Virtual environment
│
├── chroma.sqlite3                        # ✅ ChromaDB metadata (STAYS)
├── [8 GUID directories]                  # ✅ ChromaDB collections (STAY)
│
├── README.md                             # ✨ NEW: Main project documentation
├── requirements.txt                      # ✨ NEW: Python dependencies
├── requirements-dev.txt                  # ✨ NEW: Dev dependencies
│
├── src/                                  # ✨ Python package (organized)
│   ├── __init__.py                       # ✨ NEW
│   │
│   ├── chunkers/                         # Document chunking
│   │   ├── __init__.py                   # ✨ NEW
│   │   ├── monster_encyclopedia.py       # ← FROM: chunk_monster_encyclopedia.py
│   │   └── players_handbook.py           # ← FROM: chunk_players_handbook_docling.py
│   │
│   ├── embedders/                        # Embedding modules
│   │   ├── __init__.py                   # ✨ NEW
│   │   └── docling_embedder.py           # ← FROM: embed_docling.py
│   │
│   ├── query/                            # Query/RAG modules
│   │   ├── __init__.py                   # ✨ NEW
│   │   └── docling_query.py              # ← FROM: query_docling.py
│   │
│   ├── converters/                       # PDF conversion
│   │   ├── __init__.py                   # ✨ NEW
│   │   └── pdf_converter.py              # ← FROM: convert_pdfs_to_markdown.py
│   │
│   └── utils/                            # General utilities
│       └── __init__.py                   # ✨ NEW
│
├── scripts/                              # ✨ Executable scripts
│   ├── benchmark_models.py               # ← FROM: root
│   ├── list_chromadb_collections.py      # ← FROM: root
│   ├── start_chroma.sh                   # ← FROM: root
│   ├── setup_docling.sh                  # ← FROM: root
│   └── setup_venv.sh                     # ✨ NEW
│
├── data/                                 # ✨ All data files (organized!)
│   ├── source_pdfs/                      # Original PDF files (TBD)
│   │
│   ├── markdown/                         # ← FROM: dndmarkdown/docling/
│   │   ├── Monster_Manual_(1e).md
│   │   └── Monster_Manual_(1e).pdf
│   │
│   └── chunks/                           # ← FROM: chunk_files/
│       └── chunks_Monster_Manual_(1e).json
│
├── docs/                                 # ✨ Documentation (enhanced)
│   ├── README.md                         # ✨ NEW: Documentation index
│   │
│   ├── setup/                            # ✨ NEW: Setup guides
│   │   ├── installation.md
│   │   └── chromadb_setup.md
│   │
│   ├── implementations/                  # ✨ NEW: Class documentation
│   │   ├── MonsterEncyclopediaChunker.md
│   │   ├── DoclingEmbedder.md
│   │   ├── DnDRAG.md
│   │   └── adaptive_filtering.md
│   │
│   ├── early_notes/                      # Existing
│   ├── implementation_notes/             # Existing
│   ├── questions/                        # Existing
│   └── todos/                            # Existing
│       ├── 00_quick_checklist.md
│       ├── 01_project_cleanup.md
│       ├── SUMMARY.md
│       ├── STRUCTURE_COMPARISON.md
│       └── README.md
│
├── tests/                                # ✨ Test files (empty for now)
│   └── __init__.py                       # ✨ NEW
│
└── archive/                              # ✨ Archived/obsolete code
    ├── chunk_monster_manual_docling.py   # ← FROM: root (superseded)
    ├── embed_and_store_markdown.py       # ← FROM: root (superseded)
    └── embed_and_store_semantic.py       # ← FROM: root (superseded)

Benefits:
✅ Clear separation: source / data / docs / scripts
✅ All Python code in src/ (importable as package)
✅ Data files organized by stage (markdown → chunks)
✅ ChromaDB GUID directories stay in place (shared resource)
✅ Scripts consolidated in one place
✅ Documentation enhanced with new guides
✅ Archive for obsolete code (not deleted, just moved)
✅ Easy to navigate and maintain
✅ Ready for future git repository
✅ Can eventually be installed as Python package
```

---

## Migration Path (UPDATED)

### What Moves Where

**Python Source Files** → `src/`:
```
chunk_monster_encyclopedia.py       → src/chunkers/monster_encyclopedia.py
chunk_players_handbook_docling.py   → src/chunkers/players_handbook.py
embed_docling.py                    → src/embedders/docling_embedder.py
query_docling.py                    → src/query/docling_query.py
convert_pdfs_to_markdown.py         → src/converters/pdf_converter.py
```

**Scripts** → `scripts/`:
```
benchmark_models.py                 → scripts/benchmark_models.py
list_chromadb_collections.py        → scripts/list_chromadb_collections.py
start_chroma.sh                     → scripts/start_chroma.sh
setup_docling.sh                    → scripts/setup_docling.sh
(new)                               → scripts/setup_venv.sh
```

**Data Files** → `data/`:
```
chunk_files/*                       → data/chunks/*
dndmarkdown/docling/*               → data/markdown/*
```

**Directories to Remove**:
```
dndmarkdown/pymupdf/                → DELETE (docling is better)
dndmarkdown/                        → DELETE (after moving docling/)
chunk_files/                        → DELETE (after moving to data/chunks/)
```

**ChromaDB GUID Directories**:
```
[8 GUID directories]                → STAY IN PLACE (shared resource)
chroma.sqlite3                      → STAY IN PLACE (shared resource)
```

**Obsolete Files** → `archive/`:
```
chunk_monster_manual_docling.py     → archive/
embed_and_store_markdown.py         → archive/
embed_and_store_semantic.py         → archive/
```

**Documentation** → Create new files:
```
(new)                               → README.md (integrate README_DOCLING.md)
(new)                               → requirements.txt
(new)                               → requirements-dev.txt
(new)                               → docs/implementations/*.md
(new)                               → docs/setup/*.md
(later)                             → docs/copilot_instructions.md (Mike handles)
```

---

## Size Comparison

### Current (cluttered):
- **Root level**: 20+ items (files + directories)
- **Python files**: Mixed in root
- **Data files**: Multiple locations
- **Hard to find**: Specific functionality

### Proposed (organized):
- **Root level**: 8 clear directories + config files
- **Python files**: All in `src/` by category
- **Data files**: All in `data/` by stage
- **Easy to find**: Everything has its place

---

## Import Examples (UPDATED)

### Before (current structure):
```python
# Imports from root level
from chunk_monster_encyclopedia import MonsterEncyclopediaChunker
from embed_docling import DoclingEmbedder
from query_docling import DnDRAG
```

### After (proposed structure):
```python
# Clean package imports
from src.chunkers.monster_encyclopedia import MonsterEncyclopediaChunker
from src.embedders.docling_embedder import DoclingEmbedder
from src.query.docling_query import DnDRAG

# Or if installed as package:
from dnd_rag.chunkers import MonsterEncyclopediaChunker
from dnd_rag.embedders import DoclingEmbedder
from dnd_rag.query import DnDRAG
```

---

**Visual Legend:**
- ✨ NEW: Files/directories to be created
- ← : Files being moved/renamed
- (optional): Can be omitted if not needed
