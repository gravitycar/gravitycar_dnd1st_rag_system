#!/usr/bin/env python3
"""
Unit tests for query_must_filter module.

Tests all operators and edge cases for post-retrieval filtering.
"""

import pytest
from src.query.query_must_filter import (
    validate_contain_one_of,
    validate_contain_all_of,
    validate_contain,
    validate_contain_range,
    satisfies_query_must
)


class TestValidateContainOneOf:
    """Tests for contain_one_of operator (AND of ORs)."""
    
    def test_single_group_match(self):
        """Single group with matching term should pass."""
        query = "what is a cleric"
        query_must = {"contain_one_of": [["cleric", "clerics"]]}
        assert validate_contain_one_of(query, query_must) == True
    
    def test_single_group_no_match(self):
        """Single group with no matching terms should fail."""
        query = "what is a fighter"
        query_must = {"contain_one_of": [["cleric", "clerics"]]}
        assert validate_contain_one_of(query, query_must) == False
    
    def test_multiple_groups_all_match(self):
        """Multiple groups all matching should pass."""
        query = "7th level cleric attacking armor class 6"
        query_must = {
            "contain_one_of": [
                ["cleric", "clerics"],
                ["armor class 6", "ac 6"]
            ]
        }
        assert validate_contain_one_of(query, query_must) == True
    
    def test_multiple_groups_partial_match(self):
        """Multiple groups with only some matching should fail."""
        query = "7th level cleric attacking armor class 5"
        query_must = {
            "contain_one_of": [
                ["cleric", "clerics"],
                ["armor class 6", "ac 6"]  # This group fails
            ]
        }
        assert validate_contain_one_of(query, query_must) == False
    
    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        query = "What is a CLERIC"
        query_must = {"contain_one_of": [["cleric"]]}
        assert validate_contain_one_of(query, query_must) == True
    
    def test_substring_matching(self):
        """Should match substrings, not just whole words."""
        query = "attacking ac 6"
        query_must = {"contain_one_of": [["ac 6"]]}
        assert validate_contain_one_of(query, query_must) == True
    
    def test_no_operator_present(self):
        """Missing operator should pass through."""
        query = "anything"
        query_must = {}
        assert validate_contain_one_of(query, query_must) == True
    
    def test_empty_term_group(self):
        """Empty group should pass (no requirements)."""
        query = "cleric"
        query_must = {"contain_one_of": [[]]}
        # Empty OR is always false, so this should fail
        assert validate_contain_one_of(query, query_must) == False


class TestValidateContainAllOf:
    """Tests for contain_all_of operator (all terms required)."""
    
    def test_all_terms_present(self):
        """All required terms present should pass."""
        query = "psionic blast attack"
        query_must = {"contain_all_of": ["psionic", "attack"]}
        assert validate_contain_all_of(query, query_must) == True
    
    def test_missing_one_term(self):
        """Missing one term should fail."""
        query = "psionic defense"
        query_must = {"contain_all_of": ["psionic", "attack"]}
        assert validate_contain_all_of(query, query_must) == False
    
    def test_missing_all_terms(self):
        """Missing all terms should fail."""
        query = "magic missile"
        query_must = {"contain_all_of": ["psionic", "attack"]}
        assert validate_contain_all_of(query, query_must) == False
    
    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        query = "PSIONIC ATTACK"
        query_must = {"contain_all_of": ["psionic", "attack"]}
        assert validate_contain_all_of(query, query_must) == True
    
    def test_no_operator_present(self):
        """Missing operator should pass through."""
        query = "anything"
        query_must = {}
        assert validate_contain_all_of(query, query_must) == True
    
    def test_empty_list(self):
        """Empty list should pass (no requirements)."""
        query = "anything"
        query_must = {"contain_all_of": []}
        assert validate_contain_all_of(query, query_must) == True


class TestValidateContain:
    """Tests for contain operator (single term required)."""
    
    def test_term_present(self):
        """Term present should pass."""
        query = "psionic blast"
        query_must = {"contain": "psionic"}
        assert validate_contain(query, query_must) == True
    
    def test_term_absent(self):
        """Term absent should fail."""
        query = "magic missile"
        query_must = {"contain": "psionic"}
        assert validate_contain(query, query_must) == False
    
    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        query = "PSIONIC blast"
        query_must = {"contain": "psionic"}
        assert validate_contain(query, query_must) == True
    
    def test_substring_matching(self):
        """Should match as substring."""
        query = "a temperate forest"
        query_must = {"contain": "temperate"}
        assert validate_contain(query, query_must) == True
    
    def test_no_operator_present(self):
        """Missing operator should pass through."""
        query = "anything"
        query_must = {}
        assert validate_contain(query, query_must) == True


