# Advanced RAG Strategies: Beyond Naive Chunking

## Current State: What We Did Wrong (And Why)

### Naive Chunking Problems We Observed:

1. **Arbitrary Boundaries**
   - Chunks split mid-sentence, mid-concept
   - Tables broken across multiple chunks
   - Section headers separated from content
   - Related information scattered

2. **No Semantic Understanding**
   - Doesn't know "ALIGNMENT" is a section header
   - Doesn't recognize tables vs narrative
   - Can't identify spell descriptions vs rules text
   - No concept of document structure

3. **Context Loss**
   - "Prismatic Spray" description might be split
   - XP table rows separated from headers
   - Related spells not grouped together

4. **Poor Metadata**
   - Only track: source file, chunk index
   - Missing: section, page, content type, hierarchy

---

## Better Chunking Strategies: The Full Spectrum

### Strategy 1: Semantic Chunking (RECOMMENDED FOR PHASE 2)

**Concept**: Use NLP to understand document structure and chunk by meaning.

#### Approach A: Header-Based Chunking
```
1. Parse document for headers (ALL CAPS, consistent patterns)
2. Create chunks based on section boundaries
3. Include header in chunk text for context

Example from DM Guide:
Chunk 1: "ALIGNMENT\n[entire alignment section]"
Chunk 2: "CHARACTER CLASSES\n[entire classes section]"
```

**Pros:**
- ✅ Preserves semantic units
- ✅ Headers provide context
- ✅ No mid-concept splits

**Cons:**
- ⚠️ Sections might be too large (need sub-chunking)
- ⚠️ Requires pattern recognition for headers

**Implementation Complexity:** Medium
**Expected Improvement:** 40-60%

---

#### Approach B: Recursive Chunking with Hierarchical Metadata
```
1. Identify document hierarchy (Chapter → Section → Subsection)
2. Chunk at lowest semantic level that fits size limit
3. Store hierarchical metadata

Example:
{
  "text": "Paladins must be lawful good...",
  "metadata": {
    "chapter": "CHARACTER CLASSES",
    "section": "SUB-CLASSES",
    "subsection": "PALADIN",
    "level": 3
  }
}
```

**Pros:**
- ✅ Rich metadata for filtering
- ✅ Can retrieve at different granularities
- ✅ Preserves document structure

**Cons:**
- ⚠️ Complex to implement
- ⚠️ Requires understanding document structure

**Implementation Complexity:** High
**Expected Improvement:** 60-80%

---

#### Approach C: Sentence-Window Chunking
```
1. Split by sentences using NLP (spaCy, NLTK)
2. Create chunks of N sentences
3. Add overlap of M sentences

Example:
Chunk 1: Sentences 1-10
Chunk 2: Sentences 8-17 (overlap at 8-10)
```

**Pros:**
- ✅ Never splits mid-sentence
- ✅ Clean boundaries
- ✅ Good for narrative text

**Cons:**
- ⚠️ Doesn't help with tables
- ⚠️ Variable chunk sizes
- ⚠️ OCR errors break sentence detection

**Implementation Complexity:** Low-Medium
**Expected Improvement:** 20-30%

---

### Strategy 2: Content-Aware Chunking

**Concept**: Different chunking strategies for different content types.

#### Implementation:
```python
def chunk_document(text, source_file):
    sections = detect_sections(text)
    
    for section in sections:
        content_type = classify_content(section)
        
        if content_type == "table":
            chunks.append(process_table(section))
        elif content_type == "spell_description":
            chunks.append(process_spell(section))
        elif content_type == "narrative":
            chunks.append(process_narrative(section))
```

#### Content Type Strategies:

**Tables:**
- Extract as structured data (CSV, JSON)
- Convert to natural language: "A fighter needs 250,000 XP for level 9"
- Store both structured + NL versions
- Add table headers to every row

**Spell Descriptions:**
- Keep complete spell as single chunk (even if large)
- Add metadata: spell_name, level, school, class
- Include cross-references to related spells

**Monster Stats:**
- Extract stats into structured format
- Add metadata: monster_name, HD, AC, alignment
- Keep descriptive text separate from stats

**Narrative Rules:**
- Use sentence-window chunking
- Preserve paragraph boundaries
- Add section context

**Pros:**
- ✅ Optimal handling per content type
- ✅ Dramatically better table retrieval
- ✅ Structured data enables filtering

**Cons:**
- ⚠️ Complex classification required
- ⚠️ Multiple processing pipelines
- ⚠️ High development time

**Implementation Complexity:** Very High
**Expected Improvement:** 70-90%

---

### Strategy 3: Hybrid Approach (PRAGMATIC CHOICE)

