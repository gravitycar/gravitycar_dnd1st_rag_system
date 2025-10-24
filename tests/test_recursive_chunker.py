#!/usr/bin/env python3
"""
Unit tests for RecursiveChunker.

Run with: pytest tests/test_recursive_chunker.py -v
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chunkers.recursive_chunker import (  # noqa: E402
    HeadingParser,
    Heading,
    ChunkBuilder,
    SpecialCaseRegistry,
    SpellSectionHandler,
    NotesRegardingHandler,
    SplitManager,
    RecursiveChunker,
)


class TestHeadingParser:
    """Tests for HeadingParser."""

    def test_parse_level_2_heading(self):
        parser = HeadingParser()
        heading = parser.parse_heading("## CHARACTER ABILITIES", 1)

        assert heading is not None
        assert heading.level == 2
        assert heading.text == "CHARACTER ABILITIES"
        assert heading.hierarchy == ["CHARACTER ABILITIES"]

    def test_parse_level_3_heading(self):
        parser = HeadingParser()
        parser.parse_heading("## CHARACTER ABILITIES", 1)
        heading = parser.parse_heading("### Strength", 2)

        assert heading is not None
        assert heading.level == 3
        assert heading.text == "Strength"
        assert heading.hierarchy == ["CHARACTER ABILITIES", "Strength"]

    def test_hierarchy_reset_on_new_level_2(self):
        parser = HeadingParser()
        parser.parse_heading("## INTRODUCTION", 1)
        heading = parser.parse_heading("## THE GAME", 2)

        assert heading.hierarchy == ["THE GAME"]
        assert "INTRODUCTION" not in heading.hierarchy

    def test_level_3_siblings(self):
        parser = HeadingParser()
        parser.parse_heading("## CHARACTER ABILITIES", 1)
        parser.parse_heading("### Strength", 2)
        heading = parser.parse_heading("### Intelligence", 3)

        assert heading.hierarchy == ["CHARACTER ABILITIES", "Intelligence"]
        assert "Strength" not in heading.hierarchy


class TestSpellSectionHandler:
    """Tests for SpellSectionHandler."""

    def test_matches_cleric_spell_hierarchy(self):
        handler = SpellSectionHandler()
        hierarchy = ["SPELL EXPLANATIONS", "CLERIC SPELLS", "First Level Spells"]

        assert handler.matches(hierarchy) is True

    def test_matches_magic_user_spell_hierarchy(self):
        handler = SpellSectionHandler()
        hierarchy = ["SPELL EXPLANATIONS", "MAGIC-USER SPELLS", "Ninth Level Spells"]

        assert handler.matches(hierarchy) is True

    def test_does_not_match_non_spell_hierarchy(self):
        handler = SpellSectionHandler()
        hierarchy = ["CHARACTER ABILITIES", "Strength"]

        assert handler.matches(hierarchy) is False

    def test_get_chunk_level(self):
        handler = SpellSectionHandler()
        assert handler.get_chunk_level([]) == 5

    def test_include_level_6_subheadings(self):
        handler = SpellSectionHandler()
        assert handler.should_include_subheadings(6) is True
        assert handler.should_include_subheadings(5) is False


class TestNotesRegardingHandler:
    """Tests for NotesRegardingHandler."""

    def test_matches_notes_regarding_cleric(self):
        handler = NotesRegardingHandler()
        hierarchy = [
            "SPELL EXPLANATIONS",
            "CLERIC SPELLS",
            "Notes Regarding Cleric Spells:",
        ]

        assert handler.matches(hierarchy) is True

    def test_matches_notes_regarding_druid(self):
        handler = NotesRegardingHandler()
        hierarchy = ["Notes Regarding Druid Spells:"]

        assert handler.matches(hierarchy) is True

    def test_does_not_match_regular_heading(self):
        handler = NotesRegardingHandler()
        hierarchy = ["First Level Spells"]

        assert handler.matches(hierarchy) is False


class TestSplitManager:
    """Tests for SplitManager."""

    def test_no_split_under_threshold(self):
        from chunkers.recursive_chunker import Chunk

        splitter = SplitManager(max_chunk_size=2000)
        chunk = Chunk(
            uid="test_1",
            book="test",
            title="Test",
            content="Short content",
            metadata={
                "hierarchy": ["Test"],
                "chunk_level": 2,
                "char_count": 13,
            },
        )

        result = splitter.split_chunk(chunk)
        assert len(result) == 1
        assert result[0].uid == "test_1"

    def test_table_compression(self):
        splitter = SplitManager()

        table_line = "|  Column 1  |  Column 2  |  Column 3  |"
        compressed = splitter.compress_table_line(table_line)

        assert compressed == "|Column 1|Column 2|Column 3|"
        assert len(compressed) < len(table_line)

    def test_split_creates_siblings(self):
        from chunkers.recursive_chunker import Chunk

        splitter = SplitManager(max_chunk_size=100)
        long_content = (
            "Paragraph 1.\n\n" + ("x" * 100) + "\n\nParagraph 2.\n\n" + ("y" * 100)
        )

        chunk = Chunk(
            uid="test_1",
            book="test",
            title="Test",
            content=long_content,
            metadata={
                "hierarchy": ["Test"],
                "chunk_level": 2,
                "char_count": len(long_content),
            },
        )

        result = splitter.split_chunk(chunk)
        assert len(result) > 1

        # Check sibling references
        for sub_chunk in result:
            assert "sibling_chunks" in sub_chunk.metadata
            assert "total_parts" in sub_chunk.metadata
            assert sub_chunk.metadata["total_parts"] == len(result)


class TestChunkBuilder:
    """Tests for ChunkBuilder."""

    def test_default_chunking_level_2_and_3(self):
        registry = SpecialCaseRegistry()
        builder = ChunkBuilder("test_book", registry)

        # Level 2 should create chunk
        h2 = Heading(level=2, text="Section", line_number=1, hierarchy=["Section"])
        assert builder.should_create_chunk(h2) is True

        # Level 3 should create chunk
        h3 = Heading(
            level=3,
            text="Subsection",
            line_number=2,
            hierarchy=["Section", "Subsection"],
        )
        assert builder.should_create_chunk(h3) is True

        # Level 4 should NOT create chunk
        h4 = Heading(
            level=4,
            text="Subsubsection",
            line_number=3,
            hierarchy=["Section", "Subsection", "Subsubsection"],
        )
        assert builder.should_create_chunk(h4) is False

    def test_spell_chunking_level_5(self):
        registry = SpecialCaseRegistry()
        builder = ChunkBuilder("test_book", registry)

        # Spell heading (level 5 in spell section)
        h5 = Heading(
            level=5,
            text="Bless",
            line_number=100,
            hierarchy=[
                "SPELL EXPLANATIONS",
                "CLERIC SPELLS",
                "First Level Spells",
                "Bless",
            ],
        )

        assert builder.should_create_chunk(h5) is True


class TestRecursiveChunker:
    """Integration tests for RecursiveChunker."""

    def test_simple_markdown_chunking(self):
        # Create temporary markdown file
        markdown_content = """## Section 1

This is section 1 content.

### Subsection 1.1

This is subsection 1.1 content.

### Subsection 1.2

This is subsection 1.2 content.

## Section 2

This is section 2 content.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(markdown_content)
            temp_md = f.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_json = f.name

        try:
            chunker = RecursiveChunker(
                temp_md, temp_json, max_chunk_size=2000, report=False
            )
            chunks = chunker.process()

            # Should have 5 chunks: Section 1, Sub 1.1, Sub 1.2, Section 2, and their content
            assert len(chunks) >= 4

            # Check hierarchies
            section1_chunks = [c for c in chunks if "Section 1" in c.title]
            assert len(section1_chunks) >= 1

            subsection_chunks = [c for c in chunks if "Subsection" in c.title]
            assert len(subsection_chunks) >= 2

            # Verify output file was created
            assert Path(temp_json).exists()

            # Verify JSON structure
            with open(temp_json, "r") as f:
                data = json.load(f)
                assert isinstance(data, list)
                assert len(data) > 0
                assert "uid" in data[0]
                assert "metadata" in data[0]
                assert "hierarchy" in data[0]["metadata"]

        finally:
            Path(temp_md).unlink(missing_ok=True)
            Path(temp_json).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
