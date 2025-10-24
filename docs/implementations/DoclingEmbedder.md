# Docling Embedder (CLI Entry Point)

**File**: `src/embedders/docling_embedder.py`  
**Purpose**: Command-line interface for the embedder system  
**Status**: ⚠️ **LEGACY DOCUMENTATION** - See `EmbedderArchitecture.md` for current architecture

---

## Note: Architecture Changed (October 2025)

This document describes the **legacy monolithic implementation**. The system has been refactored into a modular architecture:

- **New Architecture**: Orchestrator + Strategy pattern with format auto-detection
- **See**: `docs/implementations/EmbedderArchitecture.md` for current design
- **CLI Still Works**: The `docling_embedder.py` script now uses the orchestrator internally

**Current Entry Point**:
```bash
python -m src.embedders.docling_embedder \
    data/chunks/chunks_Monster_Manual_(1e).json \
    dnd_monster_manual \
    --test-queries
```

This now delegates to:
1. `EmbedderOrchestrator` - Auto-detects format
2. `MonsterBookEmbedder` or `RuleBookEmbedder` - Format-specific logic
3. `Embedder` base class - Common operations

---

## Legacy Overview (Historical Context)

The original Docling Embedder took chunked JSON files (from `monster_encyclopedia.py` or `players_handbook.py`) and:

1. **Embeds** text using Sentence Transformers
2. **Prepends statistics** to chunk text for better searchability
3. **Flattens metadata** for ChromaDB compatibility
4. **Stores** embeddings and metadata in ChromaDB collections

This was a **universal embedder**—it worked with any chunked JSON format from the chunking pipeline, but used conditional logic to handle different formats.

---

## Key Features

### 1. Embedding Model Selection

Currently uses **`all-mpnet-base-v2`** (768 dimensions):
- High-quality semantic embeddings
- Excellent for RAG retrieval
- Good balance of speed and accuracy
- Proven performance on D&D content

**Other Models Tested**:
- `all-MiniLM-L6-v2` (384d): Faster, slightly lower quality
- `all-mpnet-base-v2` (768d): **✅ Current choice**
- OpenAI `text-embedding-ada-002` (1536d): Expensive, not significantly better

**Model Initialization**:
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-mpnet-base-v2')
# Model loaded once, reused for all chunks
```

### 2. Statistics Prepending

For chunks with monster statistics, the embedder **prepends** the statistics block to the text before embedding.

**Why?**
- Embedding models can't see structured metadata
- Statistics must be part of searchable text
- Queries like "How many HP does X have?" depend on this

**Implementation**:
```python
def prepare_text_for_embedding(chunk):
    """
    Prepend statistics to text if present.
    
    Example:
        Input: {
            'text': 'Owlbears are fierce...',
            'statistics': {
                'ARMOR CLASS': '5',
                'HIT DICE': '5+2',
                ...
            }
        }
        
        Output:
            'ARMOR CLASS: 5\nHIT DICE: 5+2\n...\nOwlbears are fierce...'
    """
    if 'statistics' in chunk and chunk['statistics']:
        stats_text = format_statistics(chunk['statistics'])
        return f"{stats_text}\n\n{chunk['text']}"
    return chunk['text']
```

**Format**:
```
FREQUENCY: Rare
NO. APPEARING: 1-6
ARMOR CLASS: 5
MOVE: 12"
HIT DICE: 5+2
...

Owlbears are probably the result of genetic experimentation...
```

### 3. Metadata Flattening

ChromaDB requires **flat metadata** (no nested dictionaries).

**Problem**: Chunker outputs nested structures:
```json
{
  "metadata": {
    "page": 76,
    "category": null,
    "character_count": 892
  },
  "statistics": {
    "ARMOR CLASS": "5",
    "HIT DICE": "5+2"
  }
}
```

**Solution**: Flatten to single-level keys:
```json
{
  "page": 76,
  "category": null,
  "character_count": 892,
  "stat_ARMOR_CLASS": "5",
  "stat_HIT_DICE": "5+2"
}
```

**Implementation**:
```python
def flatten_metadata(chunk):
    """
    Flatten nested metadata for ChromaDB.
    
    Rules:
    1. Lift 'metadata' keys to top level
    2. Prefix 'statistics' keys with 'stat_'
    3. Convert None → 'null' (ChromaDB compatibility)
    4. Ensure all values are strings
    """
    flat = {}
    
    # Copy metadata fields
    if 'metadata' in chunk:
        for key, value in chunk['metadata'].items():
            flat[key] = str(value) if value is not None else 'null'
    
    # Copy and prefix statistics
    if 'statistics' in chunk and chunk['statistics']:
        for key, value in chunk['statistics'].items():
            safe_key = key.replace(' ', '_').replace('/', '_')
            flat[f"stat_{safe_key}"] = str(value)
    
    # Add type and title
    flat['type'] = chunk.get('type', 'unknown')
    flat['title'] = chunk.get('title', 'Untitled')
    
    return flat
