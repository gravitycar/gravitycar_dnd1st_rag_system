# Query Must Production Sync Issue

## Issue Summary

**Date:** November 10, 2025  
**Status:** IDENTIFIED - Production data out of sync with local chunks  
**Severity:** High - Incorrect filtering in production

## Problem

The `query_must` filtering is **working correctly** in local ChromaDB but **not working** in production (ChromaCloud). DMG chunks with `query_must` metadata are being included in results when they should be excluded.

### Example

**Query:** "what does a 7th level fighter need to roll to hit armor class 6?"

**Production (ChromaCloud) - INCORRECT:**
```
✅ KEEP: I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 7 
         [chunk 1/15] (no restrictions)
```

**Local (test_dmg_filtering) - CORRECT:**
```
❌ EXCLUDE: I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS Opponent Armor Class 7
    ❌ Failed contain_one_of: [
        ['cleric', 'clerics', 'druid', 'druids', 'monk', 'monks'], 
        ['opponent armor class 7', 'armor class 7', 'a.c. 7', 'ac 7']
    ]
```

## Root Cause

The production ChromaCloud collection (`adnd_1e`) was created **before** the `query_must` metadata was added to DMG chunks. The local collection (`test_dmg_filtering`) has the updated chunks from `chunks_DMG_with_query_must.json`, but production does not.

## Verification

### Local Chunks File (CORRECT)
```json
{
  "metadata": {
    "uid": "Dungeon_Master_s_Guide_(1e)_organized_with_json_tables_COMBAT_COMBAT_TABLES_I_A__ATTACK_MATRIX_FOR_CLERICS__DRUIDS_AND_MONKS_Opponent_Armor_Class_7_1",
    "query_must": {
      "contain_one_of": [
        ["cleric", "clerics", "druid", "druids", "monk", "monks"],
        ["opponent armor class 7", "armor class 7", "a.c. 7", "ac 7"]
      ]
    }
  }
}
```

### Production ChromaDB Metadata (MISSING query_must)
The production collection shows `(no restrictions)` for chunks that should have `query_must` constraints.

## Solution

Re-embed the DMG chunks with the new `query_must` metadata and upload to production:

### Step 1: Embed Updated Chunks Locally
```bash
cd /home/mike/projects/gravitycar_dnd1st_rag_system
source venv/bin/activate

# Embed the updated DMG chunks to a new collection
python -m src.cli embed \
  data/chunks/chunks_DMG_with_query_must.json \
  dnd_dmg_with_filtering \
  --overwrite
```

### Step 2: Upload to ChromaCloud
```bash
# Use the upload script (if available) or manually upload
# Ensure you're using .env.dndchat.production for ChromaCloud credentials

# Option A: Upload script
python scripts/upload_to_chromacloud.py \
  --collection dnd_dmg_with_filtering \
  --target-collection adnd_1e \
  --merge

# Option B: Re-embed directly to ChromaCloud
# (requires setting ChromaCloud credentials in .env.dndchat)
python -m src.cli embed \
  data/chunks/chunks_DMG_with_query_must.json \
  adnd_1e \
  --merge
```

### Step 3: Verify in Production
```bash
# Query production to verify filtering works
dnd-query --debug "what does a 7th level fighter need to roll to hit armor class 6?"

# Should see:
# ❌ EXCLUDE: I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 7
```

## Why Monster Manual Filtering Works

The Monster Manual filtering works correctly in production because:
1. Monster chunks use `contain` operator (single term: "owlbear", "bear", etc.)
2. These chunks were embedded **after** the `query_must` feature was implemented
3. No re-deployment needed for Monster Manual

## Prevention

To prevent this in the future:

1. **Version Control:** Add collection version metadata to track schema changes
2. **Migration Scripts:** Create scripts to update metadata in existing collections
3. **Testing:** Always test against production data before deploying
4. **Documentation:** Update deployment docs to include metadata schema version

## Related Files

- `/home/mike/projects/gravitycar_dnd1st_rag_system/data/chunks/chunks_DMG_with_query_must.json` - Updated chunks (local)
- `/home/mike/projects/gravitycar_dnd1st_rag_system/src/query/query_must_filter.py` - Filtering logic (working correctly)
- `/home/mike/projects/gravitycar_dnd1st_rag_system/src/query/docling_query.py` - Query pipeline (working correctly)
- `.env.dndchat` - Production ChromaCloud credentials
- `.env.dndchat.local` - Local ChromaDB config (for testing)

## Test Results

### Local Collection (test_dmg_filtering) - ✅ WORKING
- Total chunks with query_must: 1369
- Filtering: Correctly excludes non-matching chunks
- Debug output shows detailed filter failures

### Production Collection (adnd_1e) - ❌ NOT WORKING
- Total chunks: 2466 (includes MM, PHB, DMG)
- DMG chunks missing query_must metadata
- Shows "(no restrictions)" for chunks that should filter

## Next Steps

1. ✅ Issue identified and root cause confirmed
2. ⏳ Re-embed DMG chunks to production with query_must metadata
3. ⏳ Verify filtering works in production
4. ⏳ Update deployment documentation
5. ⏳ Add version tracking to prevent future schema drift
