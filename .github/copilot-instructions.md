# GravityCar D&D 1st Edition RAG System - AI Agent Instructions

## Project Overview

This is a production-ready RAG (Retrieval-Augmented Generation) system for querying Advanced Dungeons & Dragons 1st Edition rulebooks. The system features intelligent chunking, entity-aware retrieval, and adaptive semantic filtering to provide accurate answers about game mechanics, monsters, spells, and character progression.

**Package**: `gravitycar_dnd1st_rag_system`  
**Tech Stack**: Python 3.10+, ChromaDB 1.1.1, OpenAI GPT-4o-mini, Sentence Transformers (all-mpnet-base-v2, 768d), Docling 2.55.1  
**Architecture**: Standalone scripts → ChromaDB vector store → OpenAI API

## Critical Context

### The ChromaDB Split-Brain Pattern
**This is NOT a typical monorepo**. ChromaDB data lives at `/home/mike/projects/rag/chroma/` as a shared resource across multiple projects, while the Python code will eventually move to its own directory. When you see GUID directories (e.g., `1601c5cc-29c5-4f3d-9e8f-cf135413dcc1/`), these are ChromaDB collection storage - **never delete or move them**.

**Key insight**: ChromaDB configuration in `.env` uses these variables:
- `chroma_host_url=http://localhost`
- `chroma_host_port=8060`
- `chroma_data_path=/home/mike/projects/rag/chroma/`

All scripts assume ChromaDB is already running. Start it with `./scripts/start_chroma.sh` (uses v2 API, reads .env, runs in background).

### The Three-Stage Pipeline Architecture

**Stage 1: PDF → Markdown** (`src/converters/pdf_converter.py`)
- Uses Docling (winner after 5 failed approaches: OCR, PyMuPDF, LlamaParse)
- Critical: Preserves table structure (Fighter XP table is the acid test)
- Configuration: `do_table_structure=True`, `TableFormerMode.ACCURATE`

**Stage 2: Markdown → Chunks** (`src/chunkers/`)
- **Monster Manual** (`monster_encyclopedia.py`): Category-aware (DEMON → Orcus, Demogorgon)
  - Detects top-level categories vs. nested monsters
  - Prepends statistics to text for searchability (FREQUENCY, AC, HD, etc.)
  - Output: One monster = one chunk with structured metadata
- **Player's Handbook** (`players_handbook.py`): Table-aware
  - Each spell/section = one chunk
  - Merges tables with related notes
  - Preserves hierarchy

**Stage 3: Chunks → Embeddings → ChromaDB** (`src/embedders/`)
- **Architecture**: Modular embedder system using Orchestrator + Strategy patterns
  - `embedder_orchestrator.py`: Auto-detects format, coordinates pipeline
  - `base_embedder.py`: Template method pattern (common operations)
  - `monster_book_embedder.py`: Monster Manual format (statistics prepending)
  - `rule_book_embedder.py`: PHB/DMG format (hierarchy flattening)
- **ChromaDB Access**: All ChromaDB operations go through `ChromaDBConnector` (single source of truth)
  - Centralized connection management in `src/utils/chromadb_connector.py`
  - Eliminates code duplication across embedders, CLI, and query modules
  - Provides consistent API: `get_collection()`, `create_collection()`, `truncate_collection()`, etc.
- **Model**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **Strategy**: Format-specific text preparation (statistics prepending for monsters)
- **Metadata**: Flattened for ChromaDB (`statistics.ARMOR_CLASS` → `armor_class`)
- **Collections**: `dnd_monster_manual` (294 chunks), `dnd_players_handbook` (735 chunks), `dnd_dmg` (1,184 chunks)

**Query Pipeline** (`src/query/docling_query.py`)
- **Entity-aware retrieval**: Comparison queries ("owlbear vs orc") → expand to k×3, reorder to ensure both entities in top results
- **Adaptive gap detection**: Returns 2-k results based on semantic similarity cliffs (gap threshold: 0.1, distance threshold: 0.4)
- **Temperature: 0.0** for deterministic, factual answers (no creativity needed)

