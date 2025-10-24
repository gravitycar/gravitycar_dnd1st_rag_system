"""
GravityCar D&D 1st Edition RAG System

A production-ready RAG system for querying Advanced Dungeons & Dragons 1st Edition rulebooks.
Features intelligent chunking, entity-aware retrieval, and adaptive semantic filtering.
"""

__version__ = "1.0.0"
__author__ = "GravityCar"

# Main classes available for library use
from .query.docling_query import DnDRAG
from .embedders.embedder_orchestrator import EmbedderOrchestrator
from .embedders.base_embedder import Embedder
from .embedders.monster_book_embedder import MonsterBookEmbedder
from .embedders.rule_book_embedder import RuleBookEmbedder
from .chunkers.monster_encyclopedia import MonsterEncyclopediaChunker
from .chunkers.players_handbook import PlayersHandbookChunker
from .utils.config import get_chroma_connection_params, get_openai_api_key, get_default_collection_name
from .utils.chromadb_connector import ChromaDBConnector

__all__ = [
    "DnDRAG",
    "EmbedderOrchestrator",
    "Embedder",
    "MonsterBookEmbedder",
    "RuleBookEmbedder",
    "MonsterEncyclopediaChunker",
    "PlayersHandbookChunker",
    "ChromaDBConnector",
    "get_chroma_connection_params",
    "get_openai_api_key",
    "get_default_collection_name",
]