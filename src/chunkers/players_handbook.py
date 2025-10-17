#!/usr/bin/env python3
"""
Chunk the Player's Handbook (Docling markdown) using Strategy 1: Hybrid Semantic + Table-Aware

Rules:
1. Each spell (## Spell Name (School)) = 1 chunk
2. Tables + their "Notes Regarding..." sections = 1 merged chunk
3. Other ## headers = standalone chunks (may be large, that's OK for now)
4. Preserve metadata: section type, title, character count
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any


class PlayersHandbookChunker:
    def __init__(self, markdown_file: str, output_file: str = "chunks_players_handbook.json"):
        self.markdown_file = Path(markdown_file)
        self.output_file = Path('data/chunks/' + output_file)
        self.chunks: List[Dict[str, Any]] = []
        
    def detect_chunk_type(self, title: str) -> str:
        """Determine the type of chunk based on the title."""
        if '(' in title and ')' in title and not title.startswith('CHARACTER'):
            # Likely a spell: "Command (Enchantment/Charm)"
            return "spell"
        elif 'TABLE' in title.upper():
            return "table"
        elif title.startswith('Notes Regarding') or title.startswith('Notes on'):
            return "notes"
        elif title.isupper():
            return "major_section"
        elif title.endswith(':'):
            return "subsection"
        else:
            return "text_section"
    
    def should_merge_with_previous(self, current_type: str, prev_type: str, prev_title: str) -> bool:
        """Determine if current chunk should be merged with previous."""
        # Merge "Notes Regarding X" with the preceding table/section
        if current_type == "notes":
            # Check if previous was a table or related section
            if prev_type == "table":
                return True
            # Also merge if the note references the previous section by name
            if prev_title and any(word in prev_title.upper() for word in ['TABLE', 'CHART', 'MATRIX']):
                return True
        return False
    
    def extract_spell_school(self, title: str) -> str:
        """Extract spell school from title like 'Command (Enchantment/Charm)'."""
        match = re.search(r'\(([^)]+)\)', title)
        return match.group(1) if match else ""
    
    def chunk_document(self):
        """Parse the markdown and create chunks."""
        print(f"Reading {self.markdown_file}...")
        
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_chunk = {
            "title": None,
            "content": [],
            "metadata": {}
        }
        
        chunks_created = 0
        
        for line_num, line in enumerate(lines, 1):
            # Detect section headers
            if line.startswith('## '):
                # Save previous chunk if it exists
                if current_chunk["title"] is not None and current_chunk["content"]:
                    prev_type = current_chunk["metadata"].get("type")
                    prev_title = current_chunk["title"]
                    
                    title = line[3:].strip()
                    chunk_type = self.detect_chunk_type(title)
                    
                    # Check if we should merge with previous
                    if self.should_merge_with_previous(chunk_type, prev_type, prev_title):
                        # Merge: append new header and continue building current chunk
                        current_chunk["content"].append(line)
                        current_chunk["metadata"]["merged_section"] = title
                        current_chunk["metadata"]["type"] = f"{prev_type}_with_notes"
                        continue
                    else:
                        # Finalize previous chunk
                        self._finalize_chunk(current_chunk, line_num - 1)
                        chunks_created += 1
                    
                    # Start new chunk
                    current_chunk = {
                        "title": title,
                        "content": [line],
                        "metadata": {
                            "type": chunk_type,
                            "start_line": line_num
                        }
                    }
                    
                    # Add spell-specific metadata
                    if chunk_type == "spell":
                        current_chunk["metadata"]["spell_school"] = self.extract_spell_school(title)
                
                elif current_chunk["title"] is None:
                    # First chunk in document
                    title = line[3:].strip()
                    chunk_type = self.detect_chunk_type(title)
                    
                    current_chunk = {
                        "title": title,
                        "content": [line],
                        "metadata": {
                            "type": chunk_type,
                            "start_line": line_num
                        }
                    }
                    
                    if chunk_type == "spell":
                        current_chunk["metadata"]["spell_school"] = self.extract_spell_school(title)
            else:
                # Add content to current chunk
                current_chunk["content"].append(line)
        
        # Don't forget the last chunk
        if current_chunk["title"] is not None and current_chunk["content"]:
            self._finalize_chunk(current_chunk, len(lines))
            chunks_created += 1
        
        print(f"Created {chunks_created} chunks")
        print(f"\nChunk type breakdown:")
        type_counts = {}
        for chunk in self.chunks:
            chunk_type = chunk["metadata"]["type"]
            type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1
        
        for chunk_type, count in sorted(type_counts.items()):
            print(f"  {chunk_type}: {count}")
    
    def _finalize_chunk(self, chunk: Dict[str, Any], end_line: int):
        """Finalize a chunk and add it to the chunks list."""
        content_text = ''.join(chunk["content"])
        
        # Add metadata
        chunk["metadata"]["end_line"] = end_line
        chunk["metadata"]["char_count"] = len(content_text)
        chunk["metadata"]["line_count"] = len(chunk["content"])
        
        # Store the chunk
        self.chunks.append({
            "title": chunk["title"],
            "content": content_text,
            "metadata": chunk["metadata"]
        })
    
    def save_chunks(self):
        """Save chunks to JSON file."""
        print(f"\nSaving chunks to {self.output_file}...")
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(self.chunks)} chunks")
        
        # Print statistics
        char_counts = [c["metadata"]["char_count"] for c in self.chunks]
        print(f"\nChunk size statistics:")
        print(f"  Min: {min(char_counts)} chars")
        print(f"  Max: {max(char_counts)} chars")
        print(f"  Average: {sum(char_counts) // len(char_counts)} chars")
        print(f"  Chunks > 3000 chars: {sum(1 for c in char_counts if c > 3000)}")
    
    def process(self):
        """Main processing pipeline."""
        self.chunk_document()
        self.save_chunks()
        
        print("\n✅ Player's Handbook chunking complete!")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/chunkers/players_handbook.py <path_to_players_handbook.md>")
        print("\nExample:")
        print("  python src/chunkers/players_handbook.py data/markdown/Players_Handbook_(1e).md")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    
    if not Path(markdown_file).exists():
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    chunker = PlayersHandbookChunker(markdown_file)
    chunker.process()


if __name__ == "__main__":
    main()
