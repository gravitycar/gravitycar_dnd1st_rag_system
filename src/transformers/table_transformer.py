#!/usr/bin/env python3
"""
TableTransformer - Main orchestrator for table transformation pipeline.

Coordinates all components to transform markdown tables to JSON using OpenAI.
"""

import logging
import time
import sys
from pathlib import Path
from typing import List, Tuple, Optional

from .data_models import (
    TableRecord,
    TransformationResult,
    TransformationReport
)
from .components.markdown_file_reader import MarkdownFileReader
from .components.table_list_parser import TableListParser
from .components.context_extractor import ContextExtractor
from .components.table_preprocessor import TablePreprocessor
from .components.openai_transformer import OpenAITransformer
from .components.table_replacer import TableReplacer
from .components.file_writer import FileWriter

logger = logging.getLogger(__name__)


class TableTransformer:
    """
    Main orchestrator for table transformation pipeline.
    
    Coordinates all components to:
    1. Load markdown and table list files
    2. Extract context around tables
    3. Preprocess tables to minimize tokens
    4. Transform tables to JSON using OpenAI
    5. Replace tables with heading+JSON pairs
    6. Write transformed markdown to output file
    """
    
    def __init__(
        self,
        markdown_file: str,
        table_list_file: str,
        output_dir: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        delay_seconds: float = 1.0,
        cost_limit_usd: float = 5.0
    ):
        """
        Initialize transformer with configuration.
        
        Args:
            markdown_file: Path to markdown file to transform
            table_list_file: Path to complex table list file
            output_dir: Output directory (default: data/markdown/docling/good_pdfs/)
            api_key: OpenAI API key (if None, loads from .env)
            model: OpenAI model to use
            delay_seconds: Delay between API calls
            cost_limit_usd: Maximum cost in USD
        """
        self.markdown_file = Path(markdown_file)
        self.table_list_file = Path(table_list_file)
        
        # Set default output directory
        if output_dir is None:
            self.output_dir = Path("data/markdown/docling/good_pdfs/")
        else:
            self.output_dir = Path(output_dir)
        
        self.model = model
        self.delay_seconds = delay_seconds
        self.cost_limit_usd = cost_limit_usd
        
        # Get API key
        if api_key is None:
            api_key = self._get_api_key()
        
        # Initialize components
        self.file_reader = MarkdownFileReader(self.markdown_file)
        self.table_parser = TableListParser(self.table_list_file)
        self.preprocessor = TablePreprocessor()
        self.openai_transformer = OpenAITransformer(
            api_key=api_key,
            model=model,
            temperature=0.0
        )
        self.file_writer = FileWriter(self.output_dir)
    
    def transform(self, dry_run: bool = False) -> TransformationReport:
        """
        Execute transformation pipeline.
        
        Args:
            dry_run: If True, estimate cost without executing
            
        Returns:
            TransformationReport with statistics
        """
        start_time = time.time()
        
        logger.info("Starting table transformation pipeline")
        print("\n" + "=" * 60)
        print("TABLE TRANSFORMATION PIPELINE")
        print("=" * 60)
        
        # Load files
        print("\n[1/6] Loading files...")
        markdown_lines, table_records = self._load_files()
        print(f"  ✓ Loaded {len(markdown_lines)} lines from markdown")
        print(f"  ✓ Found {len(table_records)} tables to transform")
        
        # Estimate cost
        print("\n[2/6] Estimating cost...")
        estimated_cost = self._estimate_cost(markdown_lines, table_records)
        print(f"  ✓ Estimated cost: ${estimated_cost:.4f}")
        
        if dry_run:
            print("\n[DRY RUN] Skipping transformation")
            execution_time = time.time() - start_time
            return TransformationReport(
                total_tables=len(table_records),
                successful=0,
                failed=0,
                total_tokens=0,
                total_cost_usd=estimated_cost,
                failures=[],
                execution_time_seconds=execution_time
            )
        
        # Check cost limit
        if estimated_cost > self.cost_limit_usd:
            print(f"\n⚠️  Warning: Estimated cost (${estimated_cost:.4f}) exceeds limit (${self.cost_limit_usd:.2f})")
            response = input("Continue? (y/n): ")
            if response.lower() != 'y':
                print("Transformation cancelled")
                sys.exit(0)
        
        # Process tables
        print("\n[3/6] Processing tables with OpenAI...")
        results = self._process_tables(markdown_lines, table_records)
        
        # Apply transformations
        print("\n[4/6] Applying transformations...")
        transformed_lines = self._apply_transformations(markdown_lines, results)
        print(f"  ✓ Replaced {sum(1 for r in results if r.success)} tables")
        
        # Write output
        print("\n[5/6] Writing output file...")
        output_path = self.file_writer.write_transformed_file(
            self.markdown_file,
            transformed_lines,
            create_backup=True
        )
        print(f"  ✓ Wrote: {output_path}")
        
        # Generate report
        print("\n[6/6] Generating report...")
        report = self._generate_report(results, start_time)
        
        return report
    
    def _load_files(self) -> Tuple[List[str], List[TableRecord]]:
        """
        Load markdown and table list files.
        
        Returns:
            Tuple of (markdown_lines, table_records)
        """
        # Read markdown
        markdown_lines = self.file_reader.read_lines()
        
        # Parse table list
        table_records = self.table_parser.parse_table_list()
        
        # Extract table markdown for each record
        for record in table_records:
            record.table_markdown = self.file_reader.extract_lines(
                record.start_line, record.end_line
            )
        
        return markdown_lines, table_records
    
    def _estimate_cost(
        self,
        markdown_lines: List[str],
        table_records: List[TableRecord]
    ) -> float:
        """
        Estimate total cost based on table sizes.
        
        Uses approximation: 1 token ≈ 4 characters for English text.
        Accounts for preprocessing savings (30-50% reduction).
        
        Args:
            markdown_lines: Markdown file lines
            table_records: List of tables to transform
            
        Returns:
            Estimated cost in USD
        """
        total_chars = 0
        context_extractor = ContextExtractor(markdown_lines)
        
        for record in table_records:
            # Estimate table size after preprocessing
            table_chars = len(record.table_markdown)
            preprocessing_factor = 0.65  # 35% reduction on average
            preprocessed_chars = table_chars * preprocessing_factor
            
            # Estimate context size
            try:
                context = context_extractor.extract_context(
                    record.start_line,
                    record.end_line
                )
                context_chars = len(context)
            except Exception:
                context_chars = 1000  # Conservative fallback
            
            # Prompt overhead (template text)
            prompt_overhead = 1500
            
            total_chars += preprocessed_chars + context_chars + prompt_overhead
        
        # Convert to tokens (rough approximation)
        estimated_tokens = total_chars / 4
        
        # gpt-4o-mini pricing (as of Oct 2024)
        INPUT_COST_PER_1K = 0.00015  # $0.15 per 1M tokens
        OUTPUT_COST_PER_1K = 0.0006   # $0.60 per 1M tokens
        
        # Assume 70% input, 30% output
        input_tokens = estimated_tokens * 0.7
        output_tokens = estimated_tokens * 0.3
        
        cost = (
            (input_tokens / 1000) * INPUT_COST_PER_1K +
            (output_tokens / 1000) * OUTPUT_COST_PER_1K
        )
        
        return cost
    
    def _process_tables(
        self,
        markdown_lines: List[str],
        table_records: List[TableRecord]
    ) -> List[TransformationResult]:
        """
        Process all tables through OpenAI transformation.
        
        Args:
            markdown_lines: Markdown file lines
            table_records: List of tables to transform
            
        Returns:
            List of transformation results
        """
        results = []
        context_extractor = ContextExtractor(markdown_lines)
        
        for i, record in enumerate(table_records, 1):
            # Progress indicator
            desc = record.description[:50] if record.description else "Unnamed table"
            print(f"  [{i}/{len(table_records)}] {desc}...")
            
            try:
                # Extract context
                context = context_extractor.extract_context(
                    record.start_line,
                    record.end_line
                )
                record.table_context = context
                
                # Preprocess table
                preprocessed_table = self.preprocessor.preprocess_table(
                    record.table_markdown
                )
                
                # Transform with OpenAI
                json_objects, tokens_used, cost_usd = self.openai_transformer.transform_table(
                    preprocessed_table,
                    context
                )
                
                # Create result
                result = TransformationResult(
                    table_record=record,
                    json_objects=json_objects,
                    success=True,
                    tokens_used=tokens_used,
                    cost_usd=cost_usd
                )
                
                results.append(result)
                
                if result.success:
                    print(f"    ✓ Success ({len(result.json_objects)} rows, {result.tokens_used} tokens, ${result.cost_usd:.4f})")
                else:
                    print(f"    ✗ Failed: {result.error_message}")
                
                # Rate limiting delay
                if i < len(table_records):
                    time.sleep(self.delay_seconds)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                print(f"Processed {i-1}/{len(table_records)} tables")
                raise
            except Exception as e:
                logger.error(f"Error processing table at lines {record.start_line}-{record.end_line}: {e}")
                results.append(TransformationResult(
                    table_record=record,
                    json_objects=[],
                    success=False,
                    error_message=str(e),
                    tokens_used=0,
                    cost_usd=0.0
                ))
                print(f"    ✗ Error: {e}")
        
        return results
    
    def _apply_transformations(
        self,
        markdown_lines: List[str],
        results: List[TransformationResult]
    ) -> List[str]:
        """
        Apply successful transformations to markdown.
        
        CRITICAL: Process in reverse order to avoid line number shifts.
        
        Args:
            markdown_lines: Original markdown lines
            results: Transformation results
            
        Returns:
            Transformed markdown lines
        """
        # Create replacer
        replacer = TableReplacer(markdown_lines)
        
        # Sort by start_line descending (reverse order)
        sorted_results = sorted(
            [r for r in results if r.success],
            key=lambda r: r.table_record.start_line,
            reverse=True
        )
        
        # Apply each replacement
        for result in sorted_results:
            record = result.table_record
            
            # Determine heading level from context
            heading_level = replacer.extract_heading_level_from_context(
                record.start_line
            )
            
            # Replace table with heading+JSON pairs
            replacer.replace_table_with_json_rows(
                record.start_line,
                record.end_line,
                result.json_objects,
                heading_level
            )
        
        return replacer.get_transformed_lines()
    
    def _generate_report(
        self,
        results: List[TransformationResult],
        start_time: float
    ) -> TransformationReport:
        """
        Generate summary report.
        
        Args:
            results: List of transformation results
            start_time: Pipeline start time
            
        Returns:
            TransformationReport
        """
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_tokens = sum(r.tokens_used for r in results)
        total_cost = sum(r.cost_usd for r in results)
        failures = [r for r in results if not r.success]
        execution_time = time.time() - start_time
        
        report = TransformationReport(
            total_tables=len(results),
            successful=successful,
            failed=failed,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            failures=failures,
            execution_time_seconds=execution_time
        )
        
        # Display report
        print("\n" + "=" * 60)
        print("TRANSFORMATION REPORT")
        print("=" * 60)
        print(f"Total tables:     {report.total_tables}")
        print(f"Successful:       {report.successful} ({report.success_rate:.1%})")
        print(f"Failed:           {report.failed}")
        print(f"Total tokens:     {report.total_tokens:,}")
        print(f"Total cost:       ${report.total_cost_usd:.4f}")
        print(f"Execution time:   {report.execution_time_seconds:.1f}s")
        
        if failures:
            print(f"\n⚠️  Failed transformations:")
            for failure in failures:
                record = failure.table_record
                print(f"  • Lines {record.start_line}-{record.end_line}: {failure.error_message}")
        
        print("=" * 60 + "\n")
        
        return report
    
    def _get_api_key(self) -> str:
        """
        Load OpenAI API key from .env file.
        
        Returns:
            API key string
            
        Raises:
            ValueError: If API key not found
        """
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        api_key = os.getenv("gravitycar_openai_api_key")
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Set gravitycar_openai_api_key in .env file or pass api_key parameter."
            )
        
        return api_key
