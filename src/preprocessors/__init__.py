#!/usr/bin/env python3
"""
Preprocessors for D&D 1st Edition markdown files.

This module contains utilities for preprocessing markdown files
before chunking, including heading organization and normalization.
"""

from .heading_organizer import HeadingOrganizer, TOCParser, StateMachine, HeadingRewriter

__all__ = [
    'HeadingOrganizer',
    'TOCParser',
    'StateMachine',
    'HeadingRewriter',
]
