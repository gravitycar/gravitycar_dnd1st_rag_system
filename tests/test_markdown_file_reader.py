"""
Tests for the MarkdownFileReader component.

Tests cover:
- File reading with proper encoding
- Line range extraction with 1-indexed line numbers
- Validation of line numbers
- Edge cases (empty files, boundary conditions)
- Error handling (missing files, invalid ranges)
"""

import pytest
from pathlib import Path
from src.transformers.components.markdown_file_reader import MarkdownFileReader


# Test fixtures paths
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "table_transformer"
SAMPLE_FILE = FIXTURES_DIR / "sample_markdown.md"
EMPTY_FILE = FIXTURES_DIR / "empty_file.md"


class TestMarkdownFileReaderInitialization:
    """Test reader initialization and file validation."""

    def test_init_with_valid_file(self):
        """Should initialize successfully with existing file."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        assert reader.file_path == SAMPLE_FILE
        assert reader._lines is None  # Lines not loaded yet

    def test_init_with_string_path(self):
        """Should accept string paths and convert to Path objects."""
        reader = MarkdownFileReader(str(SAMPLE_FILE))
        assert isinstance(reader.file_path, Path)
        assert reader.file_path == SAMPLE_FILE

    def test_init_with_missing_file(self):
        """Should raise FileNotFoundError for missing files."""
        missing_file = FIXTURES_DIR / "nonexistent.md"
        with pytest.raises(FileNotFoundError) as exc_info:
            MarkdownFileReader(missing_file)
        assert "File not found" in str(exc_info.value)


class TestMarkdownFileReaderFileReading:
    """Test file reading operations."""

    def test_read_file(self):
        """Should read entire file content as string."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        content = reader.read_file()
        assert isinstance(content, str)
        assert "# Test Markdown File" in content
        assert "## Section One" in content
        assert "End of file." in content

    def test_read_lines(self):
        """Should read file as list of lines."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        lines = reader.read_lines()
        assert isinstance(lines, list)
        assert len(lines) == 22
        assert lines[0] == "# Test Markdown File\n"
        assert lines[-1] == "End of file.\n"

    def test_read_lines_caching(self):
        """Should cache lines and not re-read file."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        lines1 = reader.read_lines()
        lines2 = reader.read_lines()
        assert lines1 is lines2  # Same object reference

    def test_read_empty_file(self):
        """Should handle empty files correctly."""
        reader = MarkdownFileReader(EMPTY_FILE)
        content = reader.read_file()
        assert content == ""
        lines = reader.read_lines()
        assert lines == []

    def test_get_line_count(self):
        """Should return correct line count."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        assert reader.get_line_count() == 22

    def test_get_line_count_empty_file(self):
        """Should return 0 for empty files."""
        reader = MarkdownFileReader(EMPTY_FILE)
        assert reader.get_line_count() == 0


class TestMarkdownFileReaderLineExtraction:
    """Test line range extraction with 1-indexed line numbers."""

    def test_extract_single_line(self):
        """Should extract a single line correctly."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        # Line 1 is "# Test Markdown File\n"
        extracted = reader.extract_lines(1, 1)
        assert extracted == "# Test Markdown File\n"

    def test_extract_multiple_lines(self):
        """Should extract multiple consecutive lines."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        # Lines 3-5: "## Section One", blank line, "This is the first paragraph."
        extracted = reader.extract_lines(3, 5)
        assert extracted == "## Section One\n\nThis is the first paragraph.\n"

    def test_extract_entire_file(self):
        """Should extract entire file when range covers all lines."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        extracted = reader.extract_lines(1, 22)
        full_content = reader.read_file()
        assert extracted == full_content

    def test_extract_preserves_whitespace(self):
        """Should preserve blank lines and whitespace."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        # Lines 7-8: "This is the second paragraph.\n" and blank line
        extracted = reader.extract_lines(7, 8)
        assert extracted == "This is the second paragraph.\n\n"

    def test_extract_table_content(self):
        """Should correctly extract table rows."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        # Lines 16-19: table content
        extracted = reader.extract_lines(16, 19)
        assert "| Column A | Column B |" in extracted
        assert "| Value 1  | Value 2  |" in extracted


class TestMarkdownFileReaderValidation:
    """Test line number validation."""

    def test_extract_invalid_start_line_zero(self):
        """Should reject start_line of 0."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        with pytest.raises(ValueError) as exc_info:
            reader.extract_lines(0, 5)
        assert "start_line must be >= 1" in str(exc_info.value)

    def test_extract_invalid_start_line_negative(self):
        """Should reject negative start_line."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        with pytest.raises(ValueError) as exc_info:
            reader.extract_lines(-1, 5)
        assert "start_line must be >= 1" in str(exc_info.value)

    def test_extract_invalid_line_order(self):
        """Should reject end_line < start_line."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        with pytest.raises(ValueError) as exc_info:
            reader.extract_lines(10, 5)
        assert "end_line (5) must be >= start_line (10)" in str(exc_info.value)

    def test_extract_start_line_exceeds_file_length(self):
        """Should reject start_line beyond file length."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        with pytest.raises(ValueError) as exc_info:
            reader.extract_lines(100, 105)
        assert "start_line (100) exceeds file length (22 lines)" in str(exc_info.value)

    def test_extract_end_line_exceeds_file_length(self):
        """Should reject end_line beyond file length."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        with pytest.raises(ValueError) as exc_info:
            reader.extract_lines(10, 100)
        assert "end_line (100) exceeds file length (22 lines)" in str(exc_info.value)


class TestMarkdownFileReaderEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extract_from_empty_file(self):
        """Should handle extraction from empty file gracefully."""
        reader = MarkdownFileReader(EMPTY_FILE)
        with pytest.raises(ValueError) as exc_info:
            reader.extract_lines(1, 1)
        assert "exceeds file length (0 lines)" in str(exc_info.value)

    def test_extract_last_line_of_file(self):
        """Should correctly extract the last line."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        extracted = reader.extract_lines(22, 22)
        assert extracted == "End of file.\n"

    def test_extract_first_line_of_file(self):
        """Should correctly extract the first line."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        extracted = reader.extract_lines(1, 1)
        assert extracted == "# Test Markdown File\n"

    def test_multiple_extractions(self):
        """Should handle multiple extractions from same reader."""
        reader = MarkdownFileReader(SAMPLE_FILE)
        extract1 = reader.extract_lines(1, 5)
        extract2 = reader.extract_lines(10, 15)
        extract3 = reader.extract_lines(1, 5)
        
        assert extract1 == extract3  # Same extraction should be identical
        assert extract1 != extract2  # Different extractions should differ
