"""
Tests for the TableListParser component.

Tests cover:
- Parsing valid table lists
- Extracting line numbers correctly
- Splitting records on delimiter
- Handling malformed records gracefully
- Edge cases (empty files, single records, missing fields)
"""

import pytest
from pathlib import Path
from src.transformers.components.table_list_parser import TableListParser
from src.transformers.data_models import TableRecord


# Test fixtures paths
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "table_transformer"
SAMPLE_LIST = FIXTURES_DIR / "sample_table_list.md"
MALFORMED_LIST = FIXTURES_DIR / "malformed_table_list.md"
SINGLE_TABLE_LIST = FIXTURES_DIR / "single_table_list.md"
EMPTY_FILE = FIXTURES_DIR / "empty_file.md"


class TestTableListParserInitialization:
    """Test parser initialization and file validation."""

    def test_init_with_valid_file(self):
        """Should initialize successfully with existing file."""
        parser = TableListParser(SAMPLE_LIST)
        assert parser.table_list_path == SAMPLE_LIST

    def test_init_with_string_path(self):
        """Should accept string paths and convert to Path objects."""
        parser = TableListParser(str(SAMPLE_LIST))
        assert isinstance(parser.table_list_path, Path)
        assert parser.table_list_path == SAMPLE_LIST

    def test_init_with_missing_file(self):
        """Should raise FileNotFoundError for missing files."""
        missing_file = FIXTURES_DIR / "nonexistent.md"
        with pytest.raises(FileNotFoundError) as exc_info:
            TableListParser(missing_file)
        assert "File not found" in str(exc_info.value)


class TestTableListParserRecordSplitting:
    """Test splitting records on delimiter."""

    def test_split_records_multiple(self):
        """Should split multiple records on \\n--- delimiter."""
        parser = TableListParser(SAMPLE_LIST)
        with open(SAMPLE_LIST, 'r') as f:
            content = f.read()
        records = parser._split_records(content)
        assert len(records) == 5

    def test_split_records_single(self):
        """Should handle single record without delimiter."""
        parser = TableListParser(SINGLE_TABLE_LIST)
        with open(SINGLE_TABLE_LIST, 'r') as f:
            content = f.read()
        records = parser._split_records(content)
        assert len(records) == 1

    def test_split_records_empty(self):
        """Should return empty list for empty file."""
        parser = TableListParser(EMPTY_FILE)
        records = parser._split_records("")
        assert len(records) == 0

    def test_split_records_filters_empty(self):
        """Should filter out empty records."""
        parser = TableListParser(SAMPLE_LIST)
        # Content with extra delimiters creating empty records
        content = "Record 1\n---\n\n---\nRecord 2\n---\n---"
        records = parser._split_records(content)
        assert len(records) == 2


class TestTableListParserLineNumberExtraction:
    """Test line number extraction from location fields."""

    def test_extract_line_numbers_valid(self):
        """Should extract line numbers from valid location field."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "**Location**: Lines 10-15"
        result = parser._extract_line_numbers(record_text)
        assert result == (10, 15)

    def test_extract_line_numbers_with_whitespace(self):
        """Should handle extra whitespace around location."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "**Location**:   Lines   123 - 456  "
        result = parser._extract_line_numbers(record_text)
        assert result == (123, 456)

    def test_extract_line_numbers_missing(self):
        """Should return None if location field missing."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "Some text without location"
        result = parser._extract_line_numbers(record_text)
        assert result is None

    def test_extract_line_numbers_malformed(self):
        """Should return None for malformed line numbers."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "**Location**: Lines invalid-data"
        result = parser._extract_line_numbers(record_text)
        assert result is None


