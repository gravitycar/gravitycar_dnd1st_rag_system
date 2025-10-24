# Implementation Plan: Embedder Refactoring

**Version:** 2.0  
**Date:** October 21, 2025  
**Status:** ✅ **COMPLETE** - All phases implemented and tested  
**Target File:** `src/embedders/docling_embedder.py`

---

## 1. Feature Overview

Refactor the monolithic `DoclingEmbedder` class into a modular, extensible architecture using the **Strategy Pattern** and **Template Method Pattern**. This refactoring separates concerns, improves testability, and makes it easy to add new book types in the future.

### Current Problems
1. **Tight coupling**: Single class handles both Monster Manual and rulebook formats
2. **Conditional logic**: Many `if/elif` branches based on chunk type
3. **Low extensibility**: Adding new book types requires modifying existing code
4. **Violates SRP**: Class handles detection, formatting, metadata extraction, and embedding
5. **Hard to test**: Cannot test book-specific logic in isolation

### Proposed Architecture

```
EmbedderOrchestrator (Orchestration)
├── Auto-detection (format detection)
├── Pipeline execution (process coordination)
└── Test query coordination

Embedder (Base - Template Method Pattern)
├── Common operations (no orchestration)
└── Abstract methods for children

MonsterBookEmbedder (Strategy)
RuleBookEmbedder (Strategy)
```

**Key Insight**: The chunk file structure itself tells us which embedder to use:
- Monster Manual chunks: `{"name": "...", "description": "...", "statistics": {...}}`
- Rulebook chunks: `{"uid": "...", "title": "...", "content": "...", "book": "..."}`

**Architectural Benefits**:
- **SRP**: Orchestration (EmbedderOrchestrator) separated from operations (Embedder)
- **Testability**: Can test orchestration logic with mocked embedders
- **Flexibility**: Easy to add pipeline variations (batch, parallel, hybrid detection)

---

## 2. Requirements

### 2.1 Functional Requirements

**FR1: Base Embedder Class**
- Provide common functionality for all embedder types
- Handle ChromaDB connection and collection management (create/get collection)
- Get embeddings from OpenAI API in batches
- Truncate collections
- Provide template methods for subclasses to override
- Execute embedding pipeline (`embed_chunks()`)
- Execute individual test queries (`test_query()`)
- Accept pre-loaded chunks via `_cached_chunks` attribute (injected by orchestrator)

**FR2: Monster Book Embedder**
- Handle Monster Manual chunk format (legacy)
- Support both `"monster"` and `"category"` types
- Transform `"default"` type to `"monster"` (if present)
- Prepend statistics to monster descriptions for searchability via `add_statistic_block()`
- Extract and flatten statistics metadata (frequency, AC, HD, alignment, etc.) via `process_metadata()`
- Generate IDs from `monster_id` or `category_id`
- Map legacy field names: `name`, `description`
- Provide test queries via `get_test_queries()`

**FR3: Rule Book Embedder**
- Handle Player's Handbook and DMG chunk format (recursive_chunker output)
- Support all chunk types: `default`, `spell`, `encounter`, `magic_item`, `insanity`, `treasure`, `lower_planes`, `sample_dungeon`, `pursuit_evasion`, `split`
- Transform `"default"` type to `"rule"` in metadata
- Extract hierarchy-based metadata via `process_metadata()`
- Preserve parent-child relationships (`parent_chunk_uid`)
- Generate IDs from top-level `uid` field
- Map recursive_chunker field names: `title`, `content`, `book`
- Flatten hierarchy using Unicode arrow separator (` → `)
- Provide test queries via `get_test_queries()`

**FR4: EmbedderOrchestrator Class**
- Load chunks once and cache in memory for reuse
- Discover all child embedder classes dynamically
- Loop through child classes, testing each `chunk_format_is_compatible()` static method
- Instantiate and return first embedder where `chunk_format_is_compatible()` returns `True`
- Raise exception if no embedder's `chunk_format_is_compatible()` returns `True`
- Coordinate full embedding pipeline (`process()`)
- Coordinate test query execution (`run_test_queries()`)
- Monster Manual detection criteria (in `MonsterBookEmbedder.chunk_format_is_compatible()`):
  - Has `"name"` field (not `"title"`)
  - Has `"description"` field (not `"content"`)
  - Optional: Has `"statistics"` field (strong indicator)
- Rulebook detection criteria (in `RuleBookEmbedder.chunk_format_is_compatible()`):
  - Has `"uid"` at top level (not in metadata)
  - Has `"title"` field (not `"name"`)
  - Has `"content"` field (not `"description"`)
  - Has `"book"` field at top level

**FR5: Backwards Compatibility**
- Support existing Monster Manual chunks without changes
- Support new recursive_chunker format
- Maintain existing CLI interface
- Collection names remain configurable

**FR6: Error Handling**
- Network/connection errors from OpenAI API: Throw exception and terminate
- ChromaDB connection issues: Throw exception and terminate
- No chunk validation at this time (fail fast with clear errors)

### 2.2 Non-Functional Requirements

**NFR1: SOLID Principles**
- **SRP**: Each class has single responsibility
  - `EmbedderOrchestrator`: Orchestration (detection, pipeline coordination, test query coordination)
  - `Embedder`: Common embedding operations (ChromaDB, OpenAI, collection management)
  - `MonsterBookEmbedder`: Monster-specific formatting
  - `RuleBookEmbedder`: Rulebook-specific formatting