## Development Workflow

### Environment Setup
```bash
# ALWAYS activate venv first
source venv/bin/activate

# Verify ChromaDB is running (must return JSON)
curl -s http://localhost:8060/api/v2/heartbeat

# If not running
./scripts/start_chroma.sh
```

### Running the Pipeline
```bash
# 1. Convert PDF (if needed)
python src/converters/pdf_converter.py
# Input: data/source_pdfs/*.pdf → Output: data/markdown/*.md

# 2. Chunk markdown
python src/chunkers/monster_encyclopedia.py data/markdown/Monster_Manual_(1e).md
# Output: data/chunks/chunks_Monster_Manual_(1e).json

# 3. Embed and store
python src/embedders/docling_embedder.py data/chunks/chunks_Monster_Manual_(1e).json dnd_monster_manual
# Creates/overwrites ChromaDB collection

# 4. Query
python src/query/docling_query.py dnd_monster_manual "What is a beholder?" --debug
# Add --debug to see adaptive gap detection in action
```

### Code Quality Tools
```bash
black src/          # Format (mandatory before commits)
flake8 src/         # Lint
mypy src/           # Type check
pytest tests/       # Run tests (directory currently empty)
```

## Project-Specific Conventions

### SOLID Principles Enforcement
This codebase strictly follows SOLID principles (see `.github/chatmodes/coder.chatmode.md`):
- **SRP**: Classes have single responsibility (e.g., `DnDRAG` only handles query pipeline, not chunking)
- **OCP**: Configuration via `.env`, not hardcoded values
- **DIP**: Depend on abstractions (ChromaDB client, embedding model) not concrete implementations

### File Naming & Structure
- Scripts: `verb_noun.py` (e.g., `convert_pdfs_to_markdown.py`)
- Classes: `NounNoun` (e.g., `MonsterManualChunker`, `DnDRAG`)
- Functions: `verb_noun()` (e.g., `extract_statistics()`, `flatten_metadata()`)
- All executable scripts: `#!/usr/bin/env python3` shebang

### Import Strategy
**No cross-module imports**. Each script is standalone and imports only:
1. Standard library
2. External dependencies (chromadb, sentence-transformers, openai, docling)
3. Type hints from `typing`

This is intentional to keep scripts independently executable.

### Path Handling
```python
# Always use Path objects, not string concatenation
from pathlib import Path

# Correct
output_path = Path("data/chunks") / f"chunks_{filename}.json"

# Wrong
output_path = "data/chunks/" + "chunks_" + filename + ".json"
```

### Error Handling Pattern
```python
# Don't: Silent failures
# Do: Explicit errors with context
try:
    collection = client.get_collection(name=collection_name)
except Exception as e:
    print(f"Error: Collection '{collection_name}' not found.")
    print("Available collections:")
    for c in client.list_collections():
        print(f"  - {c.name}")
    sys.exit(1)
```

## Critical Don'ts

