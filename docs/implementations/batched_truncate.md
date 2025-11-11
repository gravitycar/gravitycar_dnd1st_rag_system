# Batched Truncate Implementation

## Problem
ChromaCloud was failing when attempting to truncate large collections (2000+ items) because the original implementation tried to fetch and delete all IDs at once, exceeding ChromaCloud's request size limits.

## Solution
Modified `ChromaDBConnector.truncate_collection()` to process deletions in batches.

### Changes Made

#### 1. Updated `src/utils/chromadb_connector.py`
```python
def truncate_collection(self, name: str, batch_size: int = 500) -> int:
```

**Key Features:**
- Default batch size: 500 (safe for both local and cloud)
- Progress reporting: Shows `Deleted X/Y items...` for each batch
- Graceful termination: Stops when no more items are returned
- Same return value: Returns total count deleted

**Algorithm:**
```
1. Get collection count
2. Loop:
   a. Fetch batch of IDs (limit=batch_size)
   b. Delete those IDs
   c. Report progress
   d. If batch < batch_size, we're done
3. Return total deleted
```

#### 2. Updated `main.py` CLI
Added `--batch-size` argument to truncate command:
```bash
python main.py truncate adnd_1e --confirm --batch-size 100
```

**Default:** 500 (good for most cases)  
**Recommended for ChromaCloud:** 100-200 (more conservative)

## Usage Examples

### Local ChromaDB (large batches OK)
```bash
python main.py truncate test_collection --confirm
# Uses default batch_size=500
```

### ChromaCloud (smaller batches recommended)
```bash
python main.py truncate adnd_1e --confirm --batch-size 100
```

### Interactive (with confirmation prompt)
```bash
python main.py truncate adnd_1e --batch-size 100
# Will prompt: "⚠️  WARNING: This will delete ALL entries..."
```

## Performance

### Before (Failed)
- Attempted to fetch 2940 IDs in one request
- ChromaCloud request size limit exceeded
- Operation failed

### After (Success)
- Fetches and deletes 100 IDs at a time
- Each batch takes ~0.5-1 second
- Total time for 2940 items: ~30-60 seconds
- Progress feedback every batch

## Related Issue
This is required for deploying the `query_must` metadata fix to production. See `docs/issues/query_must_production_sync.md` for context.

## Testing

### Verified Working
✅ ChromaCloud truncate with batch_size=100  
✅ Progress reporting  
✅ Graceful completion  

### Next Steps
1. ✅ Truncate production collection (adnd_1e)
2. ⏳ Re-embed all chunks with query_must metadata
3. ⏳ Verify filtering works in production

## Files Modified
- `src/utils/chromadb_connector.py` - Added batch_size parameter and loop
- `main.py` - Added --batch-size CLI argument