- **OCP**: Open for extension (new embedders), closed for modification
- **LSP**: Subclasses can substitute base class
- **DIP**: Depend on abstractions (base class methods, orchestrator interface)

**NFR2: Performance**
- No performance degradation from refactoring
- Maintain batch processing (32 chunks/batch)
- Keep rate limiting (0.1s sleep between batches)

**NFR3: Testability**
- Each embedder class independently testable
- Mock-friendly interfaces
- Clear separation of concerns

---

## 3. Design

### 3.1 Class Hierarchy

```python
class EmbedderOrchestrator:
    """
    Orchestrates the embedding pipeline: format detection, processing, and testing.
    
    Responsibilities:
    - Auto-detect chunk format via child class discovery
    - Load and cache chunks in memory
    - Coordinate embedding pipeline execution
    - Coordinate test query execution
    
    This class separates orchestration logic from embedding operations,
    adhering to Single Responsibility Principle.
    """
    
    def __init__(self, embedder_classes: List[Type[Embedder]] = None)
    def detect_embedder(self, chunks_file: str, **kwargs) -> Embedder
    def process(self, chunks_file: str, **kwargs) -> Embedder
    def run_test_queries(self, embedder: Embedder)


class Embedder(ABC):
    """
    Base embedder class providing common embedding operations (no orchestration).
    
    Responsibilities:
    - ChromaDB connection and collection management (create/get)
    - OpenAI embedding generation (batched)
    - Collection truncation
    - Execute embedding pipeline
    - Execute individual test queries
    - Accept pre-loaded chunks via _cached_chunks attribute
    
    Note: Chunks are loaded and cached by EmbedderOrchestrator, then injected
    into embedder instances. This avoids double-loading and keeps orchestration
    concerns separate from embedding operations.
    """
    
    # Common operations (implemented in base class)
    def __init__(self, chunks_file, collection_name=None, chroma_host=None, chroma_port=None)
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]
    def truncate_collection(self)
    def _get_or_create_collection(self, name: str)  # Collection management
    def test_query(self, query: str, n_results: int = 5)  # Execute single test query
    
    # Template methods (abstract - subclasses must implement)
    @staticmethod
    @abstractmethod
    def chunk_format_is_compatible(chunk: Dict[str, Any]) -> bool
    
    @abstractmethod
    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32)
    
    @abstractmethod
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str
    
    @abstractmethod
    def extract_chunk_id(self, chunk: Dict[str, Any], index: int) -> str
    
    @abstractmethod
    def process_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]
    
    @abstractmethod
    def get_test_queries(self) -> List[str]
    
    # Backwards compatibility factory (delegates to orchestrator)
    @staticmethod
    def create(chunks_file: str, **kwargs) -> 'Embedder'


class MonsterBookEmbedder(Embedder):
    """
    Embedder for Monster Manual chunks (legacy format).
    
    Chunk Format:
    {
        "name": "DEMON",
        "description": "...",
        "statistics": {
            "frequency": "...",
            "armor_class": "...",
            ...
        },
        "metadata": {
            "type": "monster" | "category",
            "monster_id": "...",
            "category_id": "...",
            ...
        }
    }
    """
    
    @staticmethod
    def chunk_format_is_compatible(chunk: Dict[str, Any]) -> bool
    
    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32)
    def add_statistic_block(self, chunk: Dict[str, Any], text: str) -> str
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str
    def extract_chunk_id(self, chunk: Dict[str, Any], index: int) -> str
    def process_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]
    def get_test_queries(self) -> List[str]


class RuleBookEmbedder(Embedder):
    """
    Embedder for Player's Handbook and DMG chunks (recursive_chunker format).
    
    Chunk Format:
    {
        "uid": "Dungeon_Master_s_Guide_(1e)_organized_PREFACE_1_part1",
        "book": "Dungeon_Master_s_Guide_(1e)_organized",
        "title": "PREFACE",
        "content": "...",
        "metadata": {
            "type": "default" | "spell" | "encounter" | ...,
            "chunk_type": "default" | "split" | ...,
            "hierarchy": ["PREFACE"],
            "parent_chunk_uid": "...",
            "chunk_level": 2,
            ...
        }
    }
    """
    
    @staticmethod
    def chunk_format_is_compatible(chunk: Dict[str, Any]) -> bool
    
    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32)
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str
    def extract_chunk_id(self, chunk: Dict[str, Any], index: int) -> str
    def process_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]
    def get_test_queries(self) -> List[str]
```

### 3.2 EmbedderOrchestrator Implementation

