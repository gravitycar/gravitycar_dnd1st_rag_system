# Embedder Architecture

**Version:** 2.0  
**Date:** October 21, 2025  
**Status:** Production-Ready  

---

## Overview

The embedder system uses a modular, extensible architecture based on **Orchestrator**, **Template Method**, and **Strategy** patterns. This design separates concerns, improves testability, and makes it trivial to add support for new book formats.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Code (CLI)                        │
│              src/embedders/docling_embedder.py              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              EmbedderOrchestrator (Orchestration)           │
│         src/embedders/embedder_orchestrator.py              │
├─────────────────────────────────────────────────────────────┤
│  • Load chunks from JSON file                               │
│  • Auto-detect format (chunk_format_is_compatible())        │
│  • Inject chunks into selected embedder                     │
│  • Coordinate pipeline execution                            │
│  • Coordinate test queries                                  │
└────────────────────────┬────────────────────────────────────┘
                         │ instantiates
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Embedder (Abstract Base - Template Method)        │
│              src/embedders/base_embedder.py                 │
├─────────────────────────────────────────────────────────────┤
│  Template Methods (implemented):                            │
│    • embed_chunks() - Main pipeline                         │
│    • test_query() - Single query execution                  │
│    • _create_or_get_collection() - ChromaDB setup           │
│    • _get_embeddings_batch() - OpenAI API calls             │
│                                                              │
│  Abstract Methods (must override):                          │
│    • chunk_format_is_compatible(chunks) - Format detection  │
│    • prepare_text_for_embedding(chunk) - Text preparation   │
│    • extract_chunk_id(chunk) - ID generation                │
│    • process_metadata(chunk) - Metadata transformation      │
│    • get_test_queries() - Format-specific test queries      │
└────────────────────────┬────────────────────────────────────┘
                         │ subclasses
            ┌────────────┴────────────┐
            ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│ MonsterBookEmbedder  │  │  RuleBookEmbedder    │
