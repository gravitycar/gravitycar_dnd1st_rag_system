"""
TableListParser Component

Parses complex table list files to extract table metadata including
line numbers and descriptions. Handles the specific format used in
tmp/dmg_tables_2d_matrix_lookup.md.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from ..data_models import TableRecord

logger = logging.getLogger(__name__)


class TableListParser:
    """Parses complex table list files to extract table metadata."""

    RECORD_DELIMITER = "\n---"
    LOCATION_PATTERN = re.compile(r'\*\*Location\*\*:\s*Lines\s*(\d+)\s*-\s*(\d+)')

    def __init__(self, table_list_path: str | Path):
        """
        Initialize parser with path to table list file.

        Args:
            table_list_path: Path to the table list file

        Raises:
            FileNotFoundError: If the file does not exist
        """
        self.table_list_path = Path(table_list_path)
        if not self.table_list_path.exists():
            raise FileNotFoundError(f"File not found: {self.table_list_path}")

    def parse_table_list(self) -> List[TableRecord]:
        """
        Parse entire table list into TableRecord objects.

        Returns:
            List of successfully parsed TableRecord objects

        Raises:
            IOError: If the file cannot be read
        """
        try:
            with open(self.table_list_path, "r", encoding="utf-8") as f:
                content = f.read()
        except IOError as e:
            raise IOError(f"Failed to read file {self.table_list_path}: {e}")

        # Split into individual records
        record_texts = self._split_records(content)

        # Parse each record
        table_records = []
        for i, record_text in enumerate(record_texts, 1):
            record = self._parse_single_record(record_text)
            if record:
                table_records.append(record)
            else:
                logger.warning(
                    f"Skipping record {i} - could not parse metadata"
                )

        logger.info(
            f"Parsed {len(table_records)} tables from {len(record_texts)} records"
        )
        return table_records

    def _split_records(self, content: str) -> List[str]:
        """
        Split content on delimiter.

        Args:
            content: Full file content

        Returns:
            List of record text blocks
        """
        # Split on delimiter and filter empty strings
        records = [
            record.strip()
            for record in content.split(self.RECORD_DELIMITER)
            if record.strip()
        ]
        return records

    def _parse_single_record(self, record_text: str) -> Optional[TableRecord]:
        """
        Parse individual record and extract metadata.

        Args:
            record_text: Text of a single record

        Returns:
            TableRecord if parsing successful, None otherwise
        """
        # Extract line numbers
        line_numbers = self._extract_line_numbers(record_text)
        if not line_numbers:
            return None

        start_line, end_line = line_numbers

        # Extract description (first non-empty line that isn't the location)
        description = self._extract_description(record_text)

        return TableRecord(
            start_line=start_line,
            end_line=end_line,
            description=description
        )

    def _extract_line_numbers(self, record_text: str) -> Optional[Tuple[int, int]]:
        """
        Extract start and end line numbers from location field.

        Args:
            record_text: Text of a single record

        Returns:
            Tuple of (start_line, end_line) or None if not found
        """
        match = self.LOCATION_PATTERN.search(record_text)
        if match:
            start_line = int(match.group(1))
            end_line = int(match.group(2))
            return (start_line, end_line)
        return None

    def _extract_description(self, record_text: str) -> str:
        """
        Extract table description from record.

        Takes the first non-empty line that isn't the location line.

        Args:
            record_text: Text of a single record

        Returns:
            Description string (may be empty if not found)
        """
        lines = record_text.split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines and location lines
            if line and not line.startswith('**Location**'):
                # Remove markdown formatting
                description = line.strip('*#-_ ')
                return description

        return "Unknown table"