```python
import json
from pathlib import Path
from typing import List, Dict, Any, Type

class EmbedderOrchestrator:
    """Orchestrates embedding pipeline: detection, processing, testing."""
    
    def __init__(self, embedder_classes: List[Type[Embedder]] = None):
        """
        Initialize orchestrator with optional list of embedder classes.
        
        Args:
            embedder_classes: List of Embedder subclasses to try. If None,
                             discovers all subclasses via Embedder.__subclasses__()
        """
        self.embedder_classes = embedder_classes or Embedder.__subclasses__()
        self._cached_chunks = {}  # Cache chunks by filename
    
    def detect_embedder(self, chunks_file: str, **kwargs) -> Embedder:
        """
        Auto-detect chunk format and return appropriate embedder instance.
        
        Detection Strategy:
        1. Load chunks once and cache in memory
        2. Try each embedder class's chunk_format_is_compatible() method
        3. Return instance of first matching embedder
        4. Raise exception if no embedder matches
        """
        # Load chunks once (cache for reuse)
        if chunks_file not in self._cached_chunks:
            with open(chunks_file, 'r') as f:
                self._cached_chunks[chunks_file] = json.load(f)
        
        chunks = self._cached_chunks[chunks_file]
        
        if not chunks:
            raise ValueError(f"Chunk file is empty: {chunks_file}")
        
        first_chunk = chunks[0]
        
        if not self.embedder_classes:
            raise RuntimeError("No Embedder subclasses found")
        
        # Try each embedder's chunk_format_is_compatible method
        for embedder_class in self.embedder_classes:
            if embedder_class.chunk_format_is_compatible(first_chunk):
                print(f"✓ Detected format: {embedder_class.__name__}")
                # Create instance and inject cached chunks
                instance = embedder_class(chunks_file, **kwargs)
                instance._cached_chunks = chunks
                return instance
        
        # No embedder matched
        chunk_keys = list(first_chunk.keys())
        raise ValueError(
            f"Unknown chunk format in {chunks_file}.\n"
            f"First chunk has keys: {chunk_keys}\n"
            f"No embedder's chunk_format_is_compatible() returned True."
        )
    
    def process(self, chunks_file: str, **kwargs) -> Embedder:
        """
        Detect embedder and run full embedding pipeline.
        
        Returns:
            Embedder instance (for further operations like test queries)
        """
        embedder = self.detect_embedder(chunks_file, **kwargs)
        # Chunks already cached and injected by detect_embedder()
        chunks = embedder._cached_chunks
        embedder.embed_chunks(chunks)
        return embedder
    
    def run_test_queries(self, embedder: Embedder):
        """Run all test queries defined by embedder."""
        test_queries = embedder.get_test_queries()
        print(f"\n🧪 Running {len(test_queries)} test queries...")
        for query in test_queries:
            embedder.test_query(query)


# In Embedder base class (backwards compatibility)
@staticmethod
def create(chunks_file: str, **kwargs) -> 'Embedder':
    """
    Factory method (backwards compatibility wrapper).
    Delegates to EmbedderOrchestrator.
    """
    orchestrator = EmbedderOrchestrator()
    return orchestrator.detect_embedder(chunks_file, **kwargs)
```

### 3.3 Collection Management

```python
def _get_or_create_collection(self, name: str):
    """
    Get existing collection or create new one.
    
    Handles collection lifecycle management in a single place.
    """
    try:
        collection = self.client.get_collection(name=name)
        print(f"Using existing collection: {name}")
        return collection
    except Exception:
        collection = self.client.create_collection(
            name=name,
            metadata={"description": f"D&D 1st Edition - {name}"}
        )
        print(f"Created new collection: {name}")
        return collection
```

### 3.4 Metadata Extraction Details

#### MonsterBookEmbedder Metadata
```python
{
    "name": chunk.get("name", "Unknown"),
    "type": "monster" | "category",  # "default" transformed to "monster"
    "char_count": ...,
    "book": "Monster_Manual_(1e)",
    
    # Category-specific
    "category_id": "...",  # if type == "category"
    "line_count": ...,     # if type == "category"
    
    # Monster-specific
    "monster_id": "...",           # if type == "monster"
    "parent_category": "...",       # if type == "monster"
    "parent_category_id": "...",    # if type == "monster"
    
    # Flattened statistics (for filtering)
    "frequency": "...",
    "armor_class": "...",
    "hit_dice": "...",
    "alignment": "...",
    "intelligence": "...",
    "size": "..."
}
```

#### RuleBookEmbedder Metadata
```python
{
    "name": chunk.get("title", "Unknown"),
    "type": chunk["metadata"]["type"],  # "default" transformed to "rule"
    "chunk_type": chunk["metadata"].get("chunk_type", "default"),
    "char_count": chunk["metadata"]["char_count"],
    "book": chunk.get("book", "Unknown"),
    
    # Hierarchy information
    "hierarchy": " → ".join(chunk["metadata"].get("hierarchy", [])),  # Unicode arrow separator
    "parent_heading": chunk["metadata"].get("parent_heading"),
    "parent_chunk_uid": chunk["metadata"].get("parent_chunk_uid"),
    "chunk_level": chunk["metadata"].get("chunk_level"),
    
    # Split chunk information
    "original_chunk_uid": chunk["metadata"].get("original_chunk_uid"),  # if chunk_type == "split"
    "chunk_part": chunk["metadata"].get("chunk_part"),                  # if chunk_type == "split"
    "total_parts": chunk["metadata"].get("total_parts"),                # if chunk_type == "split"
    "sibling_chunks": ",".join(chunk["metadata"].get("sibling_chunks", [])),  # CSV for ChromaDB
    
    # Line numbers
    "start_line": chunk["metadata"].get("start_line"),
    "end_line": chunk["metadata"].get("end_line")
}
```

### 3.5 embed_chunks() Method Breakdown

