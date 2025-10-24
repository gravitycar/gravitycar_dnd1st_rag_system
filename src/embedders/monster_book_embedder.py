#!/usr/bin/env python3
"""
MonsterBookEmbedder: Embedder for Monster Manual chunks (legacy format).

Handles statistics prepending and monster-specific metadata extraction.
"""

import time
from typing import List, Dict, Any

from .base_embedder import Embedder


class MonsterBookEmbedder(Embedder):
    """
    Embedder for Monster Manual chunks (legacy format).

    Chunk Format:
    {
        "name": "DEMON",
        "description": "...",
        "statistics": {
            "frequency": "...",
            "armor_class": "...",
            ...
        },
        "metadata": {
            "type": "monster" | "category",
            "monster_id": "...",
            "category_id": "...",
            ...
        }
    }
    """

    @staticmethod
    def chunk_format_is_compatible(chunks: List[Dict[str, Any]]) -> bool:
        """
        Detect if chunks are in Monster Manual format.

        Monster Manual format signature:
        - Has 'name' field (not 'title')
        - Has 'description' field (not 'content')
        - Optional: Has 'statistics' field (strong indicator)

        Args:
            chunks: List of chunk dictionaries

        Returns:
            True if chunks match Monster Manual format, False otherwise
        """
        if not chunks:
            return False

        sample = chunks[0]

        # Must have these fields
        has_name = "name" in sample
        has_description = "description" in sample

        # Must NOT have rulebook fields
        has_rulebook_fields = "uid" in sample

        return has_name and has_description and not has_rulebook_fields

    def embed_chunks(self) -> None:
        """
        Embed Monster Manual chunks into ChromaDB.

        Pipeline:
        1. Add statistics blocks to monster text (via add_statistic_block)
        2. Get embeddings from OpenAI (batched)
        3. Process metadata for each chunk
        4. Add to ChromaDB

        Raises:
            ValueError: If _cached_chunks is None
            RuntimeError: If OpenAI API or ChromaDB operations fail
        """
        if self._cached_chunks is None:
            raise ValueError(
                "No chunks loaded. Use EmbedderOrchestrator to load chunks."
            )

        chunks = self._cached_chunks
        batch_size = 32
        print(f"\n🔧 Processing {len(chunks)} monster chunks...")

        total_chunks = len(chunks)

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i : i + batch_size]
            batch_end = min(i + batch_size, total_chunks)

            print(
                f"Processing batch {i // batch_size + 1}/"
                f"{(total_chunks + batch_size - 1) // batch_size} "
                f"(chunks {i+1}-{batch_end})..."
            )

            # Step 1: Add statistics blocks to text
            texts = []
            for chunk in batch:
                text = chunk.get("description", "")
                text = self.add_statistic_block(chunk, text)
                texts.append(text)

            # Step 2: Get embeddings from OpenAI
            embeddings = self.get_embeddings_batch(texts)

            # Step 3: Process metadata for each chunk
            ids = []
            metadatas = []
            for j, chunk in enumerate(batch):
                ids.append(self.extract_chunk_id(chunk, i + j))
                metadatas.append(self.process_metadata(chunk))

            # Step 4: Add to ChromaDB
            self.collection.add(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts
            )

            time.sleep(0.1)  # Rate limiting

        print(f"✅ Successfully embedded {total_chunks} monster chunks!")

    def add_statistic_block(self, chunk: Dict[str, Any], text: str) -> str:
        """
        Prepend statistics to monster descriptions.

        Only prepends statistics for actual monsters (not categories).
        Makes statistics searchable by embedding them.

        Args:
            chunk: Monster chunk dictionary
            text: Original description text

        Returns:
            Text with statistics prepended (for monsters) or original text (for categories)
        """
        # Only prepend statistics for actual monsters (not categories)
        if chunk["metadata"]["type"] == "monster" and "statistics" in chunk:
            stats = chunk["statistics"]
            stats_text = f"## {chunk.get('name', 'Unknown')}\n\n"
            stats_text += "**Statistics:**\n"
            for key, value in stats.items():
                if value and value != "Nil":
                    display_key = key.replace("_", " ").title()
                    stats_text += f"- {display_key}: {value}\n"
            stats_text += f"\n**Description:**\n{text}"
            return stats_text
        return text

    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str:
        """
        Prepare text from Monster Manual chunk for embedding.

        Calls add_statistic_block for monsters, returns description as-is for categories.

        Args:
            chunk: Monster chunk dictionary

        Returns:
            Text ready for embedding
        """
        text = chunk.get("description", "")
        return self.add_statistic_block(chunk, text)

    def extract_chunk_id(self, chunk: Dict[str, Any], index: int) -> str:
        """
        Extract unique ID from Monster Manual chunk.

        Uses monster_id or category_id from metadata.

        Args:
            chunk: Monster chunk dictionary
            index: Chunk index (fallback for ID generation)

        Returns:
            Unique string identifier
        """
        return (
            chunk["metadata"].get("monster_id")
            or chunk["metadata"].get("category_id")
            or f"chunk_{index}"
        )

    def process_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and transform metadata for Monster Manual chunks.

        Handles both monster and category types, flattens statistics for filtering.
        Transforms "default" type to "monster" if present.

        Args:
            chunk: Monster chunk dictionary

        Returns:
            ChromaDB-compatible metadata dictionary
        """
        # Transform "default" type to "monster" (if present)
        chunk_type = chunk["metadata"]["type"]
        if chunk_type == "default":
            chunk_type = "monster"

        # Start with common fields
        metadata = {
            "name": chunk.get("name", "Unknown"),
            "type": chunk_type,
            "char_count": chunk["metadata"]["char_count"],
            "book": "Monster_Manual_(1e)",
        }

        # Add category-specific metadata
        if chunk_type == "category":
            if "category_id" in chunk["metadata"]:
                metadata["category_id"] = chunk["metadata"]["category_id"]
            if "line_count" in chunk["metadata"]:
                metadata["line_count"] = chunk["metadata"]["line_count"]

        # Add monster-specific metadata
        elif chunk_type == "monster":
            if "monster_id" in chunk["metadata"]:
                metadata["monster_id"] = chunk["metadata"]["monster_id"]
            if "parent_category" in chunk["metadata"]:
                metadata["parent_category"] = chunk["metadata"]["parent_category"]
            if "parent_category_id" in chunk["metadata"]:
                metadata["parent_category_id"] = chunk["metadata"]["parent_category_id"]

            # Flatten statistics (for filtering)
            if "statistics" in chunk:
                stats = chunk["statistics"]
                metadata["frequency"] = stats.get("frequency", "")
                metadata["armor_class"] = stats.get("armor_class", "")
                metadata["hit_dice"] = stats.get("hit_dice", "")
                metadata["alignment"] = stats.get("alignment", "")
                metadata["intelligence"] = stats.get("intelligence", "")
                metadata["size"] = stats.get("size", "")

        return metadata

    def get_test_queries(self) -> List[str]:
        """
        Return Monster Manual-specific test queries.

        Returns:
            List of test query strings
        """
        return [
            "Tell me about demons and their abilities",
            "What is a beholder?",
            "Show me undead creatures",
        ]
