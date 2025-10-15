# Phase 3: Docling PDF Processing

## 🎯 The Strategy Shift

You made an **excellent observation**: The source text files are garbage. Even a human struggles to parse them, so why would an AI do better?

**Key insight:** Docling can parse PDFs intelligently, preserving:
- Document structure (headers, sections)
- Table formatting
- Reading order
- Proper markdown formatting

---

## 📋 Implementation Plan

### Step 1: Install Docling
```bash
pip install docling
```

**Expected dependencies:** Docling will pull in PyTorch, transformers, and PDF parsing libraries. This might take a few minutes.

### Step 2: Convert PDFs to Markdown
Run the conversion script (see below) to process all PDFs in `/home/mike/projects/dnd1st/pdf/`

**Output:** Clean markdown files in `dndmarkdown/` directory

### Step 3: Chunk Markdown Intelligently
Use markdown-aware chunking (respects headers, code blocks, tables)

### Step 4: Embed and Store
Same process as before, but with much cleaner source data

### Step 5: Test with TinyLlama
Final test to see if better source data helps (it will, but LLM still bottleneck)

### Step 6: Switch to OpenAI or Gemini
After proving data quality matters, upgrade LLM

---

## 🔧 Installation Instructions

### In your venv:
```bash
# Activate venv (if not already)
source venv/bin/activate

# Install Docling
pip install docling

# This will install:
# - torch (PyTorch for ML models)
# - transformers (Hugging Face)
# - pdfplumber or similar PDF parser
# - easyocr (for OCR if needed)
# - Various dependencies
```

**Note:** Docling is a heavy package (~2-3GB with dependencies). On your hardware, this might take 5-10 minutes to install.

---

## 📊 Expected Improvements

### What Docling Will Fix:

**1. Table Structure**
- **Before:** `8,ooo 18,00145,000` (mangled)
- **After:** Proper markdown tables with headers

**2. Headers**
- **Before:** Random ALL CAPS mixed with text
- **After:** Proper `## Header` markdown syntax

**3. Reading Order**
- **Before:** Text from columns mixed randomly
- **After:** Correct sequential reading order

**4. Lists**
- **Before:** Numbers and text jumbled
- **After:** Proper markdown lists `1. Item`

**5. OCR Quality**
- **Before:** Manual text extraction artifacts
- **After:** AI-powered OCR with better accuracy

---

## 🚀 The Scripts

See below for:
1. `convert_pdfs_to_markdown.py` - PDF → Markdown converter
2. `chunk_markdown.py` - Markdown-aware chunker
3. `embed_and_store_markdown.py` - Store in ChromaDB
4. `query_rag_markdown.py` - Query interface

---

## 💰 LLM Choice After This

### OpenAI (Recommended):
- **Model:** GPT-4o-mini ($0.15/1M input tokens, $0.60/1M output)
- **Cost estimate:** ~$0.50-2.00 for your testing
- **Quality:** Excellent, industry standard
- **Speed:** Very fast (~1-2 seconds per query)
- **API:** Simple, well-documented

### Google Gemini:
- **Model:** Gemini 1.5 Flash ($0.075/1M input tokens, $0.30/1M output)
- **Cost estimate:** ~$0.25-1.00 for your testing
- **Quality:** Excellent, competitive with GPT-4
- **Speed:** Very fast
- **API:** Google Cloud setup required

### My Recommendation: **OpenAI GPT-4o-mini**
- Cheaper for your use case
- Simpler API
- Better documentation
- Free tier: $5 credit for new accounts

---

## 📈 Expected Results Timeline

### After Docling Processing:
- **Retrieval:** A+ → A++ (cleaner chunks)
- **Context quality:** D → B+ (proper formatting)
- **LLM with TinyLlama:** F → D (still weak, but better)

### After OpenAI Switch:
- **Generation:** F → A- (dramatic improvement)
- **Success rate:** 0% → 70-80%
- **Response time:** 5 minutes → 2 seconds

---

## 🤔 Why This Approach is Smart

You're addressing **both** bottlenecks:
1. **Garbage data** → Docling fixes this
2. **Weak LLM** → OpenAI/Gemini fixes this

This is the right sequence:
1. Fix what you can control (data quality)
2. Prove it helps
3. Then fix what you can't control locally (LLM)

**Learning value maintained** - You'll understand how document parsing affects RAG quality.

---

## ⚠️ Potential Issues

### Docling Installation:
- **Large download:** ~2-3GB
- **Slow on old hardware:** First run will download ML models
- **Memory usage:** Docling uses ~2-4GB RAM during conversion

### PDF Conversion:
- **Time:** ~5-10 minutes for all PDFs (with your CPU)
- **Quality varies:** Depends on PDF quality (scanned vs digital)
- **OCR needed?** If PDFs are scanned images, OCR adds time

### Hardware Constraints:
- Your 3rd gen Intel will struggle with Docling's ML models
- Expect 1-2 minutes per PDF
- But this is **one-time processing**

---

## 🎯 Success Criteria

### Minimum Success (Data Quality):
- ✅ PDFs convert without errors
- ✅ Markdown has proper headers
- ✅ Tables are formatted correctly
- ✅ Text is readable and sequential

### Good Success (TinyLlama Improvement):
- ✅ TinyLlama success rate improves from 0% to 20-30%
- ✅ At least one question answered correctly
- ✅ Fewer hallucinations (better grounding)

### Excellent Success (OpenAI Validation):
- ✅ OpenAI achieves 70%+ success rate
- ✅ Sub-2-second response times
- ✅ Tables parsed correctly
- ✅ Cost under $2 for full test suite

---

## 📝 Next Steps

1. **Install Docling** - Run: `pip install docling`
2. **Run conversion script** - Process all PDFs
3. **Inspect markdown files** - Manually check quality
4. **Re-test with TinyLlama** - See if data quality helps
5. **Switch to OpenAI** - Final validation with capable LLM

---

Ready to begin? Start with:

```bash
pip install docling
```

Then run the conversion script (next file I'll create).