1. **Never change embedding model** without re-embedding ALL collections (dimension mismatch)
2. **Never hardcode paths** - use `.env` or command-line arguments
3. **Never modify ChromaDB GUID directories** - they're managed by ChromaDB
4. **Never commit `.env`** - contains API keys
5. **Never use generic chunking** - domain-specific chunkers exist for a reason (Monster Manual ≠ Player's Handbook)
6. **Never skip statistics prepending** - makes monster stats unsearchable by embeddings

## Documentation Structure

- `docs/implementations/` - Algorithm deep-dives (adaptive_filtering.md is essential reading)
- `docs/setup/` - Installation and ChromaDB setup
- `docs/todos/` - Project planning (see `01_project_cleanup.md` for roadmap)
- `docs/early_notes/` - Historical context (why Docling won over PyMuPDF/LlamaParse)

## Key Files to Understand

1. `src/query/docling_query.py` - The "brain" (entity detection, gap detection, OpenAI integration)
2. `src/chunkers/monster_encyclopedia.py` - Category detection logic (DEMON → nested monsters)
3. `src/chunkers/recursive_chunker.py` - Hierarchical chunker with spell detection and adaptive splitting
4. `src/embedders/embedder_orchestrator.py` - Format auto-detection and pipeline coordination
5. `src/embedders/base_embedder.py` - Template method pattern (common operations)
6. `src/embedders/monster_book_embedder.py` - Monster Manual format handler
7. `src/embedders/rule_book_embedder.py` - PHB/DMG format handler
8. `src/utils/chromadb_connector.py` - **NEW**: Centralized ChromaDB connector (all DB operations)
9. `docs/implementations/adaptive_filtering.md` - Gap detection algorithm explained with examples
10. `docs/implementations/EmbedderArchitecture.md` - Embedder system architecture and design patterns
11. `docs/implementations/ChromaDBConnector.md` - **NEW**: ChromaDB connector documentation and usage
12. `docs/implementations/recursive_chunker_implementation.md` - Recursive chunker implementation details
13. `.env` - Configuration source of truth (ChromaDB host/port, OpenAI key)

## Testing Philosophy

**The Fighter XP Table Test** is the acid test for data quality:
```bash
python src/query/docling_query.py dnd_players_handbook \
  "How many experience points does a fighter need to become 9th level?"
```

Expected: GPT correctly answers "250,001 XP" by parsing the FIGHTERS TABLE. This tests:
1. PDF → Markdown table extraction (Docling quality)
2. Chunking (table must stay intact)
3. Retrieval (must find the right table)
4. LLM understanding (must parse table correctly)

If this fails, the whole pipeline needs debugging.

## When to Update This File

- New pipeline stages added (e.g., re-ranker, hybrid search)
- Major architectural changes (e.g., switching from OpenAI to local LLM)
- New conventions established (e.g., testing framework patterns)
- Integration points change (e.g., ChromaDB authentication enabled)

## Recent Architectural Changes

### ChromaDB Connector Centralization (October 2025)
All ChromaDB database operations were centralized into a single connector class:

**Old**: Direct `chromadb.HttpClient` imports in 4+ files (base_embedder, main.py, cli.py, docling_query.py)  
**New**: Centralized `ChromaDBConnector` class as single source of truth

**Benefits**:
- ✅ **Zero duplication**: Connection logic in one place
- ✅ **Consistent API**: Same methods across all modules
- ✅ **Easier testing**: Single mock point at import location
- ✅ **Maintainability**: Change connection logic in one file
- ✅ **Clean separation**: Business logic separate from DB access

**Key Methods**:
- `get_collection()`, `create_collection()`, `get_or_create_collection()`
- `delete_collection()`, `truncate_collection()`
- `list_collections()`, `collection_exists()`, `get_collection_count()`

See `docs/implementations/ChromaDBConnector.md` for full details.

### Embedder Refactoring (October 2025)
The embedder system was refactored from a monolithic class into a modular architecture:

**Old**: Single `DoclingEmbedder` class with conditional logic  
**New**: Orchestrator + Strategy pattern with format auto-detection

**Benefits**:
- ✅ **Testability**: 38 unit tests + 3 integration tests (previously 0)
- ✅ **Extensibility**: Add new book formats without modifying existing code
- ✅ **Maintainability**: SOLID principles enforced throughout
- ✅ **No regressions**: All 56 tests pass, Fighter XP Table acid test validates pipeline

**Key Components**:
- `EmbedderOrchestrator`: Auto-detection and pipeline coordination
- `Embedder`: Abstract base with template methods
- `MonsterBookEmbedder`: Monster Manual format strategy
- `RuleBookEmbedder`: PHB/DMG format strategy

See `docs/implementations/EmbedderArchitecture.md` for full details.

---

*Last Updated: October 21, 2025*  
*Version: 1.2 (ChromaDB Connector + Embedder Refactoring)*
