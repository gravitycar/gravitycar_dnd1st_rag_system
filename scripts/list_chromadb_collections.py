#!/usr/bin/env python3
"""
List all ChromaDB collections and their UUIDs.
Helps identify which GUID directories are in use vs obsolete.
"""

import chromadb
from pathlib import Path

def list_collections():
    """Connect to ChromaDB and list all collections."""
    print("Connecting to ChromaDB...")
    try:
        client = chromadb.HttpClient(host='localhost', port=8060)
        collections = client.list_collections()
        
        if not collections:
            print("No collections found.")
            return
        
        print(f"\nFound {len(collections)} collection(s):\n")
        print(f"{'Name':<30} {'UUID':<40} {'Count'}")
        print("=" * 80)
        
        for collection in collections:
            count = collection.count()
            collection_id = str(collection.id)
            print(f"{collection.name:<30} {collection_id:<40} {count}")
        
        print("\n" + "=" * 80)
        
        # List GUID directories in current directory
        current_dir = Path.cwd()
        guid_dirs = [d for d in current_dir.iterdir() 
                    if d.is_dir() and len(d.name) == 36 and '-' in d.name]
        
        if guid_dirs:
            print(f"\nFound {len(guid_dirs)} GUID directories in {current_dir}:")
            
            collection_ids = {str(c.id) for c in collections}
            
            for guid_dir in sorted(guid_dirs):
                status = "✅ IN USE" if guid_dir.name in collection_ids else "❌ OBSOLETE"
                print(f"  {guid_dir.name}  {status}")
            
            obsolete_count = sum(1 for d in guid_dirs if d.name not in collection_ids)
            if obsolete_count > 0:
                print(f"\n⚠️  {obsolete_count} obsolete directory(ies) can be safely deleted")
        
    except Exception as e:
        print(f"Error connecting to ChromaDB: {e}")
        print("\nMake sure ChromaDB is running:")
        print("  ./start_chroma.sh")
        return

if __name__ == "__main__":
    list_collections()