│  (Strategy)          │  │    (Strategy)        │
├──────────────────────┤  ├──────────────────────┤
│ Monster Manual       │  │ Player's Handbook    │
│ format (legacy)      │  │ DMG format           │
│                      │  │ (recursive_chunker)  │
│ • Statistics         │  │                      │
│   prepending         │  │ • Hierarchy          │
│ • Category support   │  │   flattening         │
│ • Metadata           │  │ • Split chunk        │
│   flattening         │  │   handling           │
└──────────────────────┘  └──────────────────────┘
```

---

## Component Responsibilities

### 1. EmbedderOrchestrator (Orchestration Layer)

**File**: `src/embedders/embedder_orchestrator.py`  
**Pattern**: Orchestrator Pattern  
**Responsibility**: High-level workflow coordination

#### Key Methods

**`__init__(embedder_classes=None)`**
- Accepts optional list of embedder classes (for testing/customization)
- Defaults to discovering all Embedder subclasses via `Embedder.__subclasses__()`

**`detect_format(chunks: List[Dict]) -> Type[Embedder]`**
- Loops through all embedder classes
- Calls each class's `chunk_format_is_compatible(chunks)` static method
- Returns first compatible embedder class
- Raises `ValueError` if no compatible format found

**`process(chunk_file, collection_name, truncate=False)`**
- Loads chunks from JSON file (caches in memory)
- Auto-detects format
- Instantiates embedder with cached chunks
- Calls `embed_chunks()` on embedder
- Returns embedder instance for further use

**`run_test_queries(embedder, collection_name)`**
- Gets test queries from embedder's `get_test_queries()`
- Executes each via embedder's `test_query()`
- Displays results with distances and content

#### Design Rationale

**Why separate orchestration?**
1. **SRP**: Orchestration logic separate from embedding operations
2. **Testability**: Can test orchestration with mocked embedders
3. **Flexibility**: Easy to add pipeline variations (batch, parallel, hybrid)

---

### 2. Embedder (Abstract Base Class)

**File**: `src/embedders/base_embedder.py`  
**Pattern**: Template Method Pattern  
**Responsibility**: Common operations, algorithm template

#### Template Methods (Implemented)

**`embed_chunks(collection_name, truncate=False)`**
- Main embedding pipeline (template algorithm)
- Steps:
  1. Create/get ChromaDB collection
  2. Optionally truncate collection
  3. Prepare chunks (call `prepare_text_for_embedding()`)
  4. Get embeddings in batches (call `_get_embeddings_batch()`)
  5. Process metadata (call `process_metadata()`)
  6. Store in ChromaDB
  7. Display summary

**`test_query(collection_name, query_text, k=5)`**
- Single query execution
- Steps:
  1. Get query embedding from OpenAI
  2. Query ChromaDB collection
  3. Return results with distances and metadata

**`_create_or_get_collection(collection_name)`**
- ChromaDB collection management
- Creates collection if doesn't exist
- Uses cosine similarity for distance metric

**`_get_embeddings_batch(texts, batch_size=32)`**
- OpenAI API batch calls
- Progress indicators for long operations
- Rate limiting (0.1s between batches)
- Uses `text-embedding-3-small` model (1536 dimensions)

#### Abstract Methods (Must Override)

**`chunk_format_is_compatible(chunks: List[Dict]) -> bool`** *(static)*
- Inspect chunk structure to determine compatibility
- Used by orchestrator for auto-detection
- Example: Check for `"name"` field vs `"title"` field

**`prepare_text_for_embedding(chunk: Dict) -> str`**
- Transform chunk into embeddable text
- Monster format: Prepend statistics block
- Rulebook format: Return content as-is

**`extract_chunk_id(chunk: Dict) -> str`**
- Generate unique ID for chunk
- Monster format: Use `monster_id` or `category_id`
- Rulebook format: Use `uid` field

**`process_metadata(chunk: Dict) -> Dict[str, Any]`**
- Transform chunk metadata for ChromaDB storage
- Flatten nested structures
- Transform types (e.g., "default" → "monster")
- Add book references

**`get_test_queries() -> List[str]`**
- Return format-specific test queries
- Used to validate embedding quality

#### Constructor

**`__init__(client, openai_api_key, _cached_chunks=None)`**
- `client`: ChromaDB client instance
- `openai_api_key`: OpenAI API key for embeddings
- `_cached_chunks`: Optional pre-loaded chunks (injected by orchestrator)

---

### 3. MonsterBookEmbedder (Strategy Implementation)

**File**: `src/embedders/monster_book_embedder.py`  
**Pattern**: Strategy Pattern  
**Responsibility**: Monster Manual format-specific logic

#### Format Detection

```python
@staticmethod
def chunk_format_is_compatible(chunks: List[Dict]) -> bool:
    """
    Monster Manual format detection.
    
    Criteria:
    - Has "name" field (not "title")
    - Has "description" field (not "content")
    - Optional: Has "statistics" field (strong indicator)
    """
    if not chunks:
        return False
    
    sample = chunks[0]
    has_name = "name" in sample
    has_description = "description" in sample
    has_statistics = "statistics" in sample
    
    return has_name and has_description
```

#### Statistics Prepending

```python
def prepare_text_for_embedding(self, chunk: Dict) -> str:
    """
    Prepend statistics to monster descriptions.
    
    Categories (no statistics):
      "DEMON
      
      Demons are chaotic evil creatures..."
    
    Monsters (with statistics):
      "FREQUENCY: Very rare
       NO. APPEARING: 1
       ARMOR CLASS: -8
       ...
       
       Demogorgon is a two-headed Prince of Demons..."
    """
    if chunk.get("type") == "category":
        # Categories have no statistics
        return chunk.get("description", "")
    
    # Monsters: prepend statistics block
    if "statistics" in chunk and chunk["statistics"]:
        stats_text = self._add_statistic_block(chunk["statistics"])
        description = chunk.get("description", "")
        return f"{stats_text}\n\n{description}"
    
    return chunk.get("description", "")
```

#### Metadata Processing

```python
def process_metadata(self, chunk: Dict) -> Dict[str, Any]:
    """
    Transform Monster Manual metadata.
    
    Transformations:
    1. Type: "default" → "monster"
    2. Flatten statistics: {"ARMOR CLASS": "5"} → {"armor_class": "5"}
    3. Add parent relationships
    4. Add book reference
    """
    metadata = {
        "type": chunk.get("type", "default"),
        "book": chunk.get("book", "Monster_Manual_(1e)")
    }
    
    # Transform "default" → "monster"
    if metadata["type"] == "default":
        metadata["type"] = "monster"
    
    # Flatten statistics
    if "statistics" in chunk:
        for key, value in chunk["statistics"].items():
            clean_key = key.lower().replace(" ", "_").replace(".", "")
            metadata[clean_key] = str(value)
    
    # Add parent relationships
    if "parent_category" in chunk:
        metadata["parent_category"] = chunk["parent_category"]
    
    return metadata
