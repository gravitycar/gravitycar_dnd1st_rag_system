"""
TablePreprocessor Component

Preprocesses markdown tables to minimize token usage while preserving
table structure and markdown rendering. Reduces OpenAI API costs by
30-50% through intelligent whitespace stripping and separator compression.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class TablePreprocessor:
    """Preprocesses markdown tables to minimize token usage."""

    SEPARATOR_PATTERN = re.compile(r'\|(\s*-{3,}\s*)\|')

    def __init__(self):
        """Initialize preprocessor."""
        pass

    def preprocess_table(self, table_markdown: str) -> Tuple[str, dict]:
        """
        Preprocess table to minimize token usage while preserving structure.

        Performs two optimizations:
        1. Strips excessive whitespace from cells (preserves 1 space padding)
        2. Compresses separator lines to minimal format (3 hyphens per column)

        Args:
            table_markdown: Raw markdown table string

        Returns:
            Tuple of (preprocessed_table, stats_dict) where stats_dict contains:
                - original_length: Character count before preprocessing
                - preprocessed_length: Character count after preprocessing
                - reduction_percent: Percentage reduction
                - lines_processed: Number of lines processed
        """
        lines = table_markdown.split('\n')
        preprocessed_lines = []
        
        for line in lines:
            if not line.strip():
                # Preserve blank lines
                preprocessed_lines.append(line)
            elif self.is_separator_line(line):
                # Compress separator line
                preprocessed_lines.append(self.compress_separator_line(line))
            else:
                # Strip cell whitespace
                preprocessed_lines.append(self.strip_cell_whitespace(line))
        
        preprocessed = '\n'.join(preprocessed_lines)
        
        # Calculate statistics
        original_length = len(table_markdown)
        preprocessed_length = len(preprocessed)
        reduction_percent = ((original_length - preprocessed_length) / original_length * 100) if original_length > 0 else 0
        
        stats = {
            'original_length': original_length,
            'preprocessed_length': preprocessed_length,
            'reduction_percent': reduction_percent,
            'lines_processed': len(lines)
        }
        
        logger.debug(
            f"Preprocessed table: {original_length} → {preprocessed_length} chars "
            f"({reduction_percent:.1f}% reduction)"
        )
        
        return preprocessed, stats

    def strip_cell_whitespace(self, line: str) -> str:
        """
        Strip excessive whitespace from table cells, preserve 1 space padding.

        Example:
            Input:  "|   Fighter Level   |     XP Required     |"
            Output: "| Fighter Level | XP Required |"

        Args:
            line: Table line (header or data row)

        Returns:
            Line with stripped cell content, 1 space padding preserved
        """
        cells = line.split('|')
        stripped_cells = []
        
        for i, cell in enumerate(cells):
            if i == 0 or i == len(cells) - 1:
                # Preserve empty cells at start/end (from leading/trailing |)
                stripped_cells.append(cell)
            else:
                # Strip whitespace and add 1 space padding
                stripped = cell.strip()
                stripped_cells.append(f" {stripped} " if stripped else " ")
        
        return '|'.join(stripped_cells)

    def compress_separator_line(self, line: str) -> str:
        """
        Reduce separator lines to 3 hyphens per column.

        Example:
            Input:  "|---------------|-----------------|"
            Output: "|---|---|"

        Args:
            line: Separator line (starts/ends with |, contains ---)

        Returns:
            Compressed separator line with exactly 3 hyphens per column
        """
        # Split on pipe
        cells = line.split('|')
        compressed_cells = []
        
        for i, cell in enumerate(cells):
            if i == 0 or i == len(cells) - 1:
                # Preserve empty cells at start/end
                compressed_cells.append(cell)
            else:
                # Replace any sequence of hyphens/spaces with "---"
                if '-' in cell:
                    compressed_cells.append("---")
                else:
                    # Preserve non-separator cells (shouldn't happen in separator line)
                    compressed_cells.append(cell)
        
        return '|'.join(compressed_cells)

    def is_separator_line(self, line: str) -> bool:
        """
        Check if line is a table separator.

        A separator line:
        - Starts and ends with |
        - Contains at least one sequence of 3+ hyphens
        - May contain spaces and colons (for alignment)

        Args:
            line: Line to check

        Returns:
            True if line is a separator, False otherwise
        """
        stripped = line.strip()
        if not stripped.startswith('|') or not stripped.endswith('|'):
            return False
        
        # Check if contains hyphen sequences
        return bool(re.search(r'-{3,}', line))

    def calculate_token_savings(
        self, 
        original_length: int, 
        preprocessed_length: int
    ) -> dict:
        """
        Calculate estimated token savings.

        Uses approximation: 1 token ≈ 4 characters for English text.

        Args:
            original_length: Character count before preprocessing
            preprocessed_length: Character count after preprocessing

        Returns:
            Dictionary with token savings metrics
        """
        chars_per_token = 4
        
        original_tokens = original_length / chars_per_token
        preprocessed_tokens = preprocessed_length / chars_per_token
        tokens_saved = original_tokens - preprocessed_tokens
        percent_saved = (tokens_saved / original_tokens * 100) if original_tokens > 0 else 0
        
        return {
            'original_tokens': round(original_tokens, 1),
            'preprocessed_tokens': round(preprocessed_tokens, 1),
            'tokens_saved': round(tokens_saved, 1),
            'percent_saved': round(percent_saved, 1)
        }
