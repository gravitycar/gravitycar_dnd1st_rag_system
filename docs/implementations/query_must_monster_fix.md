# Query Must Filter Fix: Monster Name Matching

## Summary

Fixed false positive matches in monster query filtering by changing from `contain_one_of` operator with word splitting to `contain` operator with base name extraction.

## Problem

The original implementation used `contain_one_of` with monster names split on whitespace:

```json
{
  "name": "Gold Dragon (Draco Orientalus Sino Dux)",
  "metadata": {
    "query_must": {
      "contain_one_of": [["gold", "dragon", "(draco", "orientalus", "sino", "dux)"]]
    }
  }
}
```

**Bug**: Query "blue dragon" matched "Gold Dragon" chunks because both contain the word "dragon".

**Impact**: All dragon types matched any dragon query, making the filter useless for disambiguation.

## Solution

Changed to `contain` operator with parenthetical text removed:

```json
{
  "name": "Gold Dragon (Draco Orientalus Sino Dux)",
  "metadata": {
    "query_must": {
      "contain": "gold dragon"
    }
  }
}
```

**Benefits**:
- ✅ Precise matching: "gold dragon" query only matches Gold Dragon chunks
- ✅ No false positives: Different dragon types don't cross-match
- ✅ Plural support: "gold dragons" matches "gold dragon" (optional 's' in regex)
- ✅ Case insensitive: Works with any capitalization
- ✅ Word boundaries: Prevents partial matches (e.g., "bear" won't match "owlbear")

## Files Changed

### 1. `src/chunkers/monster_encyclopedia.py`
**Function**: `build_monster_metadata()`

**Before**:
```python
# Split name into words for contain_one_of matching
name_words = name.lower().split()

metadata = {
    'query_must': {
        'contain_one_of': [name_words]
    }
}
```

**After**:
```python
# Extract base name without parenthetical text
base_name = re.sub(r'\s*\([^)]*\)\s*', '', name).strip().lower()

metadata = {
    'query_must': {
        'contain': base_name
    }
}
```

### 2. `src/query/query_must_filter.py`
**Function**: `validate_contain()`

**Enhancement**: Added plural support by allowing optional 's' at end of pattern:

```python
# Allow optional 's' at end for plurals, with word boundary after
escaped_term = re.escape(term_lower)
pattern = r'\b' + escaped_term + r's?\b'
```

This allows "gold dragon" to match both "gold dragon" and "gold dragons".

## Testing

### Unit Tests
Created `tests/test_monster_encyclopedia_chunker.py` with 6 tests:
- ✅ Monster with parenthetical name
- ✅ Monster without parenthetical name
- ✅ Case normalization
- ✅ Complex parenthetical text
- ✅ **Dragon false positive prevention** (key test)
- ✅ Plural query matching

### Integration Test
Created `tmp/compare_old_vs_new_query_must.py` demonstrating:

**Old Approach Results**:
```
Query: "What is a gold dragon?"
  Gold Dragon:  ✓ (CORRECT)
  Blue Dragon:  ✓ (FALSE POSITIVE ❌)
  Black Dragon: ✓ (FALSE POSITIVE ❌)
```

**New Approach Results**:
```
Query: "What is a gold dragon?"
  Gold Dragon:  ✓ (CORRECT)
  Blue Dragon:  ✗ (CORRECT)
  Black Dragon: ✗ (CORRECT)
```

### Test Suite Status
- **All tests pass**: 357 tests (including 36 query_must_filter tests)
- **No regressions**: Existing functionality preserved
- **New tests added**: 6 new tests for monster chunker

## Examples

### Dragon Filtering
```python
# Gold Dragon chunk
query_must = {"contain": "gold dragon"}

# Queries
"What is a gold dragon?"      → ✓ Match
"Tell me about gold dragons"  → ✓ Match (plural)
"What is a blue dragon?"      → ✗ No match
"What is a dragon?"           → ✗ No match (needs "gold dragon")
```

### Other Monsters
```python
# Beholder chunk
query_must = {"contain": "beholder"}

# Queries  
"What is a beholder?"         → ✓ Match
"Tell me about beholders"     → ✓ Match (plural)
"What is a death tyrant?"     → ✗ No match
```

## Migration Path

### Regenerating Chunks
To update existing chunk files with the new query_must format:

```bash
# Regenerate Monster Manual chunks
python src/chunkers/monster_encyclopedia.py \
  data/markdown/docling/good_pdfs/Monster_Manual_\(1e\).md

# Verify changes
python tmp/compare_old_vs_new_query_must.py
```

### Re-embedding (If Needed)
If chunks are already embedded in ChromaDB, re-run the embedder:

```bash
python src/embedders/docling_embedder.py \
  chunks_Monster_Manual_\(1e\).json \
  dnd_monster_manual
```

## Backward Compatibility

**Breaking Change**: ⚠️ Chunks with old `contain_one_of` format won't work with new code.

**Migration Required**: Yes, must regenerate all monster chunks.

**Affected Collections**:
- `dnd_monster_manual` (294 chunks)
- Any custom monster collections

## Future Considerations

### Other Book Types
This fix applies specifically to monster books. Other book types use different query_must patterns:

- **Attack tables**: Still use `contain_one_of` with multiple groups (e.g., character class + armor class)
- **Spell tables**: May need similar treatment if spell names have parenthetical text
- **Rule sections**: Generally don't need query_must filtering

### Potential Enhancements
1. **Synonym support**: "wyrm" → matches dragon chunks
2. **Abbreviation handling**: "MM" → matches "Monster Manual"
3. **Fuzzy matching**: Handle typos in queries

---

## References

- **Copilot Instructions**: `.github/copilot-instructions.md`
- **Query Must Filter Docs**: `docs/implementations/adaptive_filtering.md`
- **Test Files**:
  - `tests/test_monster_encyclopedia_chunker.py`
  - `tests/test_query_must_filter.py`
- **Demo Scripts**:
  - `tmp/test_monster_query_must.py`
  - `tmp/compare_old_vs_new_query_must.py`

---

*Date: November 5, 2025*  
*Issue: Dragon name filtering false positives*  
*Resolution: Changed from `contain_one_of` to `contain` with base name extraction*
