#!/usr/bin/env python3
"""
Unit tests for EmbedderOrchestrator class.

Tests the orchestration layer: format detection, chunk caching,
pipeline coordination, and test query execution.
"""

import json
import pytest
from unittest.mock import patch
from src.embedders.embedder_orchestrator import EmbedderOrchestrator
from src.embedders.base_embedder import Embedder


class MockMonsterEmbedder(Embedder):
    """Mock embedder for Monster Manual format."""

    @staticmethod
    def chunk_format_is_compatible(chunks):
        if not chunks:
            return False
        sample = chunks[0]
        return "name" in sample and "description" in sample

    def embed_chunks(self):
        pass

    def prepare_text_for_embedding(self, chunk):
        return ""

    def extract_chunk_id(self, chunk, index):
        return f"chunk_{index}"

    def process_metadata(self, chunk):
        return {}

    def get_test_queries(self):
        return ["test query 1"]


class MockRuleBookEmbedder(Embedder):
    """Mock embedder for rulebook format."""

    @staticmethod
    def chunk_format_is_compatible(chunks):
        if not chunks:
            return False
        sample = chunks[0]
        return "uid" in sample and "title" in sample

    def embed_chunks(self):
        pass

    def prepare_text_for_embedding(self, chunk):
        return ""

    def extract_chunk_id(self, chunk, index):
        return f"chunk_{index}"

    def process_metadata(self, chunk):
        return {}

    def get_test_queries(self):
        return ["test query 2"]


@pytest.fixture
def mock_monster_chunks():
    """Sample Monster Manual chunks."""
    return [
        {
            "name": "Demon",
            "description": "Evil creatures from the Abyss",
            "statistics": {"frequency": "Rare"},
            "metadata": {"type": "monster"},
        }
    ]


@pytest.fixture
def mock_rulebook_chunks():
    """Sample rulebook chunks."""
    return [
        {
            "uid": "test_uid_1",
            "title": "Spells",
            "content": "Magic spell descriptions",
            "book": "Players_Handbook",
            "metadata": {"type": "spell"},
        }
    ]


@pytest.fixture
def temp_chunk_file(tmp_path, mock_monster_chunks):
    """Create temporary chunk file."""
    chunk_file = tmp_path / "test_chunks.json"
    with open(chunk_file, "w") as f:
        json.dump(mock_monster_chunks, f)
    return str(chunk_file)


