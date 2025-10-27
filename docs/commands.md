# CLI Commands Reference

**Package**: `gravitycar_dnd1st_rag_system`  
**Entry Point**: `main.py`  
**Last Updated**: October 21, 2025

## Overview

The D&D 1st Edition RAG System provides a unified CLI interface for all pipeline operations. All commands are executed through `main.py` with different subcommands.

## Quick Reference

```bash
python main.py convert <pdf_file>
python main.py organize <markdown_file> [options]
python main.py transform-tables <markdown_file> <table_list> [options]
python main.py chunk <markdown_file> [--type TYPE]
python main.py embed <chunks_file> <collection_name> [--test]
python main.py query <collection_name> [question] [options]
python main.py truncate <collection_name> [--confirm]
python main.py list-collections
```

---

## Commands

### 1. `convert` - Convert PDF to Markdown

**Purpose**: Convert D&D PDF rulebooks to markdown format using Docling.

**Status**: ⚠️ Not yet integrated (placeholder)

**Syntax**:
```bash
python main.py convert <pdf_file>
```

**Arguments**:
- `pdf_file` - Path to PDF file to convert

**Example**:
```bash
python main.py convert data/source_pdfs/Players_Handbook.pdf
```

**Notes**:
- This command is currently a placeholder
- Direct script available: `python src/converters/pdf_converter.py`
- Uses Docling with table structure preservation

---

### 2. `organize` - Organize Heading Hierarchy

**Purpose**: Fix markdown heading levels using Table of Contents as reference.

**Syntax**:
```bash
python main.py organize <markdown_file> [--toc TOC_FILE] [--output OUTPUT_FILE] [--no-backup] [--debug]
```

**Arguments**:
- `markdown_file` - Path to markdown file to organize (required)

**Options**:
- `--toc TOC_FILE` - Path to Table of Contents file (auto-detects if not specified)
- `--output OUTPUT_FILE` - Output file path (default: overwrites input)
- `--no-backup` - Skip creating backup file (default: creates backup)
- `--debug` - Enable debug logging

**Examples**:
```bash
# Auto-detect TOC and create backup
python main.py organize data/markdown/Players_Handbook_(1e).md

# Specify TOC file explicitly
python main.py organize data/markdown/Players_Handbook_(1e).md \
  --toc data/source_pdfs/notes/Players_Handbook_TOC.txt

# Write to different output file
python main.py organize data/markdown/Players_Handbook_(1e).md \
  --output data/markdown/Players_Handbook_organized.md

# Skip backup and enable debug
python main.py organize data/markdown/Players_Handbook_(1e).md \
  --no-backup --debug
```

**Auto-detection**:
- If `--toc` not specified, looks for: `data/source_pdfs/notes/Players_Handbook_TOC.txt`
- Creates `.bak` backup unless `--no-backup` specified

**Use Cases**:
- Fix heading hierarchy from OCR or PDF extraction
- Ensure consistent heading levels before chunking
- Validate against official Table of Contents

---

### 3. `transform-tables` - Transform Tables to JSON

**Purpose**: Convert complex markdown tables to structured JSON using OpenAI for improved RAG accuracy.

**Syntax**:
```bash
python main.py transform-tables <markdown_file> <table_list> [options]
```

**Arguments**:
- `markdown_file` - Path to markdown file to transform (required)
- `table_list` - Path to table list file (required)

**Options**:
- `--dry-run` - Estimate cost without executing transformation
- `--model MODEL` - OpenAI model (default: `gpt-4o-mini`)
- `--delay DELAY` - Delay between API calls in seconds (default: `1.0`)
- `--cost-limit COST_LIMIT` - Maximum cost in USD (default: `5.0`)
- `--output-dir OUTPUT_DIR` - Output directory (default: `data/markdown/docling/good_pdfs/`)
- `--api-key API_KEY` - OpenAI API key (overrides `.env`)

**Examples**:

**Dry Run (Estimate Cost)**:
```bash
python main.py transform-tables \
  data/markdown/docling/good_pdfs/Dungeon_Master_s_Guide_(1e)_organized.md \
  tmp/dmg_tables_2d_matrix_lookup.md \
  --dry-run
```

**Transform All Tables**:
```bash
python main.py transform-tables \
  data/markdown/docling/good_pdfs/Dungeon_Master_s_Guide_(1e)_organized.md \
  tmp/dmg_tables_2d_matrix_lookup.md
```

