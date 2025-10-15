# Phase 2: Header-Based Semantic Chunking

## 🎯 What We Built

A smarter chunking system that understands document structure instead of blindly splitting at character counts.

## 📁 New Files Created

1. **chunk_documents_semantic.py** - Intelligent header-based chunker
2. **embed_and_store_semantic.py** - Embeds semantic chunks into new collection
3. **query_rag_semantic.py** - Query interface for semantic collection
4. **compare_chunking.py** - Analysis tool comparing naive vs semantic

## 🚀 Step-by-Step Execution

### Step 1: Generate Semantic Chunks
```bash
python chunk_documents_semantic.py
```

**What it does:**
- Detects section headers (ALL CAPS patterns)
- Splits at semantic boundaries (sections, not arbitrary character counts)
- Includes header text in each chunk for context
- Classifies content types (narrative, table, list, toc)
- Skips Table of Contents sections
- Preserves tables when possible
- Creates `chunks_semantic.json`

**Expected output:** ~2000-2500 chunks (may differ from naive's 2115)

---

### Step 2: Compare Chunking Strategies (Optional)
```bash
python compare_chunking.py
```

**What it does:**
- Loads both `chunks_output.json` (naive) and `chunks_semantic.json` (semantic)
- Shows statistics comparison
- Displays example chunks
- Highlights improvements

**What to look for:**
- Content type distribution
- Chunk size variance
- Number of detected headers
- Table detection count

---

### Step 3: Embed and Store Semantic Chunks
```bash
python embed_and_store_semantic.py
```

**What it does:**
- Loads `chunks_semantic.json`
- Generates embeddings (same model: all-MiniLM-L6-v2)
- Creates NEW collection: `dnd_rulebooks_semantic`
- Stores with rich metadata

**Time estimate:** ~3-4 minutes (similar to naive)

**Note:** This creates a SEPARATE collection, so you can compare both!

---

### Step 4: Test with Queries
```bash
# Interactive mode
python query_rag_semantic.py --interactive

# Single question
python query_rag_semantic.py --question "How many experience points does a fighter need to become 9th level?"

# Custom K value
python query_rag_semantic.py --question "What are the effects of Prismatic Spray?" --k 3
```

**Special commands in interactive mode:**
- `/k=3 your question` - Use K=3 instead of default 5
- `/type=table your question` - Only search table chunks
- `quit` or `q` - Exit

---

## 🔍 Key Improvements Over Naive

### 1. **Section Awareness**
- **Naive:** Splits mid-paragraph at character 2000
- **Semantic:** Splits at section boundaries

### 2. **Header Context**
- **Naive:** No context about what section chunk came from
- **Semantic:** Every chunk knows its section header

Example:
```
Section: MAGIC USER SPELL DESCRIPTIONS
Content: Prismatic Spray creates a cone...
```

### 3. **Content Type Classification**
- **Naive:** All chunks treated identically
- **Semantic:** Chunks tagged as narrative, table, list, or toc

### 4. **Table Preservation**
- **Naive:** Tables split arbitrarily
- **Semantic:** Tables kept together when possible (up to 4000 chars)

### 5. **TOC Filtering**
- **Naive:** Table of Contents chunked and embedded (useless)
- **Semantic:** TOC sections detected and skipped

---

## 📊 Expected Improvements

### Test Question 2 (Fighter XP Table)
- **Before:** Retrieved table chunks but split poorly
- **After:** Should retrieve complete table with header context
- **Expected improvement:** 40-50%

### Test Question 1 (Prismatic Spray)
- **Before:** Might split spell description
- **After:** Spell description kept with "SPELLS" header
- **Expected improvement:** 30%

### Test Question 3 (Thief Abilities)
- **Before:** Mixed chunks from different sections
- **After:** Clear section headers help LLM understand context
- **Expected improvement:** 20-30%

### Overall
- **Retrieval:** Should go from A+ to A++ (already excellent, minor gains)
- **Context Quality:** Should improve significantly (headers help LLM)
- **LLM Performance:** Might improve 20-40% (better context = better answers)

---

## 🤔 What Could Still Go Wrong?

1. **TinyLlama still too weak** - Even with better chunks, 1.1B params might not be enough
2. **Tables still text-based** - Plain text tables aren't ideal (Phase 3: convert to natural language)
3. **No cross-referencing** - Questions spanning multiple sections might still struggle

---

## 📈 Next Steps After Testing

### If results improve significantly (50%+ success rate):
✅ Header chunking worked!
→ Consider implementing table conversion (Phase 3a)
→ Stay with TinyLlama a bit longer

### If results improve moderately (30-40% success rate):
⚠️ Better, but LLM still bottleneck
→ Test one question with Groq API to confirm
→ Likely need to switch LLM

### If results don't improve much (<30% success rate):
❌ Problem is LLM, not retrieval
→ Switch to Groq API (Llama3-70B or Mixtral)
→ Header chunking still helps but won't fix weak LLM

---

## 🧪 Suggested Test Sequence

1. **Run all 5 test questions with semantic chunks**
2. **Document results in `phase2_test_results.md`** (create this file)
3. **Compare to phase1_test_results.md**
4. **Calculate improvement percentage per question**
5. **Decide on Phase 3** (table conversion vs LLM upgrade)

---

## 📝 Manual Testing Template

For each question, record:

```markdown
### Question X: [Question text]

**Retrieval:**
- Chunks retrieved: [number]
- Relevant: [yes/no for each]
- Headers present: [list section headers]
- Content types: [narrative/table/list]
- Grade: [A/B/C/D/F]

**Generation:**
- Answer: [paste answer]
- Correct: [yes/no]
- Issues: [list problems]
- Grade: [A/B/C/D/F]

**Improvement vs Naive:**
- Retrieval: [better/same/worse]
- Generation: [better/same/worse]
- Overall: [+X% improvement]
```

---

## 🎓 What You're Learning

1. **Document Structure Matters** - Understanding layout improves retrieval
2. **Metadata is Powerful** - Section headers, content types help filter/rank
3. **Semantic Boundaries** - Natural splits > arbitrary character counts
4. **Content Type Detection** - Tables need different handling than narrative
5. **Trade-offs** - More complex chunking = slower processing but better quality

---

## ⚡ Quick Commands Reference

```bash
# Generate semantic chunks
python chunk_documents_semantic.py

# Compare strategies
python compare_chunking.py

# Embed and store
python embed_and_store_semantic.py

# Test interactively
python query_rag_semantic.py --interactive

# Run single test question
python query_rag_semantic.py --question "What can Thieves do that other character classes cannot do?"

# Use original naive collection (for comparison)
python query_rag.py --question "same question"
```

---

## 💡 Pro Tips

1. **Test one question both ways** - Run same question on naive vs semantic to see difference
2. **Watch the headers** - Notice how retrieved chunks now show section context
3. **Check content types** - See if tables are being detected correctly
4. **Compare retrieval times** - Should be similar (~0.05s)
5. **Note metadata richness** - Semantic chunks have much more context

---

## 🐛 Troubleshooting

**"No headers detected" warning:**
- Some files might not have clear header patterns
- Falls back to paragraph-based chunking (still better than naive)

**Collection not found:**
- Make sure you ran `embed_and_store_semantic.py` first
- Collection name is `dnd_rulebooks_semantic` (not `dnd_rulebooks`)

**Fewer chunks than naive:**
- This is EXPECTED! Semantic chunking is more efficient
- Keeping sections together reduces redundancy

**Retrieval seems slower:**
- Should be same speed (~50ms)
- If slower, might be ChromaDB issue (restart it)

---

## 🎯 Success Criteria for Phase 2

**Minimum Success:**
- ✅ Chunks created successfully
- ✅ Headers detected in most files
- ✅ Tables identified
- ✅ Queries return results with section context

**Good Success:**
- ✅ Test Q2 (Fighter XP) improves to C+ or better
- ✅ At least 2/5 questions show improvement
- ✅ Retrieval maintains A-grade quality

**Excellent Success:**
- ✅ 3+ questions improve significantly
- ✅ Success rate jumps from 20% to 40%+
- ✅ Clear evidence that header context helps LLM

---

## 📚 Ready to Start!

Run this command to begin:

```bash
python chunk_documents_semantic.py
```

Then follow the steps above! Good luck! 🚀
