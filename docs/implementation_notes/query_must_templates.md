# Query-Must Metadata Templates

**Purpose**: Define standard `query_must` metadata structures for different table types to enable surgical filtering in the RAG system.

**Date**: October 30, 2025  
**Status**: Active  
**Related**: `docs/implementation_plans/query_must_filtering.md`, `docs/early_notes/Filtering.md`

---

## Overview

The `query_must` metadata declares what terms must appear in user queries for a chunk to be considered relevant. This enables post-retrieval filtering to eliminate semantically similar but contextually irrelevant chunks (e.g., AC 5 matrices when query asks about AC 6).

**Core Principle**: Only add `query_must` to "noisy" content that causes precision problems. Clean reference tables pass through unfiltered.

---

## Operator Reference

### contain_one_of (AND of ORs)
**Structure**: Array of arrays  
**Logic**: ALL inner arrays must have at least one matching term

```json
"contain_one_of": [
    ["cleric", "clerics"],      // At least one must match
    ["armor class 6", "ac 6"]   // AND at least one must match
]
```

**Use when**: Multiple requirements that can each be expressed in different ways

### contain_all_of (ALL required)
**Structure**: Array of strings  
**Logic**: ALL terms must appear in query

```json
"contain_all_of": ["psionic", "attack"]
```

**Use when**: Multiple distinct concepts must all be present (rare - usually `contain_one_of` is better)

### contain (Single term)
**Structure**: String  
**Logic**: This exact term must appear

```json
"contain": "temperate"
```

**Use when**: One specific term is required (simple filtering)

### contain_range (Numerical range)
**Structure**: Object with min/max  
**Logic**: At least one number in query must fall within [min, max]

```json
"contain_range": {"min": 10, "max": 13}
```

**Use when**: Table rows represent stat ranges (Intelligence 10-13, Wisdom 14-17, etc.)

---

## Template 1: Attack Matrices

**Problem**: Many AC variations (AC 3, 4, 5, 6, -3, -4, etc.) all semantically similar  
**Solution**: Require character class terms AND specific AC value

### Fighter/Paladin/Ranger Attack Matrix, AC 3

```json
{
    "query_must": {
        "contain_one_of": [
            ["fighter", "fighters", "paladin", "paladins", "ranger", "rangers"],
            ["opponent armor class 3", "armor class 3", "a.c. 3", "ac 3"]
        ]
    }
}
```

**Key points**:
- Include singular and plural forms
- Include all class types this matrix covers
- Include all AC abbreviation variations
- Include "opponent armor class" variant

### Cleric/Druid/Monk Attack Matrix, AC -2

```json
{
    "query_must": {
        "contain_one_of": [
            ["cleric", "clerics", "druid", "druids", "monk", "monks"],
            ["opponent armor class -2", "armor class -2", "a.c. -2", "ac -2"]
        ]
    }
}
```

**Note**: Negative AC values need special attention - include minus sign in all variants

### Magic-User/Illusionist Attack Matrix, AC 7

```json
{
    "query_must": {
        "contain_one_of": [
            ["magic-user", "magic users", "illusionist", "illusionists", "mage", "mages", "wizard", "wizards"],
            ["opponent armor class 7", "armor class 7", "a.c. 7", "ac 7"]
        ]
    }
}
```

**Note**: Include common synonyms (wizard, mage) even though not in official table title

---

## Template 2: Psionic Tables

**Problem**: Multiple stat ranges (10-13, 14-15, 16-17, 18) all semantically similar  
**Solution**: Require psionic terms + stat terms + numerical range

### Psionic Blast, Intelligence/Wisdom 10-13

```json
{
    "query_must": {
        "contain_one_of": [
            ["psionic", "psionic blast", "psychic", "psionics", "psi"],
            ["intelligence", "wisdom", "int", "wis"]
        ],
        "contain_range": {"min": 10, "max": 13}
    }
}
```

