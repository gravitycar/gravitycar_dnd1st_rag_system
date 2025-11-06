#!/usr/bin/env python3
"""
Query the D&D RAG system using ChromaDB + OpenAI.

Retrieves relevant chunks from ChromaDB and generates answers using OpenAI's GPT models.
Supports both Player's Handbook and Monster Manual collections.
"""

from openai import OpenAI
from pathlib import Path
import os
import argparse
import sys

# Import our centralized configuration
from ..utils.config import get_openai_api_key, get_default_collection_name
from ..utils.chromadb_connector import ChromaDBConnector
from ..utils.rag_output import RAGOutput


class DnDRAG:
    def __init__(
        self,
        collection_name: str = None,
        model: str = "gpt-4o-mini",
        chroma_host: str = None,
        chroma_port: int = None,
        output: RAGOutput = None
    ):
        # Initialize output buffer (create new instance if not provided)
        self.output = output if output else RAGOutput()
        
        # Use default collection name if not provided
        if collection_name is None:
            collection_name = get_default_collection_name()
        self.collection_name = collection_name
        self.model = model
        
        api_key = get_openai_api_key()
        
        self.output.info(f"Initializing D&D RAG system...")
        self.output.info(f"  Collection: {collection_name}")
        self.output.info(f"  Model: {model}")
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=api_key)
        
        # Set OpenAI embedding model (must match the model used for embedding)
        self.embedding_model_name = "text-embedding-3-small"
        self.output.info(f"  Using OpenAI embedding model: {self.embedding_model_name}")
        
        # Connect to ChromaDB using connector
        self.output.info(f"  Connecting to ChromaDB...")
        self.chroma = ChromaDBConnector(chroma_host, chroma_port)
        self.output.info(f"  ChromaDB: {self.chroma.chroma_host}:{self.chroma.chroma_port}")
        
        try:
            self.collection = self.chroma.get_collection(collection_name)
            self.output.info(f"  ✅ Connected to collection: {collection_name}")
        except Exception as e:
            self.output.error(f"  ❌ Error: Collection '{collection_name}' not found")
            self.output.error(f"     Available collections: {[c.name for c in self.chroma.list_collections()]}")
            raise
    
    def get_embedding(self, text: str):
        """Get embedding from OpenAI API."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model_name,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            self.output.error(f"Error getting embedding: {e}")
            raise
    
    def _format_chunk_info(self, metadata: dict, current_num: int = None, total_num: int = None) -> str:
        """Format chunk information for diagnostic messages.
        
        Args:
            metadata: Chunk metadata dict
            current_num: Current chunk number (1-indexed)
            total_num: Total number of chunks
            
        Returns:
            Formatted string with: "NAME [book: BOOK] [hierarchy] [chunk X of Y]"
        """
        # Get chunk name/title
        name = metadata.get('title', metadata.get('name', 'Unknown'))
        
        # Get book name
        book = metadata.get('book', 'Unknown')
        
        # Get heading hierarchy (may be stored as 'hierarchy' or 'heading_hierarchy')
        hierarchy = metadata.get('hierarchy', metadata.get('heading_hierarchy', ''))
        if hierarchy:
            hierarchy_str = f" [{hierarchy}]"
        else:
            hierarchy_str = ""
        
        # Format chunk numbering
        chunk_num_str = ""
        if current_num is not None and total_num is not None:
            chunk_num_str = f" [chunk {current_num}/{total_num}]"
        
        return f"{name} [book: {book}]{hierarchy_str}{chunk_num_str}"
    
    def retrieve(self, query: str, k: int = 15, distance_threshold: float = 0.4, debug: bool = False, enable_filtering: bool = True, max_iterations: int = 3):
        """Retrieve top-k relevant chunks from ChromaDB with entity-aware enhancement and optional query_must filtering.
        
        Args:
            query: The search query
            k: Target number of results (used as max, actual may be less if distance threshold exceeded)
            distance_threshold: Maximum distance increase from best result (default 0.4)
                               Results beyond (best_distance + threshold) are dropped
            debug: If True, print detailed gap detection and filtering info
            enable_filtering: If True, apply query_must filtering with iterative re-querying (default: True)
            max_iterations: Maximum iterations for re-querying when filtering is enabled (default: 3)
        """
        if enable_filtering:
            # Use iterative filtering wrapper
            return self._retrieve_with_filtering(query, k, distance_threshold, debug, max_iterations)
        else:
            # Use original retrieval logic
            return self._retrieve_base(query, k, distance_threshold, debug)
    
    def _retrieve_base(self, query: str, k: int = 15, distance_threshold: float = 0.4, debug: bool = False):
        """Base retrieval logic without filtering (original implementation).
        
        Args:
            query: The search query
            k: Target number of results
            distance_threshold: Maximum distance increase from best result
            debug: If True, print detailed gap detection info
        """
        # Embed the query
        query_embedding = self.get_embedding(query)
        
        # Smart enhancement: Detect if query mentions multiple specific entities
        # Common comparison patterns: "compare X and Y", "X vs Y", "X versus Y", "differences between X and Y"
        import re
        comparison_patterns = [
            r'compare\s+(?:the\s+)?(.+?)\s+and\s+(?:the\s+)?(.+?)(?:\.|$|\?)',
            r'(.+?)\s+vs\.?\s+(.+?)(?:\.|$|\?)',
            r'(.+?)\s+versus\s+(.+?)(?:\.|$|\?)',
            r'differences?\s+between\s+(?:the\s+)?(.+?)\s+and\s+(?:the\s+)?(.+?)(?:\.|$|\?)',
            r'(?:the\s+)?(.+?)\s+and\s+(?:the\s+)?(.+?)\s+differ',
        ]
        
        entities_mentioned = []
        for pattern in comparison_patterns:
            match = re.search(pattern, query.lower(), re.IGNORECASE)
            if match:
                # Extract entity names and clean them
                entity1 = match.group(1).strip()
                entity2 = match.group(2).strip()
                # Remove trailing words like "summarize", "what are", etc.
                for stop_word in ['summarize', 'what are', 'how do', 'explain']:
                    entity2 = re.sub(rf'\s+{stop_word}.*$', '', entity2, flags=re.IGNORECASE)
                entities_mentioned = [entity1, entity2]
                break
        
        # If we detected multiple entities, increase search results temporarily
        expanded_k = k
        if entities_mentioned:
            expanded_k = min(k * 3, 15)  # Search up to 3x more, but cap at 15
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=expanded_k
        )
        
        # If entities were detected, ensure they're all in the results
        if entities_mentioned:
            retrieved_names = [meta.get('name', '').lower() for meta in results['metadatas'][0]]
            missing_entities = []
            matched_indices = []  # Track indices of matched entities
            
            for entity in entities_mentioned:
                # Check if this entity is in the retrieved results
                # Prefer exact matches (with parentheses stripped) over partial matches
                found = False
                best_match = None
                best_match_index = -1
                best_match_quality = 0  # 0=no match, 1=partial, 2=exact
                
                for idx, name in enumerate(retrieved_names):
                    # Extract name without parenthetical suffix
                    base_name = name.split('(')[0].strip().lower()
                    entity_lower = entity.lower().strip()
                    
                    # Check for exact match (best)
                    if base_name == entity_lower:
                        if best_match_quality < 2:
                            found = True
                            best_match = name
                            best_match_index = idx
                            best_match_quality = 2
                    # Check for substring match (acceptable but less specific)
                    elif best_match_quality < 1 and (entity_lower in name or name in entity_lower):
                        found = True
                        best_match = name
                        best_match_index = idx
                        best_match_quality = 1
                
                if found and best_match_index >= 0:
                    matched_indices.append(best_match_index)
                else:
                    missing_entities.append(entity)
            
            # Move matched entities to the front of results (after position 0 which is best semantic match)
            if matched_indices:
                # Sort matched indices in descending order to avoid index shifting during removal
                matched_indices.sort(reverse=True)
                
                # Extract the matched items
                matched_items = []
                for idx in matched_indices:
                    matched_items.append({
                        'id': results['ids'][0][idx],
                        'document': results['documents'][0][idx],
                        'metadata': results['metadatas'][0][idx],
                        'distance': results['distances'][0][idx]
                    })
                    # Remove from current position (working backwards)
                    del results['ids'][0][idx]
                    del results['documents'][0][idx]
                    del results['metadatas'][0][idx]
                    del results['distances'][0][idx]
                
                # Insert matched items at the front (they're in reverse order, so reverse again)
                matched_items.reverse()
                for item in matched_items:
                    results['ids'][0].insert(0, item['id'])
                    results['documents'][0].insert(0, item['document'])
                    results['metadatas'][0].insert(0, item['metadata'])
                    results['distances'][0].insert(0, item['distance'])
            
            # For each missing entity, do a targeted search
            if missing_entities:
                for entity in missing_entities:
                    entity_results = self.collection.query(
                        query_embeddings=[self.get_embedding(entity)],
                        n_results=1
                    )
                    if entity_results['ids'][0]:
                        # Add this result to our main results
                        results['ids'][0].append(entity_results['ids'][0][0])
                        results['documents'][0].append(entity_results['documents'][0][0])
                        results['metadatas'][0].append(entity_results['metadatas'][0][0])
                        results['distances'][0].append(entity_results['distances'][0][0])
        
        # Smart enhancement: If the TOP result is a monster with a parent_category,
        # fetch that category and insert it as the second result
        if results['metadatas'][0] and results['metadatas'][0][0].get('parent_category_id'):
            category_id = results['metadatas'][0][0]['parent_category_id']
            existing_ids = set(results['ids'][0])
            
            # Only fetch if category not already in results
            if category_id not in existing_ids:
                try:
                    cat_result = self.collection.get(ids=[category_id])
                    if cat_result['ids']:
                        # Insert category at position 1 (after the primary result)
                        results['ids'][0].insert(1, cat_result['ids'][0])
                        results['documents'][0].insert(1, cat_result['documents'][0])
                        results['metadatas'][0].insert(1, cat_result['metadatas'][0])
                        # Use distance slightly worse than primary result
                        results['distances'][0].insert(1, results['distances'][0][0] + 0.05)
                except Exception as e:
                    # If category fetch fails, just continue
                    pass
        
        # Smart filtering: Adaptive cutoff based on distance gaps
        # Strategy:
        # 1. Look for the largest gap between consecutive distances
        # 2. If gap > threshold, cut there (indicates relevance drop-off)
        # 3. Otherwise use distance_threshold as relative cutoff
        # 4. Always keep at least 2 results, respect maximum k
        
        if len(results['ids'][0]) > 0:
            distances = results['distances'][0]
            
            # Calculate gaps between consecutive results
            # Start from position 2 (skip gap after best result, which can be large
            # simply because the best result is exceptionally good)
            gaps = []
            for i in range(2, min(len(distances), k)):
                gap = distances[i] - distances[i-1]
                gaps.append((i, gap))  # (position_after_gap, gap_size)
            
            # Find the largest gap
            max_gap_pos = None
            max_gap_size = 0
            gap_threshold = 0.06  # Significant semantic discontinuity
            
            if gaps:
                max_gap_pos, max_gap_size = max(gaps, key=lambda x: x[1])
            
            if debug and gaps:
                self.output.info(f"  [DEBUG] Gap analysis:")
                for pos, gap in sorted(gaps, key=lambda x: x[1], reverse=True)[:3]:
                    self.output.info(f"    Position {pos}: gap={gap:.4f}")
                self.output.info(f"  [DEBUG] Largest gap: {max_gap_size:.4f} at position {max_gap_pos}")
                
            # Decide where to cut
            keep_count = len(distances)  # Default: keep all
            strategy_used = "none"
            
            # Strategy 1: Cut at large gap (semantic cliff detected)
            if max_gap_size >= gap_threshold:
                keep_count = max_gap_pos
                strategy_used = f"gap detection (cliff at position {max_gap_pos}, gap={max_gap_size:.4f})"
            # Strategy 2: Use relative distance threshold
            else:
                best_distance = distances[0]
                cutoff_distance = best_distance + distance_threshold
                keep_count = 1
                for i in range(1, len(distances)):
                    if distances[i] <= cutoff_distance:
                        keep_count += 1
                    else:
                        break
                strategy_used = f"distance threshold (cutoff={cutoff_distance:.4f})"
            
            # Apply constraints
            original_keep = keep_count
            keep_count = max(2, keep_count) if len(distances) > 1 else 1  # Min 2 results
            keep_count = min(keep_count, k)  # Respect max k
            keep_count = min(keep_count, len(distances))  # Can't exceed what we have
            
            if debug:
                self.output.info(f"  [DEBUG] Strategy: {strategy_used}")
                self.output.info(f"  [DEBUG] Keep count: {original_keep} → {keep_count} (after constraints)")
                if keep_count < len(distances):
                    self.output.info(f"  [DEBUG] Dropping {len(distances) - keep_count} results with distances: {distances[keep_count:]}")
            
            # Trim results
            if keep_count < len(results['ids'][0]):
                results['ids'][0] = results['ids'][0][:keep_count]
                results['documents'][0] = results['documents'][0][:keep_count]
                results['metadatas'][0] = results['metadatas'][0][:keep_count]
                results['distances'][0] = results['distances'][0][:keep_count]
        
        return results
    
    def _retrieve_with_filtering(self, query: str, k: int = 15, distance_threshold: float = 0.4, debug: bool = False, max_iterations: int = 3):
        """Retrieve with iterative query_must filtering.
        
        Algorithm:
        1. Retrieve k chunks using base retrieval
        2. Filter based on query_must metadata
        3. If we have < k clean chunks, retrieve more (excluding already-seen chunks)
        4. Repeat until k chunks OR max_iterations reached
        5. Apply gap detection and return
        
        Args:
            query: The search query
            k: Target number of results
            distance_threshold: Maximum distance increase from best result
            debug: If True, print detailed filtering info
            max_iterations: Safety limit on re-query cycles
            
        Returns:
            Results dict in same format as _retrieve_base
        """
        import json
        import time
        from .query_must_filter import satisfies_query_must
        
        start_time = time.time()
        
        # Initialize state
        excluded_ids = set()
        kept_ids = set()  # Track IDs we've already kept to avoid duplicates
        all_kept_chunks = []
        iteration = 0
        total_excluded = 0
        
        # Get embedding once (reuse across iterations)
        query_embedding = self.get_embedding(query)
        
        if debug:
            self.output.info(f"\n[FILTERING] Starting iterative retrieval (k={k}, max_iterations={max_iterations})")
        
        while iteration < max_iterations:
            if debug:
                self.output.info(f"\n[FILTERING] === Iteration {iteration + 1} ===")
            
            # Build ChromaDB query parameters
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": k
            }
            
            # Exclude ALL previously processed chunks (both kept and excluded)
            # Use metadata.uid instead of document ID since ChromaDB where clause only works on metadata
            all_seen_ids = excluded_ids | kept_ids
            if all_seen_ids:
                query_params["where"] = {"uid": {"$nin": list(all_seen_ids)}}
                if debug:
                    self.output.info(f"[FILTERING] Excluding {len(all_seen_ids)} previously processed chunks ({len(kept_ids)} kept + {len(excluded_ids)} excluded)")
            
            # Retrieve from ChromaDB
            results = self.collection.query(**query_params)
            
            # Check if results returned
            if not results['ids'][0]:
                if debug:
                    self.output.info(f"[FILTERING] No more results available from ChromaDB")
                break
            
            # Filter based on query_must
            newly_kept = []
            newly_excluded = []
            
            # Track total chunks to process for numbering
            total_chunks_in_batch = len(results['ids'][0])
            chunk_counter = 0
            
            for chunk_id, metadata, document, distance in zip(
                results['ids'][0],
                results['metadatas'][0],
                results['documents'][0],
                results['distances'][0]
            ):
                chunk_counter += 1
                
                # Extract uid from metadata (fallback to chunk_id if not present for backwards compatibility)
                uid = metadata.get('uid', chunk_id)
                
                # Skip if already kept in a previous iteration (avoid duplicates)
                if uid in kept_ids:
                    if debug:
                        chunk_info = self._format_chunk_info(metadata, chunk_counter, total_chunks_in_batch)
                        self.output.info(f"  ⏭️  SKIP: {chunk_info} (duplicate)")
                    continue
                
                # Skip query_must filtering for reference chunks (EXPLANATORY NOTES)
                # These are educational/reference material that should always be available
                is_reference = (metadata.get('type') == 'reference' and 
                               metadata.get('section') == 'EXPLANATORY NOTES')
                
                # Check if chunk has query_must metadata (skip for reference chunks)
                if 'query_must' in metadata and not is_reference:
                    try:
                        # Parse query_must (stored as JSON string in ChromaDB)
                        query_must = json.loads(metadata['query_must']) if isinstance(metadata['query_must'], str) else metadata['query_must']
                        
                        # Check if query satisfies requirements
                        if satisfies_query_must(query, query_must, debug=debug):
                            newly_kept.append({
                                'id': chunk_id,
                                'metadata': metadata,
                                'document': document,
                                'distance': distance
                            })
                            kept_ids.add(uid)  # Track by uid
                            if debug:
                                chunk_info = self._format_chunk_info(metadata, chunk_counter, total_chunks_in_batch)
                                self.output.info(f"  ✅ KEEP: {chunk_info}")
                        else:
                            newly_excluded.append(uid)  # Track by uid
                            excluded_ids.add(uid)  # Track by uid
                            if debug:
                                chunk_info = self._format_chunk_info(metadata, chunk_counter, total_chunks_in_batch)
                                self.output.info(f"  ❌ EXCLUDE: {chunk_info}")
                    except json.JSONDecodeError as e:
                        # If query_must is malformed, keep the chunk (fail open)
                        if debug:
                            chunk_info = self._format_chunk_info(metadata, chunk_counter, total_chunks_in_batch)
                            self.output.info(f"  ⚠️  KEEP (malformed query_must): {chunk_info}")
                        newly_kept.append({
                            'id': chunk_id,
                            'metadata': metadata,
                            'document': document,
                            'distance': distance
                        })
                        kept_ids.add(uid)  # Track by uid
                else:
                    # No restrictions - always keep
                    newly_kept.append({
                        'id': chunk_id,
                        'metadata': metadata,
                        'document': document,
                        'distance': distance
                    })
                    kept_ids.add(uid)  # Track by uid
                    if debug:
                        chunk_info = self._format_chunk_info(metadata, chunk_counter, total_chunks_in_batch)
                        if is_reference:
                            self.output.info(f"  ✅ KEEP: {chunk_info} (reference - no filtering)")
                        else:
                            self.output.info(f"  ✅ KEEP: {chunk_info} (no restrictions)")
            
            # Add kept chunks to results
            all_kept_chunks.extend(newly_kept)
            total_excluded += len(newly_excluded)
            
            if debug:
                self.output.info(f"[FILTERING] Kept {len(newly_kept)}, excluded {len(newly_excluded)} (total kept: {len(all_kept_chunks)})")
            
            # Check stopping conditions
            if len(all_kept_chunks) >= k:
                if debug:
                    self.output.info(f"[FILTERING] Target k={k} reached ({len(all_kept_chunks)} chunks)")
                break
            
            if len(newly_excluded) == 0 and len(newly_kept) == 0:
                if debug:
                    self.output.info(f"[FILTERING] No new chunks this iteration (all were duplicates), stopping")
                break
            
            if len(newly_excluded) == 0:
                if debug:
                    self.output.info(f"[FILTERING] No exclusions this iteration, stopping")
                break
            
            iteration += 1
        
        # Performance metrics
        elapsed_time = (time.time() - start_time) * 1000  # Convert to ms
        
        if debug:
            self.output.info(f"\n[FILTERING] === Summary ===")
            self.output.info(f"[FILTERING] Iterations: {iteration + 1}")
            self.output.info(f"[FILTERING] Total excluded: {total_excluded}")
            self.output.info(f"[FILTERING] Final kept: {len(all_kept_chunks)}")
            self.output.info(f"[FILTERING] Time: {elapsed_time:.1f}ms")
        
        # If no chunks were kept, return empty results
        if not all_kept_chunks:
            return {
                'ids': [[]],
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }
        
        # Sort by distance and take top k
        all_kept_chunks.sort(key=lambda x: x['distance'])
        final_chunks = all_kept_chunks[:k]
        
        # Convert back to ChromaDB results format
        filtered_results = {
            'ids': [[chunk['id'] for chunk in final_chunks]],
            'documents': [[chunk['document'] for chunk in final_chunks]],
            'metadatas': [[chunk['metadata'] for chunk in final_chunks]],
            'distances': [[chunk['distance'] for chunk in final_chunks]]
        }
        
        # Now apply the same enhancements as base retrieval:
        # 1. Entity-aware repositioning (comparison queries)
        # 2. Parent category injection (monsters)
        # 3. Adaptive gap detection
        
        # Note: These enhancements were already applied in the initial retrieval,
        # so we just need to apply gap detection to the final filtered set
        
        if len(filtered_results['ids'][0]) > 0:
            distances = filtered_results['distances'][0]
            
            # Apply adaptive gap detection (same logic as base retrieval)
            gaps = []
            for i in range(2, min(len(distances), k)):
                gap = distances[i] - distances[i-1]
                gaps.append((i, gap))
            
            max_gap_pos = None
            max_gap_size = 0
            gap_threshold = 0.06
            
            if gaps:
                max_gap_pos, max_gap_size = max(gaps, key=lambda x: x[1])
            
            if debug and gaps:
                self.output.info(f"  [DEBUG] Gap analysis on filtered results:")
                for pos, gap in sorted(gaps, key=lambda x: x[1], reverse=True)[:3]:
                    self.output.info(f"    Position {pos}: gap={gap:.4f}")
            
            # Decide where to cut
            keep_count = len(distances)
            strategy_used = "none"
            
            if max_gap_size >= gap_threshold:
                keep_count = max_gap_pos
                strategy_used = f"gap detection (cliff at position {max_gap_pos}, gap={max_gap_size:.4f})"
            else:
                best_distance = distances[0]
                cutoff_distance = best_distance + distance_threshold
                keep_count = 1
                for i in range(1, len(distances)):
                    if distances[i] <= cutoff_distance:
                        keep_count += 1
                    else:
                        break
                strategy_used = f"distance threshold (cutoff={cutoff_distance:.4f})"
            
            # Apply constraints
            original_keep = keep_count
            keep_count = max(2, keep_count) if len(distances) > 1 else 1
            keep_count = min(keep_count, k)
            keep_count = min(keep_count, len(distances))
            
            if debug:
                self.output.info(f"  [DEBUG] Strategy: {strategy_used}")
                self.output.info(f"  [DEBUG] Keep count: {original_keep} → {keep_count} (after constraints)")
            
            # Trim results
            if keep_count < len(filtered_results['ids'][0]):
                filtered_results['ids'][0] = filtered_results['ids'][0][:keep_count]
                filtered_results['documents'][0] = filtered_results['documents'][0][:keep_count]
                filtered_results['metadatas'][0] = filtered_results['metadatas'][0][:keep_count]
                filtered_results['distances'][0] = filtered_results['distances'][0][:keep_count]
        
        return filtered_results
    
    def format_context(self, results):
        """Format retrieved chunks into context for the LLM."""
        contexts = []
        
        for i, (doc, metadata) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0]
        )):
            name = metadata.get('name', metadata.get('title', 'Unknown'))
            chunk_type = metadata.get('type', 'text')
            chunk_part = metadata.get('chunk_part', 1)
            # For monsters and categories, the doc already has the header with statistics
            # so we don't need to add extra formatting
            if chunk_type in ['monster', 'category']:
                contexts.append(doc)
            # Format based on chunk type for other content
            elif chunk_type == 'spell':
                school = metadata.get('spell_school', '')
                contexts.append(f"## {name}\n{school}\n\n{doc}")
            elif chunk_type == 'monster_entry':
                contexts.append(f"## {name}\n\n{doc}")
            elif chunk_type.startswith('table'):
                # Include table title prominently
                contexts.append(f"## {name}\n\n{doc}")
            else:
                contexts.append(f"### {name}\n\n{doc}")
        

        return "\n\n---\n\n".join(contexts)
    
    def generate(self, query: str, context: str, max_tokens: int = 800):
        """Generate answer using OpenAI."""
        system_prompt = """You are a knowledgeable Dungeon Master assistant for Advanced Dungeons & Dragons 1st Edition.

