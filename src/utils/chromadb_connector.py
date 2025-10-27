#!/usr/bin/env python3
"""
ChromaDB Connector: Centralized ChromaDB connection and operations.

Provides a single source of truth for all ChromaDB interactions:
- Connection management
- Collection operations (create, get, delete, list, truncate)
- Shared across embedders, CLI, and query modules
"""

import chromadb
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
        chroma_port: Optional[int] = None
    ):
        """
        Initialize ChromaDB connection.
        
        Args:
            chroma_host: ChromaDB host (optional, uses config default)
            chroma_port: ChromaDB port (optional, uses config default)
        """
        # Get configuration from centralized config utility
        if chroma_host is None or chroma_port is None:
            chroma_host, chroma_port = get_chroma_connection_params()
        
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        
        # Create HTTP client
        self.client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    
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
    
    def truncate_collection(self, name: str) -> int:
        """
        Empty a collection (delete all entries but keep collection).
        
        This is more efficient than delete + recreate when you want to
        preserve the collection structure.
        
        Args:
            name: Collection name
            
        Returns:
            Number of entries deleted
            
        Raises:
            Exception: If collection doesn't exist
        """
        collection = self.get_collection(name)
        count_before = collection.count()
        
        if count_before == 0:
            return 0
        
        # Get all IDs and delete them
        # ChromaDB v2 API requires specific IDs, not an empty where clause
        result = collection.get(limit=count_before)
        if result and result['ids']:
            collection.delete(ids=result['ids'])
        
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
        return f"ChromaDBConnector(host={self.chroma_host}, port={self.chroma_port})"
