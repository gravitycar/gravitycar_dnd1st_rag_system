"""
Components for the Complex Table Transformer pipeline.

This package contains modular components that work together to transform
tables in markdown files into structured JSON using OpenAI's API.
"""

from .markdown_file_reader import MarkdownFileReader

__all__ = [
    "MarkdownFileReader",
]
