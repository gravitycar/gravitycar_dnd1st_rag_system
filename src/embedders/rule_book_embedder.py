#!/usr/bin/env python3
"""
RuleBookEmbedder - Strategy embedder for rulebook chunks (recursive_chunker format).

This embedder handles chunks produced by the recursive_chunker, which have:
- Top-level fields: uid, title, content, book
- metadata.hierarchy: List of headings (e.g., ["TREASURE", "SCROLLS"])
- metadata.chunk_type: One of (default, spell, encounter, magic_item, etc.)
- metadata.type: Semantic type (default, spell, magic_item, etc.)
- Split chunk fields: original_chunk_uid, chunk_part, sibling_chunks, total_parts

Key transformations:
1. Hierarchy flattening: ["TREASURE", "SCROLLS"] → "TREASURE → SCROLLS"
2. Type transformation: "default" → "rule" (for filtering queries)
3. Split chunk handling: Preserve split metadata for retrieval
"""

from typing import Dict, List, Any
from .base_embedder import Embedder
import time
import json
import hashlib


class RuleBookEmbedder(Embedder):
    """Embedder for rulebook chunks from recursive_chunker."""

    @staticmethod
    def chunk_format_is_compatible(chunks: List[Dict[str, Any]]) -> bool:
        """
        Detect if chunks are in rulebook format (recursive_chunker output).

        Rulebook format signature:
        - Has top-level 'uid' field
        - Has top-level 'title' field
        - Has top-level 'content' field
        - Has top-level 'book' field
        - Does NOT have 'name' or 'description' (monster format)

        Args:
            chunks: List of chunk dictionaries

        Returns:
            True if chunks match rulebook format, False otherwise
        """
        if not chunks:
            return False

        sample = chunks[0]

        # Must have these top-level fields
        required_fields = {"uid", "title", "content", "book"}
        has_required = required_fields.issubset(sample.keys())

        # Must NOT have monster format fields
        has_monster_fields = "name" in sample or "description" in sample

        return has_required and not has_monster_fields

    def embed_chunks(self) -> None:
        """
        Embed rulebook chunks into ChromaDB.

        Pipeline (batched for ChromaCloud quota compliance):
        1. Process chunks in batches of 32
        2. For each batch:
           - Prepare texts for embedding
           - Get embeddings from OpenAI
           - Process metadata
           - Write immediately to ChromaDB (≤32 records per write)

        This batched write approach ensures compliance with ChromaCloud's
        "Maximum number of records per write" limit (300 records/write).

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
        total_chunks = len(chunks)
        print(f"\n🔧 Processing {total_chunks} rulebook chunks...")

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i : i + batch_size]
            batch_end = min(i + batch_size, total_chunks)

            print(
                f"Processing batch {i // batch_size + 1}/"
                f"{(total_chunks + batch_size - 1) // batch_size} "
                f"(chunks {i+1}-{batch_end})..."
            )

            # Step 1: Prepare texts for this batch
            texts = [self.prepare_text_for_embedding(chunk) for chunk in batch]

            # Step 2: Get embeddings from OpenAI for this batch
            embeddings = self.get_embeddings_batch(texts)

            # Step 3: Process metadata for this batch
            metadatas = [self.process_metadata(chunk) for chunk in batch]

            # Step 4: Extract IDs for this batch
            ids = [self.extract_chunk_id(chunk, i + j) for j, chunk in enumerate(batch)]

            # Step 5: Write this batch to ChromaDB immediately
            self.collection.add(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=texts
            )

            time.sleep(0.1)  # Rate limiting

        print(f"✅ Successfully embedded {total_chunks} rulebook chunks!")

    def prepare_text_for_embedding(self, chunk: Dict[str, Any]) -> str:
        """
        Prepare rulebook chunk text for embedding.

        For rulebooks, we use the content as-is (no statistics prepending needed).
        The content already includes markdown structure and hierarchy context.

        Args:
            chunk: Chunk dictionary with 'content' field

        Returns:
            Text ready for embedding (content field)
        """
        return chunk.get("content", "")

    def extract_chunk_id(self, chunk: Dict[str, Any], index: int) -> str:
        """
        Extract or generate unique ID from chunk.

        ChromaCloud free tier has a 128-byte limit on ID size.
        For UIDs longer than 120 bytes, we use a shortened version:
        - Keep first 80 characters of UID for readability
        - Append 8-character hash of full UID for uniqueness

        Args:
            chunk: Chunk dictionary with 'uid' field
            index: Chunk position in array (fallback only)

        Returns:
            Unique string identifier for this chunk (≤128 bytes)
        """
        uid = chunk.get("uid")
        if not uid:
            # Fallback (should never happen with recursive_chunker)
            return f"chunk_{index}"
        
        # ChromaCloud free tier limit: 128 bytes for ID
        # Use 120 as safety threshold (some overhead for encoding)
        MAX_ID_LENGTH = 120
        
        if len(uid) <= MAX_ID_LENGTH:
            return uid
        
        # For long UIDs: truncate + hash for uniqueness
        # Format: first_80_chars + "_" + 8_char_hash
        hash_suffix = hashlib.md5(uid.encode()).hexdigest()[:8]
        truncated = uid[:80]
        return f"{truncated}_{hash_suffix}"

    def process_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform rulebook metadata for ChromaDB storage.

        Transformations:
        1. Flatten hierarchy: ["TREASURE", "SCROLLS"] → "TREASURE → SCROLLS"
        2. Type transformation: "default" → "rule" (for semantic clarity)
        3. Preserve split chunk metadata (original_chunk_uid, chunk_part, etc.)
        4. Extract all metadata fields to top level (ChromaDB requirement)

        Args:
            chunk: Original chunk dictionary

        Returns:
            Flattened metadata dictionary suitable for ChromaDB
        """
        metadata = chunk.get("metadata", {})
        processed = {}

        # Basic fields
        processed["title"] = chunk.get("title", "")
        processed["book"] = chunk.get("book", "")
        processed["char_count"] = metadata.get("char_count", 0)
        processed["chunk_level"] = metadata.get("chunk_level", 0)

        # Flatten hierarchy with unicode arrow separator
        hierarchy = metadata.get("hierarchy", [])
        if hierarchy:
            processed["hierarchy"] = " → ".join(hierarchy)
        else:
            processed["hierarchy"] = ""

        # Type transformation: "default" → "rule" for semantic clarity
        original_type = metadata.get("type", "default")
        if original_type == "default":
            processed["type"] = "rule"
        else:
            # Keep other types (spell, magic_item, encounter, etc.)
            processed["type"] = original_type

        # Preserve chunk_type as-is
        processed["chunk_type"] = metadata.get("chunk_type", "default")

        # Parent relationships
        processed["parent_heading"] = metadata.get("parent_heading") or ""
        processed["parent_chunk_uid"] = metadata.get("parent_chunk_uid") or ""

        # Special handler (if present)
        if "special_handler" in metadata:
            processed["special_handler"] = metadata["special_handler"]

        # Split chunk metadata (if present)
        # NOTE: We store original_chunk_uid, chunk_part, and total_parts, but NOT sibling_chunks
        # because sibling_chunks can exceed ChromaCloud's 4KB metadata value limit (20+ UIDs × 150 bytes each).
        # Sibling chunks can be reconstructed from original_chunk_uid + total_parts if needed.
        if "original_chunk_uid" in metadata:
            processed["original_chunk_uid"] = metadata["original_chunk_uid"]
            processed["chunk_part"] = metadata.get("chunk_part", 1)
            processed["total_parts"] = metadata.get("total_parts", 1)

        # Line numbers (if present)
        if "start_line" in metadata:
            processed["start_line"] = metadata["start_line"]
        if "end_line" in metadata:
            processed["end_line"] = metadata["end_line"]

        # Query filtering metadata (if present)
        if "query_must" in metadata:
            # Store as JSON string since ChromaDB doesn't support nested dicts
            processed["query_must"] = json.dumps(metadata["query_must"])

        return processed

    def get_test_queries(self) -> List[str]:
        """
        Get test queries specific to rulebook content.

        Returns queries that test:
        1. Experience points (Fighter XP table - acid test)
        2. Turn undead mechanics
        3. Saving throws

        Returns:
            List of 3 test query strings
        """
        return [
            "How many experience points does a fighter need to become 9th level?",
            "How does a 7th level cleric turn undead?",
            "What are the saving throw categories in AD&D 1st edition?",
        ]
