#!/usr/bin/env python3
"""
CLI interface for table transformation system.

Provides command-line interface for transforming markdown tables to JSON.
"""

import argparse
import sys
from pathlib import Path

from src.transformers.table_transformer import TableTransformer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Transform complex markdown tables to JSON using OpenAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Estimate cost (dry run)
  python -m src.transformers.cli document.md tables.md --dry-run

  # Transform tables
  python -m src.transformers.cli document.md tables.md

  # Custom settings
  python -m src.transformers.cli document.md tables.md \\
    --model gpt-4 --delay 2.0 --cost-limit 10.0
        """
    )
    
    # Required arguments
    parser.add_argument(
        "markdown_file",
        help="Path to markdown file to transform"
    )
    
    parser.add_argument(
        "table_list_file",
        help="Path to complex table list file"
    )
    
    # Optional arguments
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate cost without executing transformation"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between API calls in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--cost-limit",
        type=float,
        default=5.0,
        help="Maximum cost in USD (default: 5.0)"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Output directory (default: data/markdown/docling/good_pdfs/)"
    )
    
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (if not set in .env)"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate files exist
    markdown_path = Path(args.markdown_file)
    table_list_path = Path(args.table_list_file)
    
    if not markdown_path.exists():
        print(f"❌ Error: Markdown file not found: {markdown_path}")
        sys.exit(1)
    
    if not table_list_path.exists():
        print(f"❌ Error: Table list file not found: {table_list_path}")
        sys.exit(1)
    
    # Execute transformation
    try:
        transformer = TableTransformer(
            markdown_file=args.markdown_file,
            table_list_file=args.table_list_file,
            output_dir=args.output_dir,
            api_key=args.api_key,
            model=args.model,
            delay_seconds=args.delay,
            cost_limit_usd=args.cost_limit
        )
        
        report = transformer.transform(dry_run=args.dry_run)
        
        # Display success message
        if args.dry_run:
            print(f"\n✅ Dry run complete")
            print(f"Estimated cost: ${report.total_cost_usd:.4f}")
            print(f"Tables to transform: {report.total_tables}")
        else:
            print(f"\n✅ Transformation complete!")
            print(f"Processed {report.successful}/{report.total_tables} tables successfully")
            print(f"Total cost: ${report.total_cost_usd:.4f}")
            
            if report.failed > 0:
                print(f"\n⚠️  {report.failed} table(s) failed to transform")
                print("See report above for details")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Transformation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
