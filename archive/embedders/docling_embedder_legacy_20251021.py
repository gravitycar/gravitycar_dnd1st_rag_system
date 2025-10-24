#!/usr/bin/env python3
"""
Embed chunks from Player's Handbook or Monster Manual into ChromaDB.

Uses OpenAI text-embedding-3-small for embeddings (1536 dimensions).
Prepends statistics to Monster Manual entries for better searchability.

NOTE: This module now uses the orchestrator architecture for automatic
format detection. Import and use EmbedderOrchestrator for new code.
DoclingEmbedder is maintained as an alias for backwards compatibility.
"""

import json
import chromadb
from openai import OpenAI
from pathlib import Path
from typing import List, Dict, Any
import time

# Import our centralized configuration
from ..utils.config import (
    get_chroma_connection_params,
    get_openai_api_key,
    get_default_collection_name,
)

# Import orchestrator and all embedder implementations
from .embedder_orchestrator import EmbedderOrchestrator
from .base_embedder import Embedder  # noqa: F401
from .monster_book_embedder import MonsterBookEmbedder  # noqa: F401
from .rule_book_embedder import RuleBookEmbedder  # noqa: F401

# NOTE: Embedder, MonsterBookEmbedder, and RuleBookEmbedder imports are
# required even though they appear unused. They enable __subclasses__()
# discovery in the orchestrator for automatic format detection.


class DoclingEmbedder:
    def __init__(
        self,
        chunks_file: str,
        collection_name: str = None,
        chroma_host: str = None,
        chroma_port: int = None,
    ):
        self.chunks_file = Path(chunks_file)

        # Use default collection name if not provided
        if collection_name is None:
            collection_name = get_default_collection_name()
        self.collection_name = collection_name

        # Get ChromaDB configuration from centralized config utility
        if chroma_host is None or chroma_port is None:
            chroma_host, chroma_port = get_chroma_connection_params()

        # Initialize OpenAI client for embeddings
        api_key = get_openai_api_key()
        self.openai_client = OpenAI(api_key=api_key)
        self.embedding_model_name = "text-embedding-3-small"
        print(f"Using OpenAI embedding model: {self.embedding_model_name}...")

        print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}...")
        self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

        # Try to get existing collection, create if it doesn't exist
        try:
            self.collection = self.client.get_collection(name=collection_name)
            print(f"Using existing collection: {collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": f"D&D 1st Edition - {collection_name}"},
            )
            print(f"Created new collection: {collection_name}")

    def load_chunks(self) -> List[Dict[str, Any]]:
        """Load chunks from JSON file."""
        print(f"\nLoading chunks from {self.chunks_file}...")
        with open(self.chunks_file, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks")
        return chunks

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for a batch of texts from OpenAI API."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name, input=texts, encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"Error getting embeddings: {e}")
            raise

    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32):
        """Embed chunks and store in ChromaDB."""
        print(f"\nEmbedding and storing chunks (batch size: {batch_size})...")

        total_chunks = len(chunks)

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i : i + batch_size]
            batch_end = min(i + batch_size, total_chunks)

            print(
                f"Processing batch {i // batch_size + 1}/"
                f"{(total_chunks + batch_size - 1) // batch_size} "
                f"(chunks {i+1}-{batch_end})..."
            )

            # Extract texts for embedding (use 'description' field for Monster Manual)
            # For monsters, prepend statistics to make them searchable
            texts = []
            for chunk in batch:
                text = chunk.get("description", chunk.get("content", ""))

                # Add statistics block for monsters
                if chunk["metadata"]["type"] == "monster" and "statistics" in chunk:
                    stats = chunk["statistics"]
                    monster_name = chunk.get("name", "Unknown")
                    stats_text = f"## {monster_name}\n\n"
                    stats_text += "**Statistics:**\n"
                    for key, value in stats.items():
                        if value and value != "Nil":
                            # Format the key nicely
                            display_key = key.replace("_", " ").title()
                            stats_text += f"- {display_key}: {value}\n"
                    stats_text += f"\n**Description:**\n{text}"
                    text = stats_text

                texts.append(text)

            # Generate embeddings
            embeddings = self.get_embeddings_batch(texts)

            # Prepare data for ChromaDB
            ids = []
            metadatas = []
            documents = []

            for j, chunk in enumerate(batch):
                # Use the chunk's ID if available, otherwise generate one
                chunk_id = (
                    chunk["metadata"].get("monster_id")
                    or chunk["metadata"].get("category_id")
                    or f"chunk_{i + j}"
                )
                ids.append(chunk_id)

                # Prepare metadata - start with common fields
                metadata = {
                    "name": chunk.get("name", chunk.get("title", "Unknown")),
                    "type": chunk["metadata"]["type"],
                    "char_count": chunk["metadata"]["char_count"],
                    "book": chunk["metadata"].get("book", "Unknown"),
                }

                # Add category-specific metadata
                if chunk["metadata"]["type"] == "category":
                    if "category_id" in chunk["metadata"]:
                        metadata["category_id"] = chunk["metadata"]["category_id"]
                    if "line_count" in chunk["metadata"]:
                        metadata["line_count"] = chunk["metadata"]["line_count"]

                # Add monster-specific metadata
                elif chunk["metadata"]["type"] == "monster":
                    if "monster_id" in chunk["metadata"]:
                        metadata["monster_id"] = chunk["metadata"]["monster_id"]
                    if "parent_category" in chunk["metadata"]:
                        metadata["parent_category"] = chunk["metadata"][
                            "parent_category"
                        ]
                        metadata["parent_category_id"] = chunk["metadata"].get(
                            "parent_category_id", ""
                        )

                    # Add statistics as flattened metadata (for filtering/querying)
                    if "statistics" in chunk:
                        stats = chunk["statistics"]
                        metadata["frequency"] = stats.get("frequency", "")
                        metadata["armor_class"] = stats.get("armor_class", "")
                        metadata["hit_dice"] = stats.get("hit_dice", "")
                        metadata["alignment"] = stats.get("alignment", "")
                        metadata["intelligence"] = stats.get("intelligence", "")
                        metadata["size"] = stats.get("size", "")

                # Add spell-specific metadata (for Player's Handbook chunks)
                if "spell_school" in chunk["metadata"]:
                    metadata["spell_school"] = chunk["metadata"]["spell_school"]

                metadatas.append(metadata)

                # Store the same formatted text that we embedded (with stats for monsters)
                documents.append(texts[j])

            # Add to ChromaDB
            self.collection.add(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
            )

            time.sleep(0.1)  # Small delay to avoid overwhelming ChromaDB

        print(f"\n✅ Successfully embedded and stored {total_chunks} chunks!")

    def test_query(self, query: str, n_results: int = 5):
        """Test the collection with a sample query."""
        print(f"\n{'='*80}")
        print(f"TEST QUERY: {query}")
        print(f"{'='*80}")

        # Embed the query
        query_embedding = self.get_embeddings_batch([query])[0]

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=n_results
        )

        # Display results
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

            # Show type-specific metadata
            if metadata.get("parent_category"):
                print(f"Category: {metadata['parent_category']}")
            if metadata.get("frequency"):
                print(f"Frequency: {metadata['frequency']}")
            if metadata.get("hit_dice"):
                print(f"Hit Dice: {metadata['hit_dice']}")
            if metadata.get("armor_class"):
                print(f"Armor Class: {metadata['armor_class']}")
            if metadata.get("alignment"):
                print(f"Alignment: {metadata['alignment']}")
            if metadata.get("spell_school"):
                print(f"Spell School: {metadata['spell_school']}")

            print(f"Content preview: {doc[:200]}...")

        print(f"\n{'='*80}\n")

    def truncate_collection(self):
        """Delete all entries in the collection without deleting the collection itself."""
        print(f"\nTruncating collection: {self.collection_name}")

        # Get all IDs from the collection
        all_results = self.collection.get()

        if not all_results["ids"]:
            print("Collection is already empty.")
            return

        count = len(all_results["ids"])
        print(f"Found {count} entries to delete...")

        # Delete all entries
        self.collection.delete(ids=all_results["ids"])

        # Verify deletion
        remaining = self.collection.count()
        print(f"✅ Truncated collection. Remaining entries: {remaining}")

    def process(self):
        """Main processing pipeline."""
        chunks = self.load_chunks()
        self.embed_chunks(chunks)


