#!/usr/bin/env python3
"""
Embed and Store Semantic Chunks - Phase 2

This script:
1. Loads semantic chunks (from chunk_documents_semantic.py)
2. Generates embeddings using sentence-transformers
3. Stores in ChromaDB with rich metadata

Key improvements:
- Uses metadata from semantic chunking
- Creates new collection (dnd_rulebooks_semantic)
- Preserves content type, section headers, etc.
"""

import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import time


class EmbeddingGenerator:
    """Generate embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"✓ Model loaded (dimension: {self.model.get_sentence_embedding_dimension()})")
    
    def generate_embeddings(self, texts: list, batch_size: int = 32) -> list:
        """Generate embeddings for a list of texts."""
        embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.model.encode(batch, show_progress_bar=False)
            embeddings.extend(batch_embeddings.tolist())
        
        return embeddings


class ChromaDBStorage:
    """Handle ChromaDB storage operations."""
    
    def __init__(self, host: str = "localhost", port: int = 8060):
        print(f"Connecting to ChromaDB at {host}:{port}")
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=Settings(allow_reset=True)
        )
        
        # Verify connection
        try:
            self.client.heartbeat()
            print("✓ Connected to ChromaDB")
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            raise
    
    def create_collection(self, collection_name: str, replace: bool = False):
        """Create or get a collection."""
        if replace:
            try:
                self.client.delete_collection(collection_name)
                print(f"✓ Deleted existing collection: {collection_name}")
            except:
                pass
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "D&D 1st Edition rulebooks - Semantic chunking"}
        )
        print(f"✓ Collection ready: {collection_name}")
    
    def add_chunks(self, chunks: list, embeddings: list, batch_size: int = 100):
        """Add chunks with embeddings to the collection."""
        total = len(chunks)
        
        for i in tqdm(range(0, total, batch_size), desc="Storing in ChromaDB"):
            batch_chunks = chunks[i:i+batch_size]
            batch_embeddings = embeddings[i:i+batch_size]
            
            # Prepare batch data
            ids = [f"chunk_{i+j}" for j in range(len(batch_chunks))]
            documents = [chunk['text'] for chunk in batch_chunks]
            metadatas = [chunk['metadata'] for chunk in batch_chunks]
            
            # Convert numeric values in metadata to strings (ChromaDB requirement)
            for metadata in metadatas:
                for key, value in metadata.items():
                    if isinstance(value, (int, float)):
                        metadata[key] = str(value)
                    elif isinstance(value, bool):
                        metadata[key] = str(value).lower()
            
            # Add to collection
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=batch_embeddings,
                metadatas=metadatas
            )
        
        print(f"✓ Stored {total} chunks in ChromaDB")


def load_semantic_chunks(input_file: str = "chunks_semantic.json") -> tuple:
    """Load semantic chunks from JSON file."""
    print(f"Loading chunks from: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chunks = data['chunks']
    metadata = data['metadata']
    
    print(f"✓ Loaded {len(chunks)} chunks")
    print(f"  Created: {metadata['created_at']}")
    print(f"  Phase: {metadata['phase']}")
    
    if 'statistics' in metadata:
        print("\n  Content Types:")
        for ctype, count in metadata['statistics']['content_types'].items():
            print(f"    {ctype}: {count}")
    
    return chunks, metadata


def main():
    """Main execution function."""
    print("=" * 60)
    print("Embedding & Storage - Semantic Chunks (Phase 2)")
    print("=" * 60)
    print()
    
    # Configuration
    INPUT_FILE = "chunks_semantic.json"
    COLLECTION_NAME = "dnd_rulebooks_semantic"
    CHROMA_HOST = "localhost"
    CHROMA_PORT = 8060
    REPLACE_COLLECTION = True
    
    print("Configuration:")
    print(f"  Input file: {INPUT_FILE}")
    print(f"  ChromaDB collection: {COLLECTION_NAME}")
    print(f"  ChromaDB: {CHROMA_HOST}:{CHROMA_PORT}")
    print(f"  Replace existing: {REPLACE_COLLECTION}")
    print()
    
    # Load chunks
    chunks, metadata = load_semantic_chunks(INPUT_FILE)
    print()
    
    # Generate embeddings
    print("Generating embeddings...")
    start_time = time.time()
    
    embedding_gen = EmbeddingGenerator()
    texts = [chunk['text'] for chunk in chunks]
    embeddings = embedding_gen.generate_embeddings(texts)
    
    elapsed = time.time() - start_time
    print(f"✓ Generated {len(embeddings)} embeddings in {elapsed:.1f}s ({elapsed/len(embeddings)*1000:.1f}ms per chunk)")
    print()
    
    # Store in ChromaDB
    print("Storing in ChromaDB...")
    storage = ChromaDBStorage(host=CHROMA_HOST, port=CHROMA_PORT)
    storage.create_collection(COLLECTION_NAME, replace=REPLACE_COLLECTION)
    storage.add_chunks(chunks, embeddings)
    print()
    
    # Verify storage
    print("Verifying storage...")
    count = storage.collection.count()
    print(f"✓ Collection contains {count} documents")
    print()
    
    # Show sample metadata
    print("Sample chunk metadata:")
    sample = storage.collection.get(limit=1, include=['metadatas'])
    if sample['metadatas']:
        print(json.dumps(sample['metadatas'][0], indent=2))
    print()
    
    print("=" * 60)
    print("✓ Semantic chunks embedded and stored!")
    print("=" * 60)
    print()
    print("Key improvements over naive chunking:")
    print("  • Section-aware chunking")
    print("  • Headers included in chunks")
    print("  • Content type metadata")
    print("  • Semantic boundaries preserved")
    print()
    print("Next steps:")
    print("  1. Test with: python query_rag_semantic.py")
    print("  2. Compare results with naive chunking")
    print("  3. Re-run your 5 test questions")
    print()
    print("To query interactively:")
    print('  python query_rag_semantic.py --interactive')
    print()


if __name__ == "__main__":
    main()
