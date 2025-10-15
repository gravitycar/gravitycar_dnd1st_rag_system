# Monster Encyclopedia Chunker

**File**: `src/chunkers/monster_encyclopedia.py`  
**Purpose**: Intelligent chunking of the AD&D 1st Edition Monster Manual with category awareness and nested entry handling.

---

## Overview

The Monster Encyclopedia Chunker is designed to parse the Monster Manual markdown into semantically meaningful chunks that preserve:

1. **Category hierarchies** (e.g., DEMON, DRAGON, GIANT)
2. **Individual monster entries** (nested under categories when applicable)
3. **Monster statistics** (FREQUENCY, NO. APPEARING, ARMOR CLASS, etc.)
4. **Descriptive text** (abilities, behavior, ecology)

Unlike generic chunking strategies, this chunker understands the **unique structure** of AD&D monster entries and creates chunks that are optimal for retrieval.

---

## Key Features

### 1. Category vs. Monster Detection

The chunker distinguishes between two types of entries:

#### **Top-Level Categories**
Entries like DEMON, DRAGON, ELEMENTAL that have nested monsters beneath them.

**Detection Pattern:**
```python
# Category detected when:
1. Entry has descriptive text
2. FOLLOWED BY nested entries with statistics
```

**Example**: DEMON
- Has general demon description
- Contains nested entries: Orcus, Demogorgon, Juiblex, etc.

#### **Standalone Monsters**
Entries with statistics and description that are NOT nested under a category.

**Detection Pattern:**
```python
# Standalone detected when:
1. Entry has statistics block
2. NOT preceded by category with same parent
```

**Example**: Owlbear
- Has statistics block
- Has description
- No parent category

### 2. Statistics Extraction

Monster statistics are **critical** for retrieval and must be captured accurately.

#### **Statistics Block Format**

```
FREQUENCY: Rare
NO. APPEARING: 1-6
ARMOR CLASS: 5
MOVE: 12"
HIT DICE: 5+2
% IN LAIR: 35%
TREASURE TYPE: C
NO. OF ATTACKS: 3
DAMAGE/ATTACK: 1-6/1-6/2-12
SPECIAL ATTACKS: Hug
SPECIAL DEFENSES: Nil
MAGIC RESISTANCE: Standard
INTELLIGENCE: Low
ALIGNMENT: Neutral
SIZE: L (8' tall)
PSIONIC ABILITY: Nil
    Attack/Defense Modes: Nil
LEVEL/X.P. VALUE: V/250 + 3/hp
```

#### **Extraction Strategy**

1. **Line-by-line parsing**: Each statistic is on its own line
2. **Pattern matching**: `STAT NAME: value`
3. **Structured storage**: Stored as dictionary for easy access
4. **Text prepending**: Statistics embedded in chunk text for searchability

**Why Prepending Matters:**
```python
# Without prepending (BAD):
chunk_text = "Owlbears are fierce, avian-headed bears..."
# Retrieval: "How many HP does owlbear have?" → Miss

# With prepending (GOOD):
chunk_text = """
FREQUENCY: Rare
NO. APPEARING: 1-6
ARMOR CLASS: 5
...
Owlbears are fierce, avian-headed bears...
"""
# Retrieval: "How many HP does owlbear have?" → Hit!
```

### 3. Nested Entry Handling

Some entries have **complex nesting** that must be preserved:

#### **Example: DEMON Category**

```
DEMON (parent category)
├── General demon description
├── Orcus (nested monster)
│   ├── Statistics
│   └── Description
├── Demogorgon (nested monster)
│   ├── Statistics
│   └── Description
└── Juiblex (nested monster)
    ├── Statistics
    └── Description
```

#### **Metadata Linkage**

Each nested monster chunk includes:
```python
{
    "type": "monster",
    "title": "Demon: Orcus",
    "category": "DEMON",
    "statistics": {...},
    "text": "..."
}
```

This allows retrieval of:
- **Specific monster**: "Tell me about Orcus" → Finds Orcus chunk
- **Category overview**: "Tell me about demons" → Finds DEMON category chunk
- **Related monsters**: System can query by category metadata

### 4. Page Number Tracking

Page numbers are preserved from markdown comments:

```markdown
<!-- Page 46 -->
```

**Benefits:**
- Citation tracking
- Source verification
- Manual lookup for users
- Debugging

---

## Algorithm

### High-Level Flow

```
1. Parse markdown line-by-line
2. Detect headers (##, ###)
3. Accumulate content under each header
4. When next header found:
   a. Check if current entry is category or monster
   b. Extract statistics (if present)
   c. Create chunk with metadata
   d. Store in output array
5. Save to JSON file
```

### Category Detection Logic

```python
def is_category(entry):
    """
    A category entry has:
    1. Descriptive text
    2. Nested entries beneath it
    """
    has_description = len(entry['text']) > 0
    has_nested_entries = detect_nested_entries(entry)
    return has_description and has_nested_entries

def detect_nested_entries(entry):
    """
    Look ahead in the markdown to see if subsequent
    entries share the same parent category.
    """
    # Implementation details...
```

### Statistics Extraction

```python
def extract_statistics(text):
    """
    Parse statistics block from text.
    
    Returns:
        dict: {
            'FREQUENCY': 'Rare',
            'NO. APPEARING': '1-6',
            'ARMOR CLASS': '5',
            ...
        }
    """
    stats = {}
    stat_pattern = r'^([A-Z\s/\.]+):\s*(.+)$'
    
    for line in text.split('\n'):
        match = re.match(stat_pattern, line)
        if match:
            stat_name = match.group(1).strip()
            stat_value = match.group(2).strip()
            stats[stat_name] = stat_value
    
    return stats
```

---

## Output Format

### Chunk Structure