**Concept**: Start simple, add complexity where needed.

#### Phase 2A: Quick Wins (1-2 days)
1. **Header Detection**
   - Regex for ALL CAPS lines
   - Include header in next chunk
   - Split at section boundaries when possible

2. **Table Handling**
   - Detect tables (consistent spacing, dashes)
   - Keep complete tables together
   - OR convert to natural language

3. **Better Metadata**
   - Extract page numbers from context
   - Identify content type (simple heuristics)
   - Add book metadata (publication date, edition)

#### Phase 2B: Refinement (3-5 days)
4. **Semantic Overlap**
   - Instead of character overlap, use sentence overlap
   - Ensure no mid-sentence splits

5. **Entity Recognition**
   - Extract spell names, monster names, class names
   - Add as metadata for precise retrieval

6. **Hierarchical Context**
   - Track which section chunk belongs to
   - Include parent section in metadata

**Pros:**
- ✅ Incremental improvement
- ✅ Can measure impact of each change
- ✅ Manageable complexity

**Cons:**
- ⚠️ Not perfect
- ⚠️ Still some edge cases

**Implementation Complexity:** Medium
**Expected Improvement:** 50-70%

---

## Document Format Comparison

### Your Question: PDF vs Plain Text vs Other Formats?

| Format | Pros | Cons | Best For |
|--------|------|------|----------|
| **Plain Text** | ✅ Simple parsing<br>✅ No OCR errors<br>✅ Fast processing | ❌ No structure info<br>❌ No formatting<br>❌ Tables are messy | Starting point |
| **PDF** | ✅ Preserves layout<br>✅ Page boundaries<br>✅ May have structure | ❌ Needs PDF parser<br>❌ OCR may be bad<br>❌ Complex extraction | Published docs |
| **Markdown** | ✅ Clear structure<br>✅ Headers explicit<br>✅ Easy parsing | ❌ Need conversion<br>❌ Tables still tricky | Best option! |
| **HTML** | ✅ Semantic tags<br>✅ Table structure<br>✅ Hierarchy clear | ❌ May have cruft<br>❌ Inconsistent markup | Web sources |
| **JSON/XML** | ✅ Structured data<br>✅ Perfect for tables<br>✅ Metadata rich | ❌ Requires conversion<br>❌ Manual structuring | Ideal but labor-intensive |

### Verdict for Your Use Case:

**Current (Plain Text)**: 
- ✅ Good enough for learning
- ⚠️ Tables are problematic
- **Keep using for Phase 2**

**PDF Analysis**: Would PDF be better?
- **Maybe** - if PDFs have good structure (bookmarks, ToC)
- **Probably not** - OCR D&D books often have errors
- **Not worth it yet** - focus on improving text processing first

**Future Goal**: Convert to Markdown or structured JSON
- **Markdown**: Best balance of structure + simplicity
- **JSON**: Ideal for spells/monsters with consistent formats
- **Tool**: Could use GPT-4 to convert sections to structured format

---

## Advanced RAG Techniques Beyond Chunking

### Technique 1: Query Transformation

**Problem**: User asks "How much XP for fighter level 9?"
**Current**: Embed query as-is
**Better**: Transform to multiple queries:
- "fighter experience points ninth level"
- "fighter advancement table"
- "fighter level 9"

**Implementation**: Use LLM to generate query variations

**Expected Improvement**: 10-20% better retrieval

---

### Technique 2: Hypothetical Document Embeddings (HyDE)

**Problem**: Query embedding might not match document embedding style

**Solution**:
1. Ask LLM to write a hypothetical answer
2. Embed the hypothetical answer
3. Use that to search

**Example**:
```
Query: "How much XP for fighter level 9?"

HyDE generates: "A fighter requires 250,000 experience points 
to advance from level 8 to level 9 according to the 
advancement table in the Player's Handbook."

→ Embed this synthetic answer
→ Search with that embedding
```

**Expected Improvement**: 15-25% for complex queries

---

### Technique 3: Re-ranking

**Problem**: Top-K results might not be optimal order

**Solution**:
1. Retrieve top-20 chunks (oversampling)
2. Use cross-encoder to re-rank
3. Return top-5 best matches

**Expected Improvement**: 20-30% better precision

---

### Technique 4: Metadata Filtering

**Problem**: Searching all 2115 chunks is sometimes too broad

**Solution**: Pre-filter by metadata
```python
# Query: "What spells can a 5th level magic-user cast?"
results = collection.query(
    query_embedding=embed(query),
    where={
        "source_file": "players_handbook.txt",
        "content_type": "spell_list",
        "level": {"$lte": 3}  # 5th level MU casts up to 3rd level spells
    }
)
```

