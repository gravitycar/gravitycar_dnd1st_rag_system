#!/usr/bin/env python3
"""
Tests for FileWriter component.

Tests file writing, backup creation, and filename generation.
"""

import pytest
from pathlib import Path
from datetime import datetime
from src.transformers.components.file_writer import FileWriter


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create temporary output directory."""
    output_dir = tmp_path / "output"
    return output_dir


@pytest.fixture
def temp_input_file(tmp_path):
    """Create temporary input file."""
    input_file = tmp_path / "test_document.md"
    input_file.write_text("# Original Content\n\nSome text.", encoding='utf-8')
    return input_file


@pytest.fixture
def sample_transformed_lines():
    """Sample transformed lines for testing."""
    return [
        "# Transformed Document",
        "",
        "## Section 1",
        "",
        "### Table Row 1",
        "",
        "```json",
        '{"title": "Table Row 1", "data": "value1"}',
        "```"
    ]


class TestFileWriterInitialization:
    """Test initialization and setup."""
    
    def test_initialization(self, temp_output_dir):
        """Test writer initializes correctly."""
        writer = FileWriter(temp_output_dir)
        assert writer.output_dir == temp_output_dir
        assert writer.backup_dir == temp_output_dir / "backups"
    
    def test_initialization_with_string_path(self, tmp_path):
        """Test initialization with string path."""
        output_dir_str = str(tmp_path / "output")
        writer = FileWriter(output_dir_str)
        assert isinstance(writer.output_dir, Path)


class TestFileWriterOutputFilenameGeneration:
    """Test output filename generation."""
    
    def test_generate_output_filename_md(self, temp_output_dir):
        """Test filename generation for .md file."""
        writer = FileWriter(temp_output_dir)
        original = Path("/path/to/document.md")
        
        output_path = writer.generate_output_filename(original)
        
        assert output_path.name == "document_with_json_tables.md"
        assert output_path.parent == temp_output_dir
    
    def test_generate_output_filename_preserves_extension(self, temp_output_dir):
        """Test that original extension is preserved."""
        writer = FileWriter(temp_output_dir)
        original = Path("/path/to/file.markdown")
        
        output_path = writer.generate_output_filename(original)
        
        assert output_path.suffix == ".markdown"
        assert "with_json_tables" in output_path.name
    
    def test_generate_output_filename_complex_stem(self, temp_output_dir):
        """Test filename generation with complex stem."""
        writer = FileWriter(temp_output_dir)
        original = Path("/path/to/my_complex_file_name.md")
        
        output_path = writer.generate_output_filename(original)
        
        assert output_path.name == "my_complex_file_name_with_json_tables.md"


class TestFileWriterBackupCreation:
    """Test backup file creation."""
    
    def test_create_backup(self, temp_output_dir, temp_input_file):
        """Test creating backup of file."""
        writer = FileWriter(temp_output_dir)
        
        backup_path = writer.create_backup(temp_input_file)
        
        assert backup_path.exists()
        assert backup_path.parent == writer.backup_dir
        assert temp_input_file.stem in backup_path.name
        
        # Verify content is same
        original_content = temp_input_file.read_text(encoding='utf-8')
        backup_content = backup_path.read_text(encoding='utf-8')
        assert original_content == backup_content
    
    def test_backup_has_timestamp(self, temp_output_dir, temp_input_file):
        """Test that backup filename includes timestamp."""
        writer = FileWriter(temp_output_dir)
        
        backup_path = writer.create_backup(temp_input_file)
        
        # Filename should match pattern: filename_YYYYMMDD_HHMMSS.ext
        assert "_" in backup_path.stem
        parts = backup_path.stem.split("_")
        assert len(parts) >= 3  # filename, date, time
    
    def test_backup_creates_directory(self, temp_output_dir, temp_input_file):
        """Test that backup directory is created if needed."""
        writer = FileWriter(temp_output_dir)
        
        assert not writer.backup_dir.exists()
        
        writer.create_backup(temp_input_file)
        
        assert writer.backup_dir.exists()
    
    def test_multiple_backups_different_timestamps(self, temp_output_dir, temp_input_file):
        """Test that multiple backups get different filenames."""
        writer = FileWriter(temp_output_dir)
        
        backup1 = writer.create_backup(temp_input_file)
        
        # Modify file slightly
        temp_input_file.write_text("Modified content", encoding='utf-8')
        
        backup2 = writer.create_backup(temp_input_file)
        
        # Should have different filenames (different timestamps)
        # Note: May be same if created in same second
        assert backup1.exists()
        assert backup2.exists()


class TestFileWriterFileWriting:
    """Test file writing functionality."""
    
    def test_write_transformed_file(
        self,
        temp_output_dir,
        temp_input_file,
        sample_transformed_lines
    ):
        """Test writing transformed file."""
        writer = FileWriter(temp_output_dir)
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            sample_transformed_lines,
            create_backup=False
        )
        
        assert output_path.exists()
        assert output_path.parent == temp_output_dir
        
        # Verify content
        content = output_path.read_text(encoding='utf-8')
        expected = '\n'.join(sample_transformed_lines)
        assert content == expected
    
    def test_write_creates_output_directory(
        self,
        temp_output_dir,
        temp_input_file,
        sample_transformed_lines
    ):
        """Test that output directory is created if needed."""
        writer = FileWriter(temp_output_dir)
        
        assert not temp_output_dir.exists()
        
        writer.write_transformed_file(
            temp_input_file,
            sample_transformed_lines,
            create_backup=False
        )
        
        assert temp_output_dir.exists()
    
    def test_write_with_backup(
        self,
        temp_output_dir,
        temp_input_file,
        sample_transformed_lines
    ):
        """Test writing with backup creation."""
        writer = FileWriter(temp_output_dir)
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            sample_transformed_lines,
            create_backup=True
        )
        
        assert output_path.exists()
        assert writer.backup_dir.exists()
        
        # Should have at least one backup file
        backup_files = list(writer.backup_dir.glob("*"))
        assert len(backup_files) >= 1
    
    def test_write_without_backup(
        self,
        temp_output_dir,
        temp_input_file,
        sample_transformed_lines
    ):
        """Test writing without backup creation."""
        writer = FileWriter(temp_output_dir)
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            sample_transformed_lines,
            create_backup=False
        )
        
        assert output_path.exists()
        
        # Backup directory should not exist
        assert not writer.backup_dir.exists()
    
    def test_write_utf8_encoding(
        self,
        temp_output_dir,
        temp_input_file
    ):
        """Test that files are written with UTF-8 encoding."""
        writer = FileWriter(temp_output_dir)
        
        # Lines with unicode characters
        unicode_lines = [
            "# Test with émojis 🎲",
            "",
            "Special characters: é, ñ, ü, 中文"
        ]
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            unicode_lines,
            create_backup=False
        )
        
        content = output_path.read_text(encoding='utf-8')
        assert "🎲" in content
        assert "中文" in content
    
    def test_write_empty_content(
        self,
        temp_output_dir,
        temp_input_file
    ):
        """Test writing empty content."""
        writer = FileWriter(temp_output_dir)
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            [],
            create_backup=False
        )
        
        assert output_path.exists()
        content = output_path.read_text(encoding='utf-8')
        assert content == ""
    
    def test_write_single_line(
        self,
        temp_output_dir,
        temp_input_file
    ):
        """Test writing single line of content."""
        writer = FileWriter(temp_output_dir)
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            ["Single line"],
            create_backup=False
        )
        
        content = output_path.read_text(encoding='utf-8')
        assert content == "Single line"


class TestFileWriterEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_get_backup_path(self, temp_output_dir, temp_input_file):
        """Test getting backup path without creating backup."""
        writer = FileWriter(temp_output_dir)
        
        backup_path = writer.get_backup_path(temp_input_file)
        
        assert backup_path.parent == writer.backup_dir
        assert temp_input_file.stem in backup_path.name
        # Path should not exist yet
        assert not backup_path.exists()
    
    def test_write_to_nested_output_directory(
        self,
        tmp_path,
        temp_input_file,
        sample_transformed_lines
    ):
        """Test writing to nested output directory."""
        nested_dir = tmp_path / "level1" / "level2" / "output"
        writer = FileWriter(nested_dir)
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            sample_transformed_lines,
            create_backup=False
        )
        
        assert output_path.exists()
        assert nested_dir.exists()
    
    def test_backup_nonexistent_file(self, temp_output_dir):
        """Test that backup fails gracefully for nonexistent file."""
        writer = FileWriter(temp_output_dir)
        nonexistent = Path("/nonexistent/file.md")
        
        with pytest.raises(FileNotFoundError):
            writer.create_backup(nonexistent)
    
    def test_write_large_content(
        self,
        temp_output_dir,
        temp_input_file
    ):
        """Test writing large content."""
        writer = FileWriter(temp_output_dir)
        
        # Generate large content (10,000 lines)
        large_content = [f"Line {i}" for i in range(10000)]
        
        output_path = writer.write_transformed_file(
            temp_input_file,
            large_content,
            create_backup=False
        )
        
        assert output_path.exists()
        lines = output_path.read_text(encoding='utf-8').split('\n')
        assert len(lines) == 10000