#### MonsterBookEmbedder.embed_chunks()
```python
def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32):
    """Embed Monster Manual chunks with statistics prepending."""
    print(f"\nEmbedding and storing chunks (batch size: {batch_size})...")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # Step 1: Add statistics blocks to text
        texts = []
        for chunk in batch:
            text = chunk.get("description", "")
            text = self.add_statistic_block(chunk, text)
            texts.append(text)
        
        # Step 2: Get embeddings from OpenAI
        embeddings = self.get_embeddings_batch(texts)
        
        # Step 3: Process metadata for each chunk
        ids = []
        metadatas = []
        for j, chunk in enumerate(batch):
            ids.append(self.extract_chunk_id(chunk, i + j))
            metadatas.append(self.process_metadata(chunk))
        
        # Step 4: Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        time.sleep(0.1)  # Rate limiting
    
    print(f"\n✅ Successfully embedded {len(chunks)} chunks!")

def add_statistic_block(self, chunk: Dict[str, Any], text: str) -> str:
    """Prepend statistics to monster descriptions."""
    # Only prepend statistics for actual monsters (not categories)
    if chunk["metadata"]["type"] == "monster" and "statistics" in chunk:
        stats = chunk["statistics"]
        stats_text = f"## {chunk.get('name', 'Unknown')}\n\n"
        stats_text += "**Statistics:**\n"
        for key, value in stats.items():
            if value and value != "Nil":
                display_key = key.replace('_', ' ').title()
                stats_text += f"- {display_key}: {value}\n"
        stats_text += f"\n**Description:**\n{text}"
        return stats_text
    return text
```

#### RuleBookEmbedder.embed_chunks()
```python
def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32):
    """Embed rulebook chunks."""
    print(f"\nEmbedding and storing chunks (batch size: {batch_size})...")
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # Step 1: Prepare text (no statistics block needed)
        texts = [chunk.get("content", "") for chunk in batch]
        
        # Step 2: Get embeddings from OpenAI
        embeddings = self.get_embeddings_batch(texts)
        
        # Step 3: Process metadata for each chunk
        ids = []
        metadatas = []
        for j, chunk in enumerate(batch):
            ids.append(self.extract_chunk_id(chunk, i + j))
            metadatas.append(self.process_metadata(chunk))
        
        # Step 4: Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        time.sleep(0.1)  # Rate limiting
    
    print(f"\n✅ Successfully embedded {len(chunks)} chunks!")
```

### 3.6 Test Query Execution

```python
# In Embedder base class (executes individual queries)
def test_query(self, query: str, n_results: int = 5):
    """Execute a single test query."""
    print(f"\n{'='*80}")
    print(f"TEST QUERY: {query}")
    print(f"{'='*80}")
    
    query_embedding = self.get_embeddings_batch([query])[0]
    results = self.collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    for i, (doc, metadata, distance) in enumerate(zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0]
    )):
        print(f"\n--- Result {i+1} (distance: {distance:.4f}) ---")
        print(f"Name: {metadata.get('name', 'N/A')}")
        print(f"Type: {metadata.get('type', 'N/A')}")
        print(f"Content preview: {doc[:200]}...")
    
    print(f"\n{'='*80}\n")

# In EmbedderOrchestrator (coordinates all test queries)
def run_test_queries(self, embedder: Embedder):
    """Run all test queries defined by embedder."""
    test_queries = embedder.get_test_queries()
    print(f"\n🧪 Running {len(test_queries)} test queries...")
    for query in test_queries:
        embedder.test_query(query)

# In MonsterBookEmbedder (provides test queries)
def get_test_queries(self) -> List[str]:
    """Return Monster Manual-specific test queries."""
    return [
        "Tell me about demons and their abilities",
        "What is a beholder?",
        "Show me undead creatures"
    ]

# In RuleBookEmbedder (provides test queries)
def get_test_queries(self) -> List[str]:
    """Return rulebook-specific test queries."""
    return [
        "How many experience points does a fighter need for 9th level?",
        "What is the turn undead table?",
        "Explain saving throws"
    ]
```

---

## 4. Implementation Steps

### Phase 1: Create EmbedderOrchestrator Class (Estimated: 1 hour)
1. ✅ Create `src/embedders/embedder_orchestrator.py`
2. ✅ Implement `__init__()`:
   - Accept optional list of embedder classes
   - Default to `Embedder.__subclasses__()` for dynamic discovery
   - Initialize chunk cache dictionary
3. ✅ Implement `detect_embedder(chunks_file, **kwargs)`:
   - Load chunks and cache in memory
   - Loop through embedder classes
   - Test each `chunk_format_is_compatible()` method
   - Instantiate first matching embedder
   - Inject cached chunks via `_cached_chunks`
   - Raise clear exception if no match
4. ✅ Implement `process(chunks_file, **kwargs)`:
   - Call `detect_embedder()` (chunks already loaded and injected)
   - Access `embedder._cached_chunks` directly
   - Call `embedder.embed_chunks(chunks)`
   - Return embedder instance
5. ✅ Implement `run_test_queries(embedder)`:
   - Get test queries from embedder
   - Loop and call `embedder.test_query()` for each
6. ✅ Add comprehensive docstrings

### Phase 2: Create Base Embedder Class (Estimated: 1.5 hours)
1. ✅ Create `src/embedders/base_embedder.py`
2. ✅ Extract and implement common methods from `DoclingEmbedder`:
   - `__init__` (ChromaDB connection, OpenAI client setup)
   - `_get_or_create_collection()` (collection management)
   - `get_embeddings_batch()` (with error handling for OpenAI failures)
   - `truncate_collection()`
   - `test_query()` (generic test query execution)
3. ✅ Define abstract template methods:
   - `@staticmethod chunk_format_is_compatible(chunk)` (for auto-detection)
   - `embed_chunks(chunks, batch_size)` (main embedding pipeline)
   - `prepare_text_for_embedding(chunk)` (text formatting)
   - `extract_chunk_id(chunk, index)` (ID generation)
   - `process_metadata(chunk)` (metadata extraction)
   - `get_test_queries()` (test query list)
4. ✅ Implement backwards compatibility `create()` static method:
   - Import `EmbedderOrchestrator`
   - Create orchestrator instance
   - Call `detect_embedder()` and return result
