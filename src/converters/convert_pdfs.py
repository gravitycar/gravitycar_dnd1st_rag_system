#!/usr/bin/env python3
"""
Convert D&D PDFs to various formats using Docling

This script uses Docling to intelligently parse PDF files and convert them
to markdown, JSON, or HTML formats with configurable OCR and table handling.

Usage:
    python convert_pdfs.py --pdf=path/to/file.pdf
    python convert_pdfs.py --pdf=path/to/directory --format=json --pages=1-10
    python convert_pdfs.py --pdf=file.pdf --do_ocr=False --table_former_mode=FAST
"""

import os
os.environ["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/5/tessdata"
import torch
torch.backends.nnpack.set_flags(False)

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Tuple, Optional

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
    TableFormerMode
)
from docling.backend.docling_parse_v4_backend import DoclingParseV4DocumentBackend


class ConversionConfig:
    """Holds all configuration options for PDF conversion."""
    
    def __init__(
        self,
        pdf_path: str,
        output_format: str = "md",
        pages: str = "*",
        do_ocr: bool = True,
        do_table_structure: bool = True,
        force_full_page_ocr: bool = False,
        table_former_mode: str = "ACCURATE",
        do_cell_matching: bool = True
    ):
        self.pdf_path = Path(pdf_path)
        self.output_format = output_format.lower()
        self.pages = pages
        self.do_ocr = do_ocr
        self.do_table_structure = do_table_structure
        self.force_full_page_ocr = force_full_page_ocr
        self.table_former_mode = table_former_mode.upper()
        self.do_cell_matching = do_cell_matching
        
    def validate(self) -> None:
        """Validate configuration options."""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF path not found: {self.pdf_path}")
            
        if self.output_format not in ["md", "json", "html"]:
            raise ValueError(f"Unsupported format: {self.output_format}. Use 'md', 'json', or 'html'")
            
        if self.table_former_mode not in ["ACCURATE", "FAST"]:
            raise ValueError(f"Invalid table_former_mode: {self.table_former_mode}. Use 'ACCURATE' or 'FAST'")
    
    def get_page_range(self) -> Optional[Tuple[int, int]]:
        """
        Parse the pages argument into a tuple for Docling.
        
        Returns:
            None for all pages, or (start, end) tuple for specific range
        """
        if self.pages == "*":
            return None
            
        # Handle single page: "5"
        if self.pages.isdigit():
            page_num = int(self.pages)
            return (page_num, page_num)
            
        # Handle range: "5-10"
        if "-" in self.pages:
            parts = self.pages.split("-")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return (int(parts[0]), int(parts[1]))
                
        # Handle comma-separated: "1,3,5,7-10"
        # For simplicity, we'll just take the min and max
        if "," in self.pages:
            numbers = []
            for part in self.pages.split(","):
                part = part.strip()
                if part.isdigit():
                    numbers.append(int(part))
                elif "-" in part:
                    subparts = part.split("-")
                    if len(subparts) == 2 and subparts[0].isdigit() and subparts[1].isdigit():
                        numbers.extend(range(int(subparts[0]), int(subparts[1]) + 1))
            
            if numbers:
                return (min(numbers), max(numbers))
        
        raise ValueError(f"Invalid pages format: {self.pages}")
    
    def get_output_directory(self, base_dir: Path = Path("output")) -> Path:
        """
        Generate output directory path based on configuration.
        
        Returns:
            Path object for the output directory
        """
        # Normalize pages string for directory name
        pages_str = self.pages.replace(",", "_").replace("-", "_") if self.pages != "*" else "all"
        
        dir_path = base_dir / (
            f"format_{self.output_format}/"
            f"pages_{pages_str}/"
            f"do_ocr_{self.do_ocr}/"
            f"do_table_structure_{self.do_table_structure}/"
            f"force_full_page_ocr_{self.force_full_page_ocr}/"
            f"table_former_mode_{self.table_former_mode}/"
            f"do_cell_matching_{self.do_cell_matching}"
        )
        
        return dir_path
    
    def get_output_extension(self) -> str:
        """Get file extension for output format."""
        extensions = {
            "md": ".md",
            "json": ".json",
            "html": ".html"
        }
        return extensions[self.output_format]