```json
{
  "type": "monster|category",
  "title": "Monster Name" or "Category: Nested Name",
  "text": "Full text with statistics prepended",
  "metadata": {
    "page": 46,
    "category": "DEMON" or null,
    "character_count": 1234
  },
  "statistics": {
    "FREQUENCY": "Rare",
    "NO. APPEARING": "1-6",
    ...
  }
}
```

### Example Chunks

#### **Category Chunk** (DEMON)

```json
{
  "type": "category",
  "title": "DEMON",
  "text": "Demons are chaotic evil creatures from the Abyss...",
  "metadata": {
    "page": 16,
    "category": null,
    "character_count": 850
  },
  "statistics": null
}
```

#### **Nested Monster Chunk** (Orcus)

```json
{
  "type": "monster",
  "title": "Demon: Orcus",
  "text": "FREQUENCY: Very rare\nNO. APPEARING: 1\n...\n\nOrcus is a bloated...",
  "metadata": {
    "page": 16,
    "category": "DEMON",
    "character_count": 1420
  },
  "statistics": {
    "FREQUENCY": "Very rare",
    "NO. APPEARING": "1",
    "ARMOR CLASS": "-6",
    "MOVE": "18\"/36\"",
    "HIT DICE": "120 hit points",
    ...
  }
}
```

#### **Standalone Monster Chunk** (Owlbear)

```json
{
  "type": "monster",
  "title": "OWLBEAR",
  "text": "FREQUENCY: Rare\nNO. APPEARING: 1-6\n...\n\nOwlbears are probably...",
  "metadata": {
    "page": 76,
    "category": null,
    "character_count": 892
  },
  "statistics": {
    "FREQUENCY": "Rare",
    "NO. APPEARING": "1-6",
    "ARMOR CLASS": "5",
    ...
  }
}
```

---

## Usage

### Basic Usage

```bash
python src/chunkers/monster_encyclopedia.py data/markdown/Monster_Manual_(1e).md
```

**Output**: `data/chunks/chunks_Monster_Manual_(1e).json`

### Integration with Embedder

```bash
# 1. Chunk Monster Manual
python src/chunkers/monster_encyclopedia.py \
  data/markdown/Monster_Manual_(1e).md

# 2. Embed chunks
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Monster_Manual_(1e).json \
  dnd_monster_manual
```

### Programmatic Usage

```python
from src.chunkers.monster_encyclopedia import chunk_monster_encyclopedia

# Chunk the markdown
chunks = chunk_monster_encyclopedia(
    markdown_file="data/markdown/Monster_Manual_(1e).md"
)

# Access chunk data
for chunk in chunks:
    print(f"Title: {chunk['title']}")
    print(f"Type: {chunk['type']}")
    if chunk['statistics']:
        print(f"ARMOR CLASS: {chunk['statistics']['ARMOR CLASS']}")
```

---

## Design Decisions

### Why Category Detection?

**Problem**: Generic chunking would create separate chunks for:
- DEMON category description (without context)
- Orcus entry (without knowing it's a demon)

**Solution**: Link nested entries to parent category via metadata.

**Benefit**: Retrieval can find both "general demon info" and "specific demon".

### Why Prepend Statistics?

**Problem**: Statistics stored only in metadata are not searchable by embedding models.

**Example Query**: "How many HP does a beholder have?"
- **Without prepending**: Embedding model can't see "120 hit points" in text
- **With prepending**: Statistics are part of searchable content

**Trade-off**: Increases chunk size, but dramatically improves retrieval accuracy.

### Why Flatten to JSON?

**Alternatives Considered**:
1. Keep original markdown structure → Hard to parse programmatically
2. Store in database → Overkill for this use case
3. Use hierarchical JSON → Complicates retrieval logic

**Decision**: Flatten to array of chunks with metadata links.

**Benefits**:
- Easy to iterate over
- Simple to embed
- Metadata provides structure when needed
- Compatible with ChromaDB

---

## Limitations & Future Work

### Current Limitations

1. **Manual category detection**: Requires looking ahead in markdown
2. **Single-level nesting**: Doesn't handle nested categories (none in MM)
3. **Page detection**: Relies on markdown comments from Docling

### Future Enhancements

1. **Automatic nesting depth**: Recursive category detection
2. **Cross-references**: Link related monsters (e.g., "see also")
3. **Statistics validation**: Ensure all expected stats are present
4. **Variant handling**: Detect and chunk monster variants (e.g., "Dragon, Black" vs "Dragon, Gold")

---

## Testing

### Key Test Cases

1. **Category with nested monsters**: DEMON, DRAGON
2. **Standalone monsters**: Owlbear, Beholder
3. **Statistics extraction**: All stat fields populated
4. **Page tracking**: Page numbers match markdown
5. **Text prepending**: Statistics appear at start of text

### Manual Verification

```bash
# Chunk the Monster Manual
python src/chunkers/monster_encyclopedia.py \
  data/markdown/Monster_Manual_(1e).md

# Verify output
jq '.[] | select(.title == "Demon: Orcus")' \
  data/chunks/chunks_Monster_Manual_(1e).json

# Check statistics
jq '.[] | select(.title == "OWLBEAR") | .statistics' \
  data/chunks/chunks_Monster_Manual_(1e).json
```

---

## Related Documentation

- **[DoclingEmbedder.md](DoclingEmbedder.md)**: Embedding and storage
- **[DnDRAG.md](DnDRAG.md)**: Query and retrieval system
- **[adaptive_filtering.md](adaptive_filtering.md)**: Gap detection algorithm
- **[../setup/chromadb_setup.md](../setup/chromadb_setup.md)**: ChromaDB configuration

---

**Author**: Mike (GravityCar)  
**Last Updated**: 2025-01-XX  
**Version**: 1.0