5. ✅ Add comprehensive docstrings and error handling
6. ✅ **Note**: Do NOT implement `load_chunks()`, `process()`, or `run_test_queries()` - these are orchestration methods now in `EmbedderOrchestrator`

### Phase 3: Implement MonsterBookEmbedder (Estimated: 1.5 hours)
1. ✅ Create `src/embedders/monster_book_embedder.py`
2. ✅ Implement `@staticmethod chunk_format_is_compatible(chunk)`:
   - Check for `"name"` field (not `"title"`)
   - Check for `"description"` field (not `"content"`)
   - Optional: Check for `"statistics"` field
3. ✅ Implement `embed_chunks(chunks, batch_size)`:
   - Loop through chunks in batches
   - Call `add_statistic_block()` for each chunk
   - Call `get_embeddings_batch()`
   - Call `process_metadata()` for each chunk
   - Call `collection.add()`
4. ✅ Implement `add_statistic_block(chunk, text)`:
   - Prepend statistics only for `type="monster"`
5. ✅ Implement `prepare_text_for_embedding(chunk)`:
   - Call `add_statistic_block()` for monsters
   - Return description as-is for categories
6. ✅ Implement `extract_chunk_id(chunk, index)`:
   - Use `monster_id` or `category_id`
   - Fallback to `f"chunk_{index}"`
7. ✅ Implement `process_metadata(chunk)`:
   - Transform `"default"` → `"monster"`
   - Flatten statistics dictionary
   - Extract monster-specific or category-specific fields
8. ✅ Implement `get_test_queries()`:
   - Return monster-specific queries
9. ✅ Add docstrings and type hints

### Phase 4: Implement RuleBookEmbedder (Estimated: 2 hours)
1. ✅ Create `src/embedders/rule_book_embedder.py`
2. ✅ Implement `@staticmethod chunk_format_is_compatible(chunk)`:
   - Check for `"uid"` at top level
   - Check for `"title"` and `"content"` fields
   - Check for `"book"` field at top level
3. ✅ Implement `embed_chunks(chunks, batch_size)`:
   - Loop through chunks in batches
   - Extract text from `"content"` field
   - Call `get_embeddings_batch()`
   - Call `process_metadata()` for each chunk
   - Call `collection.add()`
4. ✅ Implement `prepare_text_for_embedding(chunk)`:
   - Return content as-is (no statistics block)
5. ✅ Implement `extract_chunk_id(chunk, index)`:
   - Use top-level `uid` field
   - Fallback to `f"chunk_{index}"`
6. ✅ Implement `process_metadata(chunk)`:
   - Transform `"default"` type to `"rule"`
   - Extract hierarchy, parent_chunk_uid, chunk_level, etc.
   - Flatten hierarchy list with Unicode arrow (` → `)
   - Handle split chunk metadata (sibling_chunks, etc.)
   - Convert lists to CSV strings for ChromaDB
7. ✅ Implement `get_test_queries()`:
   - Return rulebook-specific queries
8. ✅ Add docstrings and type hints

### Phase 5: Update Main Entry Point (Estimated: 1 hour)
1. ✅ Update `src/embedders/docling_embedder.py`:
   - Import `EmbedderOrchestrator` and all embedder classes
   - Keep `DoclingEmbedder` as alias to `Embedder.create` for backwards compatibility
   - Update `main()` to use `EmbedderOrchestrator`:
     ```python
     orchestrator = EmbedderOrchestrator()
     embedder = orchestrator.process(chunks_file, collection_name=collection_name)
     if args.test_queries:
         orchestrator.run_test_queries(embedder)
     ```
2. ✅ Ensure all embedder classes are imported (required for `__subclasses__()`)
3. ✅ Add CLI flag `--test-queries` to optionally run test queries after embedding
4. ✅ Test backwards compatibility with existing command-line usage
5. ✅ **Important**: Verify Phase 1 (EmbedderOrchestrator) is complete before testing this phase (dependency)

### Phase 6: Testing (Estimated: 2.5 hours)
1. ✅ **Unit test EmbedderOrchestrator** (with mocked embedders):
   - `test_detect_embedder_monster_format()` - Detects MonsterBookEmbedder
   - `test_detect_embedder_rulebook_format()` - Detects RuleBookEmbedder
   - `test_detect_embedder_unknown_format()` - Raises ValueError
   - `test_detect_embedder_empty_file()` - Raises ValueError
   - `test_chunk_caching()` - Verifies chunks cached and reused
   - `test_process_pipeline()` - Verifies full pipeline execution
   - `test_run_test_queries()` - Verifies test query coordination
2. ✅ **Unit test MonsterBookEmbedder** (24 tests passing)
3. ✅ **Unit test RuleBookEmbedder** (13 tests passing)
4. ✅ **Integration test Monster Manual embedding**:
   - 294 chunks embedded successfully
   - MonsterBookEmbedder auto-detected
   - Statistics prepending working
   - Test queries returning relevant results
5. ✅ **Integration test Player's Handbook embedding**:
   - 735 chunks embedded successfully
   - RuleBookEmbedder auto-detected
   - Multiple chunk types detected (rule, spell)
   - **Fighter XP Table acid test PASSED** ✨
6. ✅ **Integration test DMG embedding**:
   - 1,184 chunks embedded successfully
   - RuleBookEmbedder auto-detected
   - Hierarchy flattening working correctly
   - Test queries returning relevant results