```

#### Test Queries

```python
def get_test_queries(self) -> List[str]:
    return [
        "Tell me about demons and their abilities",
        "What is a beholder and what are its powers?",
        "Show me undead creatures"
    ]
```

---

### 4. RuleBookEmbedder (Strategy Implementation)

**File**: `src/embedders/rule_book_embedder.py`  
**Pattern**: Strategy Pattern  
**Responsibility**: Player's Handbook/DMG format-specific logic

#### Format Detection

```python
@staticmethod
def chunk_format_is_compatible(chunks: List[Dict]) -> bool:
    """
    Rulebook format detection (recursive_chunker output).
    
    Criteria:
    - Has "uid" at top level (not in metadata)
    - Has "title" field (not "name")
    - Has "content" field (not "description")
    - Has "book" field at top level
    """
    if not chunks:
        return False
    
    sample = chunks[0]
    has_uid = "uid" in sample
    has_title = "title" in sample
    has_content = "content" in sample
    has_book = "book" in sample
    
    return has_uid and has_title and has_content and has_book
```

#### Text Preparation

```python
def prepare_text_for_embedding(self, chunk: Dict) -> str:
    """
    Return content as-is (no statistics prepending).
    
    Rulebook content is already well-formatted from recursive_chunker.
    """
    return chunk.get("content", "")
```

#### Metadata Processing

```python
def process_metadata(self, chunk: Dict) -> Dict[str, Any]:
    """
    Transform rulebook metadata.
    
    Transformations:
    1. Type: "default" → "rule"
    2. Flatten hierarchy: ["TREASURE", "SCROLLS"] → "TREASURE → SCROLLS"
    3. Preserve split chunk metadata
    4. Add parent relationships
    """
    metadata = {
        "type": chunk.get("type", "default"),
        "title": chunk.get("title", ""),
        "book": chunk.get("book", "")
    }
    
    # Transform "default" → "rule"
    if metadata["type"] == "default":
        metadata["type"] = "rule"
    
    # Flatten hierarchy with arrow separator
    if "hierarchy" in chunk:
        hierarchy = chunk["hierarchy"]
        if isinstance(hierarchy, list):
            metadata["hierarchy"] = " → ".join(hierarchy)
        else:
            metadata["hierarchy"] = str(hierarchy)
    
    # Preserve split chunk metadata
    if chunk.get("chunk_type") == "split":
        metadata["chunk_part"] = chunk.get("chunk_part", 1)
        metadata["total_parts"] = chunk.get("total_parts", 1)
        metadata["original_chunk_uid"] = chunk.get("original_chunk_uid", "")
        
        # Sibling chunks as CSV
        if "sibling_chunks" in chunk:
            metadata["sibling_chunks"] = ",".join(chunk["sibling_chunks"])
    
    # Add parent relationships
    if "parent_chunk_uid" in chunk:
        metadata["parent_chunk_uid"] = chunk["parent_chunk_uid"]
    
    return metadata
```

#### Test Queries

```python
def get_test_queries(self) -> List[str]:
    return [
        "How many experience points does a fighter need to reach 9th level?",
        "What can a 7th level cleric turn undead?",
        "What are the saving throw categories?"
    ]
```

---

## Design Patterns Explained

### 1. Orchestrator Pattern

**Purpose**: Separate high-level workflow coordination from low-level operations.

**Benefits**:
- **SRP**: Orchestration logic separate from embedding operations
- **Testability**: Can test with mocked embedders
- **Flexibility**: Easy to add pipeline variations

**Example**:
```python
# Orchestrator coordinates the workflow
orchestrator = EmbedderOrchestrator()
embedder = orchestrator.process(
    "data/chunks/monsters.json",
    "dnd_monsters"
)
orchestrator.run_test_queries(embedder, "dnd_monsters")
```

### 2. Template Method Pattern

**Purpose**: Define algorithm skeleton in base class, let subclasses fill in details.

**Benefits**:
- **Code reuse**: Common operations in base class
- **Consistency**: All embedders follow same algorithm
- **Extensibility**: Override only what differs

**Example**:
```python
class Embedder(ABC):
    def embed_chunks(self, collection_name, truncate=False):
        # Template algorithm (same for all)
        collection = self._create_or_get_collection(collection_name)
        if truncate:
            collection.delete(where={})
        
        for chunk in self._cached_chunks:
            text = self.prepare_text_for_embedding(chunk)  # Subclass implements
            metadata = self.process_metadata(chunk)  # Subclass implements
            chunk_id = self.extract_chunk_id(chunk)  # Subclass implements
            # ... embed and store
