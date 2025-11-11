#!/usr/bin/env python3
"""
Unit tests for RuleBookEmbedder class.

Tests rulebook format detection, hierarchy flattening,
metadata processing, and embedding pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.embedders.rule_book_embedder import RuleBookEmbedder


@pytest.fixture
def sample_default_chunk():
    """Sample default rulebook chunk."""
    return {
        "uid": "DMG_TREASURE_1",
        "book": "Dungeon_Masters_Guide_(1e)",
        "title": "TREASURE",
        "content": "Treasure is the reward for adventuring.",
        "metadata": {
            "hierarchy": ["TREASURE"],
            "parent_heading": None,
            "parent_chunk_uid": None,
            "start_line": 100,
            "end_line": 120,
            "char_count": 500,
            "chunk_type": "default",
            "type": "default",
            "chunk_level": 2,
        },
    }


@pytest.fixture
def sample_spell_chunk():
    """Sample spell chunk."""
    return {
        "uid": "PHB_SPELLS_FIREBALL_1",
        "book": "Players_Handbook_(1e)",
        "title": "Fireball",
        "content": "A fireball spell creates a sphere of fire.",
        "metadata": {
            "hierarchy": ["SPELLS", "MAGIC-USER", "Fireball"],
            "parent_heading": "MAGIC-USER",
            "parent_chunk_uid": "PHB_SPELLS_MAGIC_USER",
            "start_line": 500,
            "end_line": 520,
            "char_count": 800,
            "chunk_type": "spell",
            "type": "spell",
            "chunk_level": 4,
        },
    }


@pytest.fixture
def sample_split_chunk():
    """Sample split chunk."""
    return {
        "uid": "DMG_PREFACE_1_part1",
        "book": "Dungeon_Masters_Guide_(1e)",
        "title": "PREFACE",
        "content": "This is part 1 of the preface.",
        "metadata": {
            "hierarchy": ["PREFACE"],
            "parent_heading": None,
            "parent_chunk_uid": None,
            "start_line": 1,
            "end_line": 50,
            "char_count": 2500,
            "chunk_type": "split",
            "type": "default",
            "chunk_level": 2,
            "original_chunk_uid": "DMG_PREFACE_1",
            "chunk_part": 1,
            "total_parts": 3,
            "sibling_chunks": ["DMG_PREFACE_1_part2", "DMG_PREFACE_1_part3"],
        },
    }


class TestRuleBookEmbedder:
    """Test suite for RuleBookEmbedder."""

    def test_chunk_format_is_compatible_positive(self, sample_default_chunk):
        """Test that rulebook format is recognized."""
        chunks = [sample_default_chunk]
        assert RuleBookEmbedder.chunk_format_is_compatible(chunks) is True

    def test_chunk_format_is_compatible_negative_monster(self):
        """Test that Monster Manual format is not recognized."""
        monster_chunk = {
            "name": "Beholder",
            "description": "A floating eye creature",
            "statistics": {"frequency": "Rare"},
        }
        chunks = [monster_chunk]
        assert RuleBookEmbedder.chunk_format_is_compatible(chunks) is False

    def test_chunk_format_is_compatible_empty(self):
        """Test that empty chunks list returns False."""
        assert RuleBookEmbedder.chunk_format_is_compatible([]) is False

    def test_prepare_text_for_embedding(self, sample_default_chunk):
        """Test text preparation returns content as-is."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.prepare_text_for_embedding(sample_default_chunk)
                assert result == sample_default_chunk["content"]

    def test_extract_chunk_id(self, sample_default_chunk):
        """Test ID extraction from uid field."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.extract_chunk_id(sample_default_chunk, 0)
                assert result == "DMG_TREASURE_1"

    def test_extract_chunk_id_fallback(self):
        """Test ID extraction fallback when no uid present."""
        chunk = {"title": "Test", "content": "Test", "book": "Test"}
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.extract_chunk_id(chunk, 42)
                assert result == "chunk_42"

    def test_process_metadata_default(self, sample_default_chunk):
        """Test metadata processing for default chunk."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(sample_default_chunk)

                # Check basic fields
                assert result["title"] == "TREASURE"
                assert result["book"] == "Dungeon_Masters_Guide_(1e)"
                assert result["char_count"] == 500
                assert result["chunk_level"] == 2

                # Check type transformation
                assert result["type"] == "rule"  # 'default' → 'rule'
                assert result["chunk_type"] == "default"

                # Check hierarchy flattening
                assert result["hierarchy"] == "TREASURE"

                # Check parent relationships
                assert result["parent_heading"] == ""
                assert result["parent_chunk_uid"] == ""

                # Check line numbers
                assert result["start_line"] == 100
                assert result["end_line"] == 120

    def test_process_metadata_spell(self, sample_spell_chunk):
        """Test metadata processing for spell chunk."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(sample_spell_chunk)

                # Type should NOT be transformed (already 'spell')
                assert result["type"] == "spell"
                assert result["chunk_type"] == "spell"

                # Check hierarchy flattening with arrow separator
                assert result["hierarchy"] == "SPELLS → MAGIC-USER → Fireball"

                # Check parent relationships
                assert result["parent_heading"] == "MAGIC-USER"
                assert result["parent_chunk_uid"] == "PHB_SPELLS_MAGIC_USER"

    def test_process_metadata_split(self, sample_split_chunk):
        """Test metadata processing for split chunk."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(sample_split_chunk)

                # Check split-specific fields
                assert result["original_chunk_uid"] == "DMG_PREFACE_1"
                assert result["chunk_part"] == 1
                assert result["total_parts"] == 3
                # Note: sibling_chunks is NOT stored in metadata to avoid exceeding
                # ChromaCloud's 4KB metadata value limit. Siblings can be reconstructed
                # from original_chunk_uid + total_parts if needed.

    def test_hierarchy_flattening(self):
        """Test hierarchy flattening with multiple levels."""
        chunk = {
            "uid": "test_uid",
            "title": "Test",
            "content": "Test content",
            "book": "Test",
            "metadata": {
                "hierarchy": ["Level1", "Level2", "Level3", "Level4"],
                "type": "default",
                "chunk_type": "default",
                "char_count": 100,
                "chunk_level": 5,
            },
        }
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(chunk)
                assert result["hierarchy"] == "Level1 → Level2 → Level3 → Level4"

    def test_hierarchy_empty(self):
        """Test hierarchy handling when empty."""
        chunk = {
            "uid": "test_uid",
            "title": "Test",
            "content": "Test content",
            "book": "Test",
            "metadata": {
                "hierarchy": [],
                "type": "default",
                "chunk_type": "default",
                "char_count": 100,
                "chunk_level": 1,
            },
        }
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(chunk)
                assert result["hierarchy"] == ""

    def test_get_test_queries(self):
        """Test that test queries are returned."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = RuleBookEmbedder("test.json", collection_name="test")
                queries = embedder.get_test_queries()

                assert isinstance(queries, list)
                assert len(queries) == 3
                assert all(isinstance(q, str) for q in queries)

    @patch("src.embedders.base_embedder.ChromaDBConnector")
    @patch("src.embedders.base_embedder.OpenAI")
    def test_embed_chunks_pipeline(
        self, mock_openai, mock_chroma, sample_default_chunk
    ):
        """Test full embed_chunks pipeline."""
        # Setup mocks
        mock_collection = MagicMock()
        mock_chroma_instance = MagicMock()
        mock_chroma_instance.get_or_create_collection.return_value = mock_collection
        mock_chroma.return_value = mock_chroma_instance

        mock_openai_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_openai_instance.embeddings.create.return_value = mock_response
        mock_openai.return_value = mock_openai_instance

        # Create embedder and inject chunks
        embedder = RuleBookEmbedder("test.json", collection_name="test")
        embedder._cached_chunks = [sample_default_chunk]

        # Run embedding
        embedder.embed_chunks()

        # Verify OpenAI API was called
        mock_openai_instance.embeddings.create.assert_called_once()

        # Verify ChromaDB add was called
        mock_collection.add.assert_called_once()

        # Verify the call had correct structure
        call_args = mock_collection.add.call_args
        assert "embeddings" in call_args.kwargs
        assert "documents" in call_args.kwargs
        assert "metadatas" in call_args.kwargs
        assert "ids" in call_args.kwargs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
