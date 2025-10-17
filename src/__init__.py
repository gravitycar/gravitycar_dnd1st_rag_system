"""
GravityCar D&D 1st Edition RAG System

A production-ready RAG system for querying Advanced Dungeons & Dragons 1st Edition rulebooks.
Features intelligent chunking, entity-aware retrieval, and adaptive semantic filtering.
"""

__version__ = "1.0.0"
__author__ = "GravityCar"

# Main classes available for library use
from .query.docling_query import DnDRAG
from .embedders.docling_embedder import DoclingEmbedder
from .chunkers.monster_encyclopedia import MonsterEncyclopediaChunker
from .chunkers.players_handbook import PlayersHandbookChunker
from .utils.config import get_chroma_connection_params, get_openai_api_key, get_default_collection_name

__all__ = [
    "DnDRAG",
    "DoclingEmbedder", 
    "MonsterEncyclopediaChunker",
    "PlayersHandbookChunker",
    "get_chroma_connection_params",
    "get_openai_api_key",
    "get_default_collection_name",
]