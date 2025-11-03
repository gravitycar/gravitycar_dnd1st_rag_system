# Filtering

## Summary of the problem
Our query precision, the ratio of relevant chunks to non-relevent chunks, is poor. 
Our query results have good recall - we're getting relevant chunks. But we're getting many irrelevant chunks too.

## What a solution might look like
We need a way to identify that a specific chunk is the only chunk we need given the parameters of the query, and discard other similar but ultimately unrelated chunks. 

## What I need from you, the LLM:
- I need to know if filtering in ChromaDB is possible, and if it is, how does it work? 
- Are there other approaches we can use to filter out or otherwise disqualify chunks programmatically?

## Examples
**IMPORTANT** These examples are all related to the combat matrix tables, but any solution should be generic and applicable to other queries so we can expand the solution as we discover other problem areas where we need to filter.

### Example 1: The simple example of the problem
Here is question I asked our RAG pipeline: 
```markdown
What does a 7th level cleric need to roll to hit an opponent with armor class 6?"
```
**Note:** The correct answer is '10'.

Here is the answer provied by our RAG pipeline:
```markdown
To determine what a 7th level cleric needs to roll to hit an opponent with armor class 6, we will refer to the "I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 6".

1. **Identify the relevant row**: We are looking for the row corresponding to "Level 7-9" since the cleric is at 7th level.
2. **Identify the correct column header**: The armor class we are interested in is 6.
3. **Find the intersection value**: According to the matrix for armor class 6, the score needed to hit for a cleric of level 7-9 is **10**.

Thus, a 7th level cleric needs to roll a **10** on a 20-sided die to hit an opponent with armor class 6.
```

To see the problem, you need to look at the returned chunks:
```terminal
Retrieved chunks:
1. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 7 (type: special, distance: 0.6820)
2. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -7 (type: special, distance: 0.7088)
3. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 6 (type: special, distance: 0.7153)
4. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -6 (type: special, distance: 0.7419)
5. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 8 (type: special, distance: 0.7429)
6. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -8 (type: special, distance: 0.7549)
7. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 5 (type: special, distance: 0.7630)
8. Opponent Armor Class Description (If Armor is Worn): (type: special, distance: 0.7653)
9. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 9 (type: special, distance: 0.7765)
10. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 4 (type: special, distance: 0.7795)
11. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -9 (type: special, distance: 0.7814)
12. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -4 (type: special, distance: 0.7827)
13. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 2 (type: special, distance: 0.7851)
14. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -5 (type: special, distance: 0.7858)
15. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 1 (type: special, distance: 0.7922)
```

That's too many chunks!
- The attack matrix tables crowd out any other possible chunks
- Only 1 of the chunks, number 3, is actually relevant to the query

 Interestingly, the correct chunk is the 3rd chunk down.


### Example 2: comparing two characters that use the same attack matrix table.
Here is the question:
```markdown
Who is more likely to win in a fight - a 4th level fighter with an armor class of 3 or a 7th level fighter with an armor class of 9? Both fighters have a strength of 16, a constitution of 16, and a dexterity of 12. They both wield long swords.
```
**NOTE**: 
The correct answer is probably the 7th level fighter. There's a lot that would go into that answer:
- The 7th level fighter hits armor class 3 50% of the time (includes +1 strength bonus).
- The 4th level fighter hits armor class 9 60% of the time (includes +1 strength bonus).
- Both fighters use a D10 to roll their hit points, so an average roll will be 5.5.
- Both fighers get +1 hit point per level due to their constitution score.
- The 7th level fighter will likely have (5.5 * 7) + 7 = @45 hit points
- The 7th level fighter will likely have (5.5 * 4) + 4 = @26 hit points
- Both fighters do roughly 4.5 damage per hit
- The 7th level fighter will need roughly 6 hits, or 12 attacks, to kill the 4th level fighter.
- The 4th level fighter will need roughly 10 hits, or 17 attacks, to kill the 7th level fighter.