**Key points**:
- Include "psionic", "psionics" (singular/plural)
- Include full stat names + abbreviations
- Use contain_range for stat threshold (extracts numbers from query, checks if any in range)
- Range is inclusive: [10, 13] matches 10, 11, 12, or 13

### Psionic Defense, Intelligence/Wisdom 16-17

```json
{
    "query_must": {
        "contain_one_of": [
            ["psionic", "psionic defense", "psychic", "psionics", "psi", "defense"],
            ["intelligence", "wisdom", "int", "wis"]
        ],
        "contain_range": {"min": 16, "max": 17}
    }
}
```

**Note**: Include "defense" in first group to distinguish from attack/blast tables

### Psionic Strength Points, Wisdom 18+

```json
{
    "query_must": {
        "contain_one_of": [
            ["psionic", "psionic strength", "psychic", "psionics", "psi", "strength points"],
            ["wisdom", "wis"]
        ],
        "contain_range": {"min": 18, "max": 25}
    }
}
```

**Note**: For "18+" ranges, use max=25 (reasonable upper bound for ability scores in AD&D)

---

## Template 3: Encounter Tables

**Problem**: Multiple terrain types (desert, forest, swamp, etc.) and encounter types  
**Solution**: Require terrain terms + encounter-related terms

### Temperate Forest Encounters

```json
{
    "query_must": {
        "contain_one_of": [
            ["temperate", "forest", "woodland", "sylvan", "woods"],
            ["encounter", "random encounter", "wandering monster", "random monster"]
        ]
    }
}
```

**Key points**:
- Include climate + terrain descriptors
- Include synonyms (forest = woodland = sylvan)
- Include encounter-related terms
- No contain_range needed (not numerical)

### Desert Encounters

```json
{
    "query_must": {
        "contain_one_of": [
            ["desert", "arid", "sand", "dunes"],
            ["encounter", "random encounter", "wandering monster", "random monster"]
        ]
    }
}
```

### Tropical Swamp Encounters

```json
{
    "query_must": {
        "contain_one_of": [
            ["tropical", "swamp", "marsh", "bog", "wetland", "jungle"],
            ["encounter", "random encounter", "wandering monster", "random monster"]
        ]
    }
}
```

**Note**: Combine multiple terrain descriptors (tropical + swamp) in one array as OR

---

## Template 4: Clean Tables (NO query_must)

**These tables should NOT have query_must metadata** - they're unique reference data:

### Strength Table (Ability Bonuses)
```json
{
    "title": "STRENGTH TABLE II.: ABILITY ADJUSTMENTS - Strength 18/51-75",
    "description": "...",
    // NO query_must - unique reference data
}
```

**Why**: Only one strength table exists, no confusion possible

### Equipment Price List
```json
{
    "title": "EQUIPMENT: Weapons",
    "description": "...",
    // NO query_must - general reference
}
```

**Why**: Equipment tables are queried by item name, not by categories that cause confusion

### Spell Descriptions
```json
{
    "title": "Magic-User Spells: Fireball",
    "description": "...",
    // NO query_must - spell name is unique
}
```

**Why**: Each spell is distinct, semantic search works well

### Experience Point Tables (Single-Class)
```json
{
    "title": "FIGHTERS TABLE I.: EXPERIENCE POINTS AND LEVEL",
    "description": "...",
    // NO query_must - one table per class
}
```

**Why**: Only one XP table per class, class name in query is sufficient

---

## Decision Tree: When to Add query_must

```
Is the table part of a family of similar tables?
├─ NO → Don't add query_must (clean table)
└─ YES → Continue...
    │
    Do queries about this table risk returning similar but wrong tables?
    ├─ NO → Don't add query_must
    └─ YES → Continue...
        │
        What makes each table in the family distinct?
        ├─ Character class? → Use contain_one_of with class terms
        ├─ Armor class value? → Use contain_one_of with AC + abbreviations
        ├─ Terrain/environment? → Use contain_one_of with terrain terms
        ├─ Stat range? → Use contain_one_of with stat names + contain_range
        └─ Other category? → Design custom contain_one_of structure
```

