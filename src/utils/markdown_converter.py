#!/usr/bin/env python3
"""
Markdown to HTML Converter for D&D RAG System.

Converts OpenAI's Markdown responses to HTML for web clients
while preserving Markdown output for CLI clients.
"""

import markdown
from flask import Request
from typing import Optional


class MarkdownConverter:
    """
    Convert Markdown to HTML for web display.
    
    Uses Python markdown library with extensions for:
    - Tables (stat blocks)
    - Fenced code blocks (JSON tables)
    - Newline to <br> conversion
    - Syntax highlighting
    
    Follows Single Responsibility Principle: Only handles Markdown → HTML conversion.
    """
    
    def __init__(self):
        """Initialize markdown parser with D&D-friendly extensions."""
        self.md = markdown.Markdown(extensions=[
            'tables',           # Support markdown tables
            'fenced_code',      # Code blocks with ```
            'nl2br',            # Convert newlines to <br>
            'sane_lists',       # Better list handling
            'codehilite',       # Syntax highlighting for JSON
        ])
    
    def convert(self, markdown_text: str) -> str:
        """
        Convert Markdown to HTML.
        
        Args:
            markdown_text: Raw markdown string from OpenAI
            
        Returns:
            HTML string with proper structure
            
        Raises:
            ValueError: If markdown_text is None (empty string is valid)
        """
        if markdown_text is None:
            raise ValueError("markdown_text cannot be None")
        
        if not markdown_text:
            return ""
        
        # Convert markdown to HTML
        html = self.md.convert(markdown_text)
        
        # Reset parser state for next conversion
        self.md.reset()
        
        return html
    
    def is_web_request(self, request: Request) -> bool:
        """
        Detect if request is from web client.
        
        Args:
            request: Flask request object
            
        Returns:
            True if web client (browser/React), False if CLI (curl/requests)
            
        Detection Strategy:
        1. Check User-Agent header
        2. Web clients: Mozilla, Chrome, Safari, Edge, axios
        3. CLI clients: curl, python-requests, httpie
        4. Default: False (Markdown - backwards compatible)
        """
        user_agent = request.headers.get('User-Agent', '').lower()
        
        # Web browser indicators
        web_indicators = [
            'mozilla',      # Most browsers
            'chrome',       # Chrome/Chromium
            'safari',       # Safari
            'edge',         # Edge
            'firefox',      # Firefox
            'axios',        # Axios (common in React apps)
            'fetch',        # Fetch API
        ]
        
        # CLI client indicators
        cli_indicators = [
            'curl',         # curl
            'python-requests',  # Python requests library
            'httpie',       # HTTPie CLI tool
            'wget',         # wget
            'postman',      # Postman (treat as CLI for now)
        ]
        
        # Check for CLI indicators first (explicit Markdown)
        for indicator in cli_indicators:
            if indicator in user_agent:
                return False
        
        # Check for web indicators
        for indicator in web_indicators:
            if indicator in user_agent:
                return True
        
        # Default to CLI (Markdown) for backwards compatibility
        return False
