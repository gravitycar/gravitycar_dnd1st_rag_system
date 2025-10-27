"""
Unit tests for data models.
"""

import pytest
from src.transformers.data_models import (
    TableRecord,
    TransformationResult,
    TransformationReport,
)


class TestTableRecord:
    """Tests for TableRecord dataclass."""
    
    def test_valid_table_record(self):
        """Test creating a valid TableRecord."""
        record = TableRecord(
            start_line=10,
            end_line=20,
            description="Test table",
            table_markdown="| A | B |\n|---|---|",
            table_context="Context here"
        )
        
        assert record.start_line == 10
        assert record.end_line == 20
        assert record.description == "Test table"
        assert record.table_markdown == "| A | B |\n|---|---|"
        assert record.table_context == "Context here"
    
    def test_default_values(self):
        """Test default values for optional fields."""
        record = TableRecord(
            start_line=5,
            end_line=10,
            description="Test"
        )
        
        assert record.table_markdown == ""
        assert record.table_context == ""
    
    def test_invalid_start_line(self):
        """Test that start_line must be >= 1."""
        with pytest.raises(ValueError, match="start_line must be >= 1"):
            TableRecord(start_line=0, end_line=10, description="Test")
    
    def test_invalid_line_order(self):
        """Test that end_line must be >= start_line."""
        with pytest.raises(ValueError, match="end_line .* must be >= start_line"):
            TableRecord(start_line=10, end_line=5, description="Test")


class TestTransformationResult:
    """Tests for TransformationResult dataclass."""
    
    def test_successful_transformation(self):
        """Test a successful transformation result."""
        record = TableRecord(1, 5, "Test")
        result = TransformationResult(
            table_record=record,
            json_objects=[{"title": "Row 1"}, {"title": "Row 2"}],
            success=True,
            tokens_used=100,
            cost_usd=0.001
        )
        
        assert result.success is True
        assert result.row_count == 2
        assert result.tokens_used == 100
        assert result.cost_usd == 0.001
        assert result.error_message is None
    
    def test_failed_transformation(self):
        """Test a failed transformation result."""
        record = TableRecord(1, 5, "Test")
        result = TransformationResult(
            table_record=record,
            success=False,
            error_message="API timeout"
        )
        
        assert result.success is False
        assert result.row_count == 0
        assert result.error_message == "API timeout"
    
    def test_default_values(self):
        """Test default values."""
        record = TableRecord(1, 5, "Test")
        result = TransformationResult(table_record=record)
        
        assert result.json_objects == []
        assert result.success is False
        assert result.error_message is None
        assert result.tokens_used == 0
        assert result.cost_usd == 0.0


class TestTransformationReport:
    """Tests for TransformationReport dataclass."""
    
    def test_full_success_report(self):
        """Test report with 100% success rate."""
        report = TransformationReport(
            total_tables=10,
            successful=10,
            failed=0,
            total_tokens=5000,
            total_cost_usd=0.05,
            failures=[],
            execution_time_seconds=120.5
        )
        
        assert report.success_rate == 100.0
        assert report.total_tables == 10
        assert report.successful == 10
        assert report.failed == 0
    
    def test_partial_success_report(self):
        """Test report with partial success."""
        record = TableRecord(1, 5, "Failed table")
        failure = TransformationResult(
            table_record=record,
            success=False,
            error_message="Timeout"
        )
        
        report = TransformationReport(
            total_tables=10,
            successful=7,
            failed=3,
            total_tokens=3500,
            total_cost_usd=0.035,
            failures=[failure],
            execution_time_seconds=100.0
        )
        
        assert report.success_rate == 70.0
        assert len(report.failures) == 1
    
    def test_zero_tables(self):
        """Test report with zero tables."""
        report = TransformationReport(
            total_tables=0,
            successful=0,
            failed=0,
            total_tokens=0,
            total_cost_usd=0.0,
            failures=[],
            execution_time_seconds=0.0
        )
        
        assert report.success_rate == 0.0
    
    def test_str_representation(self):
        """Test string representation of report."""
        report = TransformationReport(
            total_tables=5,
            successful=4,
            failed=1,
            total_tokens=2500,
            total_cost_usd=0.025,
            failures=[],
            execution_time_seconds=60.0
        )
        
        report_str = str(report)
        assert "Total tables: 5" in report_str
        assert "Successful: 4 (80.0%)" in report_str
        assert "Failed: 1" in report_str
        assert "Total tokens: 2,500" in report_str
        assert "$0.0250" in report_str
        assert "60.0s" in report_str
