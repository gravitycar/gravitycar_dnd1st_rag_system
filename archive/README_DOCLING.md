# D&D 1st Edition RAG System - Docling Pipeline

Complete RAG pipeline for Advanced Dungeons & Dragons 1st Edition rulebooks using high-quality Docling markdown extracts.

## Overview

This system uses:
- **PDF Processing**: Docling (high-quality table extraction)
- **Chunking**: Strategy 1 (Hybrid Semantic + Table-Aware)
- **Embeddings**: all-MiniLM-L6-v2 (384 dimensions)
- **Vector Store**: ChromaDB (HTTP mode, localhost:8060)
- **LLM**: OpenAI GPT-4o-mini (via API)

## Prerequisites

```bash
# Install required packages
pip install sentence-transformers chromadb openai python-dotenv

# Ensure ChromaDB server is running
# (Check with: curl http://localhost:8060/api/v1/heartbeat)
```

## Setup

1. **Environment Variables**
   - The `.env` file already contains your OpenAI API key as `gravitycar_openai_api_key`
   - No additional setup needed

2. **Source Files**
   - Player's Handbook: `dndmarkdown/docling/good_pdfs/Players_Handbook_(1e).md`
   - Monster Manual: `dndmarkdown/docling/good_pdfs/Monster_Manual.md`

## Complete Workflow

### Step 1: Chunk the Player's Handbook

```bash
python chunk_players_handbook_docling.py dndmarkdown/docling/good_pdfs/Players_Handbook_(1e).md
```

**What it does:**
- Parses the markdown into semantic chunks
- Each spell = 1 chunk
- Tables + their "Notes" sections merged
- Other sections chunked at `##` headers
- Outputs: `chunks_players_handbook.json`

**Expected output:**
```
Created XXX chunks

Chunk type breakdown:
  spell: ~200
  table: ~40
  major_section: ~30
  subsection: ~50
  ...
```

### Step 2: Embed Player's Handbook

```bash
python embed_docling.py chunks_players_handbook.json dnd_players_handbook
```

**What it does:**
- Loads chunks from JSON
- Generates embeddings using all-MiniLM-L6-v2
- Stores in ChromaDB collection `dnd_players_handbook`
- Automatically runs test query: "How many experience points does a fighter need for 9th level?"

**Expected output:**
```
Loaded XXX chunks
Embedding and storing chunks (batch size: 32)...
✅ Successfully embedded and stored XXX chunks!

TEST QUERY: How many experience points...
--- Result 1 (distance: 0.XXXX) ---
Title: FIGHTERS TABLE
Type: table
Content preview: ...
```

### Step 3: Query Player's Handbook

**Single Query:**
```bash
python query_docling.py dnd_players_handbook "How many XP does a fighter need for 9th level?"
```

**Test Mode (runs all test questions):**
```bash
python query_docling.py dnd_players_handbook --test
```

Test questions for Player's Handbook:
1. "How many experience points does a fighter need to reach 9th level?"
2. "What are the unique abilities that only thieves have?"
3. "What are the six character abilities in D&D?"

**Interactive Mode:**
```bash
python query_docling.py dnd_players_handbook
```

### Step 4: Process Monster Manual (Optional)

```bash
# Chunk
python chunk_monster_manual_docling.py dndmarkdown/docling/good_pdfs/Monster_Manual.md

# Embed
python embed_docling.py chunks_monster_manual.json dnd_monster_manual

# Query
python query_docling.py dnd_monster_manual "Tell me about owlbears"
```

## Query Options

```bash
# Retrieve more chunks (default: 5)
python query_docling.py dnd_players_handbook "fighter xp table" -k 10

# Show the context sent to GPT
python query_docling.py dnd_players_handbook "fighter xp table" --show-context

# Use a different OpenAI model
python query_docling.py dnd_players_handbook "fighter xp table" --model gpt-4

# Interactive mode with more context
python query_docling.py dnd_players_handbook -k 10
```

## Testing Your Critical Question

The Fighter XP table was **the acid test** for data quality:

