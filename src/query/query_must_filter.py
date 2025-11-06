#!/usr/bin/env python3
"""
Query-Must Filter for RAG Pipeline.

Implements post-retrieval filtering based on query_must metadata.
Enables surgical filtering of semantically similar but contextually irrelevant chunks.

NOTE: Reference chunks (type='reference', section='EXPLANATORY NOTES') bypass
query_must filtering in docling_query.py. This module only validates the operators;
the decision to skip filtering is made at the pipeline level.
"""

import re
from typing import Dict, Any, Optional


def validate_contain_one_of(query: str, query_must: Dict[str, Any]) -> bool:
    """
    Validate contain_one_of operator (AND of ORs).
    
    Logic: ALL inner arrays must have at least one matching term.
    Each inner array is an OR - at least one term must match.
    All arrays must pass for overall success (AND of ORs).
    
    Uses word boundaries to prevent partial matches (e.g., "bear" won't match "owlbear").
    
    Args:
        query: User's natural language query
        query_must: Chunk's requirement specification
        
    Returns:
        True if query satisfies contain_one_of OR operator not present
        
    Examples:
        >>> query = "7th level cleric attacking armor class 6"
        >>> query_must = {
        ...     "contain_one_of": [
        ...         ["cleric", "clerics"],
        ...         ["armor class 6", "ac 6"]
        ...     ]
        ... }
        >>> validate_contain_one_of(query, query_must)
        True
        
        >>> # Fails if any group has no matches
        >>> query_must["contain_one_of"] = [["fighter"], ["ac 6"]]
        >>> validate_contain_one_of(query, query_must)
        False
    """
    if "contain_one_of" not in query_must:
        return True  # No requirement, pass through
    
    query_lower = query.lower()
    for term_group in query_must["contain_one_of"]:
        # Each group is an OR - at least one term must match
        # Use word boundaries to prevent partial matches
        group_matched = False
        for term in term_group:
            term_lower = term.lower()
            # Escape special regex characters and add word boundaries
            pattern = r'\b' + re.escape(term_lower) + r'\b'
            if re.search(pattern, query_lower):
                group_matched = True
                break
        
        if not group_matched:
            return False  # This group failed, overall failure
    
    return True  # All groups passed


def validate_contain_all_of(query: str, query_must: Dict[str, Any]) -> bool:
    """
    Validate contain_all_of operator (all terms required).
    
    Logic: ALL terms in the array must appear in the query.
    This is stricter than contain_one_of - use sparingly.
    
    Uses word boundaries to prevent partial matches (e.g., "bear" won't match "owlbear").
    
    Args:
        query: User's natural language query
        query_must: Chunk's requirement specification
        
    Returns:
        True if query satisfies contain_all_of OR operator not present
        
    Examples:
        >>> query = "psionic blast attack"
        >>> query_must = {"contain_all_of": ["psionic", "attack"]}
        >>> validate_contain_all_of(query, query_must)
        True
        
        >>> query = "psionic defense"  # Missing "attack"
        >>> validate_contain_all_of(query, query_must)
        False
    """
    if "contain_all_of" not in query_must:
        return True  # No requirement, pass through
    
    query_lower = query.lower()
    for term in query_must["contain_all_of"]:
        term_lower = term.lower()
        # Escape special regex characters and add word boundaries
        pattern = r'\b' + re.escape(term_lower) + r'\b'
        if not re.search(pattern, query_lower):
            return False
    
    return True


def validate_contain(query: str, query_must: Dict[str, Any]) -> bool:
    """
    Validate contain operator (single term required).
    
    Logic: The specified term must appear in the query.
    This is the simplest operator - use for single-term requirements.
    
    Uses word boundaries at the start to prevent partial matches (e.g., "bear" won't 
    match "owlbear"), but allows plural forms at the end (e.g., "gold dragon" matches 
    "gold dragons").
    
    Args:
        query: User's natural language query
        query_must: Chunk's requirement specification
        
    Returns:
        True if query satisfies contain OR operator not present
        
    Examples:
        >>> query = "psionic blast attack"
        >>> query_must = {"contain": "psionic"}
        >>> validate_contain(query, query_must)
        True
        
        >>> query = "magic missile"
        >>> validate_contain(query, query_must)
        False
        
        >>> query = "tell me about gold dragons"
        >>> query_must = {"contain": "gold dragon"}
        >>> validate_contain(query, query_must)
        True
    """
    if "contain" not in query_must:
        return True  # No requirement, pass through
    
    query_lower = query.lower()
    term_lower = str(query_must["contain"]).lower()
    
    # Escape special regex characters and add word boundary at start
    # Allow optional 's' at end for plurals, with word boundary after
    escaped_term = re.escape(term_lower)
    pattern = r'\b' + escaped_term + r's?\b'
    
    return bool(re.search(pattern, query_lower))



