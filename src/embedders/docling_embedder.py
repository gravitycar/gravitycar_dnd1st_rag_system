#!/usr/bin/env python3
"""
Embed chunks from Player's Handbook or Monster Manual into ChromaDB.

Uses all-mpnet-base-v2 for embeddings (768 dimensions).
Provides better semantic understanding for D&D content.
Stores rich metadata for each chunk.
Creates separate collections for each book.
"""

import json
import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path
from typing import List, Dict, Any
import time


class DoclingEmbedder:
    def __init__(
        self, 
        chunks_file: str, 
        collection_name: str,
        chroma_host: str = "localhost",
        chroma_port: int = 8060
    ):
        self.chunks_file = Path(chunks_file)
        self.collection_name = collection_name
        
        print(f"Loading embedding model: all-mpnet-base-v2...")
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        
        print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}...")
        self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
        
        # Delete collection if it exists (fresh start)
        try:
            self.client.delete_collection(name=collection_name)
            print(f"Deleted existing collection: {collection_name}")
        except:
            pass
        
        # Create new collection
        self.collection = self.client.create_collection(
            name=collection_name,
            metadata={"description": f"D&D 1st Edition - {collection_name}"}
        )
        print(f"Created collection: {collection_name}")
    
    def load_chunks(self) -> List[Dict[str, Any]]:
        """Load chunks from JSON file."""
        print(f"\nLoading chunks from {self.chunks_file}...")
        with open(self.chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks")
        return chunks
    
    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32):
        """Embed chunks and store in ChromaDB."""
        print(f"\nEmbedding and storing chunks (batch size: {batch_size})...")
        
        total_chunks = len(chunks)
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            batch_end = min(i + batch_size, total_chunks)
            
            print(f"Processing batch {i // batch_size + 1}/{(total_chunks + batch_size - 1) // batch_size} "
                  f"(chunks {i+1}-{batch_end})...")
            
            # Extract texts for embedding (use 'description' field for Monster Manual)
            # For monsters, prepend statistics to make them searchable
            texts = []
            for chunk in batch:
                text = chunk.get("description", chunk.get("content", ""))
                
                # Add statistics block for monsters
                if chunk["metadata"]["type"] == "monster" and "statistics" in chunk:
                    stats = chunk["statistics"]
                    stats_text = f"## {chunk.get('name', 'Unknown')}\n\n"
                    stats_text += f"**Statistics:**\n"
                    for key, value in stats.items():
                        if value and value != "Nil":
                            # Format the key nicely
                            display_key = key.replace('_', ' ').title()
                            stats_text += f"- {display_key}: {value}\n"
                    stats_text += f"\n**Description:**\n{text}"
                    text = stats_text
                
                texts.append(text)
            
            # Generate embeddings
            embeddings = self.model.encode(texts, show_progress_bar=False)
            
            # Prepare data for ChromaDB
            ids = []
            metadatas = []
            documents = []
            
            for j, chunk in enumerate(batch):
                # Use the chunk's ID if available, otherwise generate one
                chunk_id = chunk["metadata"].get("monster_id") or chunk["metadata"].get("category_id") or f"chunk_{i + j}"
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
                        metadata["parent_category"] = chunk["metadata"]["parent_category"]
                        metadata["parent_category_id"] = chunk["metadata"].get("parent_category_id", "")
                    
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
                ids=ids,
                embeddings=embeddings.tolist(),
                metadatas=metadatas,
                documents=documents
            )
            
            time.sleep(0.1)  # Small delay to avoid overwhelming ChromaDB
        
        print(f"\n✅ Successfully embedded and stored {total_chunks} chunks!")
    
    def test_query(self, query: str, n_results: int = 5):
        """Test the collection with a sample query."""
        print(f"\n{'='*80}")
        print(f"TEST QUERY: {query}")
        print(f"{'='*80}")
        
        # Embed the query
        query_embedding = self.model.encode([query])[0]
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results
        )
        
        # Display results
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            print(f"\n--- Result {i+1} (distance: {distance:.4f}) ---")
            print(f"Name: {metadata.get('name', 'N/A')}")
            print(f"Type: {metadata.get('type', 'N/A')}")
            
            # Show type-specific metadata
            if metadata.get('parent_category'):
                print(f"Category: {metadata['parent_category']}")
            if metadata.get('frequency'):
                print(f"Frequency: {metadata['frequency']}")
            if metadata.get('hit_dice'):
                print(f"Hit Dice: {metadata['hit_dice']}")
            if metadata.get('armor_class'):
                print(f"Armor Class: {metadata['armor_class']}")
            if metadata.get('alignment'):
                print(f"Alignment: {metadata['alignment']}")
            if metadata.get('spell_school'):
                print(f"Spell School: {metadata['spell_school']}")
            
            print(f"Content preview: {doc[:200]}...")
        
        print(f"\n{'='*80}\n")
    
    def process(self):
        """Main processing pipeline."""
        chunks = self.load_chunks()
        self.embed_chunks(chunks)


def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Embed D&D 1st Edition book chunks into ChromaDB"
    )
    parser.add_argument(
        "chunks_file",
        help="Path to chunks JSON file (e.g., chunks_players_handbook.json)"
    )
    parser.add_argument(
        "collection_name",
        help="ChromaDB collection name (e.g., dnd_players_handbook)"
    )
    parser.add_argument(
        "--test-query",
        help="Optional test query to run after embedding",
        default=None
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="ChromaDB host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8060,
        help="ChromaDB port (default: 8060)"
    )
    
    args = parser.parse_args()
    
    if not Path(args.chunks_file).exists():
        print(f"Error: File not found: {args.chunks_file}")
        sys.exit(1)
    
    embedder = DoclingEmbedder(
        chunks_file=args.chunks_file,
        collection_name=args.collection_name,
        chroma_host=args.host,
        chroma_port=args.port
    )
    
    embedder.process()
    
    # Run test query if provided
    if args.test_query:
        embedder.test_query(args.test_query)
    else:
        # Run default test queries based on collection type
        if "player" in args.collection_name.lower():
            embedder.test_query("How many experience points does a fighter need for 9th level?")
        elif "monster" in args.collection_name.lower():
            embedder.test_query("Tell me about demons and their abilities")


if __name__ == "__main__":
    main()
