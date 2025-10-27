#!/usr/bin/env python3
"""
Tests for OpenAITransformer component.

Tests OpenAI API integration with mocking, including retry logic,
JSON extraction, validation, and cost calculation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from openai import APIError, RateLimitError, APITimeoutError
from src.transformers.components.openai_transformer import OpenAITransformer


@pytest.fixture
def transformer():
    """Create OpenAITransformer instance with dummy API key."""
    return OpenAITransformer(api_key="sk-test-key-123", model="gpt-4o-mini")


@pytest.fixture
def sample_table():
    """Sample markdown table for testing."""
    return """| Level | XP Required |
|-------|-------------|
| 1     | 0           |
| 2     | 2000        |"""


@pytest.fixture
def sample_context():
    """Sample context for testing."""
    return "Experience points required for each fighter level."


@pytest.fixture
def sample_json_array():
    """Sample JSON array response."""
    return [
        {
            "title": "Fighter XP Table for Level 1",
            "description": "Experience requirements",
            "level": 1,
            "experience_points_required": 0
        },
        {
            "title": "Fighter XP Table for Level 2",
            "description": "Experience requirements",
            "level": 2,
            "experience_points_required": 2000
        }
    ]


class TestOpenAITransformerInitialization:
    """Test initialization and setup."""
    
    def test_initialization_defaults(self):
        """Test transformer initializes with default values."""
        transformer = OpenAITransformer(api_key="test-key")
        assert transformer.model == "gpt-4o-mini"
        assert transformer.temperature == 0.0
    
    def test_initialization_custom_model(self):
        """Test initialization with custom model."""
        transformer = OpenAITransformer(api_key="test-key", model="gpt-4")
        assert transformer.model == "gpt-4"
    
    def test_initialization_custom_temperature(self):
        """Test initialization with custom temperature."""
        transformer = OpenAITransformer(api_key="test-key", temperature=0.7)
        assert transformer.temperature == 0.7


class TestOpenAITransformerPromptConstruction:
    """Test prompt construction."""
    
    def test_construct_prompt_includes_table(self, transformer, sample_table, sample_context):
        """Test prompt includes table markdown."""
        prompt = transformer._construct_prompt(sample_table, sample_context)
        assert sample_table in prompt
    
    def test_construct_prompt_includes_context(self, transformer, sample_table, sample_context):
        """Test prompt includes context."""
        prompt = transformer._construct_prompt(sample_table, sample_context)
        assert sample_context in prompt
    
    def test_construct_prompt_includes_instructions(self, transformer, sample_table, sample_context):
        """Test prompt includes transformation instructions."""
        prompt = transformer._construct_prompt(sample_table, sample_context)
        assert "JSON" in prompt
        assert "array" in prompt.lower()
        assert "title" in prompt


class TestOpenAITransformerAPICall:
    """Test OpenAI API calls with mocking."""
    
    def test_call_openai_success(self, transformer):
        """Test successful API call."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["test"]'
        mock_response.usage.total_tokens = 100
        
        with patch.object(transformer.client.chat.completions, 'create', return_value=mock_response):
            response, tokens = transformer._call_openai_with_retry("test prompt")
            assert response == '["test"]'
            assert tokens == 100
    
    def test_call_openai_retry_on_rate_limit(self, transformer):
        """Test retry logic on rate limit error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["success"]'
        mock_response.usage.total_tokens = 100
        
        # Create properly structured RateLimitError
        mock_http_response = MagicMock()
        mock_http_response.status_code = 429
        rate_limit_error = RateLimitError(
            "Rate limit exceeded",
            response=mock_http_response,
            body={"error": "rate_limit"}
        )
        
        # First call raises RateLimitError, second succeeds
        with patch.object(
            transformer.client.chat.completions, 
            'create',
            side_effect=[rate_limit_error, mock_response]
        ):
            with patch('time.sleep'):  # Don't actually sleep in tests
                response, tokens = transformer._call_openai_with_retry("test", max_retries=3)
                assert response == '["success"]'
                assert tokens == 100
    
    def test_call_openai_retry_on_timeout(self, transformer):
        """Test retry logic on timeout error."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["success"]'
        mock_response.usage.total_tokens = 100
        
        # First call times out, second succeeds
        with patch.object(
            transformer.client.chat.completions,
            'create',
            side_effect=[APITimeoutError("Timeout"), mock_response]
        ):
            with patch('time.sleep'):
                response, tokens = transformer._call_openai_with_retry("test", max_retries=3)
                assert response == '["success"]'
    
    def test_call_openai_max_retries_exceeded(self, transformer):
        """Test failure after max retries."""
        mock_http_response = MagicMock()
        mock_http_response.status_code = 429
        rate_limit_error = RateLimitError(
            "Rate limit exceeded",
            response=mock_http_response,
            body={"error": "rate_limit"}
        )
        
        with patch.object(
            transformer.client.chat.completions,
            'create',
            side_effect=rate_limit_error
        ):
            with patch('time.sleep'):
                with pytest.raises(RateLimitError):
                    transformer._call_openai_with_retry("test", max_retries=2)


