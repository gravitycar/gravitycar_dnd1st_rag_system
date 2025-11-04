#!/usr/bin/env python3
"""
RAGOutput: Structured output buffer for RAG queries.

Captures three types of output:
- Answer: The LLM's response
- Diagnostics: Execution context (timing, retrieval stats)
- Errors: Failure messages

Designed for dependency injection into DnDRAG class.
"""

from typing import Optional


class RAGOutput:
    """
    Output buffer for RAG queries.
    
    Captures all output from query execution in structured format
    that can be returned as JSON (Flask) or printed (CLI).
    
    Thread safety: Not required (per-request instance).
    """
    
    def __init__(self):
        """Initialize empty output buffer."""
        self.answer: Optional[str] = None
        self.diagnostics: list[str] = []
        self.errors: list[str] = []
    
    def set_answer(self, text: str) -> None:
        """
        Store the LLM's response.
        
        Args:
            text: Answer text from LLM
        """
        self.answer = text
    
    def info(self, msg: str) -> None:
        """
        Add diagnostic message.
        
        Args:
            msg: Diagnostic message (e.g., "Retrieved 3 chunks in 0.15s")
        """
        self.diagnostics.append(msg)
    
    def error(self, msg: str) -> None:
        """
        Add error message.
        
        Args:
            msg: Error message (e.g., "Collection not found")
        """
        self.errors.append(msg)
    
    def to_dict(self) -> dict:
        """
        Convert to JSON-serializable dict.
        
        Returns:
            Dict with keys: answer, diagnostics, errors
        """
        return {
            'answer': self.answer,
            'diagnostics': self.diagnostics,
            'errors': self.errors
        }
