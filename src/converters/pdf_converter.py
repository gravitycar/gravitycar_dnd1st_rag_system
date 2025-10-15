#!/usr/bin/env python3
"""
Convert D&D PDFs to Markdown using Docling

This script uses Docling to intelligently parse PDF files and convert them
to clean, well-structured markdown files.

Docling advantages:
- Preserves document structure
- Properly formats tables
- Maintains reading order
- Better OCR if needed

Usage:
    python convert_pdfs_to_markdown.py
"""

import os
os.environ["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/5/tessdata"
import torch
torch.backends.nnpack.set_flags(False)

from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.backend.pdf_backend import PdfPageBackend
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions, TesseractOcrOptions, TableFormerMode
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend


import time

def print_intro():
    print("=" * 60)
    print("D&D PDF to Markdown Converter (using Docling)")
    print("=" * 60)
    print()

def get_pdf_pipeline():
    # Set up pipeline options for better PDF processing
    pipeline_options = PdfPipelineOptions(do_ocr=False)
    pipeline_options.do_ocr = False  # Enable OCR if PDFs are scanned
    pipeline_options.do_table_structure = True  # Extract table structure
    pipeline_options.ocr_options = EasyOcrOptions(force_full_page_ocr=False)
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    return pipeline_options

def get_docling_converter(pipeline_options):
    # Initialize converter
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=PyPdfiumDocumentBackend
                )
        }
    )
    return converter

def get_path(path_str: str, create_if_not_exists: bool) -> Path:
    """Helper to get a Path object and ensure it exists."""
    path = Path(path_str)
    if not path.exists():
        if create_if_not_exists:
            print(f"Creating directory: {path_str}")
            path.mkdir(parents=True, exist_ok=True)
        else:
            raise FileNotFoundError(f"Directory not found: {path_str}")
    return path

def get_pdf_file_paths(pdf_directory: Path) -> list[Path]:
    """Helper to get a list of PDF file paths in a directory."""
    pdf_files = list(pdf_directory.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ Error: No PDF files found in {pdf_directory.absolute()}")
        return []
    
    print(f"Found {len(pdf_files)} PDF files:")
    return pdf_files

def convert_pdfs_to_markdown(
    pdf_directory: str = "/home/mike/projects/dnd1st/pdfs",
    output_directory: str = "/home/mike/projects/dnd1st/md",
    force_ocr: bool = True
):
    """
    Convert all PDFs in a directory to markdown files.
    
    Args:
        pdf_directory: Path to directory containing PDF files
        output_directory: Path to output directory for markdown files
        force_ocr: Whether to force OCR for all PDFs (slower but better for scans)
    """

    print_intro()

    try:
        # Create output directory
        output_path = get_path(output_directory, create_if_not_exists=True)
        # Find all PDF files
        pdf_path = get_path(pdf_directory, create_if_not_exists=False)
    except FileNotFoundError as e:  # Catch directory not found errors
        print(f"Bad path: ❌ Error: {e}") 
        return

    pdf_files = get_pdf_file_paths(pdf_path)
    
    # Configure Docling
    print("Initializing Docling converter...")
    
    # Set up pipeline options for better PDF processing
    pipeline_options = get_pdf_pipeline()


    # Initialize converter
    converter = get_docling_converter(pipeline_options)
    
    print("✓ Docling converter ready")
    print()
    
    # Convert each PDF
    results = []
    total_start = time.time()
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            # Convert PDF
            print("  Converting PDF...")
            result = converter.convert(str(pdf_file), page_range=(6, 104))
            doc = result.document
            
            # Export to markdown
            print("  Exporting to markdown...")
            markdown_content = doc.export_to_markdown()
            
            # Save markdown file
            output_file = output_path / f"{pdf_file.stem}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            elapsed = time.time() - start_time
            
            # Get statistics
            char_count = len(markdown_content)
            line_count = markdown_content.count('\n')
            
            print(f"  ✓ Converted in {elapsed:.1f}s")
            print(f"  Output: {output_file.name}")
            print(f"  Size: {char_count:,} characters, {line_count:,} lines")
            
            results.append({
                'filename': pdf_file.name,
                'success': True,
                'output_file': str(output_file),
                'chars': char_count,
                'lines': line_count,
                'time': elapsed
            })
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ Error: {str(e)}")
            
            results.append({
                'filename': pdf_file.name,
                'success': False,
                'error': str(e),
                'time': elapsed
            })
        
        print()
    
    # Summary
    total_elapsed = time.time() - total_start
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print("=" * 60)
    print("Conversion Summary")
    print("=" * 60)
    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total time: {total_elapsed:.1f}s")
    print()
    
    if successful > 0:
        print("Successful conversions:")
        for result in results:
            if result['success']:
                print(f"  ✓ {result['filename']}")
                print(f"    → {result['chars']:,} chars, {result['time']:.1f}s")
        print()
    
    if failed > 0:
        print("Failed conversions:")
        for result in results:
            if not result['success']:
                print(f"  ✗ {result['filename']}")
                print(f"    Error: {result['error']}")
        print()
    
    print("=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Inspect markdown files in the 'data/markdown/' directory")
    print("2. Check if tables are properly formatted")
    print("3. Verify headers are structured correctly")
    print("4. Run: python src/chunkers/monster_encyclopedia.py")
    print()


def inspect_markdown_sample(markdown_dir: str = "data/markdown"):
    """
    Show a sample of the first markdown file for quick inspection.
    """
    markdown_path = Path(markdown_dir)
    
    if not markdown_path.exists():
        return
    
    md_files = list(markdown_path.glob("*.md"))
    
    if not md_files:
        return
    
    print("=" * 60)
    print("Sample Output (first 50 lines)")
    print("=" * 60)
    
    sample_file = md_files[0]
    print(f"File: {sample_file.name}\n")
    
    with open(sample_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()[:50]
        print(''.join(lines))
    
    if len(lines) == 50:
        print("\n[... file continues ...]")
    
    print()


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert D&D PDFs to Markdown using Docling")
    parser.add_argument(
        '--pdf-dir',
        default="/home/mike/projects/dnd1st/pdfs",
        help="Directory containing PDF files"
    )
    parser.add_argument(
        '--output-dir',
        default="md",
        help="Directory for markdown output"
    )
    parser.add_argument(
        '--force-ocr',
        action='store_true',
        help="Force OCR for all PDFs (slower, use if PDFs are scanned images)"
    )
    parser.add_argument(
        '--sample',
        action='store_true',
        help="Show sample of converted markdown"
    )
    
    args = parser.parse_args()
    
    # Run conversion
    convert_pdfs_to_markdown(
        pdf_directory=args.pdf_dir,
        output_directory=args.output_dir,
        force_ocr=args.force_ocr
    )
    
    # Show sample if requested
    if args.sample:
        inspect_markdown_sample(args.output_dir)


if __name__ == "__main__":
    main()