Given that the 4th level fighter likely dies after 12 attacks, but would need 17 attacks to kill the 7th level fighter, the 7th level fighter is likely to win this battle.

Now look at the chunks returned. I'll add a ✅ to the relevant chunks, and an ❌ to the irrelevant chunks.
1. The Fighter (type: rule, distance: 0.8003) ✅
2. Opponent Armor Class Description (If Armor is Worn): (type: special, distance: 0.8566) ✅
3. Armor Class: (type: rule, distance: 0.8705) ✅
4. Strength (type: rule, distance: 0.8782) ✅
5. Using The Combat Tables: (type: special, distance: 0.9100) ✅
6. I.B. ATTACK MATRIX FOR FIGHTERS, PALADINS, RANGERS, BARDS, AND 0 LEVEL HALFLINGS AND HUMANS* (type: special, distance: 0.9168) ✅
7. MEN (type: category, distance: 0.9250) ❌
8. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 4 (type: special, distance: 0.9392) ❌
9. I.B. ATTACK MATRIX FOR FIGHTERS, PALADINS, RANGERS, BARDS, AND 0 LEVEL HALFLINGS AND HUMANS* (type: special, distance: 0.9513) ❌
10. I.C. ATTACK MATRIX FOR MAGIC-USERS AND ILLUSIONISTS - Opponent Armor Class 4 (type: special, distance: 0.9639) ❌
11. FIGHTERS', PALADINS', &amp; RANGERS' ATTACKS PER MELEE ROUND TABLE (type: rule, distance: 0.9679) ✅
12. ARMOR (type: rule, distance: 0.9693) ✅
13. I.C. ATTACK MATRIX FOR MAGIC-USERS AND ILLUSIONISTS - Opponent Armor Class 4 (type: special, distance: 0.9703) ❌
14. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -4 (type: special, distance: 0.9774) ❌
15. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 7 (type: special, distance: 0.9789) ❌

The LLM gets the answer wrong for several reasons, but they aren't important here. What's important is that we're poluting the context with many irrelevant chunks.


### Example 3: comparing two characters that use different attack matrix tables
Here is the question:
```markdown
Who is more likely to win in a fight - a 4th level fighter with an armor class of 3 or a 7th level druid with an armor class of 9? Both characters have a strength of 16, a constitution of 16, and a dexterity of 12. They both wield long swords.
```
Similar logic would apply as with the previous example, but this example is more complex from a filtering standpoint because we now need TWO attack matrices: One for druids, and one for fighters.

Here are the returned chunks:
1. The Fighter (type: rule, distance: 0.8636) ✅
2. Armor Class: (type: rule, distance: 0.8637) ✅
3. MEN (type: category, distance: 0.8869) ✅
4. I.B. ATTACK MATRIX FOR FIGHTERS, PALADINS, RANGERS, BARDS, AND 0 LEVEL HALFLINGS AND HUMANS* (type: special, distance: 0.8908) ✅
5. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 4 (type: special, distance: 0.8983) ❌
6. Opponent Armor Class Description (If Armor is Worn): (type: special, distance: 0.9118) ✅
7. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor -4 (type: special, distance: 0.9252) ❌
8. CHARACTER CLASSES (DRUID) (type: rule, distance: 0.9310) ✅
9. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 7 (type: special, distance: 0.9334) ❌
10. CHARACTER CLASSES (DRUID) (type: rule, distance: 0.9343) ✅
11. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 6 (type: special, distance: 0.9398) ❌
12. PROTECTIVE ITEMS TABLE Character Class Paladin (type: rule, distance: 0.9404) ❌
13. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 8 (type: special, distance: 0.9420) ❌
14. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 3 (type: special, distance: 0.9423) ✅
15. Strength (type: rule, distance: 0.9432) ✅


## Possible paths to a solution

### Example 1 solution
For example 1, we would need to filter out every "ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS" chunk except one:
3. I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 6 (type: special, distance: 0.7153)