7. ✅ Verify metadata correctness in ChromaDB
   - Monster metadata: statistics flattened, parent categories preserved
   - Rulebook metadata: hierarchy flattened with → separator, split chunks handled
8. ✅ Compare results with old implementation (no regressions)
   - All formats working correctly
   - Auto-detection eliminates manual format selection
   - Metadata structure improved with better organization

### Phase 7: Documentation (Estimated: 1.5 hours) ✅ COMPLETE
**Actual Time**: 1 hour

1. ✅ Update `docs/implementations/DoclingEmbedder.md` - Added legacy notice
2. ✅ Create `docs/implementations/EmbedderArchitecture.md`:
   - Documented EmbedderOrchestrator responsibility
   - Explained separation of concerns (orchestration vs operations)
   - Showed UML class diagram with all components
   - Provided usage examples and code snippets
   - Documented SOLID principles in action
   - Added guide for adding new book formats
3. ✅ Update `.github/copilot-instructions.md`:
   - Updated Stage 3 architecture description
   - Added new embedder files to "Key Files to Understand"
   - Added "Recent Architectural Changes" section
   - Updated version to 1.1 (Embedder Refactoring)
4. ✅ Inline code comments - Already present in implementation

**Deliverables Created**:
- `docs/implementations/EmbedderArchitecture.md` (comprehensive architecture guide)
- `docs/implementations/EmbedderRefactoringTestResults.md` (test results summary)
- Updated `.github/copilot-instructions.md`
- Updated `docs/implementations/DoclingEmbedder.md`

### Phase 8: Cleanup (Estimated: 30 minutes) ✅ COMPLETE
**Actual Time**: 15 minutes

1. ✅ Fixed import statements in test files (removed unused imports)
2. ✅ Run black formatter on tests/ (4 files reformatted)
3. ✅ Run flake8 linter (all issues resolved)
4. ✅ Final smoke tests - All 56 tests passing (38 embedder + 18 recursive chunker)

**Total Estimated Time: 10.25 hours** (reduced 0.5 hours by removing load_chunks())  
**Total Actual Time: ~8 hours** (20% faster than estimated)

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Test EmbedderOrchestrator:**
- `test_detect_embedder_monster_format()` - MonsterBookEmbedder selected
- `test_detect_embedder_rulebook_format()` - RuleBookEmbedder selected
- `test_detect_embedder_unknown_format()` - ValueError raised
- `test_detect_embedder_empty_file()` - ValueError on empty chunks
- `test_chunk_caching()` - Chunks loaded once and reused
- `test_process_pipeline()` - Full pipeline executes correctly
- `test_run_test_queries()` - Test queries coordinated correctly
- `test_custom_embedder_classes()` - Accepts custom embedder list

**Test Base Embedder:**
- `test_get_embeddings_batch()` - Mock OpenAI API
- `test_get_or_create_collection_existing()` - Get existing collection
- `test_get_or_create_collection_new()` - Create new collection
- `test_backwards_compatibility_create()` - Embedder.create() still works
- `test_cached_chunks_injection()` - Verify embedder uses injected _cached_chunks
**Test MonsterBookEmbedder:**
- `test_chunk_format_is_compatible_positive()` - Monster Manual chunk recognized
- `test_chunk_format_is_compatible_negative()` - Rulebook chunk not recognized
- `test_add_statistic_block_monster()` - Statistics prepended correctly for monsters
- `test_add_statistic_block_category()` - No statistics for categories
- `test_extract_chunk_id()` - Correct ID extraction
- `test_process_metadata_monster()` - All monster fields present, type correct
- `test_process_metadata_category()` - All category fields present
- `test_process_metadata_default_transform()` - "default" transformed to "monster"
- `test_embed_chunks()` - Full pipeline with mocked OpenAI/ChromaDB
- `test_get_test_queries()` - Returns list of test queries
- `test_prepare_text_monster()` - Statistics prepended correctly
- `test_prepare_text_category()` - No statistics for categories
- `test_extract_chunk_id()` - Correct ID extraction
**Test RuleBookEmbedder:**
- `test_chunk_format_is_compatible_positive()` - Rulebook chunk recognized
- `test_chunk_format_is_compatible_negative()` - Monster Manual chunk not recognized
- `test_prepare_text()` - Content extracted correctly
- `test_extract_chunk_id()` - UID extracted correctly
- `test_process_metadata_default()` - Default chunk metadata, "default" → "rule"
- `test_process_metadata_spell()` - Spell chunk metadata
- `test_process_metadata_split()` - Split chunk metadata with siblings
- `test_hierarchy_flattening()` - List converted to string with arrow separator
- `test_hierarchy_with_arrow_in_text()` - Edge case: arrow in heading text
- `test_embed_chunks()` - Full pipeline with mocked OpenAI/ChromaDB
- `test_get_test_queries()` - Returns list of test queriesta
- `test_extract_metadata_spell()` - Spell chunk metadata
- `test_extract_metadata_split()` - Split chunk metadata
- `test_hierarchy_flattening()` - List converted to string

### 5.2 Integration Tests

**Test End-to-End Embedding:**
- `test_embed_monster_manual()` - Full pipeline with real ChromaDB
- `test_embed_players_handbook()` - Full pipeline with real ChromaDB
- `test_embed_dmg()` - Full pipeline with real ChromaDB
- `test_query_after_embedding()` - Verify searchability

### 5.3 Manual Testing Checklist