```

### 3. Strategy Pattern

**Purpose**: Define family of algorithms, make them interchangeable.

**Benefits**:
- **Flexibility**: Switch algorithms at runtime
- **Maintainability**: Each strategy is self-contained
- **Extensibility**: Add new strategies without modifying existing code

**Example**:
```python
# Same interface, different implementations
class MonsterBookEmbedder(Embedder):
    def prepare_text_for_embedding(self, chunk):
        # Strategy: Prepend statistics
        return f"{stats}\n\n{description}"

class RuleBookEmbedder(Embedder):
    def prepare_text_for_embedding(self, chunk):
        # Strategy: Use content as-is
        return chunk["content"]
```

### 4. Factory Pattern (Implicit)

**Purpose**: Create objects without specifying exact class.

**Benefits**:
- **Decoupling**: Client doesn't need to know about concrete classes
- **Discovery**: Automatic discovery via `__subclasses__()`

**Example**:
```python
# Automatic discovery of all embedders
embedder_classes = Embedder.__subclasses__()
# [MonsterBookEmbedder, RuleBookEmbedder, ...]

# Auto-detect and instantiate correct embedder
for embedder_class in embedder_classes:
    if embedder_class.chunk_format_is_compatible(chunks):
        return embedder_class(client, api_key, chunks)
```

---

## Adding New Book Formats

Adding support for a new book format (e.g., Unearthed Arcana) requires:

### Step 1: Create New Embedder Class

```python
# src/embedders/unearthed_arcana_embedder.py

from typing import Dict, List, Any
from src.embedders.base_embedder import Embedder

class UnearthedArcanaEmbedder(Embedder):
    """Handle Unearthed Arcana format."""
    
    @staticmethod
    def chunk_format_is_compatible(chunks: List[Dict]) -> bool:
        """
        Detect Unearthed Arcana format.
        
        Unique characteristics:
        - Has "variant_rule" field
        - Has "class_feature" field
        - Or whatever makes it unique
        """
        if not chunks:
            return False
        
        sample = chunks[0]
        return "variant_rule" in sample or "class_feature" in sample
    
    def prepare_text_for_embedding(self, chunk: Dict) -> str:
        """Format-specific text preparation."""
        # Implement your logic
        return chunk.get("text", "")
    
    def extract_chunk_id(self, chunk: Dict) -> str:
        """Generate unique ID."""
        return chunk.get("rule_id", f"ua_{chunk.get('title', 'unknown')}")
    
    def process_metadata(self, chunk: Dict) -> Dict[str, Any]:
        """Transform metadata for ChromaDB."""
        return {
            "type": "variant_rule",
            "title": chunk.get("title", ""),
            "book": "Unearthed_Arcana",
            # ... other metadata
        }
    
    def get_test_queries(self) -> List[str]:
        """Format-specific test queries."""
        return [
            "What are the barbarian class features?",
            "Tell me about weapon specialization"
        ]
```

### Step 2: That's It!

The orchestrator will **automatically discover** the new embedder via `Embedder.__subclasses__()`. No changes needed to existing code.

```python
# Automatically works with new format
orchestrator = EmbedderOrchestrator()
embedder = orchestrator.process(
    "data/chunks/unearthed_arcana.json",
    "dnd_unearthed_arcana"
)
```

---

## SOLID Principles in Action

### Single Responsibility Principle (SRP)

Each class has one reason to change:
- **EmbedderOrchestrator**: Workflow coordination changes
- **Embedder**: Common operations changes
- **MonsterBookEmbedder**: Monster format changes
- **RuleBookEmbedder**: Rulebook format changes

### Open/Closed Principle (OCP)

- **Open for extension**: Add new embedders without modifying existing code
- **Closed for modification**: Core logic (base Embedder) doesn't change

### Liskov Substitution Principle (LSP)

All embedders can substitute base `Embedder`:
```python
def process_any_embedder(embedder: Embedder):
    embedder.embed_chunks("collection_name")  # Works for any embedder
```

### Interface Segregation Principle (ISP)

Abstract methods are minimal and focused:
- `chunk_format_is_compatible()` - Detection only
- `prepare_text_for_embedding()` - Text only
- `extract_chunk_id()` - ID only
- `process_metadata()` - Metadata only
- `get_test_queries()` - Queries only

### Dependency Inversion Principle (DIP)

Depend on abstractions (base `Embedder`), not concrete implementations:
```python
class EmbedderOrchestrator:
    def process(self, chunk_file, collection_name):
        # Depends on Embedder abstraction, not concrete class
        embedder: Embedder = self.detect_format(chunks)
        embedder.embed_chunks(collection_name)