class TestEmbedderOrchestrator:
    """Test suite for EmbedderOrchestrator."""

    def test_init_default_discovery(self):
        """Test initialization with default class discovery."""
        orchestrator = EmbedderOrchestrator()
        assert orchestrator.embedder_classes is not None
        assert len(orchestrator.embedder_classes) > 0
        assert orchestrator._cached_chunks == {}

    def test_init_custom_classes(self):
        """Test initialization with custom embedder classes."""
        custom_classes = [MockMonsterEmbedder, MockRuleBookEmbedder]
        orchestrator = EmbedderOrchestrator(embedder_classes=custom_classes)
        assert orchestrator.embedder_classes == custom_classes

    @patch("src.utils.chromadb_connector.ChromaDBConnector")
    @patch("src.embedders.base_embedder.OpenAI")
    def test_detect_embedder_monster_format(
        self, mock_openai, mock_chroma, temp_chunk_file, mock_monster_chunks
    ):
        """Test detection of Monster Manual format."""
        orchestrator = EmbedderOrchestrator(
            embedder_classes=[MockMonsterEmbedder, MockRuleBookEmbedder]
        )

        embedder = orchestrator.detect_embedder(temp_chunk_file, collection_name="test")

        assert isinstance(embedder, MockMonsterEmbedder)
        assert embedder._cached_chunks == mock_monster_chunks

    @patch("src.utils.chromadb_connector.ChromaDBConnector")
    @patch("src.embedders.base_embedder.OpenAI")
    def test_detect_embedder_rulebook_format(
        self, mock_openai, mock_chroma, tmp_path, mock_rulebook_chunks
    ):
        """Test detection of rulebook format."""
        chunk_file = tmp_path / "test_rulebook.json"
        with open(chunk_file, "w") as f:
            json.dump(mock_rulebook_chunks, f)

        orchestrator = EmbedderOrchestrator(
            embedder_classes=[MockMonsterEmbedder, MockRuleBookEmbedder]
        )

        embedder = orchestrator.detect_embedder(str(chunk_file), collection_name="test")

        assert isinstance(embedder, MockRuleBookEmbedder)
        assert embedder._cached_chunks == mock_rulebook_chunks

    def test_detect_embedder_unknown_format(self, tmp_path):
        """Test that unknown format raises ValueError."""
        unknown_chunks = [{"unknown_field": "value"}]
        chunk_file = tmp_path / "unknown.json"
        with open(chunk_file, "w") as f:
            json.dump(unknown_chunks, f)

        orchestrator = EmbedderOrchestrator(
            embedder_classes=[MockMonsterEmbedder, MockRuleBookEmbedder]
        )

        with pytest.raises(ValueError, match="Unknown chunk format"):
            orchestrator.detect_embedder(str(chunk_file), collection_name="test")

    def test_detect_embedder_empty_file(self, tmp_path):
        """Test that empty chunk file raises ValueError."""
        chunk_file = tmp_path / "empty.json"
        with open(chunk_file, "w") as f:
            json.dump([], f)

        orchestrator = EmbedderOrchestrator(
            embedder_classes=[MockMonsterEmbedder, MockRuleBookEmbedder]
        )

        with pytest.raises(ValueError, match="empty"):
            orchestrator.detect_embedder(str(chunk_file), collection_name="test")

    @patch("src.utils.chromadb_connector.ChromaDBConnector")
    @patch("src.embedders.base_embedder.OpenAI")
    def test_chunk_caching(
        self, mock_openai, mock_chroma, temp_chunk_file, mock_monster_chunks
    ):
        """Test that chunks are cached and reused."""
        orchestrator = EmbedderOrchestrator(embedder_classes=[MockMonsterEmbedder])

        # First call should load chunks
        embedder1 = orchestrator.detect_embedder(
            temp_chunk_file, collection_name="test1"
        )
        assert temp_chunk_file in orchestrator._cached_chunks

        # Second call should reuse cached chunks
        embedder2 = orchestrator.detect_embedder(
            temp_chunk_file, collection_name="test2"
        )
        assert embedder1._cached_chunks is embedder2._cached_chunks

    @patch("src.utils.chromadb_connector.ChromaDBConnector")
    @patch("src.embedders.base_embedder.OpenAI")
    def test_process_pipeline(self, mock_openai, mock_chroma, temp_chunk_file):
        """Test full process pipeline execution."""
        orchestrator = EmbedderOrchestrator(embedder_classes=[MockMonsterEmbedder])

        # Mock the embed_chunks method to track if it was called
        with patch.object(MockMonsterEmbedder, "embed_chunks") as mock_embed:
            embedder = orchestrator.process(temp_chunk_file, collection_name="test")

            # Verify embed_chunks was called
            mock_embed.assert_called_once()

            # Verify we got the right embedder type
            assert isinstance(embedder, MockMonsterEmbedder)

    @patch("src.utils.chromadb_connector.ChromaDBConnector")
    @patch("src.embedders.base_embedder.OpenAI")
    def test_run_test_queries(self, mock_openai, mock_chroma, temp_chunk_file):
        """Test test query coordination."""
        orchestrator = EmbedderOrchestrator(embedder_classes=[MockMonsterEmbedder])

        embedder = orchestrator.detect_embedder(temp_chunk_file, collection_name="test")

        # Mock test_query method
        with patch.object(embedder, "test_query") as mock_test_query:
            orchestrator.run_test_queries(embedder)

            # Verify test_query was called with each test query
            assert mock_test_query.call_count == 1
            mock_test_query.assert_called_with("test query 1")

    def test_no_embedder_classes(self, tmp_path, mock_monster_chunks):
        """Test that empty list falls back to auto-discovery."""
        chunk_file = tmp_path / "test.json"
        with open(chunk_file, "w") as f:
            json.dump(mock_monster_chunks, f)

        # Empty list should trigger auto-discovery (fallback behavior)
        orchestrator = EmbedderOrchestrator(embedder_classes=[])

        # Should auto-discover and find MonsterBookEmbedder
        embedder = orchestrator.detect_embedder(str(chunk_file), collection_name="test")
        assert embedder is not None
        # Will be either MonsterBookEmbedder or MockMonsterEmbedder depending on discovery
        assert hasattr(embedder, "_cached_chunks")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