class TestOpenAITransformerJSONExtraction:
    """Test JSON extraction and validation."""
    
    def test_extract_json_pure_array(self, transformer, sample_json_array):
        """Test extraction of pure JSON array."""
        response = json.dumps(sample_json_array)
        result = transformer._extract_and_validate_json(response)
        assert result == sample_json_array
    
    def test_extract_json_with_code_block(self, transformer, sample_json_array):
        """Test extraction from markdown code block."""
        response = f"```json\n{json.dumps(sample_json_array)}\n```"
        result = transformer._extract_and_validate_json(response)
        assert result == sample_json_array
    
    def test_extract_json_with_text_before(self, transformer, sample_json_array):
        """Test extraction with explanatory text before JSON."""
        response = f"Here is the result:\n{json.dumps(sample_json_array)}"
        result = transformer._extract_and_validate_json(response)
        assert result == sample_json_array
    
    def test_extract_json_single_object_wrapped(self, transformer):
        """Test single object gets wrapped in array."""
        single_object = {"title": "Test", "data": 123}
        response = json.dumps(single_object)
        result = transformer._extract_and_validate_json(response)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == single_object
    
    def test_extract_json_invalid_json(self, transformer):
        """Test error on invalid JSON."""
        response = "This is not valid JSON"
        with pytest.raises(ValueError, match="No valid JSON"):
            transformer._extract_and_validate_json(response)
    
    def test_extract_json_malformed_json(self, transformer):
        """Test error on malformed JSON."""
        response = '[{"title": "Test", "data": }]'  # Missing value
        with pytest.raises(ValueError, match="Invalid JSON"):
            transformer._extract_and_validate_json(response)
    
    def test_validate_json_not_array(self, transformer):
        """Test error when JSON is not an array."""
        response = '{"title": "Test"}'
        # Will wrap single object, so this should succeed
        result = transformer._extract_and_validate_json(response)
        assert isinstance(result, list)
    
    def test_validate_json_empty_array(self, transformer):
        """Test error on empty array."""
        response = '[]'
        with pytest.raises(ValueError, match="empty"):
            transformer._extract_and_validate_json(response)
    
    def test_validate_json_missing_title(self, transformer):
        """Test error when object missing title field."""
        response = '[{"description": "Test", "data": 123}]'
        with pytest.raises(ValueError, match="title"):
            transformer._extract_and_validate_json(response)
    
    def test_validate_json_non_dict_object(self, transformer):
        """Test error when array contains non-dict."""
        response = '["string", "another string"]'
        with pytest.raises(ValueError, match="not a dictionary"):
            transformer._extract_and_validate_json(response)


class TestOpenAITransformerCostCalculation:
    """Test cost calculation."""
    
    def test_calculate_cost_zero_tokens(self, transformer):
        """Test cost calculation with zero tokens."""
        cost = transformer._calculate_cost(0)
        assert cost == 0.0
    
    def test_calculate_cost_100_tokens(self, transformer):
        """Test cost calculation with 100 tokens."""
        cost = transformer._calculate_cost(100)
        # 70 input tokens: (70/1M) * 0.150 = 0.0000105
        # 30 output tokens: (30/1M) * 0.600 = 0.000018
        # Total: ~0.0000285
        assert cost > 0
        assert cost < 0.0001
    
    def test_calculate_cost_1000_tokens(self, transformer):
        """Test cost calculation with 1000 tokens."""
        cost = transformer._calculate_cost(1000)
        assert cost > 0
        assert cost < 0.001


