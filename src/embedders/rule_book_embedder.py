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

        Pipeline:
        1. Prepare text for embedding (use content as-is, no statistics prepending)
        2. Get embeddings from OpenAI (batched)
        3. Process metadata (flatten hierarchy, transform type)
        4. Add to ChromaDB collection

        Raises:
            ValueError: If _cached_chunks is None
            RuntimeError: If OpenAI API or ChromaDB operations fail
        """
        if self._cached_chunks is None:
            raise ValueError(
                "No chunks loaded. Use EmbedderOrchestrator to load chunks."
            )

        chunks = self._cached_chunks
        print(f"\n🔧 Processing {len(chunks)} rulebook chunks...")

        # Step 1: Prepare texts for embedding
        print("📝 Preparing texts for embedding...")
        texts = [self.prepare_text_for_embedding(chunk) for chunk in chunks]

        # Step 2: Get embeddings from OpenAI (batched)
        print("🤖 Getting embeddings from OpenAI...")
        batch_size = 32
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_embeddings = self.get_embeddings_batch(batch_texts)
            all_embeddings.extend(batch_embeddings)

            print(
                f"  Embedded batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}"
            )
            time.sleep(0.1)  # Rate limiting

        # Step 3: Process metadata
        print("🏷️  Processing metadata...")
        all_metadata = [self.process_metadata(chunk) for chunk in chunks]

        # Step 4: Add to ChromaDB
        print("💾 Adding to ChromaDB collection...")
        ids = [self.extract_chunk_id(chunk, i) for i, chunk in enumerate(chunks)]

        self.collection.add(
            embeddings=all_embeddings, documents=texts, metadatas=all_metadata, ids=ids
        )

        print(f"✅ Successfully embedded {len(chunks)} rulebook chunks!")

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
        Extract unique identifier for rulebook chunk.

        Uses top-level 'uid' field from recursive_chunker.

        Args:
            chunk: Chunk dictionary with 'uid' field
            index: Chunk position in array (fallback only)

        Returns:
            Unique string identifier for this chunk
        """
        uid = chunk.get("uid")
        if uid:
            return uid

        # Fallback (should never happen with recursive_chunker)
        return f"chunk_{index}"

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
        if "original_chunk_uid" in metadata:
            processed["original_chunk_uid"] = metadata["original_chunk_uid"]
            processed["chunk_part"] = metadata.get("chunk_part", 1)
            processed["total_parts"] = metadata.get("total_parts", 1)
            # Store sibling_chunks as comma-separated string (ChromaDB doesn't support arrays)
            siblings = metadata.get("sibling_chunks", [])
            if siblings:
                processed["sibling_chunks"] = ",".join(siblings)

        # Line numbers (if present)
        if "start_line" in metadata:
            processed["start_line"] = metadata["start_line"]
        if "end_line" in metadata:
            processed["end_line"] = metadata["end_line"]

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