```

### 4. ChromaDB Collection Management

The embedder creates or overwrites ChromaDB collections.

**Collection Structure**:
```python
{
    "name": "dnd_monster_manual",
    "documents": [...],          # Text content
    "embeddings": [...],         # 768-dimensional vectors
    "metadatas": [...],          # Flat metadata dictionaries
    "ids": [...]                 # Unique IDs (chunk_0, chunk_1, ...)
}
```

**Operations**:
```python
# 1. Connect to ChromaDB
client = chromadb.HttpClient(host='localhost', port=8060)

# 2. Delete existing collection (if overwriting)
try:
    client.delete_collection(name=collection_name)
except:
    pass  # Collection doesn't exist

# 3. Create new collection
collection = client.create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"}  # Cosine similarity
)

# 4. Add documents with embeddings
collection.add(
    documents=texts,
    embeddings=embeddings,
    metadatas=metadatas,
    ids=ids
)
```

---

## Algorithm

### High-Level Flow

```
1. Load chunked JSON file
2. For each chunk:
   a. Prepend statistics to text (if present)
   b. Generate embedding using SentenceTransformer
   c. Flatten metadata
   d. Create unique ID
3. Connect to ChromaDB
4. Delete existing collection (if overwriting)
5. Create new collection with cosine similarity
6. Batch add: documents, embeddings, metadata, IDs
7. Verify storage
```

### Batch Processing

For efficiency, embeddings are generated in batches:

```python
def embed_chunks(chunks, batch_size=32):
    """
    Generate embeddings for all chunks.
    
    Args:
        chunks: List of chunk dictionaries
        batch_size: Number of chunks to embed at once
    
    Returns:
        List of embedding vectors (768-dimensional)
    """
    texts = [prepare_text_for_embedding(c) for c in chunks]
    
    # Sentence Transformers handles batching internally
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    return embeddings.tolist()
```

**Benefits**:
- Faster than one-by-one embedding
- GPU utilization (if available)
- Progress bar for user feedback

---

## Usage

### Basic Usage

```bash
# Embed Monster Manual chunks
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Monster_Manual_(1e).json \
  dnd_monster_manual

# Embed Player's Handbook chunks
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Players_Handbook_(1e).json \
  dnd_players_handbook
```

**Output**: ChromaDB collection created/updated

### Verify Storage

```bash
# List collections
python scripts/list_chromadb_collections.py

# Output:
# Collections in ChromaDB:
# - dnd_monster_manual (512 chunks)
# - dnd_players_handbook (843 chunks)
```

### Programmatic Usage

```python
from src.embedders.docling_embedder import embed_and_store

# Embed and store chunks
embed_and_store(
    json_file="data/chunks/chunks_Monster_Manual_(1e).json",
    collection_name="dnd_monster_manual"
)

# Or use with existing ChromaDB client
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.HttpClient(host='localhost', port=8060)
model = SentenceTransformer('all-mpnet-base-v2')

# Custom embedding logic
# ...
```

---

## Design Decisions

### Why Prepend Statistics?

**Alternative 1**: Store statistics only in metadata
- ❌ Embedding model can't see metadata
- ❌ Queries like "5 HD monsters" won't work
- ❌ Retrieval purely based on description text

**Alternative 2**: Embed statistics separately
- ❌ Creates duplicate chunks
- ❌ Complicates retrieval logic
- ❌ Harder to rank results

**Decision**: Prepend to text before embedding
- ✅ Statistics are searchable
- ✅ Single embedding per chunk
- ✅ Metadata still available for filtering
- ✅ Works with any embedding model

### Why Flatten Metadata?

**ChromaDB Limitation**: No nested metadata allowed.

```python
# ❌ This breaks ChromaDB:
metadata = {
    "details": {
        "page": 76,
        "category": "DEMON"
    }
}

# ✅ This works:
metadata = {
    "details_page": 76,
    "details_category": "DEMON"
}
```

**Implementation**: Flatten during embedding, not during chunking.
- Chunker outputs clean, structured JSON
- Embedder handles ChromaDB-specific constraints
- Separation of concerns

### Why Cosine Similarity?

**Options**:
1. **Cosine similarity**: Angle between vectors
2. **Euclidean distance**: Straight-line distance
3. **Dot product**: Magnitude and angle

**Decision**: Cosine similarity
- ✅ Standard for semantic search
- ✅ Invariant to vector magnitude
- ✅ Values in range [-1, 1] (easy to interpret)
- ✅ Used by most RAG systems

**Configuration**:
```python
collection = client.create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"}  # Cosine similarity
)
```

### Why `all-mpnet-base-v2`?

**Comparison**:
| Model | Dimensions | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| MiniLM-L6-v2 | 384 | Fast | Good | Prototyping |
| **mpnet-base-v2** | **768** | **Medium** | **Excellent** | **Production** |
| OpenAI Ada | 1536 | Slow (API) | Excellent | High budget |

**Decision Factors**:
1. **Open source**: No API costs, runs locally
2. **Quality**: State-of-the-art for semantic search
3. **Proven**: Used in many RAG systems
4. **Size**: 420MB model, reasonable for local hosting

---

## Configuration

### Environment Variables

```bash
# ChromaDB connection (optional, defaults shown)
CHROMA_HOST=localhost
CHROMA_PORT=8060
```

### Model Configuration

To change the embedding model, edit `docling_embedder.py`:

```python
# Current model
model = SentenceTransformer('all-mpnet-base-v2')

