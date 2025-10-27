#!/usr/bin/env python3
"""
Integration tests for TableTransformer orchestrator.

Tests the complete pipeline with mocked OpenAI API responses.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.transformers.table_transformer import TableTransformer
from src.transformers.data_models import TransformationReport


@pytest.fixture
def test_markdown_file(tmp_path):
    """Create test markdown file with tables."""
    content = """# Test Document

## Section 1

Some intro text.

### Table 1: Fighter Levels

| Level | XP Required |
|-------|-------------|
| 1     | 0           |
| 2     | 2000        |

More text here.

### Table 2: Spell List

| Spell  | Level |
|--------|-------|
| Fireball | 3   |
| Magic Missile | 1 |

End of document.
"""
    file_path = tmp_path / "test_doc.md"
    file_path.write_text(content, encoding='utf-8')
    return file_path


@pytest.fixture
def test_table_list_file(tmp_path):
    """Create test table list file."""
    content = """**Table**: Fighter Level Progression
**Location**: Lines 9-12

---

**Table**: Spell List
**Location**: Lines 16-19
"""
    file_path = tmp_path / "table_list.md"
    file_path.write_text(content, encoding='utf-8')
    return file_path


@pytest.fixture
def mock_openai_responses():
    """Mock OpenAI responses for transformations."""
    return [
        # Response for first table
        [
            {"title": "Fighter Level 1", "level": 1, "xp_required": 0},
            {"title": "Fighter Level 2", "level": 2, "xp_required": 2000}
        ],
        # Response for second table
        [
            {"title": "Spell: Fireball", "spell": "Fireball", "level": 3},
            {"title": "Spell: Magic Missile", "spell": "Magic Missile", "level": 1}
        ]
    ]


class TestTableTransformerInitialization:
    """Test initialization and configuration."""
    
    def test_initialization(self, test_markdown_file, test_table_list_file, tmp_path):
        """Test transformer initializes correctly."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file),
                output_dir=str(tmp_path / "output")
            )
            
            assert transformer.markdown_file == test_markdown_file
            assert transformer.table_list_file == test_table_list_file
            assert transformer.output_dir == tmp_path / "output"
    
    def test_initialization_with_api_key(self, test_markdown_file, test_table_list_file, tmp_path):
        """Test initialization with explicit API key."""
        transformer = TableTransformer(
            markdown_file=str(test_markdown_file),
            table_list_file=str(test_table_list_file),
            output_dir=str(tmp_path / "output"),
            api_key="explicit-key"
        )
        
        assert transformer.openai_transformer is not None
    
    def test_initialization_default_output_dir(self, test_markdown_file, test_table_list_file):
        """Test default output directory."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file)
            )
            
            assert transformer.output_dir == Path("data/markdown/docling/good_pdfs/")


class TestTableTransformerDryRun:
    """Test dry run mode."""
    
    def test_dry_run_returns_estimate(self, test_markdown_file, test_table_list_file, tmp_path):
        """Test dry run returns cost estimate without processing."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file),
                output_dir=str(tmp_path / "output")
            )
            
            report = transformer.transform(dry_run=True)
            
            assert isinstance(report, TransformationReport)
            assert report.total_tables == 2
            assert report.successful == 0
            assert report.failed == 0
            assert report.total_cost_usd > 0  # Has estimate
            assert report.total_tokens == 0  # No actual processing
    
    def test_dry_run_no_api_calls(self, test_markdown_file, test_table_list_file, tmp_path):
        """Test dry run doesn't call OpenAI API."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file),
                output_dir=str(tmp_path / "output")
            )
            
            with patch.object(transformer.openai_transformer, 'transform_table') as mock_transform:
                transformer.transform(dry_run=True)
                mock_transform.assert_not_called()


class TestTableTransformerEndToEnd:
    """Test complete transformation pipeline."""
    
    def test_successful_transformation(
        self,
        test_markdown_file,
        test_table_list_file,
        tmp_path,
        mock_openai_responses
    ):
        """Test successful end-to-end transformation."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file),
                output_dir=str(tmp_path / "output"),
                delay_seconds=0  # No delay for tests
            )
            
            # Mock OpenAI transformer to return our test responses
            response_index = [0]
            def mock_transform(table, context):
                json_objects = mock_openai_responses[response_index[0]]
                response_index[0] += 1
                return (json_objects, 100, 0.001)
            
            with patch.object(transformer.openai_transformer, 'transform_table', side_effect=mock_transform):
                report = transformer.transform(dry_run=False)
            
            # Verify report
            assert report.total_tables == 2
            assert report.successful == 2
            assert report.failed == 0
            assert report.total_tokens == 200
            assert report.total_cost_usd == 0.002
            
            # Verify output file was created
            output_file = tmp_path / "output" / "test_doc_with_json_tables.md"
            assert output_file.exists()
            
            # Verify transformed content
            content = output_file.read_text(encoding='utf-8')
            assert "### Fighter Level 1" in content
            assert "### Fighter Level 2" in content
            assert "### Spell: Fireball" in content
            assert "```json" in content
            assert '"xp_required": 0' in content
            
            # Verify original tables are replaced
            assert "| Level | XP Required |" not in content
            assert "| Spell  | Level |" not in content
    
    def test_partial_failure_handling(
        self,
        test_markdown_file,
        test_table_list_file,
        tmp_path,
        mock_openai_responses
    ):
        """Test handling of partial failures."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file),
                output_dir=str(tmp_path / "output"),
                delay_seconds=0
            )
            
            # Mock: first succeeds, second fails
            call_count = [0]
            def mock_transform(table, context):
                call_count[0] += 1
                if call_count[0] == 1:
                    return (mock_openai_responses[0], 100, 0.001)
                else:
                    raise ValueError("API Error")
            
            with patch.object(transformer.openai_transformer, 'transform_table', side_effect=mock_transform):
                report = transformer.transform(dry_run=False)
            
            # Verify report shows 1 success, 1 failure
            assert report.total_tables == 2
            assert report.successful == 1
            assert report.failed == 1
            assert len(report.failures) == 1
            
            # Verify output file exists
            output_file = tmp_path / "output" / "test_doc_with_json_tables.md"
            assert output_file.exists()
            
            # Verify first table was replaced
            content = output_file.read_text(encoding='utf-8')
            assert "### Fighter Level 1" in content
            
            # Verify second table remains as markdown
            assert "| Spell  | Level |" in content


class TestTableTransformerCostLimit:
    """Test cost limit enforcement."""
    
    def test_cost_limit_prompts_user(
        self,
        test_markdown_file,
        test_table_list_file,
        tmp_path,
        monkeypatch
    ):
        """Test that exceeding cost limit prompts user."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file),
                output_dir=str(tmp_path / "output"),
                cost_limit_usd=0.0001  # Very low limit
            )
            
            # Mock input to cancel
            monkeypatch.setattr('builtins.input', lambda _: 'n')
            
            with pytest.raises(SystemExit):
                transformer.transform(dry_run=False)