**Custom Settings**:
```bash
python main.py transform-tables \
  data/markdown/docling/good_pdfs/Dungeon_Master_s_Guide_(1e)_organized.md \
  tmp/dmg_tables_2d_matrix_lookup.md \
  --model gpt-4o \
  --delay 2.0 \
  --cost-limit 10.0 \
  --output-dir output/
```

**Table List Format**:
```markdown
# Table List

---

## Table 1

**Location**: Lines 1615-1640

**Description**: Troop Type Table

---

## Table 2

**Location**: Lines 2777-2786

**Description**: Encounter Frequency
```

**Output**:
- Creates: `<original_name>_with_json_tables.md` in output directory
- Backup: `<original_name>.bak` created before transformation
- Report: Displays transformation statistics and cost

**Process**:
1. **Load Phase**: Read markdown and parse table list metadata
2. **Estimation Phase**: Calculate expected API cost (accounts for 30-50% token reduction from preprocessing)
3. **Processing Phase**: For each table:
   - Extract heading-bounded context
   - Preprocess table (strip whitespace, compress separators)
   - Transform via OpenAI API
   - Track tokens and cost
4. **Application Phase**: Replace tables in markdown (reverse order to preserve line numbers)
5. **Output Phase**: Write transformed file with backup
6. **Reporting Phase**: Generate summary statistics

**Token Optimization**:
- Strips excessive whitespace (preserves 1 space padding per cell)
- Compresses separator lines to 3 hyphens
- Achieves 30-50% token reduction while preserving table structure
- Validated: Tables still render correctly in markdown

**Cost Management**:
- Dry run provides accurate cost estimate
- Default limit: $5.00 (prompts user if exceeded)
- Typical costs: $0.05-$0.10 per 100 tables (gpt-4o-mini)
- Progress tracking shows per-table token usage and cost

**Error Handling**:
- Automatic retries for rate limits (3 attempts, exponential backoff)
- Graceful per-table failures (continues processing, reports at end)
- Keyboard interrupt handling (saves progress)
- Detailed error messages with table locations

**Requirements**:
- OpenAI API key in `.env` file (`gravitycar_openai_api_key`)
- Valid table list with line numbers matching markdown
- Tables must be valid markdown format

**Standalone CLI**:
```bash
python -m src.transformers.cli <markdown_file> <table_list> [options]
```

**Documentation**:
- Full guide: `docs/implementations/TableTransformer.md`
- Implementation plan: `docs/implementation_plans/complex_table_transformer.md`

---

### 4. `chunk` - Chunk Markdown Documents

**Purpose**: Split markdown documents into semantic chunks for embedding.

**Syntax**:
```bash
````
**Arguments**:
- `markdown_file` - Path to markdown file to chunk (required)

**Options**:
- `--type {monster|player}` - Document type (auto-detects from filename if not specified)
  - `monster` - Uses `MonsterEncyclopediaChunker` (category-aware)
  - `player` - Uses `PlayersHandbookChunker` (spell/section-aware)

**Examples**:
```bash
# Auto-detect type from filename (contains "monster")
python main.py chunk data/markdown/Monster_Manual_(1e).md

# Explicitly specify type
python main.py chunk data/markdown/Players_Handbook_(1e).md --type player

# Works with any name if type specified
python main.py chunk data/markdown/my_custom_monster_list.md --type monster
```

**Output**:
- Creates: `data/chunks/chunks_<filename>.json`
- Format: JSON array of chunk objects
- Creates `data/chunks/` directory if it doesn't exist

**Auto-detection Rules**:
- If filename contains "monster" → Monster Manual format
- If filename contains "player" → Player's Handbook format
- If neither and no `--type` specified → error

**Chunk Formats**:

**Monster Manual Format**:
```json
{
  "name": "Beholder",
  "description": "A floating sphere...",
  "statistics": {
    "frequency": "Rare",
    "armor_class": "-1/2/7",
    "hit_dice": "45-75 hit points"
  },
  "metadata": {
    "type": "monster",
    "monster_id": "beholder"
  }
}
```

**Player's Handbook Format**:
```json
{
  "uid": "PHB_SPELLS_FIREBALL_1",
  "book": "Players_Handbook_(1e)",
  "title": "Fireball",
  "content": "A fireball spell...",
  "metadata": {
    "hierarchy": ["SPELLS", "MAGIC-USER", "Fireball"],
    "chunk_type": "spell",
    "char_count": 800
  }
}
```

---

### 5. `embed` - Embed Chunks into ChromaDB

**Purpose**: Generate embeddings and store chunks in ChromaDB vector database.

**Syntax**:
```bash
python main.py embed <chunks_file> <collection_name> [--test]
```

**Arguments**:
- `chunks_file` - Path to JSON chunks file (required)
- `collection_name` - ChromaDB collection name (required)

**Options**:
- `--test` - Run test queries after embedding

**Examples**:
```bash
# Embed Monster Manual chunks
python main.py embed data/chunks/chunks_Monster_Manual_(1e).json dnd_monster_manual