- [ ] Monster Manual chunks embed without errors
- [ ] Player's Handbook chunks embed without errors
- [ ] DMG chunks embed without errors
- [ ] Metadata appears correctly in ChromaDB
- [ ] Test queries return relevant results
- [ ] Collection truncation works
- [ ] CLI arguments work as expected
- [ ] Error messages are helpful

---

## 6. Migration Path

### For Existing Users:

**No Breaking Changes:**
- `python src/embedders/docling_embedder.py <chunk_file>` still works
- Collection names still configurable
- Auto-detection happens transparently

**New Flexibility:**
- Can import and use `Embedder.create()` in custom scripts
- Can subclass `Embedder` for new book types
- Can test embedders independently

### For Developers:

**Before (Monolithic):**
```python
embedder = DoclingEmbedder(
    chunks_file="data/chunks/chunks_DMG.json",
    collection_name="dnd_dmg"
)
embedder.process()
```

**After (Modular with Orchestrator):**
```python
# Recommended: Use orchestrator
orchestrator = EmbedderOrchestrator()
embedder = orchestrator.process(
    chunks_file="data/chunks/chunks_DMG.json",
    collection_name="dnd_dmg"
)
orchestrator.run_test_queries(embedder)

# Backwards compatible: Use factory (for direct embedding control)
embedder = Embedder.create(
    chunks_file="data/chunks/chunks_DMG.json",
    collection_name="dnd_dmg"
)
# Chunks already injected by orchestrator
embedder.embed_chunks(embedder._cached_chunks)

# Or explicit selection (manual orchestration)
embedder = RuleBookEmbedder(
    chunks_file="data/chunks/chunks_DMG.json",
    collection_name="dnd_dmg"
)
# Manually load chunks when not using orchestrator
with open("data/chunks/chunks_DMG.json", 'r') as f:
    chunks = json.load(f)
embedder._cached_chunks = chunks  # Inject manually
embedder.embed_chunks(chunks)
```

---

## 7. Risks and Mitigations

### Risk 1: Breaking Existing Embeddings
**Likelihood:** Low  
**Impact:** High  
**Mitigation:**
- Keep original `DoclingEmbedder` as fallback during transition
- Test metadata compatibility with existing collections
- Provide migration script if needed

### Risk 2: Performance Degradation
**Likelihood:** Very Low  
**Impact:** Medium  
**Mitigation:**
- Keep same batch processing logic
- Profile before/after refactoring
- No additional network calls or processing

### Risk 3: Incomplete Auto-Detection
**Likelihood:** Medium  
**Impact:** Medium  
**Mitigation:**
- Comprehensive detection criteria
- Clear error messages
- Allow manual embedder selection
- Add `--embedder-type` CLI flag as escape hatch

### Risk 4: Missing Edge Cases
**Likelihood:** Medium  
**Impact:** Low  
**Mitigation:**
- Test with all existing chunk files
- Add extensive logging during embedding
- Graceful fallbacks for missing fields

---

## 8. Future Enhancements

### 8.1 Additional Embedder Types
- **MonsterManual2eEmbedder** - For 2nd edition monsters
- **SpellCompendiumEmbedder** - For spell books with different structure
- **ModuleEmbedder** - For adventure modules

### 8.2 Advanced Orchestration Features
- **BatchEmbedderOrchestrator**: Process multiple files in batch
- **ParallelEmbedderOrchestrator**: Parallel embedding with worker pools
- **HybridDetectionOrchestrator**: Filename-based + content-based detection
- **PipelineMiddleware**: Pre/post-processing hooks (validation, enrichment, etc.)
- **RetryOrchestrator**: Handle transient OpenAI API failures

### 8.3 Advanced Embedder Features
- **Hybrid Metadata Extraction**: Combine statistics + hierarchy context
- **Custom Embedding Models**: Support local models (sentence-transformers)
- **Metadata Enrichment**: Add computed fields (word count, heading depth, etc.)
- **Validation Layer**: Validate chunk structure before embedding

### 8.4 Performance Optimizations
- **Parallel Processing**: Process batches concurrently (in orchestrator)
- **Caching**: Cache embeddings for unchanged chunks (in embedder)
- **Incremental Updates**: Only embed new/modified chunks (in orchestrator)

---

## 9. Success Criteria

### Must Have (Phase 1)
- ✅ All existing chunk files embed successfully
- ✅ Metadata correctness verified
- ✅ No performance degradation
- ✅ Backwards compatibility maintained
- ✅ Code passes all linters

### Should Have (Phase 2)
- ✅ Unit test coverage >80%
- ✅ Integration tests for each embedder
- ✅ Comprehensive documentation
- ✅ Clear error messages

### Nice to Have (Future)
- ⏳ Performance benchmarks documented
- ⏳ Migration guide for custom scripts
- ⏳ Video walkthrough of new architecture
## 10. Design Decisions (From Reviews)

### From Initial Review (v1.1)

1. **Q:** Collection management - where does it belong?  
   **A:** ✅ In base `Embedder` class via `_get_or_create_collection()` method.

2. **Q:** How to avoid double-loading chunks?  
   **A:** ✅ Load once in orchestrator, cache in `_cached_chunks`, inject to embedder instance. Embedder base class does NOT have `load_chunks()` method - orchestrator handles all chunk loading.

3. **Q:** Should `chunk_format_is_compatible()` be static or instance method?  
   **A:** ✅ Static method. Orchestrator uses dynamic class discovery via `__subclasses__()`.

4. **Q:** Type field collision between Monster Manual and rulebooks?  
   **A:** ✅ Transform in child classes: `"default"` → `"monster"` or `"rule"`.

