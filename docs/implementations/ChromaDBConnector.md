# ChromaDBConnector Implementation

**Created**: October 21, 2025  
**Purpose**: Centralize all ChromaDB connection logic and operations  
**File**: `src/utils/chromadb_connector.py`

## Overview

The `ChromaDBConnector` class is a centralized connector that handles all ChromaDB database operations across the codebase. It eliminates code duplication by providing a single source of truth for ChromaDB interactions.

## Design Pattern

**Pattern**: Connector/Gateway Pattern  
**Purpose**: Encapsulate external database access behind a clean interface  
**Benefits**:
- Single point of configuration
- Consistent error handling
- Easier testing (single mock point)
- No code duplication

## Architecture

```
┌─────────────────────────────────────────┐
│      Application Components             │
│  (Embedders, Query, CLI Commands)       │
└───────────────┬─────────────────────────┘
                │
                │ uses
                ▼
┌─────────────────────────────────────────┐
│       ChromaDBConnector                 │
│  - Connection management                │
│  - Collection operations                │
│  - Error handling                       │
└───────────────┬─────────────────────────┘
                │
                │ wraps
                ▼
┌─────────────────────────────────────────┐
│       chromadb.HttpClient               │
│  (External ChromaDB Python SDK)         │
└─────────────────────────────────────────┘
```

## Key Methods

### Connection Methods

**`__init__(chroma_host: str = None, chroma_port: int = None)`**
- Initializes connection to ChromaDB server
- Uses `.env` configuration if parameters not provided
- Creates `HttpClient` instance
- **Returns**: None (sets `self.client`)

### Collection Management

**`get_collection(name: str)`**
- Retrieves existing collection
- **Raises**: `ValueError` if collection doesn't exist
- **Returns**: ChromaDB Collection object

**`create_collection(name: str, metadata: Dict = None)`**
- Creates new collection with optional metadata
- **Raises**: `ValueError` if collection already exists
- **Returns**: ChromaDB Collection object

**`get_or_create_collection(name: str, metadata: Dict = None)`**
- Gets collection if exists, creates if not
- **Idempotent**: Safe to call multiple times
- **Returns**: ChromaDB Collection object

**`delete_collection(name: str)`**
- Permanently deletes collection and all its data
- **Warning**: Irreversible operation
- **Returns**: None

**`truncate_collection(name: str)`**
- Deletes all entries but keeps collection structure
- **Returns**: `int` - Number of entries deleted
- **Use case**: Clearing data for re-embedding

### Query Methods

**`list_collections()`**
- Lists all available collections
- **Returns**: `List[Collection]` - List of collection objects

**`collection_exists(name: str)`**
- Checks if collection exists
- **Returns**: `bool`

**`get_collection_count(name: str)`**
- Returns number of entries in collection
- **Returns**: `int`

**`get_collection_info(name: str)`**
- Returns full collection metadata
- **Returns**: `Dict` with name, id, count, metadata

## Usage Examples

### Basic Connection

```python
from src.utils.chromadb_connector import ChromaDBConnector

# Use default .env configuration
chroma = ChromaDBConnector()

# Or specify connection explicitly
chroma = ChromaDBConnector(chroma_host="localhost", chroma_port=8060)
```

### Working with Collections

```python
# Create new collection
collection = chroma.create_collection("my_collection")

# Get existing collection
collection = chroma.get_collection("dnd_monster_manual")

# Get or create (idempotent)
collection = chroma.get_or_create_collection("dnd_phb")

# Delete collection permanently
chroma.delete_collection("old_collection")

# Truncate collection (keep structure, delete data)
count_deleted = chroma.truncate_collection("dnd_dmg")
print(f"Deleted {count_deleted} entries")
```

### Collection Queries

```python
# List all collections
for collection in chroma.list_collections():
    print(f"{collection.name}: {collection.count()} entries")

# Check if collection exists
if chroma.collection_exists("dnd_monster_manual"):
    print("Collection found!")

# Get entry count
count = chroma.get_collection_count("dnd_phb")
print(f"PHB has {count} chunks")

# Get full collection info
info = chroma.get_collection_info("dnd_dmg")
print(f"Name: {info['name']}")
print(f"Count: {info['count']}")
print(f"Metadata: {info['metadata']}")
```

