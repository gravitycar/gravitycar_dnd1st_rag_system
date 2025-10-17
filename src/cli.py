#!/usr/bin/env python3
"""
Command-line interface for the D&D 1st Edition RAG System.

This module provides CLI entry points that can be used directly or installed via pip.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Import package modules using proper relative imports
from .converters.pdf_converter import convert_pdfs_to_markdown, inspect_markdown_sample
from .chunkers.monster_encyclopedia import MonsterEncyclopediaChunker
from .chunkers.players_handbook import PlayersHandbookChunker
from .embedders.docling_embedder import DoclingEmbedder
from .query.docling_query import DnDRAG
from .utils.config import get_chroma_connection_params, get_default_collection_name


def convert_main():
    """Entry point for dnd-convert command."""
    parser = argparse.ArgumentParser(description="Convert PDF to markdown")
    parser.add_argument('pdf_file', help='PDF file to convert')
    parser.add_argument('--output-dir', default='data/markdown', 
                       help='Output directory (default: data/markdown)')
    parser.add_argument('--force-ocr', action='store_true',
                       help='Force OCR for all PDFs (slower, use if PDFs are scanned images)')
    parser.add_argument('--sample', action='store_true',
                       help='Show sample of converted markdown')
    
    args = parser.parse_args()
    
    # Create a directory containing just the specified PDF file for conversion
    pdf_path = Path(args.pdf_file)
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Run conversion
    convert_pdfs_to_markdown(
        pdf_directory=str(pdf_path.parent),
        output_directory=args.output_dir,
        force_ocr=args.force_ocr
    )
    
    # Show sample if requested  
    if args.sample:
        inspect_markdown_sample(args.output_dir)
    
    print(f"✅ PDF conversion complete: {args.output_dir}")


def chunk_main():
    """Entry point for dnd-chunk command."""
    parser = argparse.ArgumentParser(description="Chunk markdown documents")
    parser.add_argument('markdown_file', help='Markdown file to chunk')
    parser.add_argument('--type', choices=['monster', 'player'], 
                       help='Document type (auto-detected if not specified)')
    parser.add_argument('--output-dir', default='data/chunks',
                       help='Output directory (default: data/chunks)')
    
    args = parser.parse_args()
    
    markdown_file = Path(args.markdown_file)
    
    if not markdown_file.exists():
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    # Determine chunker type and output file
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"chunks_{markdown_file.stem}.json"
    
    if args.type == "monster" or "monster" in markdown_file.name.lower():
        print(f"Chunking Monster Manual: {markdown_file}")
        chunker = MonsterEncyclopediaChunker(str(markdown_file), str(output_file))
        chunker.process()
    elif args.type == "player" or "player" in markdown_file.name.lower():
        print(f"Chunking Player's Handbook: {markdown_file}")
        chunker = PlayersHandbookChunker(str(markdown_file), str(output_file))
        chunker.process()
    else:
        print(f"Error: Could not determine document type for {markdown_file}")
        print("Use --type monster or --type player, or ensure filename contains 'monster' or 'player'")
        sys.exit(1)
    
    print(f"✅ Chunking complete: {output_file}")


def embed_main():
    """Entry point for dnd-embed command."""
    parser = argparse.ArgumentParser(description="Embed chunks into ChromaDB")
    parser.add_argument('chunks_file', help='JSON file containing chunks')
    parser.add_argument('--test', action='store_true', 
                       help='Run test query after embedding')
    parser.add_argument('--test-query', help='Custom test query')
    
    args = parser.parse_args()
    
    chunks_file = Path(args.chunks_file)
    
    if not chunks_file.exists():
        print(f"Error: File not found: {chunks_file}")
        sys.exit(1)
    
    print(f"Embedding chunks: {chunks_file} → unified collection")
    
    embedder = DoclingEmbedder(
        chunks_file=str(chunks_file)
    )
    
    chunks = embedder.load_chunks()
    embedder.embed_chunks(chunks)
    
    # Run test query if requested
    if args.test or args.test_query:
        test_query = args.test_query
        if not test_query:
            # Use unified collection tests
            test_query = "What are the six character abilities?"
        
        embedder.test_query(test_query)


def truncate_main():
    """Entry point for dnd-truncate command."""
    parser = argparse.ArgumentParser(
        description="Truncate (empty) the ChromaDB collection without deleting it"
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirm truncation without prompting'
    )
    
    args = parser.parse_args()
    
    # Get collection name from config
    try:
        from .utils.config import get_default_collection_name
        collection_name = get_default_collection_name()
    except Exception:
        collection_name = "adnd_1e"
    
    # Confirm deletion unless --confirm flag is used
    if not args.confirm:
        response = input(
            f"\n⚠️  WARNING: This will delete ALL entries from collection '{collection_name}'.\n"
            f"This action cannot be undone. Continue? (yes/no): "
        ).strip().lower()
        
        if response not in ['yes', 'y']:
            print("Truncation cancelled.")
            sys.exit(0)
    
    # Create a dummy embedder just to get access to the collection
    # We need a chunks file argument but won't use it for truncation
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('[]')
        temp_file = f.name
    
    try:
        embedder = DoclingEmbedder(chunks_file=temp_file)
        embedder.truncate_collection()
    finally:
        # Clean up temp file
        import os
        os.unlink(temp_file)


def query_main():
    """Entry point for dnd-query command."""
    parser = argparse.ArgumentParser(description="Query ChromaDB collection")
    parser.add_argument('question', nargs='?', 
                       help='Question to ask (interactive mode if not provided)')
    parser.add_argument('--model', default='gpt-4o-mini', 
                       help='OpenAI model (default: gpt-4o-mini)')
    parser.add_argument('-k', type=int, default=15, 
                       help='Max chunks to retrieve (default: 15)')
    parser.add_argument('--distance-threshold', type=float, default=0.4, 
                       help='Distance threshold (default: 0.4)')
    parser.add_argument('--show-context', action='store_true', 
                       help='Show context sent to LLM')
    parser.add_argument('--debug', action='store_true', help='Show debug info')
    parser.add_argument('--test', action='store_true', help='Run test questions')
    
    args = parser.parse_args()
    
    print(f"Querying unified D&D 1st Edition collection")
    
    rag = DnDRAG(model=args.model)
    
    if args.test:
        # Run unified test questions
        test_questions = [
            "How many experience points does a fighter need to reach 9th level?",
            "Tell me about owlbears and their abilities",
            "What is the difference between a red dragon and a white dragon?",
            "What are the six character abilities in D&D?"
        ]
        
        for question in test_questions:
            print(f"\n{'='*60}")
            print(f"TEST: {question}")
            print('='*60)
            rag.query(question, k=args.k, distance_threshold=args.distance_threshold, 
                     show_context=args.show_context, debug=args.debug)
    else:
        # Single query or interactive mode
        if args.question:
            rag.query(args.question, k=args.k, distance_threshold=args.distance_threshold,
                     show_context=args.show_context, debug=args.debug)
        else:
            # Interactive mode
            print("\nInteractive mode - enter questions (or 'quit' to exit)")
            while True:
                try:
                    question = input("\nQuestion: ").strip()
                    if not question:
                        continue
                    if question.lower() in ['quit', 'exit', 'q']:
                        print("Goodbye!")
                        break
                    rag.query(question, k=args.k, distance_threshold=args.distance_threshold,
                             show_context=args.show_context, debug=args.debug)
                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break


def list_main():
    """Entry point for dnd-list command."""
    parser = argparse.ArgumentParser(description="List ChromaDB collections")
    parser.add_argument('--detailed', action='store_true', 
                       help='Show detailed collection information')
    
    args = parser.parse_args()
    
    import chromadb
    
    chroma_host, chroma_port = get_chroma_connection_params()
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    
    collections = client.list_collections()
    
    if not collections:
        print("No collections found.")
        return
    
    print(f"\nFound {len(collections)} collection(s):\n")
    
    if args.detailed:
        for collection in collections:
            count = collection.count()
            print(f"Collection: {collection.name}")
            print(f"  Documents: {count}")
            print(f"  ID: {collection.id}")
            if hasattr(collection, 'metadata') and collection.metadata:
                print(f"  Metadata: {collection.metadata}")
            print()
    else:
        print(f"{'Name':<30} {'Count':<8} {'ID'}")
        print("=" * 70)
        
        for collection in collections:
            count = collection.count()
            print(f"{collection.name:<30} {count:<8} {collection.id}")


def main():
    """Main entry point for dnd-rag command (unified interface)."""
    parser = argparse.ArgumentParser(
        description="D&D 1st Edition RAG System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Commands:
  convert     Convert PDF to markdown
  chunk       Chunk markdown documents  
  embed       Embed chunks into ChromaDB
  query       Query ChromaDB collection
  list        List ChromaDB collections

Examples:
  dnd-rag chunk data/markdown/Monster_Manual.md --type monster
  dnd-rag embed data/chunks/chunks_Monster_Manual.json dnd_monster_manual_openai
  dnd-rag query dnd_monster_manual_openai "What is a beholder?"
  dnd-rag list --detailed

Individual Commands:
  dnd-chunk data/markdown/Monster_Manual.md --type monster
  dnd-embed data/chunks/chunks_Monster_Manual.json dnd_monster_manual_openai  
  dnd-query dnd_monster_manual_openai "What is a beholder?" --debug
  dnd-list --detailed
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert PDF to markdown')
    convert_parser.add_argument('pdf_file', help='PDF file to convert')
    convert_parser.add_argument('--output-dir', default='data/markdown', 
                               help='Output directory')
    
    # Chunk command  
    chunk_parser = subparsers.add_parser('chunk', help='Chunk markdown documents')
    chunk_parser.add_argument('markdown_file', help='Markdown file to chunk')
    chunk_parser.add_argument('--type', choices=['monster', 'player'], 
                             help='Document type')
    chunk_parser.add_argument('--output-dir', default='data/chunks',
                             help='Output directory')
    
    # Embed command
    embed_parser = subparsers.add_parser('embed', help='Embed chunks into ChromaDB')
    embed_parser.add_argument('chunks_file', help='JSON file containing chunks')
    embed_parser.add_argument('collection_name', help='ChromaDB collection name')
    embed_parser.add_argument('--test', action='store_true', help='Run test query')
    embed_parser.add_argument('--test-query', help='Custom test query')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query ChromaDB collection')
    query_parser.add_argument('collection_name', help='ChromaDB collection name')
    query_parser.add_argument('question', nargs='?', help='Question to ask')
    query_parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model')
    query_parser.add_argument('-k', type=int, default=15, help='Max chunks to retrieve')
    query_parser.add_argument('--distance-threshold', type=float, default=0.4, 
                             help='Distance threshold')
    query_parser.add_argument('--show-context', action='store_true', 
                             help='Show context sent to LLM')
    query_parser.add_argument('--debug', action='store_true', help='Show debug info')
    query_parser.add_argument('--test', action='store_true', help='Run test questions')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List ChromaDB collections')
    list_parser.add_argument('--detailed', action='store_true', 
                            help='Show detailed information')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to appropriate command handler
    if args.command == 'convert':
        convert_main()
    elif args.command == 'chunk':
        chunk_main()  
    elif args.command == 'embed':
        embed_main()
    elif args.command == 'query':
        query_main()
    elif args.command == 'list':
        list_main()


if __name__ == "__main__":
    main()