class TestTableTransformerErrorHandling:
    """Test error handling scenarios."""
    
    def test_missing_markdown_file(self, test_table_list_file, tmp_path):
        """Test handling of missing markdown file."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            with pytest.raises(FileNotFoundError):
                transformer = TableTransformer(
                    markdown_file=str(tmp_path / "nonexistent.md"),
                    table_list_file=str(test_table_list_file),
                    output_dir=str(tmp_path / "output")
                )
                transformer.transform(dry_run=False)
    
    def test_missing_table_list_file(self, test_markdown_file, tmp_path):
        """Test handling of missing table list file."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            with pytest.raises(FileNotFoundError):
                transformer = TableTransformer(
                    markdown_file=str(test_markdown_file),
                    table_list_file=str(tmp_path / "nonexistent.md"),
                    output_dir=str(tmp_path / "output")
                )
                transformer.transform(dry_run=False)
    
    def test_missing_api_key(self, test_markdown_file, test_table_list_file, tmp_path):
        """Test handling of missing API key."""
        with patch('dotenv.load_dotenv'):
            with patch('os.getenv', return_value=None):
                with pytest.raises(ValueError, match="OpenAI API key not found"):
                    TableTransformer(
                        markdown_file=str(test_markdown_file),
                        table_list_file=str(test_table_list_file),
                        output_dir=str(tmp_path / "output")
                    )


class TestTableTransformerProgressTracking:
    """Test progress indicators and reporting."""
    
    def test_progress_messages_displayed(
        self,
        test_markdown_file,
        test_table_list_file,
        tmp_path,
        capsys
    ):
        """Test that progress messages are displayed."""
        with patch('src.transformers.table_transformer.TableTransformer._get_api_key', return_value='test-key'):
            transformer = TableTransformer(
                markdown_file=str(test_markdown_file),
                table_list_file=str(test_table_list_file),
                output_dir=str(tmp_path / "output"),
                delay_seconds=0
            )
            
            # Mock successful transformation
            def mock_transform(table, context):
                return ([{"title": "Test", "data": 1}], 50, 0.0005)
            
            with patch.object(transformer.openai_transformer, 'transform_table', side_effect=mock_transform):
                transformer.transform(dry_run=False)
            
            captured = capsys.readouterr()
            assert "[1/2]" in captured.out
            assert "[2/2]" in captured.out
            assert "Loading files..." in captured.out
            assert "Estimating cost..." in captured.out
            assert "Processing tables" in captured.out
