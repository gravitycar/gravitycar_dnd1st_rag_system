#!/usr/bin/env python3
"""
D&D 1st Edition RAG System - Main Entry Point

This is the single entry point for all D&D RAG system operations:
- Convert PDFs to markdown
- Chunk documents 
- Embed chunks into ChromaDB
- Query collections

Usage:
    python main.py convert <pdf_file>
    python main.py chunk <markdown_file> [--type monster|player]
    python main.py embed <chunks_file> <collection_name>
    python main.py query <collection_name> <question>
    python main.py list-collections
"""

import argparse
import sys
from pathlib import Path

# Use package imports instead of direct imports
from gravitycar_dnd1st_rag_system.converters.pdf_converter import convert_pdfs_to_markdown, inspect_markdown_sample
from gravitycar_dnd1st_rag_system.chunkers.monster_encyclopedia import MonsterEncyclopediaChunker
from gravitycar_dnd1st_rag_system.chunkers.players_handbook import PlayersHandbookChunker
from gravitycar_dnd1st_rag_system.embedders.docling_embedder import DoclingEmbedder
from gravitycar_dnd1st_rag_system.query.docling_query import DnDRAG
from gravitycar_dnd1st_rag_system.utils.config import get_chroma_connection_params


def cmd_convert(args):
    """Convert PDF to markdown."""
    print(f"Converting PDF: {args.pdf_file}")
    # TODO: Implement PDFConverter call
    print("PDF conversion not yet integrated into main.py")


def cmd_chunk(args):
    """Chunk markdown documents."""
    markdown_file = Path(args.markdown_file)
    
    if not markdown_file.exists():
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    # Determine chunker type
    if args.type == "monster" or "monster" in markdown_file.name.lower():
        print(f"Chunking Monster Manual: {markdown_file}")
        chunker = MonsterEncyclopediaChunker()
        chunks = chunker.chunk_markdown_file(str(markdown_file))
    elif args.type == "player" or "player" in markdown_file.name.lower():
        print(f"Chunking Player's Handbook: {markdown_file}")
        chunker = PlayersHandbookChunker()
        chunks = chunker.chunk_markdown_file(str(markdown_file))
    else:
        print(f"Error: Could not determine document type for {markdown_file}")
        print("Use --type monster or --type player, or ensure filename contains 'monster' or 'player'")
        sys.exit(1)
    
    # Generate output filename
    output_file = Path("data/chunks") / f"chunks_{markdown_file.stem}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save chunks
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created {len(chunks)} chunks: {output_file}")


def cmd_embed(args):
    """Embed chunks into ChromaDB."""
    chunks_file = Path(args.chunks_file)
    
    if not chunks_file.exists():
        print(f"Error: File not found: {chunks_file}")
        sys.exit(1)
    
    print(f"Embedding chunks: {chunks_file} → {args.collection_name}")
    
    embedder = DoclingEmbedder(
        chunks_file=str(chunks_file),
        collection_name=args.collection_name
    )
    
    chunks = embedder.load_chunks()
    embedder.embed_chunks(chunks)
    
    # Run test query if requested
    if args.test:
        if "monster" in args.collection_name.lower():
            test_query = "Tell me about demons"
        else:
            test_query = "What are the six character abilities?"
        
        embedder.test_query(test_query)


def cmd_truncate(args):
    """Truncate (empty) a ChromaDB collection."""
    # Confirm deletion unless --confirm flag is used
    if not args.confirm:
        response = input(
            f"\n⚠️  WARNING: This will delete ALL entries from collection '{args.collection_name}'.\n"
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
        embedder = DoclingEmbedder(
            chunks_file=temp_file,
            collection_name=args.collection_name
        )
        embedder.truncate_collection()
    finally:
        # Clean up temp file
        import os
        os.unlink(temp_file)


def cmd_query(args):
    """Query a ChromaDB collection."""
    print(f"Querying collection: {args.collection_name}")

    
    rag = DnDRAG(collection_name=args.collection_name, model=args.model)
    
    if args.test:
        # Run test questions
        if "player" in args.collection_name.lower() or "handbook" in args.collection_name.lower():
            test_questions = [
                "How many experience points does a fighter need to reach 9th level?",
                "What are the unique abilities that only thieves have?",
                "What are the six character abilities in D&D?"
            ]
        else:  # Monster manual
            test_questions = [
                "Tell me about owlbears and their abilities",
                "What is the difference between a red dragon and a white dragon?",
                "What are lizard men and how dangerous are they?"
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


def cmd_list_collections(args):
    """List all ChromaDB collections."""
    import chromadb
    
    chroma_host, chroma_port = get_chroma_connection_params()
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    
    collections = client.list_collections()
    
    if not collections:
        print("No collections found.")
        return
    
    print(f"\nFound {len(collections)} collection(s):\n")
    print(f"{'Name':<30} {'Count':<8} {'ID'}")
    print("=" * 70)
    
    for collection in collections:
        count = collection.count()
        print(f"{collection.name:<30} {count:<8} {collection.id}")


def main():
    parser = argparse.ArgumentParser(
        description="D&D 1st Edition RAG System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py chunk data/markdown/Monster_Manual.md --type monster
  python main.py embed data/chunks/chunks_Monster_Manual.json dnd_monster_manual_openai
  python main.py query dnd_monster_manual_openai "What is a beholder?"
  python main.py query dnd_monster_manual_openai --test
  python main.py list-collections
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert PDF to markdown')
    convert_parser.add_argument('pdf_file', help='PDF file to convert')
    
    # Chunk command
    chunk_parser = subparsers.add_parser('chunk', help='Chunk markdown documents')
    chunk_parser.add_argument('markdown_file', help='Markdown file to chunk')
    chunk_parser.add_argument('--type', choices=['monster', 'player'], 
                             help='Document type (auto-detected if not specified)')
    
    # Embed command
    embed_parser = subparsers.add_parser('embed', help='Embed chunks into ChromaDB')
    embed_parser.add_argument('chunks_file', help='JSON file containing chunks')
    embed_parser.add_argument('collection_name', help='ChromaDB collection name')
    embed_parser.add_argument('--test', action='store_true', help='Run test query after embedding')
    
    # Truncate command
    truncate_parser = subparsers.add_parser('truncate', help='Truncate (empty) a ChromaDB collection')
    truncate_parser.add_argument('collection_name', help='ChromaDB collection name')
    truncate_parser.add_argument('--confirm', action='store_true', 
                                help='Confirm truncation without prompting')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query ChromaDB collection')
    query_parser.add_argument('collection_name', help='ChromaDB collection name')
    query_parser.add_argument('question', nargs='?', help='Question to ask (interactive mode if not provided)')
    query_parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model (default: gpt-4o-mini)')
    query_parser.add_argument('-k', type=int, default=15, help='Max chunks to retrieve (default: 15)')
    query_parser.add_argument('--distance-threshold', type=float, default=0.4, 
                             help='Distance threshold (default: 0.4)')
    query_parser.add_argument('--show-context', action='store_true', help='Show context sent to LLM')
    query_parser.add_argument('--debug', action='store_true', help='Show debug info')
    query_parser.add_argument('--test', action='store_true', help='Run test questions')
    
    # List collections command
    list_parser = subparsers.add_parser('list-collections', help='List all ChromaDB collections')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to appropriate command handler
    command_handlers = {
        'convert': cmd_convert,
        'chunk': cmd_chunk,
        'embed': cmd_embed,
        'truncate': cmd_truncate,
        'query': cmd_query,
        'list-collections': cmd_list_collections,
    }
    
    try:
        command_handlers[args.command](args)
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()