#!/usr/bin/env python3
"""
EmbedderOrchestrator: Coordinates embedding pipeline with format auto-detection.

This class separates orchestration concerns (format detection, chunk loading,
pipeline coordination) from embedding operations, adhering to Single Responsibility
Principle.
"""

import json
from pathlib import Path
from typing import List, Type, TYPE_CHECKING

# Avoid circular import at runtime
if TYPE_CHECKING:
    from .base_embedder import Embedder


class EmbedderOrchestrator:
    """
    Orchestrates the embedding pipeline: format detection, processing, and testing.

    Responsibilities:
    - Auto-detect chunk format via child class discovery
    - Load and cache chunks in memory
    - Coordinate embedding pipeline execution
    - Coordinate test query execution

    This class separates orchestration logic from embedding operations,
    adhering to Single Responsibility Principle.
    """

    def __init__(self, embedder_classes: List[Type["Embedder"]] = None):
        """
        Initialize orchestrator with optional list of embedder classes.

        Args:
            embedder_classes: List of Embedder subclasses to try. If None,
                             discovers all subclasses via Embedder.__subclasses__()
        """
        # Import here to avoid circular dependency
        from .base_embedder import Embedder

        self.embedder_classes = embedder_classes or Embedder.__subclasses__()
        self._cached_chunks = {}  # Cache chunks by filename

    def detect_embedder(self, chunks_file: str, **kwargs) -> "Embedder":
        """
        Auto-detect chunk format and return appropriate embedder instance.

        Detection Strategy:
        1. Load chunks once and cache in memory
        2. Try each embedder class's chunk_format_is_compatible() method
        3. Return instance of first matching embedder
        4. Raise exception if no embedder matches

        Args:
            chunks_file: Path to JSON file containing chunks
            **kwargs: Additional arguments passed to embedder constructor
                     (e.g., collection_name, chroma_host, chroma_port)

        Returns:
            Embedder instance with chunks pre-loaded and injected

        Raises:
            ValueError: If chunk file is empty or no embedder matches format
            RuntimeError: If no Embedder subclasses are found
            FileNotFoundError: If chunks_file doesn't exist
        """
        chunks_path = Path(chunks_file)

        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunk file not found: {chunks_file}")

        # Load chunks once (cache for reuse)
        if chunks_file not in self._cached_chunks:
            print(f"Loading chunks from {chunks_file}...")
            with open(chunks_path, "r", encoding="utf-8") as f:
                self._cached_chunks[chunks_file] = json.load(f)
            print(f"Loaded {len(self._cached_chunks[chunks_file])} chunks")

        chunks = self._cached_chunks[chunks_file]

        if not chunks:
            raise ValueError(f"Chunk file is empty: {chunks_file}")

        if not self.embedder_classes:
            raise RuntimeError("No Embedder subclasses found")

        # Try each embedder's chunk_format_is_compatible method
        for embedder_class in self.embedder_classes:
            if embedder_class.chunk_format_is_compatible(chunks):
                print(f"✓ Detected format: {embedder_class.__name__}")
                # Create instance and inject cached chunks
                instance = embedder_class(chunks_file, **kwargs)
                instance._cached_chunks = chunks
                return instance

        # No embedder matched
        first_chunk = chunks[0]
        chunk_keys = list(first_chunk.keys())
        raise ValueError(
            f"Unknown chunk format in {chunks_file}.\n"
            f"First chunk has keys: {chunk_keys}\n"
            f"No embedder's chunk_format_is_compatible() returned True."
        )

    def process(self, chunks_file: str, **kwargs) -> "Embedder":
        """
        Detect embedder and run full embedding pipeline.

        This is the main entry point for embedding chunks. It:
        1. Detects the appropriate embedder for the chunk format
        2. Runs the embedding pipeline (chunks already loaded and injected)
        3. Returns the embedder instance for further operations

        Args:
            chunks_file: Path to JSON file containing chunks
            **kwargs: Additional arguments passed to embedder constructor

        Returns:
            Embedder instance (for further operations like test queries)

        Example:
            >>> orchestrator = EmbedderOrchestrator()
            >>> embedder = orchestrator.process(
            ...     "data/chunks/chunks_DMG.json",
            ...     collection_name="dnd_dmg"
            ... )
        """
        embedder = self.detect_embedder(chunks_file, **kwargs)
        # Chunks already cached and injected by detect_embedder()
        embedder.embed_chunks()
        return embedder

    def run_test_queries(self, embedder: "Embedder"):
        """
        Run all test queries defined by embedder.

        Coordinates test query execution by:
        1. Getting test queries from the embedder
        2. Executing each query via embedder.test_query()
        3. Displaying results

        Args:
            embedder: Embedder instance with embedded chunks

        Example:
            >>> orchestrator = EmbedderOrchestrator()
            >>> embedder = orchestrator.process("data/chunks/chunks_DMG.json")
            >>> orchestrator.run_test_queries(embedder)
        """
        test_queries = embedder.get_test_queries()
        print(f"\n🧪 Running {len(test_queries)} test queries...")
        for query in test_queries:
            embedder.test_query(query)