```bash
python query_docling.py dnd_players_handbook \
  "How many experience points does a fighter need to become 9th level?" \
  --show-context
```

**What to expect:**
- Retrieved chunk should contain the complete FIGHTERS TABLE
- Table should show: `250,001—500,000 | 9 | 9 | Lord`
- GPT should correctly answer: "A fighter needs **250,001 experience points** to reach 9th level (Lord)"

## Comparison to Previous Phases

### Phase 1-2 (Naive/Semantic Chunking)
- **Data**: Broken text files from OCR
- **Result**: ❌ Garbage in → garbage out

### Phase 3A (Docling - First Attempt)
- **Problem**: ❌ CPU incompatibility (no AVX2 instructions)

### Phase 3B (PyMuPDF)
- **Data**: Markdown with broken tables
- **Fighter XP Table**: ❌ "18,00145,000", missing rows
- **Result**: ❌ Better but still unusable

### Phase 4 (LlamaParse)
- **Data**: Perfect JSON with intact tables
- **Problem**: ❌ Truncated paragraphs after 2 sentences
- **Result**: ❌ Tables great, prose broken

### **Phase 5 (Docling - Second Computer)**
- **Data**: ✅ Clean markdown, complete paragraphs, perfect tables
- **Fighter XP Table**: ✅ `250,001—500,000 | 9 | 9 | Lord`
- **Result**: ✅ **This is the winner!**

## File Structure

```
chroma/
├── .env                                    # OpenAI API key
├── chunk_players_handbook_docling.py       # Player's Handbook chunker
├── chunk_monster_manual_docling.py         # Monster Manual chunker
├── embed_docling.py                        # Universal embedder
├── query_docling.py                        # Query interface with OpenAI
├── chunks_players_handbook.json            # Output from step 1
├── chunks_monster_manual.json              # Output from monster manual
└── dndmarkdown/docling/good_pdfs/
    ├── Players_Handbook_(1e).md            # Source
    └── Monster_Manual.md                   # Source
```

## Troubleshooting

### ChromaDB Connection Error
```bash
# Check if ChromaDB is running
curl http://localhost:8060/api/v1/heartbeat

# If not, start it
docker run -p 8060:8000 chromadb/chroma
```

### OpenAI API Key Error
```bash
# Verify .env file exists and contains key
cat .env | grep gravitycar_openai_api_key

# Should show: gravitycar_openai_api_key=sk-...
```

### "Collection not found" Error
```bash
# List available collections
python -c "import chromadb; print([c.name for c in chromadb.HttpClient().list_collections()])"

# Re-run embedding step if collection missing
```

## Next Steps

After confirming this works with Player's Handbook:

1. **Test with remaining books** - Process all 5 PDFs
2. **Evaluate retrieval quality** - Are 5 chunks enough? Try k=10
3. **Compare LLMs** - Test gpt-4 vs gpt-4o-mini performance
4. **Optimize chunking** - Split large chunks if needed (>3000 chars)
5. **Add reranking** - Consider cross-encoder reranking for better precision
6. **Hybrid search** - Add BM25 for keyword matching (character names, spell names)

## Your Original Test Questions

Run these to validate the system:

```bash
# 1. Spell mechanics (should retrieve Charm Person spell chunk)
python query_docling.py dnd_players_handbook \
  "What happens when you cast charm person on someone? How long does it last and what are the effects?"

# 2. Fighter XP table (THE CRITICAL TEST)
python query_docling.py dnd_players_handbook \
  "How many experience points does a fighter need to become 9th level?"

# 3. Thief abilities
python query_docling.py dnd_players_handbook \
  "What are the unique abilities that only thieves can do?"

# 4. Comparative monsters (requires Monster Manual)
python query_docling.py dnd_monster_manual \
  "Who would win in a fight: an owlbear or a lizard man? Compare their stats."

# 5. Alignment rules
python query_docling.py dnd_players_handbook \
  "What happens if a paladin changes alignment? What are the rules?"
```

---

**Status**: ✅ Ready to test! Run Step 1-3 to validate the pipeline with Player's Handbook.
