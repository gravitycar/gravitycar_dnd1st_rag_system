#!/usr/bin/env python3
"""
Context Extractor for Table Transformer.

Extracts contextual information around markdown tables by identifying
heading boundaries. Context is bounded by the nearest heading before
the table and the next heading of equal or higher level after the table.
"""

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class ContextExtractor:
    """
    Extracts heading-bounded context around markdown tables.
    
    The context extraction follows these rules:
    1. Find the nearest heading before the table (scan backward)
    2. Determine the heading level (count # characters)
    3. Find the next heading of equal or higher level after the table
    4. Extract all lines between these boundaries
    5. Filter out table lines (lines starting with |)
    
    Edge cases:
    - If no heading found before table, use start of file
    - If no heading found after table, use end of file
    - Heading level comparison: fewer # = higher level (e.g., ## > ###)
    """
    
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$')
    TABLE_LINE_PATTERN = re.compile(r'^\|')
    
    def __init__(self, markdown_lines: List[str]):
        """
        Initialize context extractor with markdown file content.
        
        Args:
            markdown_lines: List of lines from markdown file (1-indexed when used)
        """
        self.markdown_lines = markdown_lines
        logger.info(f"ContextExtractor initialized with {len(markdown_lines)} lines")
    
    def extract_context(
        self, 
        table_start: int, 
        table_end: int
    ) -> str:
        """
        Extract and filter context for a table.
        
        The context includes all text between the nearest heading before
        the table and the next heading of equal or higher level after,
        with table content filtered out.
        
        Args:
            table_start: 1-indexed line number where table starts
            table_end: 1-indexed line number where table ends
            
        Returns:
            Filtered context as a string (table lines removed)
            
        Raises:
            ValueError: If line numbers are invalid
        """
        # Validate line numbers
        if table_start < 1 or table_end > len(self.markdown_lines):
            raise ValueError(
                f"Invalid line numbers: start={table_start}, end={table_end}, "
                f"file has {len(self.markdown_lines)} lines"
            )
        if table_start > table_end:
            raise ValueError(
                f"Invalid range: start={table_start} > end={table_end}"
            )
        
        # Find context boundaries
        context_start, heading_level = self.find_heading_before(table_start)
        context_end = self.find_next_heading(table_end, heading_level)
        
        logger.debug(
            f"Context boundaries for table at lines {table_start}-{table_end}: "
            f"lines {context_start}-{context_end} (heading level {heading_level})"
        )
        
        # Extract lines (convert to 0-indexed for slicing)
        context_lines = self.markdown_lines[context_start - 1:context_end - 1]
        
        # Filter out table lines
        filtered_lines = self.filter_table_lines(context_lines)
        
        context = '\n'.join(filtered_lines)
        logger.info(
            f"Extracted context: {len(context_lines)} lines total, "
            f"{len(filtered_lines)} lines after filtering tables"
        )
        
        return context
    
    def find_heading_before(self, line_number: int) -> Tuple[int, int]:
        """
        Find the nearest heading before a given line number.
        
        Scans backward from line_number - 1 to find the first heading.
        
        Args:
            line_number: 1-indexed line number to search before
            
        Returns:
            Tuple of (heading_line_number, heading_level)
            If no heading found, returns (1, 6) meaning start of file with lowest priority
        """
        # Scan backward from line_number - 1
        for i in range(line_number - 1, 0, -1):
            line = self.markdown_lines[i - 1]  # Convert to 0-indexed
            heading_level = self.get_heading_level(line)
            if heading_level is not None:
                logger.debug(f"Found heading at line {i}, level {heading_level}")
                return (i, heading_level)
        
        # No heading found, use start of file
        logger.debug(f"No heading found before line {line_number}, using start of file")
        return (1, 6)  # Level 6 is lowest priority
    
    def find_next_heading(
        self, 
        line_number: int, 
        min_level: int
    ) -> int:
        """
        Find the next heading of equal or higher level after a given line.
        
        "Higher level" means fewer # characters (e.g., ## is higher than ###).
        Scans forward from line_number + 1 to find first matching heading.
        
        Args:
            line_number: 1-indexed line number to search after
            min_level: Minimum heading level (1-6, where 1 is highest)
            
        Returns:
            1-indexed line number of next heading, or len(lines) + 1 if none found
        """
        # Scan forward from line_number + 1
        for i in range(line_number + 1, len(self.markdown_lines) + 1):
            line = self.markdown_lines[i - 1]  # Convert to 0-indexed
            heading_level = self.get_heading_level(line)
            if heading_level is not None and heading_level <= min_level:
                logger.debug(
                    f"Found next heading at line {i}, level {heading_level} "
                    f"(min_level={min_level})"
                )
                return i
        
        # No heading found, use end of file
        end_line = len(self.markdown_lines) + 1
        logger.debug(
            f"No heading found after line {line_number} with level <= {min_level}, "
            f"using end of file (line {end_line})"
        )
        return end_line
    
    def get_heading_level(self, line: str) -> Optional[int]:
        """
        Extract heading level from a line.
        
        Args:
            line: Line to check for heading syntax
            
        Returns:
            Heading level (1-6) if line is a heading, None otherwise
        """
        match = self.HEADING_PATTERN.match(line.strip())
        if match:
            level = len(match.group(1))  # Count # characters
            return level
        return None
    
    def filter_table_lines(self, lines: List[str]) -> List[str]:
        """
        Remove lines that are part of markdown tables.
        
        Table lines are identified by starting with | (pipe character).
        
        Args:
            lines: List of lines to filter
            
        Returns:
            List of lines with table content removed
        """
        filtered = []
        for line in lines:
            if not self.TABLE_LINE_PATTERN.match(line.strip()):
                filtered.append(line)
        return filtered