def parse_arguments() -> ConversionConfig:
    """Parse command line arguments and return configuration."""
    parser = argparse.ArgumentParser(
        description="Convert D&D PDFs to various formats using Docling",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--pdf",
        required=True,
        help="Path to PDF file or directory containing PDF files"
    )
    
    parser.add_argument(
        "--format",
        default="md",
        choices=["md", "json", "html"],
        help="Output format: 'md' (markdown), 'json', or 'html'. Default: md"
    )
    
    parser.add_argument(
        "--pages",
        default="*",
        help="Pages to convert: single number, range (1-10), comma-separated (1,3,5), or * for all. Default: *"
    )
    
    parser.add_argument(
        "--do_ocr",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Enable OCR processing. Accepts True or False. Default: True"
    )
    
    parser.add_argument(
        "--do_table_structure",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Extract table structure. Accepts True or False. Default: True"
    )
    
    parser.add_argument(
        "--force_full_page_ocr",
        type=lambda x: x.lower() == "true",
        default=False,
        help="Force OCR on entire page. Accepts True or False. Default: False"
    )
    
    parser.add_argument(
        "--table_former_mode",
        default="ACCURATE",
        choices=["ACCURATE", "FAST"],
        help="Table extraction mode: ACCURATE or FAST. Default: ACCURATE"
    )
    
    parser.add_argument(
        "--do_cell_matching",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Enable table cell matching. Accepts True or False. Default: True"
    )
    
    args = parser.parse_args()
    
    config = ConversionConfig(
        pdf_path=args.pdf,
        output_format=args.format,
        pages=args.pages,
        do_ocr=args.do_ocr,
        do_table_structure=args.do_table_structure,
        force_full_page_ocr=args.force_full_page_ocr,
        table_former_mode=args.table_former_mode,
        do_cell_matching=args.do_cell_matching
    )
    
    return config


def create_pipeline_options(config: ConversionConfig) -> PdfPipelineOptions:
    """Create PDF pipeline options from configuration."""
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = config.do_ocr
    pipeline_options.do_table_structure = config.do_table_structure
    
    # Configure OCR options
    pipeline_options.ocr_options = EasyOcrOptions(
        force_full_page_ocr=config.force_full_page_ocr
    )
    
    # Configure table structure options
    if config.table_former_mode == "ACCURATE":
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    else:
        pipeline_options.table_structure_options.mode = TableFormerMode.FAST
    
    pipeline_options.table_structure_options.do_cell_matching = config.do_cell_matching
    
    return pipeline_options


def create_converter(pipeline_options: PdfPipelineOptions) -> DocumentConverter:
    """Create and configure Docling document converter."""
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
                backend=DoclingParseV4DocumentBackend
            )
        }
    )
    return converter


def get_pdf_files(path: Path) -> List[Path]:
    """
    Get list of PDF files from path (file or directory).
    
    Args:
        path: Path to PDF file or directory
        
    Returns:
        List of PDF file paths
    """
    if path.is_file():
        if path.suffix.lower() == ".pdf":
            return [path]
        else:
            raise ValueError(f"File is not a PDF: {path}")
    elif path.is_dir():
        pdf_files = list(path.glob("*.pdf"))
        if not pdf_files:
            raise FileNotFoundError(f"No PDF files found in directory: {path}")
        return pdf_files
    else:
        raise FileNotFoundError(f"Path does not exist: {path}")


def export_document(doc, output_format: str) -> str:
    """
    Export document to specified format.
    
    Args:
        doc: Docling document object
        output_format: Output format (md, json, html)
        
    Returns:
        Exported content as string
    """
    if output_format == "md":
        return doc.export_to_markdown()
    elif output_format == "json":
        # Export to dict then pretty-print JSON
        doc_dict = doc.export_to_dict()
        return json.dumps(doc_dict, indent=2, ensure_ascii=False)
    elif output_format == "html":
        return doc.export_to_html()
    else:
        raise ValueError(f"Unsupported format: {output_format}")


