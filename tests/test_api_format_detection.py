#!/usr/bin/env python3
"""
Integration tests for Markdown/HTML format detection in Flask API.

Tests that the API correctly returns Markdown for CLI clients and HTML for web clients.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.api import app, markdown_converter


@pytest.fixture
def client():
    """Create Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_token_validator():
    """Mock token validator to bypass authentication."""
    with patch('src.api.token_validator') as mock:
        mock.validate_token.return_value = {
            'valid': True,
            'user_info': {
                'id': 'test_user_123',
                'email': 'test@example.com'
            }
        }
        yield mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter to bypass rate limiting."""
    with patch('src.api.rate_limiter') as mock:
        mock.allow_request.return_value = (True, {
            'remaining_burst': 10,
            'daily_remaining': 25,
            'reason': None
        })
        yield mock


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker to bypass budget checks."""
    with patch('src.api.cost_tracker') as mock:
        mock.is_budget_exceeded.return_value = (False, {})
        mock.record_query.return_value = {
            'query_cost': 0.0001,
            'daily_cost': 0.0050,
            'daily_budget': 1.0
        }
        yield mock


@pytest.fixture
def mock_rag():
    """Mock RAG system to return predictable responses."""
    with patch('src.api.get_rag') as mock_get_rag:
        mock_rag_instance = MagicMock()
        mock_rag_instance.query.return_value = {
            'answer': '# Beholder\n\nA **beholder** is a floating spherical creature.',
            'diagnostics': ['Retrieved 3 chunks in 0.15s'],
            'errors': [],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        mock_get_rag.return_value = mock_rag_instance
        yield mock_rag_instance


class TestFormatDetection:
    """Test Markdown vs HTML format detection based on User-Agent."""
    
    def test_cli_request_returns_markdown(
        self, client, mock_token_validator, mock_rate_limiter, 
        mock_cost_tracker, mock_rag
    ):
        """CLI requests (curl) should receive Markdown format."""
        response = client.post('/api/query',
            json={'question': 'What is a beholder?', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'curl/7.68.0'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should return Markdown
        assert data['answer_format'] == 'markdown'
        # Answer should contain markdown syntax
        assert '**' in data['answer'] or '#' in data['answer']
        # Should NOT contain HTML tags
        assert '<strong>' not in data['answer']
    
    def test_web_request_returns_html(
        self, client, mock_token_validator, mock_rate_limiter,
        mock_cost_tracker, mock_rag
    ):
        """Web requests (browsers) should receive HTML format."""
        response = client.post('/api/query',
            json={'question': 'What is a beholder?', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should return HTML
        assert data['answer_format'] == 'html'
        # Answer should contain HTML tags
        assert '<h1>' in data['answer'] or '<p>' in data['answer']
        assert '<strong>' in data['answer']
        # Should NOT contain markdown syntax
        assert '**' not in data['answer']
    
    def test_python_requests_returns_markdown(
        self, client, mock_token_validator, mock_rate_limiter,
        mock_cost_tracker, mock_rag
    ):
        """Python requests library should receive Markdown."""
        response = client.post('/api/query',
            json={'question': 'What is a beholder?', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'python-requests/2.31.0'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['answer_format'] == 'markdown'
        assert '**' in data['answer'] or '#' in data['answer']
    
    def test_axios_returns_html(
        self, client, mock_token_validator, mock_rate_limiter,
        mock_cost_tracker, mock_rag
    ):
        """Axios (React apps) should receive HTML."""
        response = client.post('/api/query',
            json={'question': 'What is a beholder?', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'axios/1.6.0'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['answer_format'] == 'html'
        assert '<' in data['answer'] and '>' in data['answer']
    
    def test_unknown_user_agent_defaults_to_markdown(
        self, client, mock_token_validator, mock_rate_limiter,
        mock_cost_tracker, mock_rag
    ):
        """Unknown User-Agents should default to Markdown (backwards compatible)."""
        response = client.post('/api/query',
            json={'question': 'What is a beholder?', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'CustomClient/1.0'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should default to Markdown for backwards compatibility
        assert data['answer_format'] == 'markdown'
        assert '**' in data['answer'] or '#' in data['answer']


class TestResponseStructure:
    """Test that response structure is correct with new answer_format field."""
    
    def test_response_includes_answer_format(
        self, client, mock_token_validator, mock_rate_limiter,
        mock_cost_tracker, mock_rag
    ):
        """Response should include answer_format field."""
        response = client.post('/api/query',
            json={'question': 'What is a beholder?', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'curl/7.68.0'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check all expected fields are present
        assert 'answer' in data
        assert 'answer_format' in data
        assert 'diagnostics' in data
        assert 'errors' in data
        assert 'meta' in data
        
        # answer_format must be one of the valid values
        assert data['answer_format'] in ['markdown', 'html']
    
    def test_meta_fields_unchanged(
        self, client, mock_token_validator, mock_rate_limiter,
        mock_cost_tracker, mock_rag
    ):
        """Existing meta fields should remain unchanged."""
        response = client.post('/api/query',
            json={'question': 'What is a beholder?', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'curl/7.68.0'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check meta structure
        assert 'meta' in data
        assert 'user_id' in data['meta']
        assert 'rate_limit' in data['meta']
        assert 'cost' in data['meta']
        assert 'performance' in data['meta']
        assert 'timestamp' in data['meta']


class TestConversionQuality:
    """Test quality of Markdown to HTML conversion."""
    
    def test_html_preserves_structure(
        self, client, mock_token_validator, mock_rate_limiter,
        mock_cost_tracker, mock_rag
    ):
        """HTML conversion should preserve document structure."""
        # Set up mock to return markdown with multiple elements
        mock_rag.query.return_value = {
            'answer': """# Title

Paragraph with **bold** and *italic*.

- List item 1
- List item 2

| Col 1 | Col 2 |
|-------|-------|
| A     | B     |""",
            'diagnostics': [],
            'errors': [],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150}
        }
        
        response = client.post('/api/query',
            json={'question': 'Test question', 'debug': False, 'k': 5},
            headers={
                'Authorization': 'Bearer test_token',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check HTML contains all expected elements
        html = data['answer']
        assert '<h1>' in html  # Title
        assert '<p>' in html  # Paragraph
        assert '<strong>' in html  # Bold
        assert '<em>' in html  # Italic
        assert '<ul>' in html  # List
        assert '<table>' in html  # Table