---

## Common Pitfalls

### ❌ Pitfall 1: Over-filtering clean tables
```json
// DON'T do this for the strength table
{
    "query_must": {
        "contain": "strength"
    }
}
```
**Why wrong**: This would exclude queries like "What bonuses does 18/00 strength give?" if they don't use the word "strength". Unnecessary filtering.

### ❌ Pitfall 2: Using contain_all_of for ranges
```json
// DON'T do this for stat ranges
{
    "query_must": {
        "contain_all_of": ["10", "13"]  // WRONG!
    }
}
```
**Why wrong**: This requires BOTH "10" AND "13" in query. User asking "intelligence 12 psionic blast" would fail. Use `contain_range` instead.

### ❌ Pitfall 3: Missing abbreviations
```json
// DON'T forget abbreviations
{
    "query_must": {
        "contain_one_of": [
            ["fighter"],
            ["armor class 3"]  // Missing "ac 3", "a.c. 3"
        ]
    }
}
```
**Why wrong**: Users often use abbreviations. Missing them causes false negatives.

### ❌ Pitfall 4: Overly specific terms
```json
// DON'T be too specific
{
    "query_must": {
        "contain_one_of": [
            ["7th level cleric"]  // TOO SPECIFIC
        ]
    }
}
```
**Why wrong**: This fails for "8th level cleric". Use just ["cleric", "clerics"] instead.

---

## Validation Checklist

Before finalizing `query_must` metadata:

- [ ] All abbreviations included (AC, HP, STR, DEX, etc.)?
- [ ] Singular and plural forms included?
- [ ] Common synonyms included (mage = wizard = magic-user)?
- [ ] For ranges: Using `contain_range` not `contain_all_of`?
- [ ] For AC values: Including "opponent armor class", "armor class", "a.c.", "ac"?
- [ ] Table is actually "noisy" (part of family of similar tables)?
- [ ] Tested with 3+ example queries?

---

## Testing Examples

### Example 1: Attack Matrix Query
**Query**: "What does a 7th level cleric need to roll to hit AC 6?"

**Should match**:
```json
{
    "query_must": {
        "contain_one_of": [
            ["cleric", "clerics"],
            ["armor class 6", "ac 6", "a.c. 6"]
        ]
    }
}
```
✅ Contains "cleric" and "ac 6" → KEEP

**Should NOT match**:
```json
{
    "query_must": {
        "contain_one_of": [
            ["fighter", "fighters"],
            ["armor class 6", "ac 6", "a.c. 6"]
        ]
    }
}
```
❌ Missing "cleric" → EXCLUDE

### Example 2: Psionic Range Query
**Query**: "What psionic strength points does a character with wisdom 12 have?"

**Should match**:
```json
{
    "query_must": {
        "contain_one_of": [
            ["psionic", "psionic strength"],
            ["wisdom", "wis"]
        ],
        "contain_range": {"min": 10, "max": 13}
    }
}
```
✅ Contains "psionic", "wisdom", and 12 is in [10, 13] → KEEP

**Should NOT match**:
```json
{
    "query_must": {
        "contain_one_of": [
            ["psionic", "psionic strength"],
            ["wisdom", "wis"]
        ],
        "contain_range": {"min": 16, "max": 17}
    }
}
```
❌ 12 is not in [16, 17] → EXCLUDE

---

## Maintenance

**When to update templates**:
- New table types discovered that cause precision problems
- User feedback reveals missing synonyms/abbreviations
- False positives detected in production (terms too broad)
- False negatives detected in production (terms too narrow)

**Process**:
1. Identify problem queries in logs
2. Analyze which chunks are wrongly included/excluded
3. Update relevant `query_must` templates
4. Re-run table transformation on affected tables
5. Re-chunk and re-embed
6. Validate with test queries

---

*Last Updated*: October 30, 2025  
*Version*: 1.0  
*Author*: GitHub Copilot
