"""
Tests for the TablePreprocessor component.

Tests cover:
- Whitespace stripping (preserve 1 space padding)
- Separator line compression
- Empty cell handling
- Token savings calculation
- Markdown rendering preservation
"""

import pytest
from pathlib import Path
from src.transformers.components.table_preprocessor import TablePreprocessor


# Test fixtures paths
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "table_transformer"
PADDED_TABLE = FIXTURES_DIR / "padded_table.md"
MINIMAL_TABLE = FIXTURES_DIR / "minimal_table.md"
EMPTY_CELLS_TABLE = FIXTURES_DIR / "table_with_empty_cells.md"


class TestTablePreprocessorInitialization:
    """Test preprocessor initialization."""

    def test_init(self):
        """Should initialize successfully."""
        preprocessor = TablePreprocessor()
        assert preprocessor is not None


class TestTablePreprocessorSeparatorDetection:
    """Test separator line detection."""

    def test_is_separator_line_standard(self):
        """Should detect standard separator line."""
        preprocessor = TablePreprocessor()
        line = "|---|---|---|"
        assert preprocessor.is_separator_line(line) is True

    def test_is_separator_line_with_spaces(self):
        """Should detect separator with spaces."""
        preprocessor = TablePreprocessor()
        line = "| --- | --- | --- |"
        assert preprocessor.is_separator_line(line) is True

    def test_is_separator_line_long_hyphens(self):
        """Should detect separator with many hyphens."""
        preprocessor = TablePreprocessor()
        line = "|---------------|---------|"
        assert preprocessor.is_separator_line(line) is True

    def test_is_separator_line_with_alignment(self):
        """Should detect separator with alignment markers."""
        preprocessor = TablePreprocessor()
        line = "|:---|:---:|---:|"
        assert preprocessor.is_separator_line(line) is True

    def test_is_not_separator_line_header(self):
        """Should not detect header as separator."""
        preprocessor = TablePreprocessor()
        line = "| Column A | Column B |"
        assert preprocessor.is_separator_line(line) is False

    def test_is_not_separator_line_data(self):
        """Should not detect data row as separator."""
        preprocessor = TablePreprocessor()
        line = "| 1 | 2 | 3 |"
        assert preprocessor.is_separator_line(line) is False

    def test_is_not_separator_line_no_pipes(self):
        """Should not detect line without pipes."""
        preprocessor = TablePreprocessor()
        line = "---"
        assert preprocessor.is_separator_line(line) is False

    def test_is_not_separator_line_missing_start_pipe(self):
        """Should not detect line missing start pipe."""
        preprocessor = TablePreprocessor()
        line = "---|---|"
        assert preprocessor.is_separator_line(line) is False


class TestTablePreprocessorCellStripping:
    """Test cell whitespace stripping."""

    def test_strip_cell_whitespace_padded(self):
        """Should strip excessive whitespace from cells."""
        preprocessor = TablePreprocessor()
        line = "|   Column A   |   Column B   |"
        result = preprocessor.strip_cell_whitespace(line)
        assert result == "| Column A | Column B |"

    def test_strip_cell_whitespace_minimal(self):
        """Should preserve already minimal cells."""
        preprocessor = TablePreprocessor()
        line = "| Column A | Column B |"
        result = preprocessor.strip_cell_whitespace(line)
        assert result == "| Column A | Column B |"

    def test_strip_cell_whitespace_no_padding(self):
        """Should add 1 space padding to cells without padding."""
        preprocessor = TablePreprocessor()
        line = "|ColumnA|ColumnB|"
        result = preprocessor.strip_cell_whitespace(line)
        assert result == "| ColumnA | ColumnB |"

    def test_strip_cell_whitespace_empty_cells(self):
        """Should handle empty cells correctly."""
        preprocessor = TablePreprocessor()
        line = "| Data |  | More |"
        result = preprocessor.strip_cell_whitespace(line)
        assert result == "| Data | | More |"  # Empty cell becomes single space

    def test_strip_cell_whitespace_mixed_spacing(self):
        """Should handle mixed spacing."""
        preprocessor = TablePreprocessor()
        line = "|  A  |B|   C   |"
        result = preprocessor.strip_cell_whitespace(line)
        assert result == "| A | B | C |"

    def test_strip_cell_whitespace_tabs(self):
        """Should handle tabs as whitespace."""
        preprocessor = TablePreprocessor()
        line = "|\tColumn\t|\tValue\t|"
        result = preprocessor.strip_cell_whitespace(line)
        assert result == "| Column | Value |"