Your role is to provide accurate, helpful answers based on the official rulebooks. When answering:
1. Be precise and cite the specific rules context element you are using to establish your answer.
2. If the context contains tables, READ THEM CAREFULLY:
   - Identify the correct row (first column)
   - Identify the correct column header
   - Show the EXACT intersection value you're using
   - Double-check your reading before calculating
3. If the context contains JSON notation:
   - Parse the JSON into an object
   - Then parse the object's properties to search for your answer.
   - Explain which properties you are using and why.
4. When calculating combat probabilities:
   - Explain which piece of context you're getting your numbers from.
   - Apply ALL relevant modifiers (strength "to hit" bonus, dexterity bonuses, etc.)
   - Modifiers REDUCE the required die roll (a +1 bonus means you need to roll 1 less)
5. If information is not in the provided context, say so clearly
6. Use D&D terminology correctly
7. Show your work step-by-step for complex calculations

The context below comes from official AD&D 1st Edition rulebooks. Use this context AND ONLY this context to answer.

IMPORTANT: you must only use the provided context to answer questions. If the context doesn't provide enough information, explain what might additional information you need.
"""
   
        user_prompt = f"""Context from D&D 1st Edition rulebooks:

{context}

---
Question: {query}

Answer based on the context above:"""

        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.1  # Lower temperature for more factual responses
        )
        
        # Return both content and token usage
        return {
            'content': response.choices[0].message.content,
            'usage': {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
        }
    
    def query(self, question: str, k: int = 15, distance_threshold: float = 0.4, show_context: bool = False, debug: bool = False, enable_filtering: bool = True, max_iterations: int = 3):
        """Full RAG pipeline: retrieve + generate."""
        self.output.info(f"\n{'='*80}")
        self.output.info(f"QUESTION: {question}")
        self.output.info(f"{'='*80}\n")
        
        # Retrieve
        filter_status = "with filtering" if enable_filtering else "without filtering"
        self.output.info(f"Retrieving up to {k} relevant chunks ({filter_status}, distance threshold: {distance_threshold})...")
        results = self.retrieve(question, k=k, distance_threshold=distance_threshold, debug=debug, 
                               enable_filtering=enable_filtering, max_iterations=max_iterations)
        
        # Show retrieved chunks
        total_chunks = len(results['metadatas'][0])
        self.output.info(f"\nRetrieved chunks:")
        for i, (metadata, distance) in enumerate(zip(
            results['metadatas'][0],
            results['distances'][0]
        ), 1):  # Start enumeration at 1
            chunk_info = self._format_chunk_info(metadata, i, total_chunks)
            self.output.info(f"  {i}. {chunk_info} (distance: {distance:.4f})")
        
        # Format context
        context = self.format_context(results)
        
        if show_context:
            self.output.info(f"\n{'='*80}")
            self.output.info("CONTEXT SENT TO LLM:")
            self.output.info(f"{'='*80}")
            self.output.info(context)
            self.output.info(f"{'='*80}\n")
        
        # Generate answer
        self.output.info(f"\nGenerating answer with {self.model}...")
        generation_result = self.generate(question, context)
        answer = generation_result['content']
        usage = generation_result['usage']
        
        self.output.info(f"\n{'='*80}")
        self.output.info("ANSWER:")
        self.output.info(f"{'='*80}")
        self.output.info(answer)
        self.output.info(f"{'='*80}\n")
        
        # Store answer and usage
        self.output.set_answer(answer)
        result_dict = self.output.to_dict()
        result_dict['usage'] = usage  # Add usage to output
        
        return result_dict


def main():
    parser = argparse.ArgumentParser(
        description="Query D&D 1st Edition RAG system"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Question to ask (if not provided, enters interactive mode)"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "-k",
        type=int,
        default=15,
        help="Maximum number of chunks to retrieve (default: 15)"
    )
    parser.add_argument(
        "--distance-threshold",
        type=float,
        default=0.4,
        help="Maximum distance increase from best result (default: 0.4). Higher = more permissive"
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Show the context sent to the LLM"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug info about gap detection and filtering"
    )
    parser.add_argument(
        "--disable-filtering",
        action="store_true",
        help="Disable query_must filtering (use base retrieval only)"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Maximum iterations for re-querying when filtering enabled (default: 3)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test questions for the collection"
    )
    
    args = parser.parse_args()
    
    # Initialize RAG system
    try:
        rag = DnDRAG(
            model=args.model
        )
    except Exception as e:
        print(f"Error initializing RAG system: {e}")
        sys.exit(1)
    
    # Test mode
    if args.test:
        # Use unified collection tests for both books
        test_questions = [
            "How many experience points does a fighter need to reach 9th level?",
            "Tell me about owlbears and their abilities",
            "What is the difference between a red dragon and a white dragon?",
            "What are the six character abilities in D&D?"
        ]
        
        print(f"\n{'*'*80}")
        print(f"RUNNING TEST QUESTIONS FOR UNIFIED COLLECTION")
        print(f"{'*'*80}\n")
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n{'#'*80}")
            print(f"TEST QUESTION {i}/{len(test_questions)}")
            print(f"{'#'*80}")
            rag.query(question, k=args.k, distance_threshold=args.distance_threshold, show_context=args.show_context, debug=args.debug,
                     enable_filtering=not args.disable_filtering, max_iterations=args.max_iterations)
            
            if i < len(test_questions):
                input("\nPress Enter to continue to next question...")
        
        sys.exit(0)
    
    # Single query mode
    if args.query:
        rag.query(args.query, k=args.k, distance_threshold=args.distance_threshold, show_context=args.show_context, debug=args.debug,
                 enable_filtering=not args.disable_filtering, max_iterations=args.max_iterations)
        sys.exit(0)
    
    # Interactive mode
    print(f"\n{'='*80}")
    print("INTERACTIVE MODE")
    print(f"{'='*80}")
    print("Enter your questions (or 'quit' to exit)")
    print(f"Using unified D&D 1st Edition collection")
    print(f"Retrieving k={args.k} chunks per query")
    print(f"{'='*80}\n")
    
    while True:
        try:
            question = input("\nQuestion: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            rag.query(question, k=args.k, distance_threshold=args.distance_threshold, show_context=args.show_context, debug=args.debug,
                     enable_filtering=not args.disable_filtering, max_iterations=args.max_iterations)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
