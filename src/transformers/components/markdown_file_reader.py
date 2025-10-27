"""
MarkdownFileReader Component

Handles reading markdown files and extracting line ranges with proper validation.
Uses 1-indexed line numbers to match editor conventions.
"""

from pathlib import Path
from typing import List


class MarkdownFileReader:
    """Reads markdown files and extracts specific line ranges."""

    def __init__(self, file_path: str | Path):
        """
        Initialize reader with a markdown file path.

        Args:
            file_path: Path to the markdown file to read

        Raises:
            FileNotFoundError: If the file does not exist
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        self._lines: List[str] | None = None

    def read_file(self) -> str:
        """
        Read the entire file contents.

        Returns:
            The complete file contents as a string

        Raises:
            IOError: If the file cannot be read
        """
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except IOError as e:
            raise IOError(f"Failed to read file {self.file_path}: {e}")

    def read_lines(self) -> List[str]:
        """
        Read the file and return it as a list of lines.

        The lines preserve their newline characters. Results are cached
        so subsequent calls don't re-read the file.

        Returns:
            List of lines from the file

        Raises:
            IOError: If the file cannot be read
        """
        if self._lines is None:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._lines = f.readlines()
            except IOError as e:
                raise IOError(f"Failed to read file {self.file_path}: {e}")
        return self._lines

    def extract_lines(self, start_line: int, end_line: int) -> str:
        """
        Extract a range of lines from the file.

        Uses 1-indexed line numbers to match editor conventions.
        Both start_line and end_line are inclusive.

        Args:
            start_line: First line to extract (1-indexed, inclusive)
            end_line: Last line to extract (1-indexed, inclusive)

        Returns:
            The extracted lines as a single string

        Raises:
            ValueError: If line numbers are invalid
            IOError: If the file cannot be read
        """
        # Validate line numbers
        if start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {start_line}")
        if end_line < start_line:
            raise ValueError(
                f"end_line ({end_line}) must be >= start_line ({start_line})"
            )

        # Read lines (cached)
        lines = self.read_lines()

        # Check bounds
        if start_line > len(lines):
            raise ValueError(
                f"start_line ({start_line}) exceeds file length ({len(lines)} lines)"
            )
        if end_line > len(lines):
            raise ValueError(
                f"end_line ({end_line}) exceeds file length ({len(lines)} lines)"
            )

        # Extract lines (convert to 0-indexed)
        extracted = lines[start_line - 1 : end_line]
        return "".join(extracted)

    def get_line_count(self) -> int:
        """
        Get the total number of lines in the file.

        Returns:
            Total number of lines
        """
        return len(self.read_lines())
