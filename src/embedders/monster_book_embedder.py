#!/usr/bin/env python3
"""
MonsterBookEmbedder: Embedder for Monster Manual chunks (legacy format).

Handles statistics prepending and monster-specific metadata extraction.
"""

import time
import json
from typing import List, Dict, Any

from .base_embedder import Embedder


class MonsterBookEmbedder(Embedder):
    """
    Embedder for Monster Manual chunks (current format).

    Supports three chunk types:
    1. Monster chunks (with statistics)
    2. Category chunks (taxonomic groupings)
    3. Reference chunks (EXPLANATORY NOTES sections)

    Chunk Format:
    {
        "name": "DEMON" | "HIT DICE",
        "content": "..." | "description": "...",  # Backwards compatible
        "statistics": {  # Only for monsters
            "frequency": "...",
            "armor_class": "...",
            ...
        },
        "metadata": {
            "type": "monster" | "category" | "reference",
            "uid": "demogorgon_mon_057" | "hit_dice_ref_005",
            "section": "EXPLANATORY NOTES",  # Only for reference chunks
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
        - Has 'content' OR 'description' field
        - Has 'metadata' with 'type' field
        - Type is one of: 'monster', 'category', 'reference'

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
        has_text = "content" in sample or "description" in sample
        has_metadata = "metadata" in sample
        
        if not (has_name and has_text and has_metadata):
            return False
        
        # Check type field
        chunk_type = sample.get("metadata", {}).get("type")
        valid_type = chunk_type in ("monster", "category", "reference", "default")

        return valid_type

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
                # Backwards compatible: support both 'content' and 'description'
                text = chunk.get("content", chunk.get("description", ""))
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

        Only prepends statistics for actual monsters (not categories or references).
        Makes statistics searchable by embedding them.

        Args:
            chunk: Monster chunk dictionary
            text: Original description text

        Returns:
            Text with statistics prepended (for monsters) or original text (for others)
        """
        # Only prepend statistics for actual monsters (not categories or references)
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

        Calls add_statistic_block for monsters, returns text as-is for categories/references.
        Backwards compatible with both 'content' and 'description' fields.

        Args:
            chunk: Monster chunk dictionary

        Returns:
            Text ready for embedding
        """
        text = chunk.get("content", chunk.get("description", ""))
        return self.add_statistic_block(chunk, text)

    def extract_chunk_id(self, chunk: Dict[str, Any], index: int) -> str:
        """
        Extract unique ID from Monster Manual chunk.

        Priority order:
        1. uid from metadata (new format)
        2. monster_id or category_id (legacy format)
        3. Fallback: chunk_{index}

        Args:
            chunk: Monster chunk dictionary
            index: Chunk index (fallback for ID generation)

        Returns:
            Unique string identifier
        """
        # Try new format first (uid in metadata)
        if "uid" in chunk.get("metadata", {}):
            return chunk["metadata"]["uid"]
        
        # Fall back to legacy format
        return (
            chunk["metadata"].get("monster_id")
            or chunk["metadata"].get("category_id")
            or f"chunk_{index}"
        )

    def process_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and transform metadata for Monster Manual chunks.

        Handles monster, category, and reference types. Flattens statistics for filtering.
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
        
        # Add hierarchy (if present - normalized field across all chunk types)
        if "hierarchy" in chunk["metadata"]:
            metadata["hierarchy"] = chunk["metadata"]["hierarchy"]
        
        # Add uid (required for new format, optional for legacy)
        if "uid" in chunk["metadata"]:
            metadata["uid"] = chunk["metadata"]["uid"]

        # Add reference-specific metadata
        if chunk_type == "reference":
            if "section" in chunk["metadata"]:
                metadata["section"] = chunk["metadata"]["section"]

        # Add category-specific metadata
        elif chunk_type == "category":
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

        # Query filtering metadata (if present in chunk metadata)
        if "query_must" in chunk.get("metadata", {}):
            # Store as JSON string since ChromaDB doesn't support nested dicts
            metadata["query_must"] = json.dumps(chunk["metadata"]["query_must"])

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
