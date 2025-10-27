#!/usr/bin/env python3
"""
Tests for TableReplacer component.

Tests table replacement with heading+JSON pairs, including
heading level detection, JSON formatting, and line replacement logic.
"""

import pytest
import json
from src.transformers.components.table_replacer import TableReplacer


@pytest.fixture
def sample_markdown_lines():
    """Sample markdown lines for testing."""
    return [
        "# Document Title",
        "",
        "## Section A",
        "",
        "Some intro text.",
        "",
        "### Subsection A.1",
        "",
        "Content before table.",
        "",
        "| Column 1 | Column 2 |",
        "|----------|----------|",
        "| Data 1   | Data 2   |",
        "| Data 3   | Data 4   |",
        "",
        "Content after table.",
        "",
        "### Subsection A.2",
        "",
        "More content."
    ]


@pytest.fixture
def sample_json_objects():
    """Sample JSON objects for replacement."""
    return [
        {
            "title": "Test Table Row 1",
            "column_1": "Data 1",
            "column_2": "Data 2"
        },
        {
            "title": "Test Table Row 2",
            "column_1": "Data 3",
            "column_2": "Data 4"
        }
    ]


class TestTableReplacerInitialization:
    """Test initialization and setup."""
    
    def test_initialization(self, sample_markdown_lines):
        """Test replacer initializes correctly."""
        replacer = TableReplacer(sample_markdown_lines)
        assert len(replacer.markdown_lines) == len(sample_markdown_lines)
    
    def test_initialization_creates_copy(self, sample_markdown_lines):
        """Test that initialization creates a copy of the lines."""
        replacer = TableReplacer(sample_markdown_lines)
        replacer.markdown_lines[0] = "Modified"
        assert sample_markdown_lines[0] == "# Document Title"


class TestTableReplacerHeadingLevelExtraction:
    """Test heading level extraction."""
    
    def test_get_heading_level_h1(self):
        """Test level 1 heading detection."""
        replacer = TableReplacer(["# Heading"])
        assert replacer._get_heading_level("# Heading") == 1
    
    def test_get_heading_level_h2(self):
        """Test level 2 heading detection."""
        replacer = TableReplacer(["## Heading"])
        assert replacer._get_heading_level("## Heading") == 2
    
    def test_get_heading_level_h3(self):
        """Test level 3 heading detection."""
        replacer = TableReplacer(["### Heading"])
        assert replacer._get_heading_level("### Heading") == 3
    
    def test_get_heading_level_h4(self):
        """Test level 4 heading detection."""
        replacer = TableReplacer(["#### Heading"])
        assert replacer._get_heading_level("#### Heading") == 4
    
    def test_get_heading_level_non_heading(self):
        """Test non-heading returns None."""
        replacer = TableReplacer(["Not a heading"])
        assert replacer._get_heading_level("Not a heading") is None
    
    def test_extract_heading_level_from_context(self, sample_markdown_lines):
        """Test extracting heading level from context."""
        replacer = TableReplacer(sample_markdown_lines)
        # Table starts at line 11, nearest heading is line 7 (### = level 3)
        level = replacer.extract_heading_level_from_context(11)
        assert level == 3
    
    def test_extract_heading_level_no_heading(self):
        """Test default level when no heading found."""
        lines = ["Some text", "| Table |", "|-------|"]
        replacer = TableReplacer(lines)
        level = replacer.extract_heading_level_from_context(2)
        assert level == 4  # Default


