# Phase 3 Quick Reference

## Installation
```bash
source venv/bin/activate
pip install docling
```

## Convert PDFs
```bash
# Basic conversion
python convert_pdfs_to_markdown.py

# With sample preview
python convert_pdfs_to_markdown.py --sample

# Custom PDF location
python convert_pdfs_to_markdown.py --pdf-dir /path/to/pdfs

# Force OCR (for scanned PDFs)
python convert_pdfs_to_markdown.py --force-ocr
```

## Inspect Results
```bash
# List markdown files
ls -lh dndmarkdown/

# View first 100 lines
head -n 100 dndmarkdown/players_handbook.md

# Compare with old text
diff dndtext/players_handbook.txt dndmarkdown/players_handbook.md | head -n 50
```

## What to Check
- [ ] All PDFs converted successfully
- [ ] Markdown files exist in `dndmarkdown/`
- [ ] Tables are properly formatted
- [ ] Headers use `##` syntax
- [ ] Text is readable and sequential
- [ ] No OCR garbage

## File Locations
- **Input PDFs:** `/home/mike/projects/dnd1st/pdf/*.pdf`
- **Output Markdown:** `./dndmarkdown/*.md`
- **Old Text Files:** `./dndtext/*.txt`

## Next Steps After Conversion
1. Inspect markdown quality
2. Compare with old text files
3. Run markdown chunking (next script)
4. Test with TinyLlama
5. Switch to OpenAI/Gemini

## Expected Timeline
- **Docling install:** 3-5 minutes
- **PDF conversion:** 5-10 minutes (all files)
- **Manual inspection:** 5 minutes
- **Total:** ~15-20 minutes

## Critical Success Factors
✅ **Must have:** Clean, readable markdown
✅ **Must have:** Tables properly formatted  
✅ **Nice to have:** Headers well-structured
⚠️ **Still expected:** TinyLlama will struggle (but less)
🎯 **End goal:** Clean data + OpenAI = working RAG system
