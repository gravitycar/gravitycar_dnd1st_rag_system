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

# Use src imports for local development
from src.converters.pdf_converter import convert_pdfs_to_markdown, inspect_markdown_sample
from src.chunkers.monster_encyclopedia import MonsterEncyclopediaChunker
from src.chunkers.players_handbook import PlayersHandbookChunker
from src.chunkers.recursive_chunker import RecursiveChunker
from src.embedders.embedder_orchestrator import EmbedderOrchestrator
from src.query.docling_query import DnDRAG
from src.utils.chromadb_connector import ChromaDBConnector
from src.preprocessors.heading_organizer import HeadingOrganizer
from src.transformers.table_transformer import TableTransformer


def cmd_convert(args):
    """Convert PDF to markdown."""
    print(f"Converting PDF: {args.pdf_file}")
    # TODO: Implement PDFConverter call
    print("PDF conversion not yet integrated into main.py")


def cmd_organize(args):
    """Organize heading hierarchy in markdown file."""
    markdown_file = Path(args.markdown_file)
    
    if not markdown_file.exists():
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    # Auto-detect TOC file if not specified
    toc_file = args.toc
    if not toc_file:
        # Look for TOC in data/source_pdfs/notes/
        possible_toc = Path('data/source_pdfs/notes/Players_Handbook_TOC.txt')
        if possible_toc.exists():
            toc_file = str(possible_toc)
        else:
            print("Error: Could not auto-detect TOC file. Please specify with --toc")
            sys.exit(1)
    
    organizer = HeadingOrganizer(
        markdown_file=str(markdown_file),
        toc_file=toc_file,
        output_file=args.output,
        create_backup=not args.no_backup,
        debug=args.debug
    )
    organizer.process()


def cmd_chunk(args):
    """Chunk markdown documents."""
    markdown_file = Path(args.markdown_file)
    
    if not markdown_file.exists():
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    # Generate output filename
    output_file = Path("data/chunks") / f"chunks_{markdown_file.stem}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Determine chunker type
    if args.type == "monster" or "monster" in markdown_file.name.lower():
        print(f"Chunking Monster Manual: {markdown_file}")
        chunker = MonsterEncyclopediaChunker()
        chunks = chunker.chunk_markdown_file(str(markdown_file))
        
        # Save chunks
        import json
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created {len(chunks)} chunks: {output_file}")
        
    elif args.type == "player" or "player" in markdown_file.name.lower() or "dungeon_master" in markdown_file.name.lower():
        print(f"Chunking rulebook with RecursiveChunker: {markdown_file}")
        
        # Use RecursiveChunker for player's handbook and DM guide
        chunker = RecursiveChunker(
            markdown_file=str(markdown_file),
            output_file=str(output_file),
            max_chunk_size=2000,
            report=True  # Show chunking statistics
        )
        
        # Process and save (RecursiveChunker handles its own output)
        chunks = chunker.process()
        
        print(f"✅ Created {len(chunks)} chunks: {output_file}")
    else:
        print(f"Error: Could not determine document type for {markdown_file}")
        print("Use --type monster or --type player, or ensure filename contains 'monster' or 'player'")
        sys.exit(1)


def cmd_embed(args):
    """Embed chunks into ChromaDB."""
    chunks_file = Path(args.chunks_file)
    
    if not chunks_file.exists():
        print(f"Error: File not found: {chunks_file}")
        sys.exit(1)
    
    print(f"Embedding chunks: {chunks_file} → {args.collection_name}")
    
    # Use orchestrator for automatic format detection
    orchestrator = EmbedderOrchestrator()
    embedder = orchestrator.process(
        str(chunks_file),
        collection_name=args.collection_name
    )
    
    # Run test queries if requested
    if args.test:
        orchestrator.run_test_queries(embedder)


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
    
    # Use ChromaDB connector to truncate collection
    chroma = ChromaDBConnector()
    
    try:
        count_deleted = chroma.truncate_collection(args.collection_name)
        print(f"✅ Truncated collection '{args.collection_name}' ({count_deleted} entries deleted)")
    except Exception as e:
        print(f"Error: Could not truncate collection '{args.collection_name}'")
        print(f"Details: {e}")
        sys.exit(1)


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
    chroma = ChromaDBConnector()
    
    collections = chroma.list_collections()
    
    if not collections:
        print("No collections found.")
        return
    
    print(f"\nFound {len(collections)} collection(s):\n")
    print(f"{'Name':<30} {'Count':<8} {'ID'}")
    print("=" * 70)
    
    for collection in collections:
        count = collection.count()


def cmd_transform_tables(args):
    """Transform complex markdown tables to JSON using OpenAI."""
    try:
        transformer = TableTransformer(
            markdown_file=args.markdown_file,
            table_list_file=args.table_list,
            output_dir=args.output_dir,
            api_key=args.api_key,
            model=args.model,
            delay_seconds=args.delay,
            cost_limit_usd=args.cost_limit
        )
        
        report = transformer.transform(dry_run=args.dry_run)
        
        if args.dry_run:
            print(f"\n✅ Dry run complete")
            print(f"Estimated cost: ${report.total_cost_usd:.4f}")
        else:
            print(f"\n✅ Transformation complete!")
            print(f"Processed {report.successful}/{report.total_tables} tables successfully")
            print(f"Cost: ${report.total_cost_usd:.4f}")
            
            if report.failed > 0:
                print(f"\n⚠️  {report.failed} table(s) failed")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Transformation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


def cmd_list_collections(args):
    """List all ChromaDB collections."""
    chroma = ChromaDBConnector()
    
    collections = chroma.list_collections()
    
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
  python main.py convert data/source_pdfs/Players_Handbook.pdf
  python main.py organize data/markdown/Players_Handbook_(1e).md
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
    
    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize heading hierarchy')
    organize_parser.add_argument('markdown_file', help='Markdown file to organize')
    organize_parser.add_argument('--toc', default=None, help='Path to Table of Contents file')
    organize_parser.add_argument('--output', default=None, help='Output file path')
    organize_parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    organize_parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
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
    
    # Transform tables command
    transform_parser = subparsers.add_parser('transform-tables', help='Transform complex markdown tables to JSON')
    transform_parser.add_argument('markdown_file', help='Markdown file to transform')
    transform_parser.add_argument('table_list', help='Table list file')
    transform_parser.add_argument('--dry-run', action='store_true', help='Estimate cost without executing')
    transform_parser.add_argument('--model', default='gpt-4o-mini', help='OpenAI model (default: gpt-4o-mini)')
    transform_parser.add_argument('--delay', type=float, default=1.0, help='Delay between API calls (default: 1.0)')
    transform_parser.add_argument('--cost-limit', type=float, default=5.0, help='Maximum cost in USD (default: 5.0)')
    transform_parser.add_argument('--output-dir', help='Output directory')
    transform_parser.add_argument('--api-key', help='OpenAI API key (if not in .env)')
    
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
        'organize': cmd_organize,
        'chunk': cmd_chunk,
        'embed': cmd_embed,
        'truncate': cmd_truncate,
        'transform-tables': cmd_transform_tables,
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