class TestTableReplacerHeadingAndJsonBlockCreation:
    """Test creation of heading+JSON blocks."""
    
    def test_create_heading_and_json_block(self):
        """Test creating heading+JSON block from object."""
        replacer = TableReplacer([])
        json_obj = {
            "title": "Test Title",
            "data": 123
        }
        lines = replacer._create_heading_and_json_block(json_obj, heading_level=3)
        
        assert lines[0] == "### Test Title"
        assert lines[1] == ""
        assert lines[2] == "```json"
        assert "Test Title" in lines[3]
        assert lines[-1] == "```"
    
    def test_create_heading_with_level_1(self):
        """Test creating heading at level 1."""
        replacer = TableReplacer([])
        json_obj = {"title": "Test", "value": 1}
        lines = replacer._create_heading_and_json_block(json_obj, heading_level=1)
        assert lines[0] == "# Test"
    
    def test_create_heading_with_level_6(self):
        """Test creating heading at level 6."""
        replacer = TableReplacer([])
        json_obj = {"title": "Test", "value": 1}
        lines = replacer._create_heading_and_json_block(json_obj, heading_level=6)
        assert lines[0] == "###### Test"
    
    def test_json_block_formatting(self):
        """Test JSON is properly formatted in code block."""
        replacer = TableReplacer([])
        json_obj = {
            "title": "Test",
            "nested": {"key": "value"},
            "array": [1, 2, 3]
        }
        lines = replacer._create_heading_and_json_block(json_obj, heading_level=4)
        
        # Find JSON content (between ``` markers)
        json_start = lines.index("```json") + 1
        json_end = len(lines) - 1  # Before closing ```
        json_content = '\n'.join(lines[json_start:json_end])
        
        # Verify it's valid JSON
        parsed = json.loads(json_content)
        assert parsed["title"] == "Test"
        assert parsed["nested"]["key"] == "value"
    
    def test_json_block_without_title(self):
        """Test JSON object without title property."""
        replacer = TableReplacer([])
        json_obj = {"data": 123}
        lines = replacer._create_heading_and_json_block(json_obj, heading_level=4)
        assert lines[0] == "#### Untitled"


class TestTableReplacerReplacement:
    """Test table replacement logic."""
    
    def test_replace_single_table(self, sample_markdown_lines, sample_json_objects):
        """Test replacing a single table."""
        replacer = TableReplacer(sample_markdown_lines)
        
        # Table is at lines 11-14 (1-indexed)
        replacer.replace_table_with_json_rows(11, 14, sample_json_objects, heading_level=3)
        
        result = replacer.get_transformed_lines()
        
        # Check that table lines are replaced
        assert "| Column 1 | Column 2 |" not in result
        
        # Check that heading+JSON pairs exist
        result_str = '\n'.join(result)
        assert "### Test Table Row 1" in result_str
        assert "### Test Table Row 2" in result_str
        assert "```json" in result_str
    
    def test_replacement_preserves_surrounding_content(self, sample_markdown_lines, sample_json_objects):
        """Test that content before and after table is preserved."""
        replacer = TableReplacer(sample_markdown_lines)
        
        replacer.replace_table_with_json_rows(11, 14, sample_json_objects, heading_level=3)
        result = replacer.get_transformed_lines()
        
        assert "# Document Title" in result
        assert "## Section A" in result
        assert "### Subsection A.1" in result
        assert "Content before table." in result
        assert "Content after table." in result
        assert "### Subsection A.2" in result
    
    def test_replacement_line_count_changes(self, sample_markdown_lines, sample_json_objects):
        """Test that line count changes after replacement."""
        replacer = TableReplacer(sample_markdown_lines)
        original_count = len(sample_markdown_lines)
        
        replacer.replace_table_with_json_rows(11, 14, sample_json_objects, heading_level=3)
        result = replacer.get_transformed_lines()
        
        # Should have more lines (heading+JSON blocks are larger than simple table)
        assert len(result) != original_count
    
    def test_replace_with_single_object(self, sample_markdown_lines):
        """Test replacing table with single JSON object."""
        replacer = TableReplacer(sample_markdown_lines)
        single_object = [{"title": "Single Row", "data": 123}]
        
        replacer.replace_table_with_json_rows(11, 14, single_object, heading_level=3)
        result = replacer.get_transformed_lines()
        
        result_str = '\n'.join(result)
        assert "### Single Row" in result_str
        assert result_str.count("```json") == 1
    
    def test_replace_with_empty_list(self, sample_markdown_lines):
        """Test that empty JSON list doesn't crash."""
        replacer = TableReplacer(sample_markdown_lines)
        original_lines = replacer.get_transformed_lines().copy()
        
        replacer.replace_table_with_json_rows(11, 14, [], heading_level=3)
        result = replacer.get_transformed_lines()
        
        # Should not crash, lines should remain unchanged
        assert len(result) == len(original_lines)