def validate_contain_range(query: str, query_must: Dict[str, Any]) -> bool:
    """
    Validate contain_range operator (numerical range match).
    
    Logic: Extract all numbers from query, check if any fall within [min, max].
    Range is inclusive on both bounds.
    
    This is useful for stat-based tables (Intelligence 10-13, Wisdom 14-17, etc.)
    where the user's query might mention any stat value in that range.
    
    Args:
        query: User's natural language query
        query_must: Chunk's requirement specification
        
    Returns:
        True if query satisfies contain_range OR operator not present
        
    Examples:
        >>> query = "intelligence 12 psionic blast"
        >>> query_must = {"contain_range": {"min": 10, "max": 13}}
        >>> validate_contain_range(query, query_must)
        True
        
        >>> query = "intelligence 8 psionic blast"  # 8 not in [10, 13]
        >>> validate_contain_range(query, query_must)
        False
        
        >>> query = "wisdom 10"  # Boundary value (inclusive)
        >>> validate_contain_range(query, query_must)
        True
    """
    if "contain_range" not in query_must:
        return True  # No requirement, pass through
    
    range_spec = query_must["contain_range"]
    min_val = range_spec["min"]
    max_val = range_spec["max"]
    
    # Extract all numbers from query using regex
    numbers = [int(n) for n in re.findall(r'\b\d+\b', query)]
    
    # Check if any number falls in range [min, max] (inclusive)
    return any(min_val <= num <= max_val for num in numbers)


def satisfies_query_must(query: str, query_must: Optional[Dict[str, Any]], debug: bool = False) -> bool:
    """
    Check if query satisfies chunk's query_must requirements.
    
    The query_must structure declares what terms must appear in queries
    for this chunk to be relevant. This enables surgical filtering of
    semantically similar but contextually irrelevant chunks (e.g.,
    attack matrices for wrong armor class values).
    
    All operators are combined with AND logic:
    - contain_one_of must pass (if present)
    - contain_all_of must pass (if present)
    - contain must pass (if present)
    - contain_range must pass (if present)
    
    Chunks without query_must metadata always pass through (no filtering).
    
    Args:
        query: User's natural language query (any case)
        query_must: Chunk's requirement specification with optional operators:
            - contain_one_of: List of term groups (AND of ORs)
            - contain_all_of: List of terms (all required)
            - contain: Single term that must be present
            - contain_range: Dict with min/max for numerical range
        debug: If True, log which operator failed (for troubleshooting)
        
    Returns:
        True if query satisfies all requirements, False otherwise
        
    Examples:
        >>> query = "7th level cleric attacking armor class 6"
        >>> query_must = {
        ...     "contain_one_of": [
        ...         ["cleric", "clerics"],
        ...         ["armor class 6", "ac 6"]
        ...     ]
        ... }
        >>> satisfies_query_must(query, query_must)
        True
        
        >>> query_must["contain_one_of"] = [["fighter"], ["ac 6"]]
        >>> satisfies_query_must(query, query_must)
        False  # Query doesn't contain "fighter"
        
        >>> # No query_must = always pass
        >>> satisfies_query_must(query, None)
        True
    """
    # No restrictions = always pass through
    if query_must is None or not query_must:
        return True
    
    # Call each validation method - all must pass (AND logic)
    if not validate_contain_one_of(query, query_must):
        if debug:
            print(f"    ❌ Failed contain_one_of: {query_must.get('contain_one_of')}")
        return False
    
    if not validate_contain_all_of(query, query_must):
        if debug:
            print(f"    ❌ Failed contain_all_of: {query_must.get('contain_all_of')}")
        return False
    
    if not validate_contain(query, query_must):
        if debug:
            print(f"    ❌ Failed contain: {query_must.get('contain')}")
        return False
    
    if not validate_contain_range(query, query_must):
        if debug:
            print(f"    ❌ Failed contain_range: {query_must.get('contain_range')}")
        return False
    
    return True  # All validations passed


if __name__ == "__main__":
    # Self-test examples
    print("Testing query_must_filter.py...")
    print()
    
    # Test 1: Attack matrix - should pass
    query1 = "What does a 7th level cleric need to roll to hit armor class 6?"
    query_must1 = {
        "contain_one_of": [
            ["cleric", "clerics"],
            ["armor class 6", "ac 6", "a.c. 6"]
        ]
    }
    result1 = satisfies_query_must(query1, query_must1)
    print(f"Test 1 - Cleric AC 6 (should pass): {result1}")
    assert result1 == True, "Test 1 failed"
    
    # Test 2: Wrong class - should fail
    query2 = query1  # Same query
    query_must2 = {
        "contain_one_of": [
            ["fighter", "fighters"],  # Wrong class
            ["armor class 6", "ac 6", "a.c. 6"]
        ]
    }
    result2 = satisfies_query_must(query2, query_must2)
    print(f"Test 2 - Fighter AC 6 (should fail): {result2}")
    assert result2 == False, "Test 2 failed"
    
    # Test 3: Psionic range - should pass
    query3 = "What psionic strength does intelligence 12 give?"
    query_must3 = {
        "contain_one_of": [
            ["psionic", "psionics"],
            ["intelligence", "int"]
        ],
        "contain_range": {"min": 10, "max": 13}
    }
    result3 = satisfies_query_must(query3, query_must3)
    print(f"Test 3 - Psionic int 12 (should pass): {result3}")
    assert result3 == True, "Test 3 failed"
    
    # Test 4: Outside range - should fail
    query4 = "What psionic strength does intelligence 8 give?"
    query_must4 = query_must3  # Same requirements
    result4 = satisfies_query_must(query4, query_must4)
    print(f"Test 4 - Psionic int 8 (should fail): {result4}")
    assert result4 == False, "Test 4 failed"
    
    # Test 5: No query_must - should pass
    query5 = "What is the strength bonus for 18 strength?"
    query_must5 = None
    result5 = satisfies_query_must(query5, query_must5)
    print(f"Test 5 - No query_must (should pass): {result5}")
    assert result5 == True, "Test 5 failed"
    
    print()
    print("✅ All tests passed!")
