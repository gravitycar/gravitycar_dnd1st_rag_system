#!/usr/bin/env python3
"""
Upload a local ChromaDB collection to ChromaCloud.

Usage:
    python scripts/upload_to_chromacloud.py <collection_name>
    
Example:
    python scripts/upload_to_chromacloud.py adnd_1e
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.chromadb_connector import ChromaDBConnector
import chromadb


def upload_collection(collection_name: str, batch_size: int = 100):
    """
    Upload a collection from local ChromaDB to ChromaCloud.
    
    Args:
        collection_name: Name of collection to upload
        batch_size: Number of documents to upload per batch
    """
    print(f"Uploading collection: {collection_name}")
    print("=" * 80)
    
    # Connect to LOCAL ChromaDB
    print("\n1. Connecting to LOCAL ChromaDB...")
    local_connector = ChromaDBConnector(use_cloud=False)
    print(f"   Connected: {local_connector}")
    
    try:
        local_collection = local_connector.get_collection(collection_name)
        local_count = local_collection.count()
        print(f"   Found collection: {collection_name} ({local_count} documents)")
    except Exception as e:
        print(f"   ERROR: Collection '{collection_name}' not found locally")
        print(f"   Available collections: {[c.name for c in local_connector.list_collections()]}")
        return False
    
    # Connect to ChromaCloud
    print("\n2. Connecting to ChromaCloud...")
    cloud_connector = ChromaDBConnector(use_cloud=True)
    print(f"   Connected: {cloud_connector}")
    
    # Check if collection exists in cloud
    if cloud_connector.collection_exists(collection_name):
        response = input(f"\n   Collection '{collection_name}' already exists in cloud. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("   Aborted.")
            return False
        print(f"   Deleting existing cloud collection...")
        cloud_connector.delete_collection(collection_name)
    
    # Create cloud collection
    print(f"\n3. Creating cloud collection...")
    cloud_collection = cloud_connector.create_collection(
        collection_name,
        metadata=local_collection.metadata
    )
    print(f"   Created: {collection_name}")
    
    # Fetch all data from local collection
    print(f"\n4. Fetching data from local collection ({local_count} documents)...")
    local_data = local_collection.get(
        include=['embeddings', 'documents', 'metadatas']
    )
    
    if not local_data['ids']:
        print("   ERROR: No documents found in local collection")
        return False
    
    print(f"   Fetched {len(local_data['ids'])} documents")
    
    # Upload to cloud in batches
    print(f"\n5. Uploading to cloud (batch size: {batch_size})...")
    total = len(local_data['ids'])
    
    for i in range(0, total, batch_size):
        end = min(i + batch_size, total)
        batch_ids = local_data['ids'][i:end]
        batch_embeddings = local_data['embeddings'][i:end] if local_data['embeddings'] else None
        batch_documents = local_data['documents'][i:end] if local_data['documents'] else None
        batch_metadatas = local_data['metadatas'][i:end] if local_data['metadatas'] else None
        
        cloud_collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas
        )
        
        print(f"   Uploaded batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({end}/{total} documents)")
    
    # Verify upload
    cloud_count = cloud_collection.count()
    print(f"\n6. Verification:")
    print(f"   Local:  {local_count} documents")
    print(f"   Cloud:  {cloud_count} documents")
    
    if cloud_count == local_count:
        print(f"   ✅ SUCCESS: All documents uploaded!")
        return True
    else:
        print(f"   ⚠️  WARNING: Document counts don't match!")
        return False


def main():
    parser = argparse.ArgumentParser(description='Upload local ChromaDB collection to ChromaCloud')
    parser.add_argument('collection_name', help='Name of collection to upload')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for upload (default: 100)')
    
    args = parser.parse_args()
    
    success = upload_collection(args.collection_name, args.batch_size)
    
    if success:
        print("\n" + "=" * 80)
        print("Upload complete!")
        print("\nNext steps:")
        print("1. Test queries against cloud collection")
        print("2. Update .env to use ChromaCloud in production")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("Upload failed. Please check errors above.")
        print("=" * 80)
        sys.exit(1)


if __name__ == '__main__':
    main()