class TestTableReplacerMultipleTables:
    """Test replacing multiple tables."""
    
    def test_replace_multiple_tables_reverse_order(self):
        """Test that tables should be replaced in reverse order to avoid line shifts."""
        lines = [
            "# Document",
            "",
            "## Section 1",
            "| T1 C1 | T1 C2 |",
            "|-------|-------|",
            "| T1 D1 | T1 D2 |",
            "",
            "## Section 2",
            "| T2 C1 | T2 C2 |",
            "|-------|-------|",
            "| T2 D1 | T2 D2 |",
            "",
            "End"
        ]
        
        replacer = TableReplacer(lines)
        
        json1 = [{"title": "Table 1 Row", "col1": "T1 D1", "col2": "T1 D2"}]
        json2 = [{"title": "Table 2 Row", "col1": "T2 D1", "col2": "T2 D2"}]
        
        # Replace second table first (reverse order)
        replacer.replace_table_with_json_rows(9, 11, json2, heading_level=2)
        # Then replace first table
        replacer.replace_table_with_json_rows(4, 6, json1, heading_level=2)
        
        result = replacer.get_transformed_lines()
        result_str = '\n'.join(result)
        
        assert "## Table 1 Row" in result_str
        assert "## Table 2 Row" in result_str
        assert "| T1 C1 | T1 C2 |" not in result_str
        assert "| T2 C1 | T2 C2 |" not in result_str


class TestTableReplacerEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_replace_at_file_start(self):
        """Test replacing table at start of file."""
        lines = [
            "| Column | Data |",
            "|--------|------|",
            "| Value  | Info |",
            "",
            "Content after"
        ]
        
        replacer = TableReplacer(lines)
        json_objs = [{"title": "Row 1", "column": "Value", "data": "Info"}]
        
        replacer.replace_table_with_json_rows(1, 3, json_objs, heading_level=4)
        result = replacer.get_transformed_lines()
        
        assert "#### Row 1" in result
        assert "Content after" in result
    
    def test_replace_at_file_end(self):
        """Test replacing table at end of file."""
        lines = [
            "# Title",
            "",
            "Content before",
            "",
            "| Column | Data |",
            "|--------|------|",
            "| Value  | Info |"
        ]
        
        replacer = TableReplacer(lines)
        json_objs = [{"title": "Last Row", "column": "Value"}]
        
        replacer.replace_table_with_json_rows(5, 7, json_objs, heading_level=4)
        result = replacer.get_transformed_lines()
        
        assert "# Title" in result
        assert "Content before" in result
        assert "#### Last Row" in result
    
    def test_json_with_unicode(self):
        """Test JSON with unicode characters."""
        replacer = TableReplacer([])
        json_obj = {
            "title": "Test with émojis 🎲",
            "data": "Special chars: é, ñ, ü"
        }
        
        lines = replacer._create_heading_and_json_block(json_obj, heading_level=4)
        result_str = '\n'.join(lines)
        
        assert "🎲" in result_str
        assert "é" in result_str
    
    def test_large_json_object(self):
        """Test handling large JSON object."""
        replacer = TableReplacer([])
        json_obj = {
            "title": "Large Object",
            "data": {f"key_{i}": f"value_{i}" for i in range(100)}
        }
        
        lines = replacer._create_heading_and_json_block(json_obj, heading_level=4)
        
        # Should not crash and should contain all keys
        result_str = '\n'.join(lines)
        assert "key_0" in result_str
        assert "key_99" in result_str
    
    def test_get_transformed_lines_returns_copy(self, sample_markdown_lines):
        """Test that get_transformed_lines returns the modified lines."""
        replacer = TableReplacer(sample_markdown_lines)
        json_objs = [{"title": "Test", "data": 1}]
        
        replacer.replace_table_with_json_rows(11, 14, json_objs, heading_level=3)
        result1 = replacer.get_transformed_lines()
        result2 = replacer.get_transformed_lines()
        
        # Both calls should return the same content
        assert result1 == result2