# Embed Player's Handbook with test queries
python main.py embed data/chunks/chunks_Players_Handbook_(1e).json dnd_phb --test

# Embed custom collection
python main.py embed data/chunks/my_custom_chunks.json my_collection
```

**Process**:
1. **Auto-detection**: Orchestrator detects chunk format (monster vs rulebook)
2. **Format Selection**: Chooses appropriate embedder strategy
3. **Text Preparation**: Format-specific text processing
   - Monster format: Prepends statistics block
   - Rulebook format: Flattens hierarchy
4. **Embedding**: Calls OpenAI API (text-embedding-3-small, 1536d)
5. **Storage**: Stores in ChromaDB collection
6. **Test Queries** (if `--test`): Runs format-specific test questions

**Embedder Selection**:
- Detects Monster Manual format → Uses `MonsterBookEmbedder`
- Detects PHB/DMG format → Uses `RuleBookEmbedder`
- Automatic based on chunk structure

**Requirements**:
- ChromaDB server running on `localhost:8060` (start with `./scripts/start_chroma.sh`)
- OpenAI API key in `.env` file
- Chunks file must exist and be valid JSON

**Collection Naming**:
- Use descriptive names: `dnd_monster_manual`, `dnd_phb`, `dnd_dmg`
- Avoid spaces (use underscores)
- Collection created if doesn't exist

**Output**:
```
Using OpenAI embedding model: text-embedding-3-small...
Connecting to ChromaDB at localhost:8060...
Using collection: dnd_monster_manual

🔧 Processing 294 monster chunks...
Processing batch 1/10 (chunks 1-32)...
Processing batch 2/10 (chunks 33-64)...
...
✅ Successfully embedded 294 monster chunks!
```

---

### 6. `query` - Query ChromaDB Collection

**Purpose**: Ask questions about D&D rules using RAG (Retrieval-Augmented Generation).

**Syntax**:
```bash
python main.py query <collection_name> [question] [options]
```

**Arguments**:
- `collection_name` - ChromaDB collection name (required)
- `question` - Question to ask (optional, interactive mode if not provided)

**Options**:
- `--model MODEL` - OpenAI model (default: `gpt-4o-mini`)
- `-k K` - Max chunks to retrieve (default: 15)
- `--distance-threshold THRESHOLD` - Distance threshold for filtering (default: 0.4)
- `--show-context` - Display context sent to LLM
- `--debug` - Show debug information (similarity scores, gap detection)
- `--test` - Run predefined test questions for collection

**Examples**:

**Single Question**:
```bash
python main.py query dnd_monster_manual "What is a beholder?"

python main.py query dnd_phb "How many experience points does a fighter need to reach 9th level?"
```

**Interactive Mode** (no question provided):
```bash
python main.py query dnd_monster_manual

# Output:
# Interactive mode - enter questions (or 'quit' to exit)
# 
# Question: What is a beholder?
# [Answer displays]
# 
# Question: Tell me about owlbears
# [Answer displays]
# 
# Question: quit
# Goodbye!
```

**Test Mode** (runs predefined questions):
```bash
# Monster Manual test questions
python main.py query dnd_monster_manual --test

# Player's Handbook test questions
python main.py query dnd_phb --test
```

**Debug Mode** (shows retrieval details):
```bash
python main.py query dnd_monster_manual "What is a beholder?" --debug

# Shows:
# - Retrieved chunk count
# - Similarity scores
# - Gap detection analysis
# - Adaptive filtering decisions
```

**Show Context** (display what LLM sees):
```bash
python main.py query dnd_monster_manual "What is a beholder?" --show-context

# Displays:
# - System prompt
# - Retrieved context chunks
# - User question
# - Full prompt sent to OpenAI
```

**Custom Retrieval Parameters**:
```bash
# Retrieve more chunks
python main.py query dnd_monster_manual "Compare owlbear and orc" -k 30