def main():
    """
    Main entry point using orchestrator architecture.

    Automatically detects chunk format and uses the appropriate embedder.
    Supports both Monster Manual and rulebook (recursive_chunker) formats.
    """
    import sys
    import argparse

    # Get defaults from config
    try:
        default_host, default_port = get_chroma_connection_params()
        default_collection = get_default_collection_name()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        print("Please ensure .env file exists with required settings.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Embed D&D 1st Edition chunks into ChromaDB (auto-detects format)"
    )
    parser.add_argument(
        "chunks_file",
        help="Path to chunks JSON file (e.g., chunks_players_handbook.json)",
    )
    parser.add_argument(
        "collection_name",
        nargs="?",
        default=default_collection,
        help=f"ChromaDB collection name (default from .env: {default_collection})",
    )
    parser.add_argument(
        "--test-queries",
        action="store_true",
        help="Run format-specific test queries after embedding",
    )
    parser.add_argument(
        "--host",
        default=default_host,
        help=f"ChromaDB host (default from .env: {default_host})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=default_port,
        help=f"ChromaDB port (default from .env: {default_port})",
    )

    args = parser.parse_args()

    # Validate chunks file exists
    if not Path(args.chunks_file).exists():
        print(f"Error: File not found: {args.chunks_file}")
        sys.exit(1)

    # Create orchestrator (auto-discovers all embedder classes)
    orchestrator = EmbedderOrchestrator()

    # Process chunks (auto-detects format and embeds)
    print(f"\n{'='*60}")
    print(f"Processing: {args.chunks_file}")
    print(f"Collection: {args.collection_name}")
    print(f"{'='*60}\n")

    try:
        embedder = orchestrator.process(
            chunks_file=args.chunks_file,
            collection_name=args.collection_name,
            chroma_host=args.host,
            chroma_port=args.port,
        )

        print(f"\n✅ Successfully embedded chunks using {embedder.__class__.__name__}")

        # Run test queries if requested
        if args.test_queries:
            print(f"\n{'='*60}")
            print("Running test queries...")
            print(f"{'='*60}\n")
            orchestrator.run_test_queries(embedder)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
