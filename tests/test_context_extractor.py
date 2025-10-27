#!/usr/bin/env python3
"""
Tests for ContextExtractor component.

Tests context extraction bounded by markdown headings, including
edge cases like tables at file boundaries and nested headings.
"""

import pytest
from pathlib import Path
from src.transformers.components.context_extractor import ContextExtractor


@pytest.fixture
def context_test_file():
    """Load context test file fixture."""
    fixture_path = Path("tests/fixtures/table_transformer/context_test_file.md")
    with open(fixture_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Strip newlines but preserve line structure
    lines = [line.rstrip('\n') for line in lines]
    return lines


@pytest.fixture
def extractor(context_test_file):
    """Create ContextExtractor instance with test file."""
    return ContextExtractor(context_test_file)


class TestContextExtractorInitialization:
    """Test initialization and setup."""
    
    def test_initialization(self, context_test_file):
        """Test extractor initializes correctly."""
        extractor = ContextExtractor(context_test_file)
        assert extractor.markdown_lines == context_test_file
        assert len(extractor.markdown_lines) > 0


class TestContextExtractorHeadingDetection:
    """Test heading level detection."""
    
    def test_get_heading_level_h1(self, extractor):
        """Test level 1 heading detection."""
        assert extractor.get_heading_level("# Document Title") == 1
    
    def test_get_heading_level_h2(self, extractor):
        """Test level 2 heading detection."""
        assert extractor.get_heading_level("## Section A") == 2
    
    def test_get_heading_level_h3(self, extractor):
        """Test level 3 heading detection."""
        assert extractor.get_heading_level("### Subsection A.1") == 3
    
    def test_get_heading_level_h4(self, extractor):
        """Test level 4 heading detection."""
        assert extractor.get_heading_level("#### Table 1: Simple Data") == 4
    
    def test_get_heading_level_h5(self, extractor):
        """Test level 5 heading detection."""
        assert extractor.get_heading_level("##### Even Deeper") == 5
    
    def test_get_heading_level_h6(self, extractor):
        """Test level 6 heading detection."""
        assert extractor.get_heading_level("###### Level 6") == 6
    
    def test_get_heading_level_non_heading(self, extractor):
        """Test non-heading line returns None."""
        assert extractor.get_heading_level("This is not a heading") is None
    
    def test_get_heading_level_table_line(self, extractor):
        """Test table line returns None."""
        assert extractor.get_heading_level("| Column | Data |") is None
    
    def test_get_heading_level_with_whitespace(self, extractor):
        """Test heading detection with leading/trailing whitespace."""
        assert extractor.get_heading_level("  ## Section A  ") == 2


class TestContextExtractorFindHeadingBefore:
    """Test finding nearest heading before a line."""
    
    def test_find_heading_before_simple(self, extractor):
        """Test finding heading before a line."""
        # Line 11 is "Content for subsection A.1 goes here."
        # Nearest heading is line 9: "### Subsection A.1"
        heading_line, level = extractor.find_heading_before(11)
        assert heading_line == 9
        assert level == 3
    
    def test_find_heading_before_table(self, extractor):
        """Test finding heading before a table."""
        # Line 15 is "| Column 1 | Column 2 |"
        # Nearest heading is line 13: "#### Table 1: Simple Data"
        heading_line, level = extractor.find_heading_before(15)
        assert heading_line == 13
        assert level == 4
    
    def test_find_heading_before_at_file_start(self, extractor):
        """Test finding heading when near start of file."""
        # Line 3 is "This is the introduction to the document."
        # Nearest heading is line 1: "# Document Title"
        heading_line, level = extractor.find_heading_before(3)
        assert heading_line == 1
        assert level == 1
    
    def test_find_heading_before_no_heading(self, extractor):
        """Test behavior when no heading found (before line 1)."""
        # Create extractor with no headings
        lines = ["No heading here", "Just content", "More content"]
        extractor_no_heading = ContextExtractor(lines)
        heading_line, level = extractor_no_heading.find_heading_before(3)
        assert heading_line == 1  # Start of file
        assert level == 6  # Lowest priority
    
    def test_find_heading_before_immediate_heading(self, extractor):
        """Test when line immediately after heading."""
        # Line 6 is right after "## Section A" (line 5)
        heading_line, level = extractor.find_heading_before(6)
        assert heading_line == 5
        assert level == 2


class TestContextExtractorFindNextHeading:
    """Test finding next heading of equal or higher level."""
    
    def test_find_next_heading_simple(self, extractor):
        """Test finding next heading at same level."""
        # After line 22 ("Additional notes about the table."),
        # next heading at level 4 or higher is line 24: "#### Another Heading"
        next_line = extractor.find_next_heading(22, min_level=4)
        assert next_line == 24
    
    def test_find_next_heading_higher_level(self, extractor):
        """Test finding next heading at higher level (fewer #)."""
        # After line 13 ("#### Table 1: Simple Data"),
        # next heading at level 3 or higher is line 28: "### Subsection A.2"
        next_line = extractor.find_next_heading(13, min_level=3)
        assert next_line == 28
    
    def test_find_next_heading_skip_lower_levels(self, extractor):
        """Test that lower level headings are skipped."""
        # After line 62 ("#### Deep Heading"), looking for level 3 or higher
        # Should skip "##### Even Deeper" and find "#### Back to Level 4" at line 75 or "## Section E" at line 79
        next_line = extractor.find_next_heading(62, min_level=3)
        # Should find "#### Back to Level 4" at line 75 or "## Section E" at line 79
        assert next_line in [75, 79]
    
    def test_find_next_heading_at_file_end(self, extractor):
        """Test behavior when no next heading found."""
        # After last line, should return len(lines) + 1
        next_line = extractor.find_next_heading(len(extractor.markdown_lines), min_level=1)
        assert next_line == len(extractor.markdown_lines) + 1
    
    def test_find_next_heading_equal_level(self, extractor):
        """Test finding heading at exactly the same level."""
        # After "## Section A" (line 5), next level 2 is "## Section B" (line 32)
        next_line = extractor.find_next_heading(5, min_level=2)
        assert next_line == 32


class TestContextExtractorFilterTableLines:
    """Test filtering table lines from context."""
    
    def test_filter_table_lines_removes_tables(self, extractor):
        """Test that table lines are removed."""
        lines = [
            "This is text",
            "| Column | Data |",
            "|--------|------|",
            "| Value  | Info |",
            "More text"
        ]
        filtered = extractor.filter_table_lines(lines)
        assert len(filtered) == 2
        assert "This is text" in filtered
        assert "More text" in filtered
    
    def test_filter_table_lines_preserves_non_tables(self, extractor):
        """Test that non-table lines are preserved."""
        lines = [
            "# Heading",
            "Paragraph text",
            "Another paragraph",
            "## Another heading"
        ]
        filtered = extractor.filter_table_lines(lines)
        assert len(filtered) == 4
        assert filtered == lines
    
    def test_filter_table_lines_handles_whitespace(self, extractor):
        """Test table detection with leading whitespace."""
        lines = [
            "Text",
            "  | Column | Data |",
            "   |--------|------|",
            "Text again"
        ]
        filtered = extractor.filter_table_lines(lines)
        assert len(filtered) == 2
        assert "Text" in filtered
        assert "Text again" in filtered
    
    def test_filter_table_lines_empty_list(self, extractor):
        """Test filtering empty list."""
        filtered = extractor.filter_table_lines([])
        assert filtered == []


class TestContextExtractorExtractContext:
    """Test full context extraction."""
    
    def test_extract_context_basic(self, extractor, context_test_file):
        """Test basic context extraction for a table."""
        # Table at lines 15-18 ("#### Table 1: Simple Data")
        # Context should be bounded by line 13 (heading) and line 22 (next heading)
        context = extractor.extract_context(15, 18)
        
        # Should include description line but not table lines
        assert "This table shows simple data." in context
        assert "Additional notes about the table." in context
        assert "| Column 1 | Column 2 |" not in context
        assert "| Data 1   | Data 2   |" not in context
    
    def test_extract_context_includes_heading(self, extractor, context_test_file):
        """Test that context includes the heading."""
        # Table at lines 15-18
        context = extractor.extract_context(15, 18)
        assert "#### Table 1: Simple Data" in context
    
    def test_extract_context_stops_at_same_level_heading(self, extractor):
        """Test that context stops at next heading of same level."""
        # Table at lines 15-18 (level 4 heading)
        # Should stop at line 22 ("#### Another Heading")
        context = extractor.extract_context(15, 18)
        assert "#### Another Heading" not in context
        assert "This is content after the first table." not in context
    
    def test_extract_context_table_at_section_start(self, extractor):
        """Test context for table right after heading."""
        # Table at lines 32-34 is right after "## Section B"
        context = extractor.extract_context(32, 34)
        assert "## Section B" in context
        assert "This section describes section B content." in context
        assert "| Column A | Column B |" not in context
    
    def test_extract_context_nested_heading(self, extractor):
        """Test context extraction with nested headings."""
        # Table at lines 64-67 under "#### Deep Heading" (line 62)
        context = extractor.extract_context(64, 67)
        assert "#### Deep Heading" in context
        # Should include content after table (line 69) until next heading at level <= 4
        assert "Content after nested table." in context
        # Level 5 heading is LOWER level (more #), so it's included until we find level <= 4
        assert "##### Even Deeper" in context
        assert "More content." in context
        # Should stop at "#### Back to Level 4" (level 4, equal to our min_level)
        assert "#### Back to Level 4" not in context
    
    def test_extract_context_invalid_line_numbers(self, extractor):
        """Test error handling for invalid line numbers."""
        with pytest.raises(ValueError, match="Invalid line numbers"):
            extractor.extract_context(0, 10)
        
        with pytest.raises(ValueError, match="Invalid line numbers"):
            extractor.extract_context(10, 10000)
        
        with pytest.raises(ValueError, match="Invalid range"):
            extractor.extract_context(20, 10)
    
    def test_extract_context_single_line_table(self, extractor):
        """Test extraction for single-line table."""
        # Table at line 44 (single line table)
        context = extractor.extract_context(44, 44)
        # Should have context around it
        assert len(context) > 0
        assert "| Test | Data |" not in context


class TestContextExtractorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_context_with_no_headings(self):
        """Test context extraction when file has no headings."""
        lines = [
            "Line 1",
            "Line 2",
            "| Table | Line |",
            "|-------|------|",
            "Line 5"
        ]
        extractor = ContextExtractor(lines)
        context = extractor.extract_context(3, 4)
        
        # Should get entire file minus table
        assert "Line 1" in context
        assert "Line 2" in context
        assert "Line 5" in context
        assert "| Table | Line |" not in context
    
    def test_context_table_at_very_start(self):
        """Test table at the very start of file."""
        lines = [
            "| Column | Data |",
            "|--------|------|",
            "| Value  | Info |",
            "",
            "## Heading After"
        ]
        extractor = ContextExtractor(lines)
        context = extractor.extract_context(1, 3)
        
        # Should get empty context (no heading before, stops at next heading)
        assert "| Column | Data |" not in context
        # But should include lines between start and first heading
        assert len(context.strip()) == 0
    
    def test_context_table_at_very_end(self):
        """Test table at the very end of file."""
        lines = [
            "## Section",
            "Content here.",
            "| Column | Data |",
            "|--------|------|",
            "| Value  | Info |"
        ]
        extractor = ContextExtractor(lines)
        context = extractor.extract_context(3, 5)
        
        # Should include heading and content, but not table
        assert "## Section" in context
        assert "Content here." in context
        assert "| Column | Data |" not in context
    
    def test_multiple_tables_same_section(self):
        """Test context extraction when multiple tables in same section."""
        lines = [
            "## Section",
            "Description",
            "| Table 1 | Data |",
            "|---------|------|",
            "Between tables text",
            "| Table 2 | Data |",
            "|---------|------|",
            "## Next Section"
        ]
        extractor = ContextExtractor(lines)
        
        # Context for first table
        context1 = extractor.extract_context(3, 4)
        assert "## Section" in context1
        assert "Description" in context1
        assert "Between tables text" in context1
        assert "| Table 1 | Data |" not in context1
        # Should include second table content (it's not filtered in this extraction)
        assert "| Table 2 | Data |" not in context1
        
        # Context for second table
        context2 = extractor.extract_context(6, 7)
        assert "## Section" in context2
        assert "Between tables text" in context2
