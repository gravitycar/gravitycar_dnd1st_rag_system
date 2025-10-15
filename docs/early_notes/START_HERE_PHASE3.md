# 🚀 Phase 3: Start Here - Docling PDF Processing

## Your Excellent Insight

You're **absolutely correct**: The text files are garbage. Even you struggle to parse them, so expecting TinyLlama to make sense of mangled text was unrealistic.

**This is the right move.** Fix the source data quality first.

---

## 📋 Step-by-Step Instructions

### Step 1: Install Docling

```bash
# Make sure you're in your venv
source venv/bin/activate

# Install docling
pip install docling
```

**What to expect:**
- Download size: ~500MB-1GB (depending on dependencies already installed)
- Installation time: 3-5 minutes
- Will install: PyTorch, transformers, PDF parsing libraries, OCR tools

**If you see warnings about PyTorch:** That's normal. Docling will work CPU-only on your system.

---

### Step 2: Convert PDFs to Markdown

```bash
python convert_pdfs_to_markdown.py
```

**What this does:**
- Reads all PDFs from `/home/mike/projects/dnd1st/pdf/`
- Uses Docling's AI models to understand document structure
- Exports clean markdown to `dndmarkdown/` directory
- Preserves tables, headers, and reading order

**Expected time:** 1-2 minutes per PDF on your hardware (5-10 min total)

**Output files:**
- `dndmarkdown/dm_guide.md`
- `dndmarkdown/players_handbook.md`
- `dndmarkdown/monster_manual.md`
- `dndmarkdown/field_folio.md`
- `dndmarkdown/deities_demigods.md` (if it exists)

---

### Step 3: Inspect the Results

```bash
# View sample of converted markdown
python convert_pdfs_to_markdown.py --sample

# Or manually inspect
head -n 100 dndmarkdown/players_handbook.md
```

**What to look for:**
- ✅ Headers formatted as `## Header Name`
- ✅ Tables with proper markdown syntax
- ✅ Lists with proper numbering
- ✅ Text in correct reading order
- ❌ No random OCR garbage
- ❌ No jumbled columns

---

### Step 4: Compare with Old Text Files

Let's see the difference:

```bash
# Old text file (first 50 lines)
head -n 50 dndtext/players_handbook.txt

# New markdown (first 50 lines)  
head -n 50 dndmarkdown/players_handbook.md
```

You should immediately see **massive** quality improvement.

---

## 🤔 What If PDF Directory Doesn't Exist?

If you see this error:
```
❌ Error: PDF directory not found: /home/mike/projects/dnd1st/pdf
```

Then either:

**Option A: Update the path**
```bash
python convert_pdfs_to_markdown.py --pdf-dir /actual/path/to/pdfs
```

**Option B: Use test PDF**
```bash
# Test with a sample PDF first
python convert_pdfs_to_markdown.py --pdf-dir ~/Downloads --output-dir test_markdown
```

---

## ⚠️ Troubleshooting

### "ModuleNotFoundError: No module named 'docling'"
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall
pip install docling
```

### "Out of memory" or system freeze
Docling uses ML models that need RAM. If your system struggles:

```bash
# Process one PDF at a time by moving others temporarily
mkdir pdf_backup
mv /path/to/pdfs/*.pdf pdf_backup/
mv pdf_backup/players_handbook.pdf /path/to/pdfs/
python convert_pdfs_to_markdown.py
# Repeat for each PDF
```

### PDFs are scanned images (OCR needed)
```bash
python convert_pdfs_to_markdown.py --force-ocr
```

This is **much slower** but handles scanned PDFs better.

---

## 📊 What Happens After Conversion?

Once you have clean markdown files, we'll:

1. **Create markdown-aware chunker** (respects markdown structure)
2. **Embed and store in ChromaDB** (new collection: `dnd_rulebooks_markdown`)
3. **Test with TinyLlama** (see if data quality helps)
4. **Switch to OpenAI** (if TinyLlama still struggles)

---

## 💡 Why This Will Help

### Before (Text Files):
```
FIGHTERS TABLE
Experience
-1
8,ooo
18,00145,000
35,001-70,OOO
```
↑ Impossible to parse

### After (Markdown):
```markdown
## FIGHTERS TABLE

| Experience Points | Level |
|-------------------|-------|
| 0-2,000          | 1     |
| 2,001-4,000      | 2     |
| 4,001-8,000      | 3     |
```
↑ LLM can actually read this!

---

## 🎯 Success Criteria for This Phase

### Minimum:
- ✅ All PDFs convert without errors
- ✅ Markdown files are readable
- ✅ No worse than text files

### Good:
- ✅ Tables properly formatted
- ✅ Headers clearly marked with `##`
- ✅ Text in correct order

### Excellent:
- ✅ Even YOU can easily read the markdown
- ✅ Tables are perfect
- ✅ No OCR artifacts
- ✅ Ready for intelligent chunking

---

## 🚀 Ready to Begin!

Run this command to start:

```bash
pip install docling
```

Then:

```bash
python convert_pdfs_to_markdown.py
```

After conversion completes, report back:
1. Did all PDFs convert successfully?
2. How long did it take?
3. Do the markdown files look good?
4. Are tables formatted correctly?

Then we'll move to Phase 3b (markdown chunking) and finally Phase 3c (OpenAI integration)!