```

---

## Testing Strategy

### Unit Tests (38 tests)

**Test orchestration with mocks**:
```python
# tests/test_embedder_orchestrator.py
class MockMonsterEmbedder(Embedder):
    # Minimal mock implementation
    pass

def test_format_detection():
    orchestrator = EmbedderOrchestrator([MockMonsterEmbedder])
    embedder_class = orchestrator.detect_format(monster_chunks)
    assert embedder_class == MockMonsterEmbedder
```

**Test each embedder in isolation**:
```python
# tests/test_monster_book_embedder.py
def test_statistics_prepending():
    embedder = MonsterBookEmbedder(mock_client, "fake_key")
    text = embedder.prepare_text_for_embedding(monster_chunk)
    assert "ARMOR CLASS: 5" in text
```

### Integration Tests (3 tests)

**Test with real ChromaDB**:
```python
# Run via CLI with --test-queries flag
python -m src.embedders.docling_embedder \
    data/chunks/chunks_Monster_Manual_(1e).json \
    test_monster_manual \
    --test-queries
```

### Acid Test

**Fighter XP Table test** validates entire pipeline:
```python
query = "How many XP does a fighter need to reach 9th level?"
# Must return correct table with 250,001 XP
```

---

## Performance Characteristics

### Embedding Speed
- **Monster Manual**: 294 chunks in ~45 seconds (6.5 chunks/sec)
- **DMG**: 1,184 chunks in ~3 minutes (6.6 chunks/sec)
- **Player's Handbook**: 735 chunks in ~2 minutes (6.1 chunks/sec)

### Memory Usage
- Chunks cached in memory (orchestrator loads once)
- Batch processing limits OpenAI API calls
- ChromaDB handles vector storage efficiently

### API Costs
- Model: `text-embedding-3-small` ($0.02 per 1M tokens)
- Batch size: 32 chunks
- Rate limiting: 0.1s between batches (600 chunks/min max)

---

## Comparison with Old Implementation

### Before (Monolithic)
```python
# Single class, lots of conditionals
class DoclingEmbedder:
    def embed_chunks(self):
        for chunk in chunks:
            if chunk.get("type") == "monster":
                # Monster logic
            elif chunk.get("type") == "category":
                # Category logic
            elif "uid" in chunk:
                # Rulebook logic
            # ... many more branches
```

**Problems**:
- Violates SRP (does everything)
- Hard to test (can't isolate logic)
- Hard to extend (must modify core class)

### After (Modular)
```python
# Orchestration separate from operations
orchestrator = EmbedderOrchestrator()
embedder = orchestrator.process(chunk_file, collection_name)

# Each strategy is self-contained
class MonsterBookEmbedder(Embedder):
    # Only monster logic
    pass

class RuleBookEmbedder(Embedder):
    # Only rulebook logic
    pass
```

**Benefits**:
- Follows SRP (each class has one job)
- Easy to test (mock orchestration, test strategies)
- Easy to extend (add new strategy, zero core changes)

---

## Future Enhancements

### Potential Improvements

1. **Hybrid Search**: Combine semantic + keyword search
2. **Incremental Updates**: Only embed changed chunks
3. **Parallel Processing**: Embed multiple books simultaneously
4. **Schema Validation**: Validate chunk format before embedding
5. **Caching**: Cache embeddings to avoid re-computing
6. **Advanced Orchestration**: Pipeline variations (batch, streaming)

### Additional Embedders

- **2nd Edition Rules** (different statistics format)
- **Spell Compendium** (spell-specific logic)
- **Adventure Modules** (encounter-focused)
- **Monstrous Compendium** (expanded monster stats)

---

## Conclusion

The refactored embedder architecture provides:

✅ **Modularity**: Clear separation of concerns  
✅ **Extensibility**: Add new formats without modifying existing code  
✅ **Testability**: 38 unit tests + 3 integration tests  
✅ **Maintainability**: SOLID principles enforced  
✅ **Performance**: No regressions, same speed as before  
✅ **Quality**: Fighter XP Table acid test passes  

The system is production-ready and can handle any D&D 1st Edition book format with minimal code changes.

---

*Last Updated: October 21, 2025*  
*Version: 2.0 (Refactored Architecture)*