# Stricter similarity threshold
python main.py query dnd_phb "Tell me about spells" --distance-threshold 0.3

# Use GPT-4 instead of GPT-4o-mini
python main.py query dnd_monster_manual "What is a beholder?" --model gpt-4
```

**Combined Options**:
```bash
python main.py query dnd_monster_manual "What is a beholder?" \
  -k 20 \
  --distance-threshold 0.35 \
  --show-context \
  --debug
```

**Predefined Test Questions**:

**Monster Manual**:
1. "Tell me about owlbears and their abilities"
2. "What is the difference between a red dragon and a white dragon?"
3. "What are lizard men and how dangerous are they?"

**Player's Handbook**:
1. "How many experience points does a fighter need to reach 9th level?"
2. "What are the unique abilities that only thieves have?"
3. "What are the six character abilities in D&D?"

**Query Features**:
- **Entity-aware retrieval**: Detects comparison queries ("X vs Y"), expands retrieval
- **Adaptive gap detection**: Returns 2-k results based on semantic similarity cliffs
- **Temperature: 0.0**: Deterministic, factual answers
- **Streaming**: Real-time response streaming from OpenAI

**Output Format**:
```
╔══════════════════════════════════════════════════════════════╗
║ ANSWER
╚══════════════════════════════════════════════════════════════╝

A beholder is a fearsome and iconic Dungeons & Dragons monster...

[Detailed answer based on retrieved context]

---
📚 Sources: 3 chunks from dnd_monster_manual
```

**Interactive Mode Controls**:
- Enter question → Get answer
- `quit`, `exit`, or `q` → Exit
- `Ctrl+C` → Exit
- Empty line → Prompt again

---

### 7. `truncate` - Empty ChromaDB Collection

**Purpose**: Remove all documents from a ChromaDB collection while keeping the collection itself.

**Syntax**:
```bash
python main.py truncate <collection_name> [--confirm]
```

**Arguments**:
- `collection_name` - ChromaDB collection name (required)

**Options**:
- `--confirm` - Skip confirmation prompt (auto-confirm)

**Examples**:

**With Confirmation Prompt** (default):
```bash
python main.py truncate dnd_test

# Output:
# ⚠️  WARNING: This will delete ALL entries from collection 'dnd_test'.
# This action cannot be undone. Continue? (yes/no): yes
# 
# Truncating collection: dnd_test
# Deleted 294 entries from collection: dnd_test
# Collection dnd_test truncated successfully
# ✅ Truncated collection 'dnd_test' (294 entries deleted)
```

**Auto-confirm** (skip prompt):
```bash
python main.py truncate dnd_test --confirm

# Output:
# Truncating collection: dnd_test
# Deleted 294 entries from collection: dnd_test
# Collection dnd_test truncated successfully
# ✅ Truncated collection 'dnd_test' (294 entries deleted)
```

**Cancel Truncation**:
```bash
python main.py truncate dnd_monster_manual

# ⚠️  WARNING: This will delete ALL entries from collection 'dnd_monster_manual'.
# This action cannot be undone. Continue? (yes/no): no
# 
# Truncation cancelled.
```

**Use Cases**:
- Re-embedding collection with different embeddings
- Clearing test data
- Resetting collection after experiments
- Preparing for fresh import

**⚠️ Warning**:
- **Irreversible**: Cannot undo once confirmed
- **Preserves collection**: Collection still exists, just empty
- **Metadata kept**: Collection metadata and configuration remain
- **To fully delete**: Collection must be deleted via ChromaDB API (not through CLI)

**Error Handling**:
```bash
# Collection doesn't exist
python main.py truncate nonexistent_collection

# Error: Could not truncate collection 'nonexistent_collection'
# Details: Collection not found
```

---

### 8. `list-collections` - List ChromaDB Collections

**Purpose**: Display all available ChromaDB collections with their document counts.

**Syntax**:
```bash
python main.py list-collections
```

**Arguments**: None

**Options**: None

**Example**:
```bash
python main.py list-collections
```

**Output**:
```
Found 12 collection(s):

