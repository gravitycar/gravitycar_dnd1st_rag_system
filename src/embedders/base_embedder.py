#!/usr/bin/env python3
"""
Base Embedder: Abstract base class for all embedder implementations.

Provides common embedding operations while enforcing format-specific
implementations via the Template Method pattern.
"""

from abc import ABC, abstractmethod
from openai import OpenAI
from pathlib import Path
from typing import List, Dict, Any

# Import our centralized configuration
from ..utils.config import (
    get_openai_api_key,
    get_default_collection_name,
)
from ..utils.chromadb_connector import ChromaDBConnector


class Embedder(ABC):
    """
    Base embedder class providing common embedding operations (no orchestration).

    Responsibilities:
    - ChromaDB connection and collection management (create/get)
    - OpenAI embedding generation (batched)
    - Collection truncation
    - Execute embedding pipeline
    - Execute individual test queries
    - Accept pre-loaded chunks via _cached_chunks attribute

    Note: Chunks are loaded and cached by EmbedderOrchestrator, then injected
    into embedder instances. This avoids double-loading and keeps orchestration
    concerns separate from embedding operations.
    """

    def __init__(
        self,
        chunks_file: str,
        collection_name: str = None,
        chroma_host: str = None,
        chroma_port: int = None,
    ):
        """
        Initialize embedder with ChromaDB and OpenAI connections.

        Args:
            chunks_file: Path to chunks JSON file (stored for reference)
            collection_name: ChromaDB collection name (optional)
            chroma_host: ChromaDB host (optional, uses config default)
            chroma_port: ChromaDB port (optional, uses config default)
        """
        self.chunks_file = Path(chunks_file)

        # Use default collection name if not provided
        if collection_name is None:
            collection_name = get_default_collection_name()
        self.collection_name = collection_name

        # Initialize OpenAI client for embeddings
        api_key = get_openai_api_key()
        self.openai_client = OpenAI(api_key=api_key)
        self.embedding_model_name = "text-embedding-3-small"
        print(f"Using OpenAI embedding model: {self.embedding_model_name}...")

        # Initialize ChromaDB connector
        self.chroma = ChromaDBConnector(chroma_host, chroma_port)
        print(f"Connecting to ChromaDB at {self.chroma.chroma_host}:{self.chroma.chroma_port}...")

        # Get or create collection
        self.collection = self.chroma.get_or_create_collection(collection_name)
        print(f"Using collection: {collection_name}")

        # Placeholder for cached chunks (injected by orchestrator)
        self._cached_chunks = None



    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a batch of texts from OpenAI API.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: If OpenAI API call fails
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name, input=texts, encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            raise

    def truncate_collection(self):
        """
        Delete all entries from collection (keeps collection structure).

        Use with caution - this permanently deletes all data in the collection.
        """
        print(f"\nTruncating collection: {self.collection_name}")
        count_deleted = self.chroma.truncate_collection(self.collection_name)
        print(f"Deleted {count_deleted} entries from collection: {self.collection_name}")
        
        # Refresh collection reference
        self.collection = self.chroma.get_collection(self.collection_name)
        print(f"Collection {self.collection_name} truncated successfully")

    def test_query(self, query: str, n_results: int = 5):
        """
        Execute a single test query.

        Args:
            query: Query string
            n_results: Number of results to return
        """
        print(f"\n{'='*80}")
        print(f"TEST QUERY: {query}")
        print(f"{'='*80}")

        query_embedding = self.get_embeddings_batch([query])[0]
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=n_results
        )

        for i, (doc, metadata, distance) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):
            print(f"\n--- Result {i+1} (distance: {distance:.4f}) ---")
            print(f"Name: {metadata.get('name', 'N/A')}")
            print(f"Type: {metadata.get('type', 'N/A')}")
            print(f"Content preview: {doc[:200]}...")

        print(f"\n{'='*80}\n")

    # Template methods (must be implemented by subclasses)

    @staticmethod
    @abstractmethod
    def chunk_format_is_compatible(chunk: Dict[str, Any]) -> bool:
        """
        Check if chunk format is compatible with this embedder.

        Used by EmbedderOrchestrator for auto-detection.

        Args:
            chunk: Single chunk dictionary

        Returns:
            True if this embedder can handle this chunk format
        """
        pass

    @abstractmethod
    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32):
        """
        Embed all chunks and store in ChromaDB.

        Main embedding pipeline. Subclasses implement format-specific logic.

        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of chunks to process per batch
        """
        pass

    @abstractmethod
    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str:
        """
        Prepare text from chunk for embedding.

        Format-specific text extraction and preparation.

        Args:
            chunk: Single chunk dictionary

        Returns:
            Text string ready for embedding
        """
        pass

    @abstractmethod
    def extract_chunk_id(self, chunk: Dict[str, Any], index: int) -> str:
        """
        Extract or generate unique ID for chunk.

        Args:
            chunk: Single chunk dictionary
            index: Chunk index (fallback for ID generation)

        Returns:
            Unique string identifier
        """
        pass

    @abstractmethod
    def process_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and transform metadata for ChromaDB storage.

        Format-specific metadata extraction and transformation.

        Args:
            chunk: Single chunk dictionary

        Returns:
            Metadata dictionary (ChromaDB-compatible)
        """
        pass

    @abstractmethod
    def get_test_queries(self) -> List[str]:
        """
        Get list of test queries for this embedder type.

        Returns:
            List of test query strings
        """
        pass

    # Backwards compatibility factory

    @staticmethod
    def create(chunks_file: str, **kwargs) -> "Embedder":
        """
        Factory method (backwards compatibility wrapper).

        Delegates to EmbedderOrchestrator for format detection.

        Args:
            chunks_file: Path to chunks JSON file
            **kwargs: Additional arguments for embedder constructor

        Returns:
            Embedder instance with format auto-detected

        Example:
            >>> embedder = Embedder.create("data/chunks/chunks_DMG.json")
            >>> embedder.embed_chunks(embedder._cached_chunks)
        """
        from .embedder_orchestrator import EmbedderOrchestrator

        orchestrator = EmbedderOrchestrator()
        return orchestrator.detect_embedder(chunks_file, **kwargs)
