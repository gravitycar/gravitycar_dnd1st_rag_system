#!/usr/bin/env python3
"""
Unit tests for MonsterBookEmbedder class.

Tests Monster Manual format detection, statistics prepending,
metadata processing, and embedding pipeline.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.embedders.monster_book_embedder import MonsterBookEmbedder


@pytest.fixture
def sample_monster_chunk():
    """Sample monster chunk."""
    return {
        "name": "Beholder",
        "description": "A floating sphere with a large central eye and ten eyestalks.",
        "statistics": {
            "frequency": "Rare",
            "armor_class": "-1/2/7",
            "hit_dice": "45-75 hit points",
            "alignment": "Lawful Evil",
            "intelligence": "Exceptional",
            "size": "Large",
        },
        "metadata": {
            "type": "monster",
            "monster_id": "beholder",
            "parent_category": "B",
            "parent_category_id": "b",
            "char_count": 1500,
        },
    }


@pytest.fixture
def sample_category_chunk():
    """Sample category chunk."""
    return {
        "name": "DEMON",
        "description": "Demons are evil creatures from the Abyss.",
        "statistics": {},
        "metadata": {
            "type": "category",
            "category_id": "demon",
            "char_count": 500,
            "line_count": 10,
        },
    }


@pytest.fixture
def sample_default_type_chunk():
    """Sample chunk with 'default' type (should be transformed)."""
    return {
        "name": "Test Monster",
        "description": "Test description",
        "statistics": {"frequency": "Common"},
        "metadata": {"type": "default", "char_count": 100},
    }


class TestMonsterBookEmbedder:
    """Test suite for MonsterBookEmbedder."""

    def test_chunk_format_is_compatible_positive(self, sample_monster_chunk):
        """Test that Monster Manual format is recognized."""
        chunks = [sample_monster_chunk]
        assert MonsterBookEmbedder.chunk_format_is_compatible(chunks) is True

    def test_chunk_format_is_compatible_negative_rulebook(self):
        """Test that rulebook format is not recognized."""
        rulebook_chunk = {
            "uid": "test_uid",
            "title": "Spells",
            "content": "Magic content",
            "book": "Players_Handbook",
        }
        chunks = [rulebook_chunk]
        assert MonsterBookEmbedder.chunk_format_is_compatible(chunks) is False

    def test_chunk_format_is_compatible_empty(self):
        """Test that empty chunks list returns False."""
        assert MonsterBookEmbedder.chunk_format_is_compatible([]) is False

    def test_add_statistic_block_monster(self, sample_monster_chunk):
        """Test statistics prepending for monster."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                text = sample_monster_chunk["description"]
                result = embedder.add_statistic_block(sample_monster_chunk, text)

                # Should contain monster name
                assert "## Beholder" in result
                # Should contain statistics header
                assert "**Statistics:**" in result
                # Should contain individual stats
                assert "Frequency: Rare" in result
                assert "Armor Class: -1/2/7" in result
                # Should contain description header
                assert "**Description:**" in result
                # Should contain original text
                assert sample_monster_chunk["description"] in result

    def test_add_statistic_block_category(self, sample_category_chunk):
        """Test that categories don't get statistics prepended."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                text = sample_category_chunk["description"]
                result = embedder.add_statistic_block(sample_category_chunk, text)

                # Should return text unchanged (no statistics block)
                assert result == text

    def test_prepare_text_for_embedding_monster(self, sample_monster_chunk):
        """Test text preparation for monster."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.prepare_text_for_embedding(sample_monster_chunk)

                # Should have statistics prepended
                assert "## Beholder" in result
                assert "**Statistics:**" in result

    def test_prepare_text_for_embedding_category(self, sample_category_chunk):
        """Test text preparation for category."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.prepare_text_for_embedding(sample_category_chunk)

                # Should be description only (no statistics)
                assert result == sample_category_chunk["description"]

    def test_extract_chunk_id_monster(self, sample_monster_chunk):
        """Test ID extraction for monster."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.extract_chunk_id(sample_monster_chunk, 0)
                assert result == "beholder"

    def test_extract_chunk_id_category(self, sample_category_chunk):
        """Test ID extraction for category."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.extract_chunk_id(sample_category_chunk, 5)
                assert result == "demon"

    def test_extract_chunk_id_fallback(self):
        """Test ID extraction fallback when no ID present."""
        chunk = {"name": "Test", "description": "Test", "metadata": {}}
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.extract_chunk_id(chunk, 42)
                assert result == "chunk_42"

    def test_process_metadata_monster(self, sample_monster_chunk):
        """Test metadata processing for monster."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(sample_monster_chunk)

                # Check basic fields
                assert result["name"] == "Beholder"
                assert result["type"] == "monster"
                assert result["char_count"] == 1500
                assert result["book"] == "Monster_Manual_(1e)"

                # Check monster-specific fields
                assert result["monster_id"] == "beholder"
                assert result["parent_category"] == "B"
                assert result["parent_category_id"] == "b"

                # Check flattened statistics
                assert result["frequency"] == "Rare"
                assert result["armor_class"] == "-1/2/7"
                assert result["hit_dice"] == "45-75 hit points"
                assert result["alignment"] == "Lawful Evil"
                assert result["intelligence"] == "Exceptional"
                assert result["size"] == "Large"

    def test_process_metadata_category(self, sample_category_chunk):
        """Test metadata processing for category."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(sample_category_chunk)

                # Check basic fields
                assert result["name"] == "DEMON"
                assert result["type"] == "category"
                assert result["char_count"] == 500

                # Check category-specific fields
                assert result["category_id"] == "demon"
                assert result["line_count"] == 10

                # Monster-specific fields should not be present
                assert "monster_id" not in result
                assert "parent_category" not in result

    def test_process_metadata_default_transform(self, sample_default_type_chunk):
        """Test that 'default' type is transformed to 'monster'."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                result = embedder.process_metadata(sample_default_type_chunk)
                assert result["type"] == "monster"

    def test_get_test_queries(self):
        """Test that test queries are returned."""
        with patch("src.utils.chromadb_connector.ChromaDBConnector"):
            with patch("src.embedders.base_embedder.OpenAI"):
                embedder = MonsterBookEmbedder("test.json", collection_name="test")
                queries = embedder.get_test_queries()

                assert isinstance(queries, list)
                assert len(queries) == 3
                assert all(isinstance(q, str) for q in queries)

    @patch("src.embedders.base_embedder.ChromaDBConnector")
    @patch("src.embedders.base_embedder.OpenAI")
    def test_embed_chunks_pipeline(
        self, mock_openai, mock_chroma, sample_monster_chunk
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
        embedder = MonsterBookEmbedder("test.json", collection_name="test")
        embedder._cached_chunks = [sample_monster_chunk]

        # Run embedding (no chunks parameter - uses _cached_chunks)
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