Name                           Count    ID
======================================================================
dnd_markdown                   1710     0831834a-4d02-4a8b-b9aa-1afadfccf5da
dnd_first_json                 356      0ea691e5-9934-4eb0-8ad2-61ee28101980
adnd_1e                        1002     128b18c5-881a-479f-bf50-7a3d9f3681a7
test_monster_manual            294      22876b04-1d97-4ae3-b667-f6fd610917fc
dnd_monster_manual_openai      294      5005abb7-d479-4153-96c6-25bb35b4075d
dnd_players_handbook           735      5f1f91dd-c2d2-42ef-99b6-e69e184bd9e5
dnd_dmg                        1184     677e984c-7575-423d-944e-8d90e6a12b64
dnd_phb                        735      76aad300-0068-4042-8bd0-d26ff0bdb86b
dnd_test                       0        8203ebef-3d9e-499c-bbbf-d4d9bebc2878
dnd_monster_manual             294      a7e72c13-0b42-4f5a-982e-b3b6be3d4cc3
test_collection                100      b9f83d24-1c53-4e6b-a83d-c4d7cf4e5dd4
production_mm                  294      c0g94e35-2d64-4f7b-b94e-d5e8dg5f6ee5
```

**Information Displayed**:
- **Name**: Collection name (used in query/embed commands)
- **Count**: Number of entries (chunks) in collection
- **ID**: Unique collection identifier (GUID)

**Use Cases**:
- Check available collections before querying
- Verify embedding success (check count)
- Find collection names for commands
- Monitor collection sizes

**Empty Result**:
```bash
python main.py list-collections

# No collections found.
```

---

## Complete Pipeline Example

**Goal**: Process Monster Manual from PDF to queryable database.

```bash
# Step 1: Activate virtual environment
source venv/bin/activate

# Step 2: Start ChromaDB server (if not running)
./scripts/start_chroma.sh

# Step 3: Verify ChromaDB is running
curl -s http://localhost:8060/api/v2/heartbeat

# Step 4: Convert PDF to markdown (use direct script, not CLI)
python src/converters/pdf_converter.py

# Step 5: Chunk the markdown
python main.py chunk data/markdown/Monster_Manual_(1e).md --type monster

# Step 6: Embed chunks into ChromaDB
python main.py embed data/chunks/chunks_Monster_Manual_(1e).json dnd_monster_manual --test

# Step 7: Query the collection
python main.py query dnd_monster_manual "What is a beholder?" --debug

# Step 8: List all collections
python main.py list-collections
```

---

## Environment Setup

### Prerequisites

**1. ChromaDB Server**:
```bash
# Start ChromaDB
./scripts/start_chroma.sh

# Verify running
curl -s http://localhost:8060/api/v2/heartbeat
# Should return: {"nanosecond heartbeat": <timestamp>}
```

**2. Environment Variables** (`.env` file):
```env
# OpenAI API
openai_api_key=sk-...

# ChromaDB Configuration
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/
```

**3. Virtual Environment**:
```bash
# Activate
source venv/bin/activate

# Verify
which python  # Should point to venv/bin/python
```

### Installation

```bash
# Clone repository
git clone <repo_url>
cd gravitycar_dnd1st_rag_system

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in editable mode
pip install -e .
```

---

## Common Workflows

### Workflow 1: Process New Rulebook

```bash
# 1. Convert PDF (if needed)
python src/converters/pdf_converter.py  # Process all PDFs

# 2. Chunk markdown
python main.py chunk data/markdown/Players_Handbook_(1e).md --type player

# 3. Embed into ChromaDB
python main.py embed data/chunks/chunks_Players_Handbook_(1e).json dnd_phb

# 4. Test queries
python main.py query dnd_phb --test
```

### Workflow 2: Re-embed Collection

```bash
# 1. Truncate existing collection
python main.py truncate dnd_monster_manual --confirm

# 2. Re-embed with same chunks
python main.py embed data/chunks/chunks_Monster_Manual_(1e).json dnd_monster_manual

# 3. Verify
python main.py list-collections
```

### Workflow 3: Interactive Q&A Session

```bash
# Start interactive mode
python main.py query dnd_monster_manual

# Ask multiple questions
# Question: What is a beholder?
# [Answer]
# Question: Tell me about dragons
# [Answer]
# Question: quit
```

### Workflow 4: Debug Retrieval Issues

```bash
# Query with full debug info
python main.py query dnd_phb "How many XP for fighter level 9?" \
  --debug \
  --show-context \
  -k 20

# Shows:
# - Retrieved chunks and scores
# - Gap detection analysis
# - Full context sent to LLM
# - Adaptive filtering decisions
```

### Workflow 5: Collection Management

```bash
# List all collections
python main.py list-collections

# Check specific collection
python main.py query dnd_test --test

# Clear if needed
python main.py truncate dnd_test --confirm

