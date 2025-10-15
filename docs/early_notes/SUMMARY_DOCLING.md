# Summary: Complete Docling-Based RAG Pipeline

## What We've Built

Three specialized scripts for processing D&D 1st Edition rulebooks from high-quality Docling markdown:

### 1. **chunk_players_handbook_docling.py** 
**Strategy 1: Hybrid Semantic + Table-Aware Chunking**

- ✅ Each spell = individual chunk (200 spells × ~200 chars each)
- ✅ Tables + "Notes Regarding..." sections merged together
- ✅ Character class sections preserved as units
- ✅ Detects chunk types: `spell`, `table`, `major_section`, `subsection`, `text_section`
- ✅ Metadata: title, type, char_count, spell_school (for spells)

**Why this works:** Respects the document's semantic structure while keeping related content together.

### 2. **chunk_monster_manual_docling.py**
**Encyclopedia-Style Chunking**

- ✅ Each monster = complete entry (one chunk per creature)
- ✅ Extracts metadata: monster_name, hit_dice, armor_class, creature_type
- ✅ Auto-categorizes: dragon, fiend, elemental, giant, humanoid
- ✅ Preserves all stats and description together

**Why this works:** Monster Manual is naturally structured as discrete entries.

### 3. **embed_docling.py**
**Universal Embedder for Both Books**

- ✅ Uses all-MiniLM-L6-v2 (384 dimensions, fast, good quality)
- ✅ Connects to ChromaDB HTTP server (localhost:8060)
- ✅ Batch processing (32 chunks at a time)
- ✅ Rich metadata preservation
- ✅ Automatic test queries after embedding

**Usage:**
```bash
python embed_docling.py chunks_players_handbook.json dnd_players_handbook
python embed_docling.py chunks_monster_manual.json dnd_monster_manual
```

### 4. **query_docling.py**
**Query Interface with OpenAI**

- ✅ Uses OpenAI GPT-4o-mini (via API key from .env)
- ✅ Retrieves top-K chunks from ChromaDB
- ✅ Formats context with section headers
- ✅ Specialized system prompt for D&D rules
- ✅ Three modes: single query, test mode, interactive

**Key Features:**
- `--test`: Runs predefined test questions
- `--show-context`: Shows what's sent to GPT
- `-k N`: Retrieve N chunks (default: 5)
- `--model`: Choose OpenAI model

## The Critical Test Case

**Question:** "How many experience points does a fighter need for 9th level?"

**Why this matters:** 
- PyMuPDF version had broken table: "18,00145,000" (gibberish)
- LlamaParse had perfect table but truncated prose
- **Docling has both:** Perfect table + complete text

**Expected result:**
```
FIGHTERS TABLE
| Experience Points | Experience Level | Hit Points | Level Title |
|-------------------|------------------|------------|-------------|
| 250,001—500,000   | 9                | 9          | Lord        |

Answer: A fighter needs 250,001 experience points to reach 9th level.
```

## What Makes This Different from Previous Attempts

| Phase | Tool | Problem | Result |
|-------|------|---------|--------|
| 1-2 | OCR text | Broken data | ❌ Failed |
| 3A | Docling | CPU incompatible | ❌ Can't run |
| 3B | PyMuPDF | Broken tables | ❌ Wrong answers |
| 4 | LlamaParse | Truncated text | ❌ Incomplete |
| **5** | **Docling (2nd PC)** | **Perfect data** | **✅ READY** |

## Configuration Notes

### .env File
- ✅ Already contains: `gravitycar_openai_api_key=sk-...`
- ✅ Scripts use `python-dotenv` to load automatically
- ✅ No need to expose key in command line

### OpenAI Model Choice
- **Default**: `gpt-4o-mini` (fast, cheap, good enough)
- **Alternative**: `gpt-4` (slower, expensive, more accurate)
- **Cost**: ~$0.01 per test run with gpt-4o-mini

### ChromaDB
- **Mode**: HTTP client (not persistent client)
- **Host**: localhost:8060
- **Collections**: Separate for each book
  - `dnd_players_handbook`
  - `dnd_monster_manual`

## Architecture Decisions