# Alternative: Faster, smaller
model = SentenceTransformer('all-MiniLM-L6-v2')

# Alternative: Larger, slightly better
model = SentenceTransformer('all-mpnet-base-v2')  # Already using!
```

**Important**: Changing models requires re-embedding all collections.

---

## Output Format

### ChromaDB Collection Schema

```python
{
    "name": "dnd_monster_manual",
    "metadata": {
        "hnsw:space": "cosine"  # Similarity metric
    },
    "count": 512,  # Number of chunks
    "documents": [
        "FREQUENCY: Rare\nNO. APPEARING: 1-6\n...",  # Text with stats
        ...
    ],
    "embeddings": [
        [0.123, -0.456, 0.789, ...],  # 768 dimensions
        ...
    ],
    "metadatas": [
        {
            "type": "monster",
            "title": "OWLBEAR",
            "page": "76",
            "category": "null",
            "character_count": "892",
            "stat_ARMOR_CLASS": "5",
            "stat_HIT_DICE": "5+2",
            ...
        },
        ...
    ],
    "ids": [
        "chunk_0",
        "chunk_1",
        ...
    ]
}
```

---

## Performance

### Embedding Speed

**Hardware**: CPU (AMD Ryzen 9 5900X, 12 cores)

| Book | Chunks | Time | Rate |
|------|--------|------|------|
| Monster Manual | 512 | ~60s | 8.5 chunks/sec |
| Player's Handbook | 843 | ~100s | 8.4 chunks/sec |

**With GPU**: 3-5x faster (tested with NVIDIA RTX 3080)

### Storage Size

**ChromaDB Disk Usage**:
- Monster Manual: ~150 MB
- Player's Handbook: ~250 MB
- Total: ~400 MB for 2 books

**Breakdown**:
- Embeddings: 768 floats × 4 bytes × num_chunks
- Metadata: ~500 bytes/chunk
- Index: ~30% overhead (HNSW)

---

## Troubleshooting

### "Connection refused" Error

```bash
# Check if ChromaDB is running
curl http://localhost:8060/api/v1/heartbeat

# If not running:
./scripts/start_chroma.sh
```

### "Model not found" Error

```bash
# Download model manually
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2')"

# Model will be cached at:
# ~/.cache/torch/sentence_transformers/
```

### Out of Memory Error

**Solution 1**: Reduce batch size
```python
embeddings = model.encode(texts, batch_size=16)  # Default: 32
```

**Solution 2**: Use smaller model
```python
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384d instead of 768d
```

### "Collection already exists" Error

This is expected! The embedder **overwrites** existing collections by default.

To preserve existing data, modify `docling_embedder.py`:
```python
# Current behavior: overwrite
try:
    client.delete_collection(name=collection_name)
except:
    pass

# Alternative: append only
collection = client.get_or_create_collection(name=collection_name)
```

---

## Future Enhancements

### 1. Incremental Embedding

Currently, the entire collection is re-embedded on each run.

**Improvement**: Track chunk hashes, only embed new/modified chunks.

### 2. Multi-Model Support

Store embeddings from multiple models in the same collection.

**Use Case**: Hybrid retrieval with different embedding strategies.

### 3. GPU Optimization

Automatically detect and use GPU if available.

```python
import torch

device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = SentenceTransformer('all-mpnet-base-v2', device=device)
```

### 4. Embedding Cache

Cache embeddings to disk to avoid re-computation.

**Format**: `{chunk_hash: embedding_vector}`

---

## Related Documentation

- **[MonsterEncyclopediaChunker.md](MonsterEncyclopediaChunker.md)**: Chunking strategy
- **[DnDRAG.md](DnDRAG.md)**: Query and retrieval pipeline
- **[adaptive_filtering.md](adaptive_filtering.md)**: Result filtering algorithm
- **[../setup/chromadb_setup.md](../setup/chromadb_setup.md)**: ChromaDB configuration

---

**Author**: Mike (GravityCar)  
**Last Updated**: 2025-01-XX  
**Version**: 1.0