## Integration Points

The `ChromaDBConnector` is used by:

1. **`base_embedder.py`**: Initializes connector in `__init__`, uses `get_or_create_collection()` and `truncate_collection()`
2. **`docling_query.py`**: Uses connector to retrieve collections for querying
3. **`main.py`**: CLI commands use connector for `list-collections` and `truncate-collection`
4. **`cli.py`**: Entry point commands use connector for all ChromaDB operations

## Error Handling

The connector provides consistent error messages:

```python
try:
    collection = chroma.get_collection("nonexistent")
except ValueError as e:
    print(f"Error: {e}")
    # Error: Collection 'nonexistent' not found
    # Available collections: [...]
```

## Testing

When writing tests that use embedders or query modules, mock at the import point:

```python
from unittest.mock import MagicMock, patch

@patch("src.embedders.base_embedder.ChromaDBConnector")
def test_embedder(mock_chroma):
    # Setup mock
    mock_collection = MagicMock()
    mock_chroma_instance = MagicMock()
    mock_chroma_instance.get_or_create_collection.return_value = mock_collection
    mock_chroma.return_value = mock_chroma_instance
    
    # Test code that uses embedder
    embedder = MonsterBookEmbedder("test.json", collection_name="test")
    # ... rest of test
```

**Key Points**:
- Mock at the **import location** (e.g., `src.embedders.base_embedder.ChromaDBConnector`)
- NOT at the definition location (`src.utils.chromadb_connector.ChromaDBConnector`)
- This ensures the mock is injected where the class is used

## Configuration

The connector reads from `.env`:

```env
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/
```

Configuration is accessed via `src/utils/config.py`:
```python
def get_chroma_connection_params():
    """Get ChromaDB connection parameters."""
    return {
        "host": os.getenv("chroma_host_url", "http://localhost"),
        "port": int(os.getenv("chroma_host_port", "8060"))
    }
```

## Benefits Over Previous Approach

### Before ChromaDBConnector

**Problems**:
- Code duplication in 4+ files (base_embedder, main.py, cli.py, query)
- Each file had own `import chromadb` and connection setup
- Inconsistent error handling
- Testing required mocking in multiple locations
- Hard to change connection logic (had to update 4+ files)

### After ChromaDBConnector

**Benefits**:
- ✅ **Single source of truth** for ChromaDB operations
- ✅ **Zero duplication** - connection logic in one place
- ✅ **Consistent API** - same methods everywhere
- ✅ **Easier testing** - mock once at import point
- ✅ **Maintainable** - change connection logic in one file
- ✅ **Clean separation** - business logic separate from DB access

## Migration Guide

If adding new code that needs ChromaDB:

### Old Way (Don't Do This)
```python
import chromadb
from src.utils.config import get_chroma_connection_params

params = get_chroma_connection_params()
client = chromadb.HttpClient(host=params["host"], port=params["port"])
collection = client.get_or_create_collection("my_collection")
```

### New Way (Use This)
```python
from src.utils.chromadb_connector import ChromaDBConnector

chroma = ChromaDBConnector()
collection = chroma.get_or_create_collection("my_collection")
```

## Related Documentation

- **Implementation**: `src/utils/chromadb_connector.py` (221 lines)
- **Usage**: `src/embedders/base_embedder.py` (embedder base class)
- **CLI Integration**: `main.py` and `src/cli.py`
- **Query Integration**: `src/query/docling_query.py`
- **Tests**: All test files mock `ChromaDBConnector` at import location

## Future Enhancements

Possible improvements:
1. **Connection pooling** - Reuse connections across multiple operations
2. **Batch operations** - `batch_get_collections()`, `batch_truncate()`
3. **Retry logic** - Automatic retries on connection failures
4. **Connection health checks** - `is_connected()`, `ping()`
5. **Metrics** - Track operation counts and timing
6. **Async support** - Non-blocking ChromaDB operations

---

*Version: 1.0*  
*Last Updated: October 21, 2025*