### Why Strategy 1 for Player's Handbook?
✅ **Respects semantic boundaries** - Spells, tables, class descriptions stay intact  
✅ **Handles inconsistent markdown** - Docling's mixed case headers handled gracefully  
✅ **Preserves table context** - "Notes Regarding X" merged with table X  
❌ **May create large chunks** - But that's acceptable for now (will split later if needed)

### Why Encyclopedia for Monster Manual?
✅ **Natural structure** - Each monster is self-contained  
✅ **Complete information** - Stats + description together  
✅ **Easy retrieval** - "Tell me about owlbears" → gets complete owlbear entry  
✅ **Consistent size** - Monster entries are fairly uniform (~500-2000 chars)

### Why all-MiniLM-L6-v2?
✅ **Fast** - 384 dimensions, encodes quickly  
✅ **Good quality** - Well-tested, general-purpose  
✅ **Local** - No API calls for embeddings  
❌ **Not domain-specific** - Could fine-tune later on D&D corpus  
❌ **Small dimensions** - Might miss nuances (vs 768 or 1536 dims)

### Why OpenAI instead of TinyLlama?
✅ **Proven quality** - GPT-4o-mini is competent  
✅ **Table interpretation** - Can parse markdown tables correctly  
✅ **Instruction following** - Understands "answer based on context"  
✅ **Cost effective** - $0.15 per 1M tokens input  
❌ **Not local** - Requires API key and internet  
❌ **Cost** - TinyLlama was free (but terrible)

## Testing Strategy

### Phase 1: Validate Data Quality
Run chunker and manually inspect `chunks_players_handbook.json`:
```bash
python chunk_players_handbook_docling.py dndmarkdown/docling/good_pdfs/Players_Handbook_(1e).md
# Check: Does FIGHTERS TABLE chunk contain "250,001—500,000"?
```

### Phase 2: Test Retrieval
Run embedder with test query:
```bash
python embed_docling.py chunks_players_handbook.json dnd_players_handbook
# Check: Does it retrieve FIGHTERS TABLE for the XP question?
```

### Phase 3: Test Generation
Run query with critical test:
```bash
python query_docling.py dnd_players_handbook \
  "How many experience points does a fighter need for 9th level?" \
  --show-context
# Check: Does GPT correctly answer "250,001"?
```

### Phase 4: Full Test Suite
```bash
python query_docling.py dnd_players_handbook --test
# Runs all 3 Player's Handbook test questions
```

## What Could Go Wrong

### Problem: "Import openai could not be resolved"
**Solution:** `pip install openai`

### Problem: "Collection not found"
**Solution:** Re-run `embed_docling.py` to create the collection

### Problem: ChromaDB connection refused
**Solution:** Start ChromaDB server or check if running on different port

### Problem: OpenAI API key not found
**Solution:** Check `.env` file exists and contains `gravitycar_openai_api_key=...`

### Problem: Chunks too large (>3000 chars)
**Solution:** Update chunker to split at paragraph boundaries (`\n\n`)

### Problem: Retrieved chunks not relevant
**Solution:** 
- Increase k (try k=10 instead of k=5)
- Check if query embedding is good
- Consider hybrid search (BM25 + semantic)

## Success Criteria

✅ **Chunker produces valid JSON** with expected chunk types  
✅ **Embedder successfully stores all chunks** in ChromaDB  
✅ **Retrieval finds correct chunks** for test queries  
✅ **GPT generates accurate answers** based on retrieved context  
✅ **Critical test passes:** Fighter 9th level = 250,001 XP

## Next Actions

1. **Run setup script**: `bash setup_docling.sh`
2. **Chunk handbook**: `python chunk_players_handbook_docling.py ...`
3. **Embed handbook**: `python embed_docling.py chunks_players_handbook.json dnd_players_handbook`
4. **Test system**: `python query_docling.py dnd_players_handbook --test`
5. **Celebrate** 🎉 (if it works)
6. **Debug** 🔧 (if it doesn't)

---

**Key Insight:** This is your **5th attempt** at solving the data quality problem. Docling (on compatible hardware) finally gives you what you need: **perfect tables AND complete text**. No more fighting with broken PDFs—time to test if the RAG architecture actually works with good data!