class TestTableListParserDescriptionExtraction:
    """Test description extraction from records."""

    def test_extract_description_from_heading(self):
        """Should extract description from markdown heading."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "### Table 1: Fighter Experience\n**Location**: Lines 10-15"
        description = parser._extract_description(record_text)
        assert "Fighter Experience" in description

    def test_extract_description_from_text(self):
        """Should extract description from plain text."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "This is a description\n**Location**: Lines 10-15"
        description = parser._extract_description(record_text)
        assert "This is a description" in description

    def test_extract_description_skips_location(self):
        """Should skip location line when finding description."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "**Location**: Lines 10-15\nActual description here"
        description = parser._extract_description(record_text)
        assert description == "Actual description here"

    def test_extract_description_strips_markdown(self):
        """Should strip common markdown formatting characters."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "### **Table Name**\n**Location**: Lines 10-15"
        description = parser._extract_description(record_text)
        assert "#" not in description
        assert "**" not in description

    def test_extract_description_default(self):
        """Should return default if no description found."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "**Location**: Lines 10-15"
        description = parser._extract_description(record_text)
        assert description == "Unknown table"


class TestTableListParserSingleRecord:
    """Test parsing individual records."""

    def test_parse_single_record_valid(self):
        """Should parse valid record successfully."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "### Table 1: Test\n**Location**: Lines 10-15\nDescription here"
        record = parser._parse_single_record(record_text)
        
        assert record is not None
        assert record.start_line == 10
        assert record.end_line == 15
        assert "Test" in record.description

    def test_parse_single_record_missing_location(self):
        """Should return None for record without location."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "### Table 1: Test\nNo location field"
        record = parser._parse_single_record(record_text)
        assert record is None

    def test_parse_single_record_malformed_location(self):
        """Should return None for malformed location."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "### Table 1: Test\n**Location**: Lines abc-def"
        record = parser._parse_single_record(record_text)
        assert record is None


class TestTableListParserFullParsing:
    """Test complete parsing of table list files."""

    def test_parse_table_list_valid_file(self):
        """Should parse valid table list file successfully."""
        parser = TableListParser(SAMPLE_LIST)
        records = parser.parse_table_list()
        
        assert len(records) == 5
        assert all(isinstance(r, TableRecord) for r in records)
        
        # Check first record
        assert records[0].start_line == 10
        assert records[0].end_line == 15
        assert "Fighter" in records[0].description
        
        # Check last record
        assert records[4].start_line == 70
        assert records[4].end_line == 80
        assert "Saving" in records[4].description

    def test_parse_table_list_single_record(self):
        """Should parse file with single record."""
        parser = TableListParser(SINGLE_TABLE_LIST)
        records = parser.parse_table_list()
        
        assert len(records) == 1
        assert records[0].start_line == 5
        assert records[0].end_line == 10

    def test_parse_table_list_malformed_file(self):
        """Should skip malformed records and parse valid ones."""
        parser = TableListParser(MALFORMED_LIST)
        records = parser.parse_table_list()
        
        # Should parse 3 valid records (1, 4, and the one with no description)
        assert len(records) == 3
        
        # Verify valid records were parsed
        assert records[0].start_line == 10
        assert records[1].start_line == 100
        assert records[2].start_line == 300

    def test_parse_table_list_empty_file(self):
        """Should return empty list for empty file."""
        parser = TableListParser(EMPTY_FILE)
        records = parser.parse_table_list()
        assert len(records) == 0

    def test_parse_table_list_ordering(self):
        """Should preserve order of tables from file."""
        parser = TableListParser(SAMPLE_LIST)
        records = parser.parse_table_list()
        
        # Verify ascending order of line numbers
        for i in range(len(records) - 1):
            assert records[i].start_line < records[i + 1].start_line


class TestTableListParserEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_large_line_numbers(self):
        """Should handle large line numbers correctly."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "**Location**: Lines 999999-1000000"
        result = parser._extract_line_numbers(record_text)
        assert result == (999999, 1000000)

    def test_single_line_table(self):
        """Should handle table that spans single line."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = "**Location**: Lines 42-42"
        result = parser._extract_line_numbers(record_text)
        assert result == (42, 42)

    def test_multiline_description(self):
        """Should extract first line as description."""
        parser = TableListParser(SAMPLE_LIST)
        record_text = """### Table Name
        
        This is line 2
        **Location**: Lines 10-15"""
        description = parser._extract_description(record_text)
        assert "Table Name" in description