class TestValidateContainRange:
    """Tests for contain_range operator (numerical range match)."""
    
    def test_number_in_range(self):
        """Number within range should pass."""
        query = "intelligence 12 psionic"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == True
    
    def test_number_below_range(self):
        """Number below range should fail."""
        query = "intelligence 8 psionic"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == False
    
    def test_number_above_range(self):
        """Number above range should fail."""
        query = "intelligence 15 psionic"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == False
    
    def test_boundary_min(self):
        """Minimum boundary should pass (inclusive)."""
        query = "wisdom 10"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == True
    
    def test_boundary_max(self):
        """Maximum boundary should pass (inclusive)."""
        query = "wisdom 13"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == True
    
    def test_multiple_numbers_one_in_range(self):
        """Multiple numbers with one in range should pass."""
        query = "8th level character with intelligence 12"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == True
    
    def test_multiple_numbers_none_in_range(self):
        """Multiple numbers with none in range should fail."""
        query = "8th level character with intelligence 15"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == False
    
    def test_no_numbers(self):
        """Query with no numbers should fail."""
        query = "psionic blast attack"
        query_must = {"contain_range": {"min": 10, "max": 13}}
        assert validate_contain_range(query, query_must) == False
    
    def test_no_operator_present(self):
        """Missing operator should pass through."""
        query = "anything"
        query_must = {}
        assert validate_contain_range(query, query_must) == True


class TestSatisfiesQueryMust:
    """Tests for main orchestrator function."""
    
    def test_no_query_must(self):
        """No query_must should always pass."""
        query = "anything at all"
        assert satisfies_query_must(query, None) == True
        assert satisfies_query_must(query, {}) == True
    
    def test_single_operator(self):
        """Single operator should work."""
        query = "cleric armor class 6"
        query_must = {
            "contain_one_of": [
                ["cleric"],
                ["armor class 6", "ac 6"]  # Need to include both variants
            ]
        }
        assert satisfies_query_must(query, query_must) == True
    
    def test_multiple_operators_all_pass(self):
        """Multiple operators all passing should pass."""
        query = "psionic blast attack intelligence 12"
        query_must = {
            "contain_one_of": [["psionic"]],
            "contain_all_of": ["attack"],
            "contain_range": {"min": 10, "max": 13}
        }
        assert satisfies_query_must(query, query_must) == True
    
    def test_multiple_operators_one_fails(self):
        """Multiple operators with one failing should fail."""
        query = "psionic defense intelligence 12"  # Missing "attack"
        query_must = {
            "contain_one_of": [["psionic"]],
            "contain_all_of": ["attack"],  # This fails
            "contain_range": {"min": 10, "max": 13}
        }
        assert satisfies_query_must(query, query_must) == False
    
    def test_complex_attack_matrix_pass(self):
        """Complex attack matrix query should pass correct chunk."""
        query = "What does a 7th level cleric need to roll to hit armor class 6?"
        query_must = {
            "contain_one_of": [
                ["cleric", "clerics", "druid", "druids", "monk", "monks"],
                ["opponent armor class 6", "armor class 6", "a.c. 6", "ac 6"]
            ]
        }
        assert satisfies_query_must(query, query_must) == True
    
    def test_complex_attack_matrix_wrong_class(self):
        """Attack matrix query should fail wrong class."""
        query = "What does a 7th level cleric need to roll to hit armor class 6?"
        query_must = {
            "contain_one_of": [
                ["fighter", "fighters"],  # Wrong class
                ["opponent armor class 6", "armor class 6", "a.c. 6", "ac 6"]
            ]
        }
        assert satisfies_query_must(query, query_must) == False
    
    def test_complex_attack_matrix_wrong_ac(self):
        """Attack matrix query should fail wrong AC."""
        query = "What does a 7th level cleric need to roll to hit armor class 6?"
        query_must = {
            "contain_one_of": [
                ["cleric", "clerics", "druid", "druids", "monk", "monks"],
                ["opponent armor class 5", "armor class 5", "a.c. 5", "ac 5"]  # Wrong AC
            ]
        }
        assert satisfies_query_must(query, query_must) == False
    
    def test_special_characters(self):
        """Special characters in query should work."""
        query = "what does a cleric need to hit a.c. 6?"
        query_must = {
            "contain_one_of": [
                ["cleric"],
                ["a.c. 6"]
            ]
        }
        assert satisfies_query_must(query, query_must) == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