If we could say something like "this chunk isn't relevant unless the query contains one of <list of relevant character types> and mentions an armor class of <armor class value>" that could help a lot with the simple example

### Examples 2 and 3
For the complex examples, the same filtering would help and allow other chunks into the mix. But with the rule cited in the Example 1 solution, we might get:
chunk for fighter attacking armor class 9  ✅
chunk for fighter attacking armor class 3 ❌ 
chunk for druid attacking armor class 9 ❌
chunk for druid attacking armor class 3 ✅

That would still be an improvement. Not a real fix, but an improvement.


## Solution Architecture: Query-Must Filtering System

### Overview
We will implement a **chunk-centric** filtering system that improves precision without sacrificing recall:

1. **Layer 1: Metadata Generation** - Generate `query_must` metadata for noisy chunks
2. **Layer 2: Post-Retrieval Filtering** - Check if query satisfies chunk requirements
3. **Layer 3: Iterative Re-Querying** - Exclude mismatched chunks and retrieve clean replacements

### Key Design Principles

**Chunk-Centric, Not Query-Centric**: Each noisy chunk declares "Only include me if the query contains X, Y, and Z" rather than trying to parse queries and map terms to metadata fields.

**Opt-In Filtering**: Only the noisiest chunks get `query_must` metadata. Chunks without this metadata pass through untouched (defaults to inclusion).

**No Query Parsing Required**: We don't need complex NLP to extract "character_classes=cleric" from natural language. We just check if the query string contains required terms.

**Leverages OpenAI**: We're already using OpenAI to transform tables to JSON. We extend this to generate `query_must` metadata automatically.

### Why Not Use ChromaDB's Where Clause?

ChromaDB's `where` clause supports filtering on metadata, but it has critical limitations for our use case:

**Problem 1: Query Parsing Complexity**
- Requires mapping natural language → metadata fields ("cleric" → "character_classes")
- Requires maintaining hard-coded mappings and synonyms
- Brittle: breaks with slight query variations

