#!/usr/bin/env python3
"""
Table Replacer for Table Transformer.

Replaces markdown tables with heading+JSON block pairs. Each JSON object
from the transformation gets its own heading (extracted from the title property)
followed by a JSON code block.
"""

import json
import re
import logging
from typing import List, Dict, Any
from copy import deepcopy

logger = logging.getLogger(__name__)


class TableReplacer:
    """
    Replaces markdown tables with heading+JSON pairs.
    
    This class handles:
    - Extracting heading level from context
    - Creating heading+JSON block pairs from JSON objects
    - Replacing tables in reverse order (to avoid line shifts)
    - Preserving document structure with blank lines
    """
    
    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+')
    
    def __init__(self, markdown_lines: List[str]):
        """
        Initialize table replacer with markdown content.
        
        Args:
            markdown_lines: List of lines from markdown file
        """
        # Create a copy to avoid modifying original
        self.markdown_lines = deepcopy(markdown_lines)
        logger.info(f"TableReplacer initialized with {len(markdown_lines)} lines")
    
    def replace_table_with_json_rows(
        self,
        table_start: int,
        table_end: int,
        json_objects: List[Dict[str, Any]],
        heading_level: int = 4
    ) -> None:
        """
        Replace a table with multiple heading+JSON pairs.
        
        Each JSON object becomes:
        - A heading at the specified level (from title property)
        - A JSON code block
        - A blank line separator
        
        Args:
            table_start: 1-indexed line number where table starts
            table_end: 1-indexed line number where table ends
            json_objects: List of JSON objects (one per row)
            heading_level: Heading level to use (1-6, default: 4)
        """
        if not json_objects:
            logger.warning(f"No JSON objects to replace table at lines {table_start}-{table_end}")
            return
        
        logger.info(f"Replacing table at lines {table_start}-{table_end} with {len(json_objects)} heading+JSON pairs")
        
        # Generate replacement lines
        replacement_lines = []
        
        for i, json_obj in enumerate(json_objects):
            # Create heading+JSON block for this object
            heading_and_json = self._create_heading_and_json_block(
                json_obj,
                heading_level
            )
            replacement_lines.extend(heading_and_json)
            
            # Add blank line between objects (except after last one)
            if i < len(json_objects) - 1:
                replacement_lines.append("")
        
        # Replace table lines (convert to 0-indexed)
        start_idx = table_start - 1
        end_idx = table_end  # end_line is inclusive, so this is correct for slicing
        
        # Replace the table lines with the new content
        self.markdown_lines[start_idx:end_idx] = replacement_lines
        
        logger.debug(f"Replaced {end_idx - start_idx} lines with {len(replacement_lines)} lines")
    
    def get_transformed_lines(self) -> List[str]:
        """
        Get the transformed markdown lines.
        
        Returns:
            List of transformed markdown lines
        """
        return self.markdown_lines
    
    def _create_heading_and_json_block(
        self,
        json_obj: Dict[str, Any],
        heading_level: int
    ) -> List[str]:
        """
        Create heading followed by JSON code block.
        
        Args:
            json_obj: JSON object containing data and title
            heading_level: Level of heading (1-6)
            
        Returns:
            List of lines for heading + JSON block
        """
        lines = []
        
        # Extract title from JSON object
        title = json_obj.get("title", "Untitled")
        
        # Create heading line
        heading_prefix = "#" * heading_level
        lines.append(f"{heading_prefix} {title}")
        lines.append("")  # Blank line after heading
        
        # Create JSON code block
        lines.append("```json")
        json_str = json.dumps(json_obj, indent=2, ensure_ascii=False)
        lines.append(json_str)
        lines.append("```")
        
        return lines
    
    def extract_heading_level_from_context(
        self,
        table_start: int
    ) -> int:
        """
        Extract heading level from the nearest heading before the table.
        
        Scans backward from table_start to find the first heading,
        then returns its level.
        
        Args:
            table_start: 1-indexed line number where table starts
            
        Returns:
            Heading level (1-6), defaults to 4 if no heading found
        """
        # Scan backward from table_start - 1
        for i in range(table_start - 1, 0, -1):
            line = self.markdown_lines[i - 1]  # Convert to 0-indexed
            level = self._get_heading_level(line)
            if level is not None:
                logger.debug(f"Found heading level {level} at line {i}")
                return level
        
        # No heading found, default to level 4
        logger.debug("No heading found before table, defaulting to level 4")
        return 4
    
    def _get_heading_level(self, line: str) -> int:
        """
        Get heading level from a line.
        
        Args:
            line: Line to check
            
        Returns:
            Heading level (1-6) or None if not a heading
        """
        match = self.HEADING_PATTERN.match(line.strip())
        if match:
            return len(match.group(1))
        return None
