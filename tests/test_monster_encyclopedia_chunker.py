#!/usr/bin/env python3
"""
Unit tests for MonsterEncyclopediaChunker.

Tests the query_must metadata generation for monster chunks.
"""

import pytest
from src.chunkers.monster_encyclopedia import MonsterEncyclopediaChunker


class TestBuildMonsterMetadata:
    """Tests for build_monster_metadata method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = MonsterEncyclopediaChunker("Test_Book.md")
    
    def test_monster_with_parenthetical_name(self):
        """Test that parenthetical text is removed from query_must."""
        metadata = self.chunker.build_monster_metadata(
            name="Gold Dragon (Draco Orientalus Sino Dux)",
            parent_category="DRAGON",
            parent_category_id="dragon_cat_001",
            start_line=100,
            end_line=150,
            char_count=1234,
            desc_char_count=800
        )
        
        # Verify query_must uses 'contain' operator with base name
        assert "query_must" in metadata
        assert "contain" in metadata["query_must"]
        assert metadata["query_must"]["contain"] == "gold dragon"
        
        # Verify other metadata fields
        assert metadata["type"] == "monster"
        assert metadata["parent_category"] == "DRAGON"
        assert metadata["start_line"] == 100
        assert metadata["end_line"] == 150
    
    def test_monster_without_parenthetical_name(self):
        """Test simple monster name without parentheses."""
        metadata = self.chunker.build_monster_metadata(
            name="Beholder",
            parent_category=None,
            parent_category_id=None,
            start_line=200,
            end_line=250,
            char_count=987,
            desc_char_count=600
        )
        
        # Verify query_must uses full name
        assert metadata["query_must"]["contain"] == "beholder"
        assert metadata["type"] == "monster"
        assert "parent_category" not in metadata
    
    def test_monster_name_case_normalization(self):
        """Test that monster names are normalized to lowercase."""
        metadata = self.chunker.build_monster_metadata(
            name="BLUE DRAGON (Draco Electricus)",
            parent_category="DRAGON",
            parent_category_id="dragon_cat_001",
            start_line=300,
            end_line=350,
            char_count=1500,
            desc_char_count=900
        )
        
        # Should be lowercase
        assert metadata["query_must"]["contain"] == "blue dragon"
    
    def test_monster_with_complex_parenthetical(self):
        """Test monster with multiple words in parentheses."""
        metadata = self.chunker.build_monster_metadata(
            name="Horned (Malebranche) (Greater devil)",
            parent_category="DEVIL",
            parent_category_id="devil_cat_002",
            start_line=400,
            end_line=450,
            char_count=1100,
            desc_char_count=700
        )
        
        # All parenthetical text should be removed
        assert metadata["query_must"]["contain"] == "horned"
    
    def test_prevents_false_dragon_matches(self):
        """
        Test that different dragon types don't match each other.
        
        This is the key bug fix - previously "Blue Dragon" would match
        "Gold Dragon" because both contained the word "dragon".
        """
        gold_metadata = self.chunker.build_monster_metadata(
            name="Gold Dragon (Draco Orientalus Sino Dux)",
            parent_category="DRAGON",
            parent_category_id="dragon_cat_001",
            start_line=100,
            end_line=150,
            char_count=1234,
            desc_char_count=800
        )
        
        blue_metadata = self.chunker.build_monster_metadata(
            name="Blue Dragon (Draco Electricus)",
            parent_category="DRAGON",
            parent_category_id="dragon_cat_001",
            start_line=200,
            end_line=250,
            char_count=1100,
            desc_char_count=700
        )
        
        # Verify they have different query_must filters
        assert gold_metadata["query_must"]["contain"] == "gold dragon"
        assert blue_metadata["query_must"]["contain"] == "blue dragon"
        
        # These should not match each other's filters
        from src.query.query_must_filter import satisfies_query_must
        
        gold_query = "What is a gold dragon?"
        blue_query = "What is a blue dragon?"
        
        # Gold dragon query should match gold dragon, not blue
        assert satisfies_query_must(gold_query, gold_metadata["query_must"]) == True
        assert satisfies_query_must(gold_query, blue_metadata["query_must"]) == False
        
        # Blue dragon query should match blue dragon, not gold
        assert satisfies_query_must(blue_query, blue_metadata["query_must"]) == True
        assert satisfies_query_must(blue_query, gold_metadata["query_must"]) == False
    
    def test_plural_queries_match(self):
        """Test that plural queries (e.g., 'gold dragons') match singular base names."""
        metadata = self.chunker.build_monster_metadata(
            name="Gold Dragon (Draco Orientalus Sino Dux)",
            parent_category="DRAGON",
            parent_category_id="dragon_cat_001",
            start_line=100,
            end_line=150,
            char_count=1234,
            desc_char_count=800
        )
        
        from src.query.query_must_filter import satisfies_query_must
        
        # Both singular and plural should match
        assert satisfies_query_must("Tell me about gold dragon", metadata["query_must"]) == True
        assert satisfies_query_must("Tell me about gold dragons", metadata["query_must"]) == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
