#!/usr/bin/env python3
"""
Chunk the Monster Manual (Docling markdown) using encyclopedia-style approach.

Rules:
1. Each monster entry starts with "## <Monster Name>"
2. Entry ends when the next "## " header is encountered
3. Each monster = 1 complete chunk
4. Preserve all monster statistics and description together
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any


class MonsterManualChunker:
    def __init__(self, markdown_file: str, output_file: str = "chunks_monster_manual.json"):
        self.markdown_file = Path(markdown_file)
        self.output_file = Path(output_file)
        self.chunks: List[Dict[str, Any]] = []
        
    def extract_monster_metadata(self, title: str, content: str) -> Dict[str, Any]:
        """Extract metadata from monster entry."""
        metadata = {
            "monster_name": title,
            "type": "monster_entry"
        }
        
        # Try to extract common monster attributes from content
        # Look for patterns like "FREQUENCY: Rare" or "Hit Dice: 8"
        
        # Extract frequency
        freq_match = re.search(r'FREQUENCY:\s*([^\n]+)', content, re.IGNORECASE)
        if freq_match:
            metadata["frequency"] = freq_match.group(1).strip()
        
        # Extract hit dice (multiple patterns)
        hd_patterns = [
            r'Hit Dice:\s*([^\n]+)',
            r'HIT DICE:\s*([^\n]+)',
            r'(\d+)\s*[Hh]it\s*[Dd]ice'
        ]
        for pattern in hd_patterns:
            hd_match = re.search(pattern, content)
            if hd_match:
                metadata["hit_dice"] = hd_match.group(1).strip()
                break
        
        # Extract armor class
        ac_match = re.search(r'ARMOR CLASS:\s*([^\n]+)', content, re.IGNORECASE)
        if ac_match:
            metadata["armor_class"] = ac_match.group(1).strip()
        
        # Check if it's a dragon, demon, devil, or other special type
        title_lower = title.lower()
        if 'dragon' in title_lower:
            metadata["creature_type"] = "dragon"
        elif 'demon' in title_lower or 'devil' in title_lower:
            metadata["creature_type"] = "fiend"
        elif 'elemental' in title_lower:
            metadata["creature_type"] = "elemental"
        elif 'giant' in title_lower:
            metadata["creature_type"] = "giant"
        elif 'goblin' in title_lower or 'orc' in title_lower or 'kobold' in title_lower:
            metadata["creature_type"] = "humanoid"
        
        return metadata
    
    def chunk_document(self):
        """Parse the markdown and create chunks (one per monster)."""
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
            # Detect monster entry headers (## Monster Name)
            if line.startswith('## '):
                # Save previous chunk if it exists
                if current_chunk["title"] is not None and current_chunk["content"]:
                    self._finalize_chunk(current_chunk, line_num - 1)
                    chunks_created += 1
                
                # Start new monster entry
                title = line[3:].strip()
                current_chunk = {
                    "title": title,
                    "content": [line],
                    "metadata": {
                        "start_line": line_num
                    }
                }
            else:
                # Add content to current monster entry
                if current_chunk["title"] is not None:
                    current_chunk["content"].append(line)
        
        # Don't forget the last chunk
        if current_chunk["title"] is not None and current_chunk["content"]:
            self._finalize_chunk(current_chunk, len(lines))
            chunks_created += 1
        
        print(f"Created {chunks_created} monster entry chunks")
    
    def _finalize_chunk(self, chunk: Dict[str, Any], end_line: int):
        """Finalize a monster chunk and add it to the chunks list."""
        content_text = ''.join(chunk["content"])
        
        # Extract monster-specific metadata
        chunk["metadata"].update(self.extract_monster_metadata(chunk["title"], content_text))
        
        # Add standard metadata
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
        
        print(f"Saved {len(self.chunks)} monster entries")
        
        # Print statistics
        char_counts = [c["metadata"]["char_count"] for c in self.chunks]
        print(f"\nChunk size statistics:")
        print(f"  Min: {min(char_counts)} chars")
        print(f"  Max: {max(char_counts)} chars")
        print(f"  Average: {sum(char_counts) // len(char_counts)} chars")
        print(f"  Chunks > 3000 chars: {sum(1 for c in char_counts if c > 3000)}")
        
        # Print creature type breakdown if available
        creature_types = {}
        for chunk in self.chunks:
            ctype = chunk["metadata"].get("creature_type", "unknown")
            creature_types[ctype] = creature_types.get(ctype, 0) + 1
        
        if creature_types:
            print(f"\nCreature type breakdown:")
            for ctype, count in sorted(creature_types.items()):
                print(f"  {ctype}: {count}")
    
    def process(self):
        """Main processing pipeline."""
        self.chunk_document()
        self.save_chunks()
        
        print("\n✅ Monster Manual chunking complete!")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python chunk_monster_manual_docling.py <path_to_monster_manual.md>")
        print("\nExample:")
        print("  python chunk_monster_manual_docling.py dndmarkdown/docling/good_pdfs/Monster_Manual.md")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    
    if not Path(markdown_file).exists():
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    chunker = MonsterManualChunker(markdown_file)
    chunker.process()


if __name__ == "__main__":
    main()