5. **Q:** Where does `embed_chunks()` live?  
   **A:** ✅ Abstract method in base, separate implementations in children with helper methods.

6. **Q:** Error handling strategy?  
   **A:** ✅ OpenAI/ChromaDB errors: throw exception and terminate. No chunk validation.

7. **Q:** Test query ownership?  
   **A:** ✅ `test_query()` in base embedder, `get_test_queries()` in children, orchestrator coordinates via `run_test_queries()`.

8. **Q:** Hierarchy separator?  
   **A:** ✅ Unicode arrow ` → ` to avoid ambiguity.

9. **Q:** Should we add a `--embedder-type` CLI flag for manual selection?  
   **A:** Not initially. Auto-detection should handle 99% of cases. Add if users report issues.

10. **Q:** How to handle new chunk formats in the future?  
    **A:** Create new embedder subclass, implement 6 abstract methods, auto-discovered by orchestrator.

### From Orchestrator Review (v2.0)

11. **Q:** Should orchestration be separated from embedding operations?  
    **A:** ✅ **YES**. Create `EmbedderOrchestrator` class for better SRP compliance.

12. **Q:** Where does auto-detection logic belong?  
    **A:** ✅ In `EmbedderOrchestrator.detect_embedder()` method, not in `Embedder.create()`.

13. **Q:** Where does `process()` pipeline coordination belong?  
    **A:** ✅ In `EmbedderOrchestrator.process()` method. Embedders only execute their part.

14. **Q:** Should `Embedder.create()` be removed entirely?  
    **A:** ✅ **NO**. Keep as backwards compatibility wrapper that delegates to orchestrator.

15. **Q:** Where should chunk caching happen?  
    **A:** ✅ In `EmbedderOrchestrator` (loads once per file), injected to embedder instances.

---

## 11. Dependencies

**Existing:**
- `chromadb` - Vector database
- `openai` - Embedding API
- `pathlib` - File handling
- `json` - Chunk loading
- `typing` - Type hints

**New:**
- `abc` - Abstract base classes
- None (no new external dependencies)

**Optional (Testing):**
- `pytest` - Unit testing
- `pytest-mock` - Mocking framework

---

## 13. Implementation Notes

### Key Design Patterns Used
- **Template Method Pattern**: Base embedder defines algorithm, subclasses fill in details
- **Strategy Pattern**: Different strategies (MonsterBook vs RuleBook) for embedding
- **Orchestrator Pattern**: EmbedderOrchestrator coordinates high-level workflow
- **Factory Method Pattern**: Dynamic class discovery via `__subclasses__()`

### Critical Implementation Details
1. **Separation of Concerns**: 
   - `EmbedderOrchestrator`: Detection, pipeline coordination, test coordination, chunk loading
   - `Embedder`: Embedding operations (ChromaDB, OpenAI, collection management)
   - Child embedders: Format-specific logic
2. **Chunk Loading Responsibility**: 
   - Orchestrator loads chunks once and injects via `_cached_chunks`
   - Embedder base class does NOT have `load_chunks()` method
   - Manual usage requires explicit chunk loading and injection
3. **Dynamic Discovery**: Use `Embedder.__subclasses__()` in orchestrator
4. **Fail Fast**: Let OpenAI/ChromaDB exceptions propagate (no retry logic yet)
5. **Type Transformation**: Child classes responsible for transforming "default" type
6. **Unicode Separator**: Use ` → ` for hierarchy to avoid common text collisions
7. **Backwards Compatibility**: `Embedder.create()` delegates to orchestrator

### Testing Strategy
- Unit tests with mocked dependencies (OpenAI, ChromaDB)
- Integration tests with real ChromaDB (test collections)
- Manual verification with all three chunk files
- Compare results with old implementation for regression testing

---

## 14. Architecture Diagram

```
┌─────────────────────────────────────┐
│   EmbedderOrchestrator              │  ← Orchestration Layer
│   ├── detect_embedder()             │     (Format detection)
│   ├── process()                     │     (Pipeline coordination)
│   └── run_test_queries()            │     (Test coordination)
└─────────────────────────────────────┘
           │ uses
           ↓
┌─────────────────────────────────────┐
│   Embedder (ABC)                    │  ← Operations Layer
│   ├── __init__()                    │     (Common embedding operations)
│   ├── get_embeddings_batch()        │     (No chunk loading - uses injected _cached_chunks)
│   ├── _get_or_create_collection()   │
│   ├── test_query()                  │
│   └── Abstract methods:             │
│       - chunk_format_is_compatible()│
│       - embed_chunks()              │
│       - prepare_text_for_embedding()│
│       - extract_chunk_id()          │
│       - process_metadata()          │
│       - get_test_queries()          │
└─────────────────────────────────────┘
           ↑ extends
      ┌────┴────┐
      │         │
┌─────┴─────┐ ┌┴─────────┐
│MonsterBook│ │RuleBook  │  ← Strategy Layer
│Embedder   │ │Embedder  │     (Format-specific logic)
└───────────┘ └──────────┘
```

---

*Last Updated: October 20, 2025*  
*Version: 2.0*  
*Status: ✅ Ready for Implementation (Orchestrator Architecture)*
- [ ] All code written and reviewed
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Manual testing checklist completed
- [ ] Documentation updated
- [ ] Code formatted (black) and linted (flake8, mypy)
- [ ] Git commit with descriptive message
- [ ] README updated if needed
- [ ] No regressions in existing functionality

---

*Last Updated: October 20, 2025*  
*Version: 1.0*  
*Status: Ready for Implementation*