class TestTablePreprocessorSeparatorCompression:
    """Test separator line compression."""

    def test_compress_separator_line_long(self):
        """Should compress long separator lines."""
        preprocessor = TablePreprocessor()
        line = "|---------------|---------|"
        result = preprocessor.compress_separator_line(line)
        assert result == "|---|---|"

    def test_compress_separator_line_with_spaces(self):
        """Should compress separators with spaces."""
        preprocessor = TablePreprocessor()
        line = "| ------------- | --------- |"
        result = preprocessor.compress_separator_line(line)
        assert result == "|---|---|"

    def test_compress_separator_line_already_minimal(self):
        """Should preserve already minimal separators."""
        preprocessor = TablePreprocessor()
        line = "|---|---|"
        result = preprocessor.compress_separator_line(line)
        assert result == "|---|---|"

    def test_compress_separator_line_with_alignment(self):
        """Should compress separators with alignment markers."""
        preprocessor = TablePreprocessor()
        line = "|:-------------|:---------:|----------:|"
        result = preprocessor.compress_separator_line(line)
        # Note: This implementation doesn't preserve alignment markers
        # That's acceptable for token optimization
        assert result == "|---|---|---|"

    def test_compress_separator_line_variable_lengths(self):
        """Should compress separators with variable hyphen counts."""
        preprocessor = TablePreprocessor()
        line = "|---|---------|---------------|---|"
        result = preprocessor.compress_separator_line(line)
        assert result == "|---|---|---|---|"


class TestTablePreprocessorFullPreprocessing:
    """Test complete table preprocessing."""

    def test_preprocess_table_padded(self):
        """Should preprocess table with excessive padding."""
        preprocessor = TablePreprocessor()
        with open(PADDED_TABLE, 'r') as f:
            table = f.read()
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        # Verify structure preserved
        assert preprocessed.count('|') == table.count('|')
        assert preprocessed.count('\n') == table.count('\n')
        
        # Verify reduction occurred
        assert stats['preprocessed_length'] < stats['original_length']
        assert stats['reduction_percent'] > 0

    def test_preprocess_table_minimal(self):
        """Should handle already minimal table."""
        preprocessor = TablePreprocessor()
        with open(MINIMAL_TABLE, 'r') as f:
            table = f.read()
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        # Should be nearly identical
        assert stats['reduction_percent'] < 5  # Allow for minor differences

    def test_preprocess_table_empty_cells(self):
        """Should handle tables with empty cells."""
        preprocessor = TablePreprocessor()
        with open(EMPTY_CELLS_TABLE, 'r') as f:
            table = f.read()
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        # Should preserve structure
        lines = preprocessed.split('\n')
        assert all('|' in line for line in lines if line.strip())

    def test_preprocess_table_multiline(self):
        """Should process multi-line tables correctly."""
        preprocessor = TablePreprocessor()
        table = """| Header 1   | Header 2   | Header 3   |
|------------|------------|------------|
| Row 1      | Data A     | Data B     |
| Row 2      | Data C     | Data D     |"""
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        # Verify all lines processed
        assert stats['lines_processed'] == 4
        
        # Verify structure
        lines = preprocessed.split('\n')
        assert len(lines) == 4

    def test_preprocess_table_blank_lines(self):
        """Should preserve blank lines."""
        preprocessor = TablePreprocessor()
        table = """| Header |
|--------|
| Data   |

| Footer |"""
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        # Blank line should be preserved
        assert '\n\n' in preprocessed

    def test_preprocess_table_statistics(self):
        """Should return accurate statistics."""
        preprocessor = TablePreprocessor()
        table = "|   A   |   B   |\n|-------|-------|\n| 1     | 2     |"
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        assert 'original_length' in stats
        assert 'preprocessed_length' in stats
        assert 'reduction_percent' in stats
        assert 'lines_processed' in stats
        
        assert stats['original_length'] == len(table)
        assert stats['preprocessed_length'] == len(preprocessed)
        assert stats['lines_processed'] == 3