def save_output(content: str, output_path: Path) -> None:
    """Save content to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)


def print_configuration(config: ConversionConfig) -> None:
    """Print configuration summary."""
    print("=" * 70)
    print("PDF Conversion Configuration")
    print("=" * 70)
    print(f"PDF Path:             {config.pdf_path}")
    print(f"Output Format:        {config.output_format}")
    print(f"Pages:                {config.pages}")
    print(f"OCR Enabled:          {config.do_ocr}")
    print(f"Table Structure:      {config.do_table_structure}")
    print(f"Force Full Page OCR:  {config.force_full_page_ocr}")
    print(f"Table Former Mode:    {config.table_former_mode}")
    print(f"Cell Matching:        {config.do_cell_matching}")
    print("=" * 70)
    print()


def convert_single_pdf(
    pdf_file: Path,
    config: ConversionConfig,
    converter: DocumentConverter,
    output_dir: Path
) -> dict:
    """
    Convert a single PDF file.
    
    Args:
        pdf_file: Path to PDF file
        config: Conversion configuration
        converter: Docling converter instance
        output_dir: Output directory
        
    Returns:
        Dictionary with conversion results
    """
    start_time = time.time()
    
    try:
        print(f"  Converting PDF...")
        
        # Get page range
        page_range = config.get_page_range()
        
        # Convert PDF
        if page_range:
            result = converter.convert(str(pdf_file), page_range=page_range)
        else:
            result = converter.convert(str(pdf_file))
        
        doc = result.document
        
        # Export to specified format
        print(f"  Exporting to {config.output_format}...")
        content = export_document(doc, config.output_format)
        
        # Save output
        output_file = output_dir / f"{pdf_file.stem}{config.get_output_extension()}"
        save_output(content, output_file)
        
        elapsed = time.time() - start_time
        
        # Get statistics
        char_count = len(content)
        line_count = content.count('\n')
        
        print(f"  ✓ Converted in {elapsed:.1f}s")
        print(f"  Output: {output_file}")
        print(f"  Size: {char_count:,} characters, {line_count:,} lines")
        
        return {
            'filename': pdf_file.name,
            'success': True,
            'output_file': str(output_file),
            'chars': char_count,
            'lines': line_count,
            'time': elapsed
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ Error: {str(e)}")
        
        return {
            'filename': pdf_file.name,
            'success': False,
            'error': str(e),
            'time': elapsed
        }


def print_summary(results: List[dict], total_time: float) -> None:
    """Print conversion summary."""
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print()
    print("=" * 70)
    print("Conversion Summary")
    print("=" * 70)
    print(f"Total files:   {len(results)}")
    print(f"Successful:    {successful}")
    print(f"Failed:        {failed}")
    print(f"Total time:    {total_time:.1f}s")
    print()
    
    if successful > 0:
        print("Successful conversions:")
        for result in results:
            if result['success']:
                print(f"  ✓ {result['filename']}")
                print(f"    → {result['chars']:,} chars, {result['time']:.1f}s")
                print(f"    → {result['output_file']}")
        print()
    
    if failed > 0:
        print("Failed conversions:")
        for result in results:
            if not result['success']:
                print(f"  ✗ {result['filename']}")
                print(f"    Error: {result['error']}")
        print()


def main():
    """Main execution function."""
    try:
        # Parse arguments
        config = parse_arguments()
        config.validate()
        
        # Print configuration
        print_configuration(config)
        
        # Get PDF files
        pdf_files = get_pdf_files(config.pdf_path)
        print(f"Found {len(pdf_files)} PDF file(s) to process:")
        for pdf in pdf_files:
            print(f"  - {pdf.name}")
        print()
        
        # Create output directory
        output_dir = config.get_output_directory()
        print(f"Output directory: {output_dir}")
        print()
        
        # Create pipeline and converter
        print("Initializing Docling converter...")
        pipeline_options = create_pipeline_options(config)
        converter = create_converter(pipeline_options)
        print("✓ Docling converter ready")
        print()
        
        # Convert files
        results = []
        total_start = time.time()
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
            print("-" * 70)
            
            result = convert_single_pdf(pdf_file, config, converter, output_dir)
            results.append(result)
            print()
        
        total_time = time.time() - total_start
        
        # Print summary
        print_summary(results, total_time)
        
        print("=" * 70)
        print("Next Steps:")
        print("=" * 70)
        print(f"1. Inspect output files in: {output_dir}")
        print("2. Compare different argument combinations")
        print("3. Choose best settings for your use case")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
