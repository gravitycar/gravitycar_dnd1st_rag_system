#!/usr/bin/env python3
"""
FileWriter component for table transformer.

Handles writing transformed markdown files with backup creation.
"""

import logging
from pathlib import Path
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


class FileWriter:
    """
    Writes transformed markdown content to files with backup support.
    
    Features:
    - UTF-8 encoding for all files
    - Automatic backup creation with timestamps
    - Output filename generation
    - Directory creation as needed
    """
    
    def __init__(self, output_dir: Path):
        """
        Initialize file writer.
        
        Args:
            output_dir: Directory where transformed files will be written
        """
        self.output_dir = Path(output_dir)
        self.backup_dir = self.output_dir / "backups"
    
    def write_transformed_file(
        self,
        original_path: Path,
        transformed_lines: List[str],
        create_backup: bool = True
    ) -> Path:
        """
        Write transformed markdown to output file.
        
        Args:
            original_path: Path to original markdown file
            transformed_lines: Lines of transformed markdown content
            create_backup: Whether to create backup of original
            
        Returns:
            Path to written output file
            
        Raises:
            OSError: If file writing fails
        """
        # Generate output filename
        output_path = self.generate_output_filename(original_path)
        
        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup if requested
        if create_backup and original_path.exists():
            self.create_backup(original_path)
        
        # Write transformed content
        content = '\n'.join(transformed_lines)
        output_path.write_text(content, encoding='utf-8')
        
        logger.info(f"Wrote transformed file: {output_path}")
        return output_path
    
    def create_backup(self, original_path: Path) -> Path:
        """
        Create timestamped backup of original file.
        
        Args:
            original_path: Path to file to backup
            
        Returns:
            Path to created backup file
            
        Raises:
            OSError: If backup creation fails
        """
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Generate backup filename
        backup_filename = f"{original_path.stem}_{timestamp}{original_path.suffix}"
        backup_path = self.backup_dir / backup_filename
        
        # Copy file to backup
        content = original_path.read_text(encoding='utf-8')
        backup_path.write_text(content, encoding='utf-8')
        
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    
    def generate_output_filename(self, original_path: Path) -> Path:
        """
        Generate output filename from original path.
        
        Adds '_with_json_tables' suffix before extension.
        Example: 'document.md' -> 'document_with_json_tables.md'
        
        Args:
            original_path: Path to original file
            
        Returns:
            Path to output file in output directory
        """
        output_filename = f"{original_path.stem}_with_json_tables{original_path.suffix}"
        return self.output_dir / output_filename
    
    def get_backup_path(self, original_path: Path) -> Path:
        """
        Get the backup path that would be used for a file.
        
        Note: This generates a path with current timestamp.
        The actual backup filename will differ if created later.
        
        Args:
            original_path: Path to original file
            
        Returns:
            Path where backup would be created (with current timestamp)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{original_path.stem}_{timestamp}{original_path.suffix}"
        return self.backup_dir / backup_filename