class TestTablePreprocessorTokenSavings:
    """Test token savings calculations."""

    def test_calculate_token_savings_significant(self):
        """Should calculate savings for significant reduction."""
        preprocessor = TablePreprocessor()
        original_length = 1000
        preprocessed_length = 600
        
        savings = preprocessor.calculate_token_savings(
            original_length, 
            preprocessed_length
        )
        
        assert savings['original_tokens'] == 250.0  # 1000 / 4
        assert savings['preprocessed_tokens'] == 150.0  # 600 / 4
        assert savings['tokens_saved'] == 100.0
        assert savings['percent_saved'] == 40.0

    def test_calculate_token_savings_minimal(self):
        """Should calculate savings for minimal reduction."""
        preprocessor = TablePreprocessor()
        original_length = 100
        preprocessed_length = 95
        
        savings = preprocessor.calculate_token_savings(
            original_length, 
            preprocessed_length
        )
        
        assert savings['original_tokens'] == 25.0
        assert savings['preprocessed_tokens'] == 23.8
        assert savings['tokens_saved'] == 1.2
        assert savings['percent_saved'] == 5.0  # Rounded to 1 decimal

    def test_calculate_token_savings_no_change(self):
        """Should handle case with no savings."""
        preprocessor = TablePreprocessor()
        original_length = 100
        preprocessed_length = 100
        
        savings = preprocessor.calculate_token_savings(
            original_length, 
            preprocessed_length
        )
        
        assert savings['tokens_saved'] == 0.0
        assert savings['percent_saved'] == 0.0

    def test_calculate_token_savings_zero_length(self):
        """Should handle zero length input."""
        preprocessor = TablePreprocessor()
        
        savings = preprocessor.calculate_token_savings(0, 0)
        
        assert savings['original_tokens'] == 0.0
        assert savings['percent_saved'] == 0.0


class TestTablePreprocessorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_preprocess_empty_string(self):
        """Should handle empty string."""
        preprocessor = TablePreprocessor()
        preprocessed, stats = preprocessor.preprocess_table("")
        
        assert preprocessed == ""
        assert stats['original_length'] == 0
        assert stats['preprocessed_length'] == 0

    def test_preprocess_single_line(self):
        """Should handle single line."""
        preprocessor = TablePreprocessor()
        table = "| Header |"
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        assert '|' in preprocessed
        assert stats['lines_processed'] == 1

    def test_preprocess_no_pipes(self):
        """Should handle text without pipes."""
        preprocessor = TablePreprocessor()
        table = "Not a table"
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        # Should pass through unchanged
        assert preprocessed == table

    def test_preprocess_malformed_table(self):
        """Should handle malformed tables gracefully."""
        preprocessor = TablePreprocessor()
        table = "| Header |\n|---\n| Data"  # Missing closing pipes
        
        preprocessed, stats = preprocessor.preprocess_table(table)
        
        # Should process without crashing
        assert preprocessed is not None

    def test_strip_cell_single_pipe(self):
        """Should handle line with single pipe."""
        preprocessor = TablePreprocessor()
        line = "|"
        
        result = preprocessor.strip_cell_whitespace(line)
        
        assert result == "|"

    def test_compress_separator_single_pipe(self):
        """Should handle separator with single pipe."""
        preprocessor = TablePreprocessor()
        line = "|"
        
        result = preprocessor.compress_separator_line(line)
        
        assert result == "|"
