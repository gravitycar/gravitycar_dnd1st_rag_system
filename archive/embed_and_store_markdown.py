#!/usr/bin/env python3
"""
Embed markdown chunks and store in ChromaDB.

This reads chunks_markdown.json and creates a new collection
in ChromaDB with embeddings.

Usage:
    python embed_and_store_markdown.py
"""

import json
import time
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


def load_chunks(chunks_file: str = "chunks_markdown.json") -> List[Dict[str, Any]]:
    """Load chunks from JSON file."""
    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    return chunks


def embed_and_store(
    chunks_file: str = "chunks_markdown.json",
    collection_name: str = "dnd_markdown",
    chroma_host: str = "localhost",
    chroma_port: int = 8060,
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32
):
    """
    Generate embeddings for chunks and store in ChromaDB.
    
    Args:
        chunks_file: JSON file containing chunks
        collection_name: Name for the ChromaDB collection
        chroma_host: ChromaDB host
        chroma_port: ChromaDB port
        model_name: Sentence transformer model name
        batch_size: Number of chunks to embed at once
    """
    print("=" * 60)
    print("Markdown Chunks → ChromaDB")
    print("=" * 60)
    print()
    
    # Load chunks
    print(f"Loading chunks from {chunks_file}...")
    chunks = load_chunks(chunks_file)
    print(f"✓ Loaded {len(chunks)} chunks")
    print()
    
    # Initialize embedding model
    print(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"✓ Model loaded (dimension: {model.get_sentence_embedding_dimension()})")
    print()
    
    # Connect to ChromaDB
    print(f"Connecting to ChromaDB at {chroma_host}:{chroma_port}")
    client = chromadb.HttpClient(
        host=chroma_host,
        port=chroma_port,
        settings=Settings(allow_reset=True)
    )
    
    # Check connection
    heartbeat = client.heartbeat()
    print(f"✓ Connected (heartbeat: {heartbeat})")
    print()
    
    # Create or get collection
    print(f"Creating collection: {collection_name}")
    
    # Delete if exists (for clean slate)
    try:
        client.delete_collection(name=collection_name)
        print(f"  ℹ Deleted existing collection")
    except:
        pass
    
    collection = client.create_collection(
        name=collection_name,
        metadata={"description": "D&D 1st Edition rulebooks (PyMuPDF markdown, intelligent chunking)"}
    )
    print(f"✓ Collection created")
    print()
    
    # Embed and store in batches
    print(f"Embedding and storing {len(chunks)} chunks (batch size: {batch_size})...")
    print()
    
    total_start = time.time()
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        
        print(f"Batch {batch_num}/{total_batches} (chunks {i+1}-{min(i+batch_size, len(chunks))})")
        
        batch_start = time.time()
        
        # Extract texts for embedding
        texts = [chunk['text'] for chunk in batch]
        
        # Generate embeddings
        print("  Generating embeddings...", end=" ", flush=True)
        embed_start = time.time()
        embeddings = model.encode(texts, show_progress_bar=False)
        embed_time = time.time() - embed_start
        print(f"✓ ({embed_time:.2f}s)")
        
        # Prepare data for ChromaDB
        ids = [f"{chunk['source_file']}_{chunk['chunk_id']}" for chunk in batch]
        metadatas = [
            {
                'source_file': chunk['source_file'],
                'chunk_id': chunk['chunk_id'],
                'chunk_type': chunk['chunk_type'],
                'header': chunk['header'],
                'char_count': chunk['char_count']
            }
            for chunk in batch
        ]
        
        # Store in ChromaDB
        print("  Storing in ChromaDB...", end=" ", flush=True)
        store_start = time.time()
        collection.add(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=texts,
            metadatas=metadatas
        )
        store_time = time.time() - store_start
        print(f"✓ ({store_time:.2f}s)")
        
        batch_time = time.time() - batch_start
        avg_time = batch_time / len(batch)
        print(f"  Batch completed in {batch_time:.2f}s ({avg_time*1000:.1f}ms per chunk)")
        print()
    
    total_time = time.time() - total_start
    avg_time = total_time / len(chunks)
    
    print("=" * 60)
    print("Embedding Complete")
    print("=" * 60)
    print(f"Total chunks: {len(chunks)}")
    print(f"Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
    print(f"Average time per chunk: {avg_time*1000:.1f}ms")
    print()
    
    # Verify collection
    print("Verifying collection...")
    count = collection.count()
    print(f"✓ Collection contains {count} documents")
    print()
    
    # Test query
    print("Testing retrieval with sample query...")
    test_query = "What spells can a magic-user cast at first level?"
    results = collection.query(
        query_embeddings=model.encode([test_query]).tolist(),
        n_results=3
    )
    
    print(f"\nQuery: '{test_query}'")
    print("\nTop 3 results:")
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
        print(f"\n{i}. [{metadata['source_file']}] {metadata['header']}")
        print(f"   Type: {metadata['chunk_type']}, Size: {metadata['char_count']} chars")
        print(f"   Preview: {doc[:150]}...")
    print()
    
    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Test queries: python query_rag_markdown.py")
    print("2. Run test questions to see if PyMuPDF data is better")
    print("3. Compare against phase1 and phase2 results")
    print()


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Embed markdown chunks and store in ChromaDB")
    parser.add_argument(
        '--chunks-file',
        default="chunks_markdown.json",
        help="JSON file containing chunks"
    )
    parser.add_argument(
        '--collection',
        default="dnd_markdown",
        help="ChromaDB collection name"
    )
    parser.add_argument(
        '--host',
        default="localhost",
        help="ChromaDB host"
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8060,
        help="ChromaDB port"
    )
    parser.add_argument(
        '--model',
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help="Batch size for embedding"
    )
    
    args = parser.parse_args()
    
    embed_and_store(
        chunks_file=args.chunks_file,
        collection_name=args.collection,
        chroma_host=args.host,
        chroma_port=args.port,
        model_name=args.model,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
