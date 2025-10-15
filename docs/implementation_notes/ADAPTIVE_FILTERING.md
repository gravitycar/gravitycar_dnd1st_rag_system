# Adaptive Result Filtering - Implementation Summary

## Overview
Implemented **automatic gap detection** to intelligently determine how many chunks to return based on semantic similarity discontinuities, rather than using a fixed `k` value.

## The Problem
When using a fixed `k=5`, you might get:
- **Too many results**: Irrelevant chunks included (e.g., MAMMOTH in a Hill Giant vs Troll query)
- **Too few results**: Missing relevant information for broad queries

## The Solution: Dual-Strategy Adaptive Filtering

### Strategy 1: Gap Detection (Primary)
**Goal**: Find the "semantic cliff" where relevance drops significantly

**Algorithm**:
1. Calculate gaps between consecutive results (starting from position 2)
   - Skip gap after best result (can be large simply because best result is exceptional)
2. Find the largest gap
3. If `gap >= 0.1`, cut at that position (semantic discontinuity detected)

**Example: Hill Giant vs Troll**
```
Position  Distance   Gap      Analysis
1         0.8813     -        Hill Giant (best)
2         0.9313     +0.0500  GIANT category (skipped for gap detection)
3         0.9356     +0.0043  TROLL (relevant, small gap)
4         1.0763     +0.1407  Frost Giant (LARGE GAP! ← cut here)
5         1.0834     +0.0071  MAMMOTH
```
**Result**: Keep 3 chunks (cuts before Frost Giant) ✅

### Strategy 2: Distance Threshold (Fallback)
**Goal**: Use relative distance when no clear semantic cliff exists

**Algorithm**:
1. Calculate `cutoff = best_distance + distance_threshold` (default: 0.4)
2. Keep all results with `distance <= cutoff`

**Example: Black Dragon vs Gold Dragon**
```
Position  Distance   Gap      Analysis
1         0.6927     -        Gold Dragon (best)
2         0.8071     +0.1144  Green Dragon (gap skipped)
3         0.8692     +0.0621  Bronze Dragon (largest eligible gap)
4         0.8936     +0.0244  Silver Dragon
5         0.9173     +0.0237  DRAGON category
```
Max gap (0.0621) < 0.1 → Use distance threshold
Cutoff: 0.6927 + 0.4 = 1.0927
All results ≤ 1.0927 → Keep all 5 ✅

### Constraints Applied
After strategy selection:
1. **Minimum**: At least 2 results (unless only 1 exists)
2. **Maximum**: Respect user's `k` parameter
3. **Boundary**: Can't exceed available results

## Usage

### Basic Query
```bash
python query_docling.py dnd_monster_manual "What monster is more powerful, a hill giant or a troll?"
```
Will automatically detect the gap and return 3 chunks (not 5).

### Adjust Distance Threshold
```bash
# More strict (only very close matches)
python query_docling.py dnd_monster_manual "query" --distance-threshold 0.2

# More permissive (include marginal matches)
python query_docling.py dnd_monster_manual "query" --distance-threshold 0.6
```

### Debug Mode (See the Algorithm in Action)
```bash
python query_docling.py dnd_monster_manual "hill giant vs troll" --debug
```

Output will show:
```
[DEBUG] Gap analysis:
  Position 4: gap=0.1407
  Position 3: gap=0.0043
[DEBUG] Largest gap: 0.1407 at position 4
[DEBUG] Strategy: gap detection (cliff at position 4, gap=0.1407)
[DEBUG] Keep count: 3 → 3 (after constraints)
[DEBUG] Dropping 2 results with distances: [1.0763, 1.0834]
```

## Parameters

### `k` (default: 5)
Maximum number of results to return. Gap detection may return fewer.

### `distance_threshold` (default: 0.4)
Used when no significant gap is detected. Higher = more permissive.

### `gap_threshold` (hardcoded: 0.1)
Minimum gap size to trigger cliff detection. Gaps smaller than this use distance threshold fallback.

## Benefits

1. **Adaptive**: Adjusts to query characteristics automatically
2. **Quality-focused**: Drops irrelevant results even if under `k`
3. **Still bounded**: Respects `k` as maximum, ensures minimum 2
4. **Transparent**: Debug mode shows exactly why decisions were made

## Edge Cases Handled

1. **Single result**: Returns just 1 (overrides min=2 constraint)
2. **No clear gap**: Falls back to distance threshold
3. **Exceptional best result**: Skips first gap to avoid premature cutting
4. **All results very close**: Keeps all (up to k)
5. **Multiple comparison entities**: Entity detection ensures both are included before gap analysis

## Comparison Detection Integration

The gap detection works **after** entity-aware retrieval:
1. Detect comparison queries ("X vs Y", "compare X and Y")
2. Expand search to find both entities
3. Reorder to put matched entities first
4. **Then** apply gap detection to final ordered list

This ensures both compared entities are always included, then irrelevant results are trimmed.
