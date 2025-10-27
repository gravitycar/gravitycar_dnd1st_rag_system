"""
Data models for table transformation.

This module defines the core data structures used throughout the table
transformation pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TableRecord:
    """
    Represents a single table to be transformed.
    
    Attributes:
        start_line: Starting line number in markdown file (1-indexed)
        end_line: Ending line number in markdown file (1-indexed)
        description: Description of table from table list metadata
        table_markdown: Raw markdown content of the table
        table_context: Contextual text surrounding the table
    """
    start_line: int
    end_line: int
    description: str
    table_markdown: str = ""
    table_context: str = ""
    
    def __post_init__(self):
        """Validate line numbers."""
        if self.start_line < 1:
            raise ValueError(f"start_line must be >= 1, got {self.start_line}")
        if self.end_line < self.start_line:
            raise ValueError(
                f"end_line ({self.end_line}) must be >= start_line ({self.start_line})"
            )


@dataclass
class TransformationResult:
    """
    Result of a single table transformation.
    
    Attributes:
        table_record: The original table record
        json_objects: Array of JSON objects, one per row
        success: Whether transformation succeeded
        error_message: Error message if transformation failed
        tokens_used: Total tokens consumed by OpenAI API
        cost_usd: Cost in USD for this transformation
    """
    table_record: TableRecord
    json_objects: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = False
    error_message: Optional[str] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    
    @property
    def row_count(self) -> int:
        """Number of rows transformed."""
        return len(self.json_objects)


@dataclass
class TransformationReport:
    """
    Summary of entire transformation process.
    
    Attributes:
        total_tables: Total number of tables processed
        successful: Number of successful transformations
        failed: Number of failed transformations
        total_tokens: Total tokens used across all transformations
        total_cost_usd: Total cost in USD
        failures: List of failed transformation results
        execution_time_seconds: Total execution time
    """
    total_tables: int
    successful: int
    failed: int
    total_tokens: int
    total_cost_usd: float
    failures: List[TransformationResult]
    execution_time_seconds: float
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful transformations."""
        if self.total_tables == 0:
            return 0.0
        return (self.successful / self.total_tables) * 100
    
    def __str__(self) -> str:
        """Human-readable summary."""
        return (
            f"Transformation Report:\n"
            f"  Total tables: {self.total_tables}\n"
            f"  Successful: {self.successful} ({self.success_rate:.1f}%)\n"
            f"  Failed: {self.failed}\n"
            f"  Total tokens: {self.total_tokens:,}\n"
            f"  Total cost: ${self.total_cost_usd:.4f}\n"
            f"  Execution time: {self.execution_time_seconds:.1f}s"
        )
