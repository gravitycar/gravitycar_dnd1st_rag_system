#!/usr/bin/env python3
"""
ChromaDB Connector: Centralized ChromaDB connection and operations.

Provides a single source of truth for all ChromaDB interactions:
- Connection management (local HTTP or ChromaCloud)
- Collection operations (create, get, delete, list, truncate)
- Shared across embedders, CLI, and query modules
"""

import chromadb
import os
from typing import Optional, List, Dict, Any
from ..utils.config import get_chroma_connection_params


class ChromaDBConnector:
    """
    Centralized ChromaDB connection and operations manager.
    
    Handles all ChromaDB interactions to avoid code duplication and ensure
    consistent connection parameters across the codebase.
    
    Example usage:
        connector = ChromaDBConnector()
        collection = connector.get_or_create_collection("dnd_monsters")
        connector.truncate_collection("dnd_monsters")
        collections = connector.list_collections()
    """
    
    def __init__(
        self,
        chroma_host: Optional[str] = None,
        chroma_port: Optional[int] = None,
        use_cloud: Optional[bool] = None
    ):
        """
        Initialize ChromaDB connection (local or cloud).
        
        Auto-detects cloud mode if chroma_cloud_api_key is set in environment.
        
        Args:
            chroma_host: ChromaDB host (optional, uses config default)
            chroma_port: ChromaDB port (optional, uses config default)
            use_cloud: Force cloud mode (optional, auto-detects from env)
        """
        # Check if cloud credentials are available
        cloud_api_key = os.getenv('chroma_cloud_api_key')
        cloud_tenant = os.getenv('chroma_cloud_tenant_id')
        cloud_database = os.getenv('chroma_cloud_database', 'default_database')
        
        # Auto-detect cloud mode if credentials present
        if use_cloud is None:
            use_cloud = bool(cloud_api_key and cloud_tenant)
        
        self.use_cloud = use_cloud
        
        if use_cloud:
            # ChromaCloud mode
            if not cloud_api_key or not cloud_tenant:
                raise ValueError(
                    "ChromaCloud mode requires chroma_cloud_api_key and "
                    "chroma_cloud_tenant_id in environment"
                )
            
            self.chroma_host = "cloud"
            self.chroma_port = 443
            self.cloud_tenant = cloud_tenant
            self.cloud_database = cloud_database
            
            print(f"Connecting to ChromaCloud (tenant: {cloud_tenant}, database: {cloud_database})")
            try:
                self.client = chromadb.CloudClient(
                    api_key=cloud_api_key,
                    tenant=cloud_tenant,
                    database=cloud_database
                )
                # Test connection by listing collections
                _ = self.client.list_collections()
                print("✅ Successfully connected to ChromaCloud")
            except Exception as e:
                raise ConnectionError(
                    f"Failed to connect to ChromaCloud: {e}\n"
                    f"Check your chroma_cloud_api_key and chroma_cloud_tenant_id in .env.dndchat"
                ) from e
        else:
            # Local HTTP mode
            if chroma_host is None or chroma_port is None:
                chroma_host, chroma_port = get_chroma_connection_params()
            
            self.chroma_host = chroma_host
            self.chroma_port = chroma_port
            
            print(f"Connecting to local ChromaDB ({chroma_host}:{chroma_port})")
            try:
                self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
                # Test connection by listing collections
                _ = self.client.list_collections()
                print("✅ Successfully connected to local ChromaDB")
            except Exception as e:
                raise ConnectionError(
                    f"Failed to connect to ChromaDB at {chroma_host}:{chroma_port}: {e}\n"
                    f"Make sure ChromaDB is running (./scripts/start_chroma.sh)"
                ) from e
    
    def get_collection(self, name: str):
        """
        Get an existing collection.
        
        Args:
            name: Collection name
            
        Returns:
            ChromaDB collection object
            
        Raises:
            Exception: If collection doesn't exist
        """
        return self.client.get_collection(name=name)
    
    def create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Create a new collection.
        
        Args:
            name: Collection name
            metadata: Optional metadata dict
            
        Returns:
            ChromaDB collection object
            
        Raises:
            Exception: If collection already exists
        """
        if metadata is None:
            metadata = {"description": f"D&D 1st Edition - {name}"}
        
        return self.client.create_collection(name=name, metadata=metadata)
    
    def get_or_create_collection(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Get existing collection or create if it doesn't exist.
        
        Args:
            name: Collection name
            metadata: Optional metadata dict (used only for creation)
            
        Returns:
            ChromaDB collection object
        """
        try:
            collection = self.get_collection(name)
            return collection
        except Exception:
            if metadata is None:
                metadata = {"description": f"D&D 1st Edition - {name}"}
            return self.create_collection(name, metadata)
    
    def delete_collection(self, name: str):
        """
        Delete a collection permanently.
        
        Args:
            name: Collection name
            
        Raises:
            Exception: If collection doesn't exist
        """
        self.client.delete_collection(name=name)
    
    def truncate_collection(self, name: str, batch_size: int = 500) -> int:
        """
        Empty a collection (delete all entries but keep collection).
        
        This is more efficient than delete + recreate when you want to
        preserve the collection structure. Uses batching to avoid 
        ChromaCloud request size limits.
        
        Args:
            name: Collection name
            batch_size: Number of items to delete per batch (default: 500)
            
        Returns:
            Number of entries deleted
            
        Raises:
            Exception: If collection doesn't exist
        """
        collection = self.get_collection(name)
        count_before = collection.count()
        
        if count_before == 0:
            return 0
        
        # Delete in batches to avoid ChromaCloud limits
        total_deleted = 0
        
        print(f"Truncating {count_before} items in batches of {batch_size}...")
        
        while True:
            # Get a batch of IDs
            result = collection.get(limit=batch_size)
            
            if not result or not result['ids']:
                break
            
            # Delete this batch
            collection.delete(ids=result['ids'])
            batch_count = len(result['ids'])
            total_deleted += batch_count
            
            print(f"  Deleted {total_deleted}/{count_before} items...")
            
            # If we got fewer items than batch_size, we're done
            if batch_count < batch_size:
                break
        
        return count_before
    
    def list_collections(self) -> List:
        """
        List all collections in ChromaDB.
        
        Returns:
            List of ChromaDB collection objects
        """
        return self.client.list_collections()
    
    def collection_exists(self, name: str) -> bool:
        """
        Check if a collection exists.
        
        Args:
            name: Collection name
            
        Returns:
            True if collection exists, False otherwise
        """
        try:
            self.get_collection(name)
            return True
        except Exception:
            return False
    
    def get_collection_count(self, name: str) -> int:
        """
        Get the number of entries in a collection.
        
        Args:
            name: Collection name
            
        Returns:
            Number of entries in collection
            
        Raises:
            Exception: If collection doesn't exist
        """
        collection = self.get_collection(name)
        return collection.count()
    
    def get_collection_info(self, name: str) -> Dict[str, Any]:
        """
        Get information about a collection.
        
        Args:
            name: Collection name
            
        Returns:
            Dict with collection metadata (name, count, id, etc.)
            
        Raises:
            Exception: If collection doesn't exist
        """
        collection = self.get_collection(name)
        return {
            "name": collection.name,
            "count": collection.count(),
            "id": collection.id,
            "metadata": collection.metadata
        }
    
    def __repr__(self) -> str:
        """String representation of connector."""
        if self.use_cloud:
            return f"ChromaDBConnector(cloud, tenant={self.cloud_tenant}, database={self.cloud_database})"
        else:
            return f"ChromaDBConnector(host={self.chroma_host}, port={self.chroma_port})"