**Expected Improvement**: 30-50% for targeted queries

---

### Technique 5: Multi-Index Strategy

**Problem**: One size doesn't fit all

**Solution**: Create multiple collections:
- `spells_collection` - Just spell descriptions
- `monsters_collection` - Just monster entries  
- `rules_collection` - General rules text
- `tables_collection` - Extracted/converted tables

**Query Logic**:
1. Classify query type
2. Search appropriate collection(s)
3. Combine results

**Expected Improvement**: 40-60% for specific query types

---

## Recommended Phase 2 Implementation Plan

### Week 1: Quick Wins (20% → 50% success rate)

**Day 1-2: Header Detection & Section Chunking**
```python
def detect_headers(text):
    # Find lines that are ALL CAPS with specific patterns
    # Return list of (position, header_text)
    
def chunk_by_section(text, headers):
    # Split at header boundaries
    # Include header in chunk text
    # Add section metadata
```

**Day 3-4: Table Handling**
```python
def detect_table(text):
    # Look for consistent column spacing
    # Look for header rows
    
def convert_table_to_nl(table):
    # "A fighter needs 250,000 XP for level 9"
    # Store multiple NL sentences per table
```

**Day 5: Metadata Enrichment**
```python
metadata = {
    "source_file": "dm_guide.txt",
    "section": "CHARACTER CLASSES",
    "content_type": "table|spell|monster|narrative",
    "page_approx": estimate_page(chunk_position),
    "entity_names": extract_entities(text)
}
```

**Expected Result**: 
- Q2 (XP table) should improve dramatically
- Q3 (Prismatic Spray) might improve
- Better source citations

---

### Week 2: Advanced Techniques (50% → 70% success rate)

**Day 1-2: Sentence-Based Chunking**
- Install spaCy
- Implement sentence detection
- Re-chunk using sentence boundaries

**Day 3-4: Query Enhancement**
- Implement query expansion
- Add synonym handling (Magic-User = Wizard)
- Try HyDE for complex queries

**Day 5: Re-ranking**
- Implement cross-encoder re-ranking
- Test on difficult queries

---

### Week 3: Content-Aware Processing (70% → 85% success rate)

**Spell Processor**:
```python
def process_spell_section(text):
    spells = extract_individual_spells(text)
    for spell in spells:
        yield {
            "text": spell.full_description,
            "metadata": {
                "spell_name": spell.name,
                "level": spell.level,
                "school": spell.school,
                "classes": spell.classes,
                "content_type": "spell"
            }
        }
```

**Monster Processor**: Similar approach

**Table Processor**: Convert to structured + NL

---

## Tools & Libraries to Consider

### For Document Processing:
- **spaCy**: Sentence detection, NER
- **pypdf2 / pdfplumber**: If you decide to use PDFs
- **python-markdown**: If you convert to MD
- **BeautifulSoup**: If you have HTML versions

### For Advanced RAG:
- **sentence-transformers**: You already have this
- **rank-bm25**: Classical IR re-ranking
- **CrossEncoder**: For re-ranking
- **LangChain**: Has many RAG utilities (but adds complexity)

### For Structured Data:
- **pandas**: Table manipulation
- **sqlite**: Store structured extracts
- **pydantic**: Data validation

---

## Your Next Decision

Given that you want to **see the difference**, here's my recommendation:

### Immediate Next Step: Pick ONE improvement to implement

**Option A: Header-Based Chunking** (Easy, 30% improvement)
- 4-6 hours of work
- Immediate visible improvement
- Foundation for more work

**Option B: Table Conversion** (Medium, 40% improvement for Q2)
- 6-8 hours of work
- Solves your biggest failure case
- Very satisfying to see working

**Option C: Multi-Collection Strategy** (Medium, 35% improvement)
- 8-10 hours of work
- Professional approach
- Great learning experience

**My recommendation**: Start with **Option A** (header-based chunking), then **Option B** (tables).

This gives you tangible improvements without overwhelming complexity.

---

## Format Recommendation

**For your learning goals, stick with plain text** for Phase 2.

**Only move to PDF if**:
- You can't get better retrieval with text processing
- PDFs have significantly better structure
- You have 10+ hours to invest in PDF parsing

**Consider Markdown conversion** as a "Phase 3" optimization if you want to continue the project long-term.

---

## Question for You

What interests you more for Phase 2:

1. **Better chunking** (header detection, table handling) - improves what you retrieve
2. **Better LLM** (Groq API) - improves how answers are generated
3. **Both** - optimal but more work

Remember: Your retrieval is already 80% good. The LLM is your biggest bottleneck. But improving retrieval is great learning!

What sounds most interesting to you? 🎯
