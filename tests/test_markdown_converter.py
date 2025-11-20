#!/usr/bin/env python3
"""
Unit tests for MarkdownConverter.

Tests Markdown-to-HTML conversion and User-Agent detection logic.
"""

import pytest
from src.utils.markdown_converter import MarkdownConverter


class MockRequest:
    """Mock Flask request object for testing."""
    
    def __init__(self, user_agent: str = ''):
        self.headers = {'User-Agent': user_agent}


class TestMarkdownConversion:
    """Test Markdown to HTML conversion."""
    
    def test_basic_conversion(self):
        """Test simple markdown to HTML."""
        converter = MarkdownConverter()
        markdown = "# Heading\n\nParagraph with **bold** text."
        html = converter.convert(markdown)
        assert "<h1>Heading</h1>" in html
        assert "<strong>bold</strong>" in html
        assert "<p>" in html
    
    def test_table_conversion(self):
        """Test markdown table to HTML table."""
        converter = MarkdownConverter()
        markdown = """| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |"""
        html = converter.convert(markdown)
        assert "<table>" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "Column 1" in html
        assert "Data 1" in html
    
    def test_code_block_conversion(self):
        """Test fenced code blocks preserve JSON."""
        converter = MarkdownConverter()
        markdown = """```json
{
  "monster": "beholder"
}
```"""
        html = converter.convert(markdown)
        # codehilite extension wraps in <div class="codehilite">
        assert "<pre>" in html and "<code>" in html
        assert '"monster": "beholder"' in html or '&quot;monster&quot;' in html
    
    def test_list_conversion(self):
        """Test list formatting."""
        converter = MarkdownConverter()
        markdown = """- Item 1
- Item 2
- Item 3"""
        html = converter.convert(markdown)
        assert "<ul>" in html
        assert "<li>Item 1" in html
        assert "<li>Item 2" in html
    
    def test_inline_formatting(self):
        """Test bold, italic, and links."""
        converter = MarkdownConverter()
        markdown = "**Bold** and *italic* text."
        html = converter.convert(markdown)
        assert "<strong>Bold</strong>" in html
        assert "<em>italic</em>" in html
    
    def test_empty_string(self):
        """Test empty string returns empty string."""
        converter = MarkdownConverter()
        html = converter.convert("")
        assert html == ""
    
    def test_none_input(self):
        """Test None input raises ValueError."""
        converter = MarkdownConverter()
        with pytest.raises(ValueError, match="markdown_text cannot be None"):
            converter.convert(None)
    
    def test_multiple_conversions(self):
        """Test multiple conversions don't interfere (reset state)."""
        converter = MarkdownConverter()
        
        html1 = converter.convert("# First")
        assert "<h1>First</h1>" in html1
        
        html2 = converter.convert("# Second")
        assert "<h1>Second</h1>" in html2
        assert "First" not in html2  # State properly reset


class TestUserAgentDetection:
    """Test User-Agent detection for format selection."""
    
    def test_mozilla_browser(self):
        """Test Mozilla/Firefox browser detected as web."""
        converter = MarkdownConverter()
        request = MockRequest('Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        assert converter.is_web_request(request) == True
    
    def test_chrome_browser(self):
        """Test Chrome browser detected as web."""
        converter = MarkdownConverter()
        request = MockRequest('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0')
        assert converter.is_web_request(request) == True
    
    def test_safari_browser(self):
        """Test Safari browser detected as web."""
        converter = MarkdownConverter()
        request = MockRequest('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15')
        assert converter.is_web_request(request) == True
    
    def test_axios_client(self):
        """Test axios library detected as web."""
        converter = MarkdownConverter()
        request = MockRequest('axios/1.6.0')
        assert converter.is_web_request(request) == True
    
    def test_curl_client(self):
        """Test curl detected as CLI."""
        converter = MarkdownConverter()
        request = MockRequest('curl/7.68.0')
        assert converter.is_web_request(request) == False
    
    def test_python_requests(self):
        """Test python-requests detected as CLI."""
        converter = MarkdownConverter()
        request = MockRequest('python-requests/2.31.0')
        assert converter.is_web_request(request) == False
    
    def test_httpie_client(self):
        """Test HTTPie detected as CLI."""
        converter = MarkdownConverter()
        request = MockRequest('HTTPie/3.2.2')
        assert converter.is_web_request(request) == False
    
    def test_postman_client(self):
        """Test Postman detected as CLI."""
        converter = MarkdownConverter()
        request = MockRequest('PostmanRuntime/7.32.3')
        assert converter.is_web_request(request) == False
    
    def test_empty_user_agent(self):
        """Test empty User-Agent defaults to CLI (Markdown)."""
        converter = MarkdownConverter()
        request = MockRequest('')
        assert converter.is_web_request(request) == False
    
    def test_unknown_user_agent(self):
        """Test unknown User-Agent defaults to CLI (Markdown)."""
        converter = MarkdownConverter()
        request = MockRequest('CustomClient/1.0')
        assert converter.is_web_request(request) == False
    
    def test_case_insensitive(self):
        """Test User-Agent detection is case-insensitive."""
        converter = MarkdownConverter()
        request = MockRequest('MOZILLA/5.0')
        assert converter.is_web_request(request) == True
        
        request = MockRequest('CURL/7.68.0')
        assert converter.is_web_request(request) == False


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_multiline_markdown(self):
        """Test multiline markdown with multiple elements."""
        converter = MarkdownConverter()
        markdown = """# Main Title

## Subtitle

Paragraph with **bold** and *italic*.

- List item 1
- List item 2

| Col 1 | Col 2 |
|-------|-------|
| A     | B     |

```python
code_block = True
```"""
        html = converter.convert(markdown)
        assert "<h1>Main Title</h1>" in html
        assert "<h2>Subtitle</h2>" in html
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "<ul>" in html
        assert "<table>" in html
        # codehilite extension wraps in <div class="codehilite">
        assert "<pre>" in html and "<code>" in html
    
    def test_special_characters(self):
        """Test special characters in markdown."""
        converter = MarkdownConverter()
        markdown = "Text with < and > characters"
        html = converter.convert(markdown)
        # Markdown should escape HTML special chars
        assert html  # Just verify it doesn't crash
    
    def test_nested_lists(self):
        """Test nested list conversion."""
        converter = MarkdownConverter()
        markdown = """- Item 1
  - Nested 1
  - Nested 2
- Item 2"""
        html = converter.convert(markdown)
        assert "<ul>" in html
        assert "<li>Item 1" in html