# Verify empty
python main.py list-collections  # dnd_test should show 0 count
```

---

## Error Handling

### Common Errors

**1. ChromaDB Not Running**:
```
Error: Could not connect to ChromaDB at localhost:8060
```
**Solution**: Start ChromaDB with `./scripts/start_chroma.sh`

**2. Missing OpenAI API Key**:
```
Error: OpenAI API key not found in environment
```
**Solution**: Add `openai_api_key=sk-...` to `.env` file

**3. File Not Found**:
```
Error: File not found: data/chunks/chunks_Monster_Manual.json
```
**Solution**: Check file path, ensure chunking step completed

**4. Collection Not Found**:
```
Error: Collection 'dnd_test' not found
```
**Solution**: Use `list-collections` to see available collections

**5. Invalid Chunk Format**:
```
Error: Could not detect chunk format
```
**Solution**: Ensure chunks file has valid Monster Manual or PHB format

---

## Tips & Best Practices

### Naming Conventions

**Collections**:
- Use descriptive names: `dnd_monster_manual`, `dnd_phb`, `dnd_dmg`
- Avoid spaces (use underscores)
- Include version/source: `dnd_monster_manual_openai`

**Files**:
- Keep original names: `Monster_Manual_(1e).md`
- Chunk files auto-named: `chunks_Monster_Manual_(1e).json`

### Query Optimization

**Comparison Queries**: Use "vs" or "compare":
```bash
python main.py query dnd_monster_manual "Compare owlbear vs orc"
# Entity detection expands retrieval automatically
```

**Specific Questions**: Be specific for better results:
```bash
# Good
python main.py query dnd_phb "How many XP does a fighter need for level 9?"

# Less good
python main.py query dnd_phb "Tell me about fighters"
```

**Adjust k for Context**:
- Simple questions: `-k 5` to `-k 10`
- Complex/comparison: `-k 20` to `-k 30`
- Default (`-k 15`) works for most queries

### Development Testing

**Use --test flag** when embedding:
```bash
python main.py embed data/chunks/chunks_Monster_Manual_(1e).json dnd_test --test
```

**Use --debug for development**:
```bash
python main.py query dnd_test "test query" --debug --show-context
```

**Clean up test collections**:
```bash
python main.py truncate dnd_test --confirm
```

---

## Advanced Usage

### Custom Retrieval Parameters

```bash
# High-precision retrieval (stricter threshold)
python main.py query dnd_monster_manual "What is a beholder?" \
  --distance-threshold 0.3 \
  -k 10

# Broad retrieval (more chunks, looser threshold)
python main.py query dnd_monster_manual "Tell me about monsters" \
  --distance-threshold 0.5 \
  -k 30

# Use GPT-4 for complex reasoning
python main.py query dnd_monster_manual "Compare combat strategies" \
  --model gpt-4
```

### Batch Processing

```bash
# Process multiple books
for book in Monster_Manual Players_Handbook Dungeon_Masters_Guide; do
  python main.py chunk "data/markdown/${book}_(1e).md"
  python main.py embed "data/chunks/chunks_${book}_(1e).json" "dnd_${book,,}"
done
```

### Scripted Workflows

```bash
#!/bin/bash
# automated_embed.sh

BOOK=$1
TYPE=$2

python main.py chunk "data/markdown/${BOOK}.md" --type "$TYPE"
python main.py embed "data/chunks/chunks_${BOOK}.json" "dnd_${BOOK}" --test
python main.py list-collections

# Usage: ./automated_embed.sh "Monster_Manual_(1e)" monster
```

---

## Getting Help

**Command Help**:
```bash
# General help
python main.py --help

# Command-specific help
python main.py query --help
python main.py embed --help
python main.py chunk --help
```

**Documentation**:
- **Architecture**: `docs/implementations/EmbedderArchitecture.md`
- **ChromaDB Connector**: `docs/implementations/ChromaDBConnector.md`
- **Adaptive Filtering**: `docs/implementations/adaptive_filtering.md`
- **Setup Guide**: `docs/setup/installation.md`

**Testing**:
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_monster_book_embedder.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## Version History

- **1.2** (October 21, 2025): Added ChromaDB Connector centralization
- **1.1** (October 21, 2025): Embedder refactoring (Orchestrator + Strategy pattern)
- **1.0** (October 2025): Initial CLI implementation

---

*For additional help, see project documentation in `docs/` directory or contact the development team.*