**Problem 2: Collateral Damage**
- A where clause like `{"character_class": "cleric", "armor_class": "5"}` would exclude:
  - The strength table (needed for the query but doesn't match filter)
  - All other relevant context chunks
  - Result: High precision but catastrophic recall loss

**Problem 3: Incomplete Metadata**
- Attack matrix chunks don't contain "character_level" or "strength" metadata
- Those are parameters to READ the table, not SELECT it
- Where clause would either over-filter or ignore unmatched terms

**Our Solution**: Post-retrieval filtering lets us be surgical - only filter chunks that explicitly request it via `query_must` metadata.

### Identified Problem Content Categories

Based on analysis, these content categories have precision problems:

1. **Attack Matrices** (Lines 12381-12850 in DMG)
   - Problem: All attack matrices are semantically similar
   - Parameters: Character class, armor class
   - Example: "I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 6"

2. **Psionic Blast Attack Tables** (Lines 4827-4845 in DMG)
   - Problem: Intelligence/Wisdom ranges are semantically similar
   - Parameters: Intelligence+Wisdom total, attack range
   - Example: "IV.C. PSIONIC BLAST ATTACK UPON NON-PSIONIC CREATURE"

3. **Encounter Tables** (Lines 14643-14686 in DMG)
   - Problem: Creature types across different terrain types are similar
   - Parameters: Terrain type (Plain/Forest/Hills/Mountains), creature type
   - Example: "Temperate Conditions - Faerie And Sylvan Settings"

### Layer 1: Metadata Generation (OpenAI-Powered)

**Purpose**: Generate `query_must` metadata that declares what terms must appear in queries for this chunk to be relevant

**Implementation Approach:**
- Extend existing OpenAI table transformation to generate `query_must` metadata
- Only generate for noisy chunks (attack matrices, similar tables)
- Metadata lives in ChromaDB alongside chunk content

**Metadata Schema:**

#### query_must Structure
```python
{
    "query_must": {
        "contain_one_of": [
            ["cleric", "clerics"],                    # OR group: query must contain at least one
            ["druid", "druids"],                      # OR group: query must contain at least one
            ["monk", "monks"],                        # OR group: query must contain at least one
            ["armor class 6", "ac 6", "a.c. 6"]      # OR group: specific AC value with context
        ]
    }
}
```

**Semantics:**
- `contain_one_of`: List of OR groups. Query must satisfy ALL groups (AND of ORs)
  - Each inner list is an OR: query must contain at least one term from that list
  - Include specific AC values with surrounding context words (e.g., "armor class 6" not just "6")
- `contain_all_of`: (Optional) All terms must appear in query

#### Example: Attack Matrix Chunk
```python
# Chunk: "I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 6"
{
    "title": "I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS - Opponent Armor 6",
    "content": "...",
    "type": "special",
    "special_handler": "CombatTablesHandler",
    "query_must": {
        "contain_one_of": [
            ["cleric", "clerics"],
            ["druid", "druids"],
            ["monk", "monks"],
            ["armor class 6", "ac 6", "a.c. 6"]
        ]
    }
}
```

#### Example: Psionic Blast Table Chunk
```python
# Chunk: "IV.C. PSIONIC BLAST ATTACK - Intelligence/Wisdom 10-13"
{
    "title": "IV.C. PSIONIC BLAST ATTACK UPON NON-PSIONIC CREATURE - Intelligence/Wisdom 10-13",
    "content": "...",
    "query_must": {
        "contain_one_of": [
            ["psionic", "psionic blast", "psychic"],
            ["intelligence", "wisdom", "int", "wis"]
        ],
        "contain_all_of": ["10", "13"]  # Range endpoints
    }
}
```

#### Example: Clean Chunk (No Restrictions)
```python
# Chunk: "STRENGTH TABLE II.: ABILITY ADJUSTMENTS"
{
    "title": "STRENGTH TABLE II.: ABILITY ADJUSTMENTS",
    "content": "...",
    # No query_must metadata - always included in results
}
```

**Key Decisions:**
- **Opt-in only**: Chunks without `query_must` are never filtered
- **Case-insensitive matching**: "Cleric" matches "cleric" or "CLERIC"
- **Flexible term lists**: Easy to add synonyms without code changes
- **OpenAI generates it**: Reduces manual maintenance burden

### Layer 2: Post-Retrieval Filtering

**Purpose**: Check if query satisfies each retrieved chunk's `query_must` requirements

**Implementation: Simple String Matching**

No complex query parsing needed! Just check if query string contains required terms:

```python
def satisfies_query_must(query: str, query_must: dict) -> bool:
    """
    Check if query satisfies chunk's requirements.
    
    Args:
        query: User's natural language query
        query_must: Chunk's requirement specification
        
    Returns:
        True if query satisfies all requirements, False otherwise
    """
    query_lower = query.lower()
    
    # Check contain_one_of (AND of ORs)
    if "contain_one_of" in query_must:
        for term_group in query_must["contain_one_of"]:
            # Each group is an OR - at least one term must match
            if not any(term.lower() in query_lower for term in term_group):
                return False  # None of the terms in this group found
    
    # Check contain (exact string must be present)
    if "contain" in query_must:
        if str(query_must["contain"]).lower() not in query_lower:
            return False
    
    # Check contain_all_of (all terms must be present)
    if "contain_all_of" in query_must:
        if not all(term.lower() in query_lower for term in query_must["contain_all_of"]):
            return False
    
    return True
```

**Example Filtering Logic:**

Query: "What does a 7th level cleric with strength 17 need to roll to hit armor class 6?"

```python
# Chunk 1: Attack matrix for clerics, AC 6
query_must = {
    "contain_one_of": [
        ["cleric", "clerics"],
        ["druid", "druids"],
        ["monk", "monks"],
        ["armor class 6", "ac 6", "a.c. 6"]
    ]
}
satisfies_query_must(query, query_must)  # → True (contains "cleric" and "armor class 6")

# Chunk 2: Attack matrix for clerics, AC 5
query_must = {
    "contain_one_of": [
        ["cleric", "clerics"],
        ["druid", "druids"],
        ["monk", "monks"],
        ["armor class 5", "ac 5", "a.c. 5"]
    ]
}
satisfies_query_must(query, query_must)  # → False (contains "armor class 6" not "5")

# Chunk 3: Strength table (no query_must)
# No query_must metadata → automatically included

# Chunk 4: Attack matrix for fighters, AC 6
query_must = {
    "contain_one_of": [
        ["fighter", "fighters"],
        ["paladin", "paladins"],
        ["ranger", "rangers"],
        ["armor class 6", "ac 6", "a.c. 6"]
    ]
}
satisfies_query_must(query, query_must)  # → False (no fighter/paladin/ranger terms)
```

**Result**: Only chunks 1 and 3 pass filtering. Noise eliminated!

### Layer 3: Iterative Re-Querying

**Purpose**: Exclude filtered chunks and retrieve clean replacements using ChromaDB's `$nin` operator

**Algorithm: Iterative Refinement**

```python
def retrieve_with_iterative_filtering(
    query: str, 
    k: int = 15, 
    max_iterations: int = 3,
    debug: bool = False
) -> List[Dict]:
    """
    Iteratively retrieve and filter until we have clean results or hit limit.
    
    Args:
        query: User's natural language query
        k: Target number of results to return
        max_iterations: Safety limit on re-query cycles
        debug: Print filtering decisions
        
    Returns:
        List of chunk dictionaries (up to k chunks)
    """
    excluded_ids = set()
    all_kept_chunks = []
    iteration = 0
    embedding = get_embedding(query)
    
    while iteration < max_iterations:
        # Build where clause to exclude already-discarded chunks
        query_params = {
            "query_embeddings": [embedding],
            "n_results": k
        }
        
        if excluded_ids:
            query_params["where"] = {"id": {"$nin": list(excluded_ids)}}
            if debug:
                print(f"[Iteration {iteration+1}] Excluding {len(excluded_ids)} chunks")
        
        # Retrieve from ChromaDB
        results = collection.query(**query_params)
        
        if not results['ids'][0]:
            if debug:
                print(f"[Iteration {iteration+1}] No more results available")
            break
        
        # Filter based on query_must
        newly_kept = []
        newly_excluded = []
        
        for i, (chunk_id, metadata, document, distance) in enumerate(zip(
            results['ids'][0],
            results['metadatas'][0],
            results['documents'][0],
            results['distances'][0]
        )):
            if 'query_must' in metadata:
                # Check if query satisfies requirements
                if satisfies_query_must(query, metadata['query_must']):
                    newly_kept.append({
                        'id': chunk_id,
                        'metadata': metadata,
                        'document': document,
                        'distance': distance
                    })
                    if debug:
                        print(f"  ✅ KEEP: {metadata.get('title', chunk_id)}")
                else:
                    newly_excluded.append(chunk_id)
                    excluded_ids.add(chunk_id)
                    if debug:
                        print(f"  ❌ EXCLUDE: {metadata.get('title', chunk_id)}")
            else:
                # No restrictions - keep it
                newly_kept.append({
                    'id': chunk_id,
                    'metadata': metadata,
                    'document': document,
                    'distance': distance
                })
                if debug:
                    print(f"  ✅ KEEP: {metadata.get('title', chunk_id)} (no restrictions)")
        
        # Add kept chunks to results
        all_kept_chunks.extend(newly_kept)
        
        # Stopping conditions
        if len(all_kept_chunks) >= k:
            if debug:
                print(f"[Iteration {iteration+1}] Target k={k} reached")
            break
        
        if len(newly_excluded) == 0:
            if debug:
                print(f"[Iteration {iteration+1}] No exclusions, stopping")
            break
        
        iteration += 1
    
    # Return up to k chunks, sorted by distance
    final_chunks = sorted(all_kept_chunks, key=lambda x: x['distance'])[:k]
    
    if debug:
        print(f"\n[FINAL] Returning {len(final_chunks)} chunks after {iteration+1} iterations")
    
    return final_chunks
```

**Performance Characteristics:**

| Scenario | Iterations | ChromaDB Queries | Notes |
|----------|-----------|------------------|-------|
| **No noisy chunks** | 1 | 1 | Typical case - most queries |
| **Some noise** | 2 | 2 | ~5 chunks excluded, retrieve 5 more |
| **Heavy noise (attack matrices)** | 2-3 | 2-3 | First query dominated by matrices, filtered, replacements retrieved |
| **All noise** | 3 (max) | 3 | Safety limit prevents infinite loops |

**Overhead**: ~10-50ms per ChromaDB query × 2-3 queries = **20-150ms total overhead**

This is negligible for high precision gains.

### Expected Improvements

#### Example 1: "What does a 7th level cleric with strength 17 need to roll to hit AC 6?"

**Before**: 15 chunks returned
- 14 irrelevant attack matrices (AC 7, -7, -6, 8, -8, 5, 9, 4, -9, -4, 2, -5, 1)
- 1 relevant attack matrix (AC 6 cleric)
- 0 strength table (would be ranked 16+ due to attack matrix dominance)

**After**: 2-3 chunks returned
- Attack matrix for clerics/druids/monks, AC 6 (satisfies query_must)
- Strength table (no query_must, passes through)
- Possibly cleric class description (no query_must, passes through)

**Precision improvement**: ~87% noise reduction, **strength table now visible**

**How it works:**
- Iteration 1: Retrieve 15 chunks, 14 attack matrices excluded due to query_must, 1 kept
- Iteration 2: Retrieve 14 more chunks (excluding the 14 from iteration 1), get strength table + context
- Stop: Have enough clean chunks

#### Example 2: "Who wins: 4th level fighter (AC 3) vs 7th level fighter (AC 9)?"

**Before**: 15 chunks
- 8 irrelevant (wrong class matrices, unrelated tables)
- 7 relevant (fighter rules, AC description, etc.)

**After**: ~8 chunks
- Fighter attack matrices (query contains "fighter" and mentions both "3" and "9")
  - Note: May retrieve multiple AC chunks if both "3" and "9" in query
- Fighter class rules (no query_must)
- Strength/Constitution tables (no query_must)
- Combat context (no query_must)

**Precision improvement**: ~47% noise reduction

**Note**: This query mentions multiple armor classes. The `query_must` matches on specific AC values with context, so:
- AC 3 fighter matrix: INCLUDED (contains "fighter" and "ac 3")
- AC 9 fighter matrix: INCLUDED (contains "fighter" and "ac 9")
- AC 4 fighter matrix: EXCLUDED (query doesn't mention "ac 4")
- AC 3 cleric matrix: EXCLUDED (query doesn't mention "cleric")

#### Example 3: "Who wins: 4th level fighter (AC 3) vs 7th level druid (AC 9)?"

**Before**: 15 chunks
- 7 irrelevant (wrong class/AC combinations)
- 8 relevant (mixed fighter and druid info)

**After**: ~10 chunks
- Fighter attack matrix for AC 3 (contains "fighter" and "ac 3")
- Druid attack matrix for AC 9 (contains "druid" and "ac 9")
- Fighter class rules (no query_must)
- Druid class rules (no query_must)
- Strength table (no query_must)
- Context chunks (no query_must)

**Precision improvement**: ~40% noise reduction

**Key insight**: The filter is **surgical**, not **comprehensive**. It removes obvious noise (wrong class/AC combos) but preserves all relevant context, including chunks we didn't anticipate needing.

### Implementation Phases

**Phase 1: Layer 1 - OpenAI Metadata Generation** (Estimated: 6 hours)
1. Extend OpenAI table transformation prompt to generate `query_must` metadata
2. Define `query_must` templates for attack matrices (character class + armor class)
3. Define `query_must` templates for psionic tables (psionic + stat ranges)
4. Define `query_must` templates for encounter tables (terrain + creature type)
5. Test metadata generation accuracy with sample chunks
6. Validate generated metadata matches expected structure

**Phase 2: Layer 2 - Post-Retrieval Filtering** (Estimated: 4 hours)
1. Implement `satisfies_query_must()` function with simple string matching
2. Add unit tests for each `query_must` operator (`contain_one_of`, `contain_all_of`)
3. Test with example queries and various `query_must` structures
4. Add case-insensitive matching and whitespace normalization
5. Add debug logging for filter decisions (which chunks kept/excluded and why)

**Phase 3: Layer 3 - Iterative Re-Querying** (Estimated: 6 hours)
1. Modify `retrieve()` in `docling_query.py` to implement iterative algorithm
2. Add `excluded_ids` tracking and ChromaDB `$nin` filtering
3. Implement stopping conditions (k reached, no exclusions, max iterations)
4. Add iteration counter and performance metrics
5. Test with attack matrix queries to verify noise elimination
6. Tune `max_iterations` parameter (default: 3)

**Phase 4: Re-Embedding with query_must Metadata** (Estimated: 4 hours)
1. Re-run table transformation on DMG to generate `query_must` for attack matrices
2. Re-embed DMG chunks with new metadata into ChromaDB
3. Verify `query_must` metadata is correctly stored in ChromaDB
4. Spot-check a few attack matrix chunks to validate metadata quality
5. Document which content categories have `query_must` metadata

**Phase 5: Testing & Refinement** (Estimated: 4 hours)
1. Run all three example queries and measure precision improvements
2. Test edge cases (multi-AC queries, multi-class queries, no AC mentioned)
3. Measure iteration counts and performance overhead
4. Identify false positives (chunks incorrectly excluded)
5. Identify false negatives (chunks incorrectly included)
6. Refine `query_must` term lists based on findings
7. Document learnings and edge cases

**Total Estimated Time**: 24 hours

### Success Criteria

1. **Precision Improvement**: Attack matrix queries return ≤3-5 relevant chunks (down from 15 total, 1-2 relevant)
   - Example 1: 15 chunks → 2-3 chunks (87% reduction)
   - Example 2: 15 chunks → 8-10 chunks (40-47% reduction)
   - Example 3: 15 chunks → 10-12 chunks (20-33% reduction)

2. **No Recall Degradation**: General queries without noisy chunks are unaffected
   - Chunks without `query_must` metadata pass through untouched
   - Semantic ranking still determines relevance
   - Only opt-in chunks are filtered

3. **Extensibility**: Adding new noisy content categories requires only metadata generation
   - No code changes needed
   - Just extend OpenAI prompt with new `query_must` templates
   - Re-embed affected chunks

4. **Performance**: Minimal latency increase despite multiple ChromaDB queries
   - Target: <150ms overhead for iterative re-querying
   - Typical case: 2 iterations × 50ms = 100ms overhead
   - Worst case: 3 iterations × 50ms = 150ms overhead

5. **Correctness**: Filtering logic is deterministic and explainable
   - `satisfies_query_must()` uses simple string matching (no ML/NLP)
   - Debug mode shows which chunks excluded and why
   - Easy to diagnose false positives/negatives

6. **Testability**: Each layer independently testable
   - Unit tests for `satisfies_query_must()` with various term combinations
   - Integration tests for iterative re-querying algorithm
   - End-to-end tests with example queries measuring precision improvements

### Next Steps
1. Review and approve this architecture
2. Create detailed implementation plan for Phase 1
3. Implement Phase 1 (metadata extraction)
4. Validate metadata extraction before proceeding to Phase 2