class TestOpenAITransformerIntegration:
    """Test full transformation flow with mocking."""
    
    def test_transform_table_success(self, transformer, sample_table, sample_context, sample_json_array):
        """Test successful table transformation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(sample_json_array)
        mock_response.usage.total_tokens = 150
        
        with patch.object(transformer.client.chat.completions, 'create', return_value=mock_response):
            json_objects, tokens, cost = transformer.transform_table(sample_table, sample_context)
            
            assert json_objects == sample_json_array
            assert tokens == 150
            assert cost > 0
    
    def test_transform_table_with_retry(self, transformer, sample_table, sample_context, sample_json_array):
        """Test transformation with retry on first failure."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(sample_json_array)
        mock_response.usage.total_tokens = 150
        
        mock_http_response = MagicMock()
        mock_http_response.status_code = 429
        rate_limit_error = RateLimitError(
            "Rate limit exceeded",
            response=mock_http_response,
            body={"error": "rate_limit"}
        )
        
        with patch.object(
            transformer.client.chat.completions,
            'create',
            side_effect=[rate_limit_error, mock_response]
        ):
            with patch('time.sleep'):
                json_objects, tokens, cost = transformer.transform_table(sample_table, sample_context)
                assert json_objects == sample_json_array
    
    def test_transform_table_api_failure(self, transformer, sample_table, sample_context):
        """Test transformation failure after max retries."""
        mock_request = MagicMock()
        api_error = APIError("API Error", request=mock_request, body={"error": "test"})
        
        with patch.object(
            transformer.client.chat.completions,
            'create',
            side_effect=api_error
        ):
            with patch('time.sleep'):
                with pytest.raises(APIError):
                    transformer.transform_table(sample_table, sample_context)
    
    def test_transform_table_invalid_json_response(self, transformer, sample_table, sample_context):
        """Test transformation failure with invalid JSON."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON"
        mock_response.usage.total_tokens = 100
        
        with patch.object(transformer.client.chat.completions, 'create', return_value=mock_response):
            with pytest.raises(ValueError, match="Failed to extract valid JSON"):
                transformer.transform_table(sample_table, sample_context)
    
    def test_transform_table_response_with_code_block(self, transformer, sample_table, sample_context, sample_json_array):
        """Test transformation with response wrapped in code block."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = f"```json\n{json.dumps(sample_json_array)}\n```"
        mock_response.usage.total_tokens = 150
        
        with patch.object(transformer.client.chat.completions, 'create', return_value=mock_response):
            json_objects, tokens, cost = transformer.transform_table(sample_table, sample_context)
            assert json_objects == sample_json_array


class TestOpenAITransformerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_table_input(self, transformer, sample_context):
        """Test handling of empty table input."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '[{"title": "Empty", "data": null}]'
        mock_response.usage.total_tokens = 50
        
        with patch.object(transformer.client.chat.completions, 'create', return_value=mock_response):
            json_objects, tokens, cost = transformer.transform_table("", sample_context)
            assert len(json_objects) == 1
    
    def test_empty_context_input(self, transformer, sample_table):
        """Test handling of empty context input."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '[{"title": "Test", "data": 123}]'
        mock_response.usage.total_tokens = 50
        
        with patch.object(transformer.client.chat.completions, 'create', return_value=mock_response):
            json_objects, tokens, cost = transformer.transform_table(sample_table, "")
            assert len(json_objects) == 1
    
    def test_large_token_count(self, transformer, sample_table, sample_context):
        """Test handling of large token counts."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '[{"title": "Test", "data": 123}]'
        mock_response.usage.total_tokens = 100000  # Large token count
        
        with patch.object(transformer.client.chat.completions, 'create', return_value=mock_response):
            json_objects, tokens, cost = transformer.transform_table(sample_table, sample_context)
            assert tokens == 100000
            assert cost > 0.01  # Should be significant cost
    
    def test_response_with_multiple_code_blocks(self, transformer, sample_json_array):
        """Test extraction when response has multiple code blocks."""
        response = f"""
Here's some text.

```python
print("not the json")
```

And here's the JSON:

```json
{json.dumps(sample_json_array)}
```
"""
        result = transformer._extract_and_validate_json(response)
        assert result == sample_json_array
