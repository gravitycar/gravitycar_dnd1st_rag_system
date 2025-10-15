#!/usr/bin/env python3
"""
Chunk D&D Monster Encyclopedia-style books (Monster Manual, Fiend Folio, etc.)

Strategy:
- Categories (DEMON, DRAGON, etc.) have general info + nested monster entries
- Standalone monsters have statistics + descriptions
- Each monster entry becomes one chunk with structured stats
- Category descriptions become separate chunks
- Monsters link to parent category via metadata
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


class MonsterEncyclopediaChunker:
    """
    Chunk monster encyclopedia books with category awareness.
    Works for: Monster Manual, Fiend Folio, Monster Manual II, etc.
    """
    
    # All known D&D monster statistics in order of appearance
    STATS_ORDER = [
        "FREQUENCY:",
        "NO. APPEARING:",
        "ARMOR CLASS:",
        "MOVE:",
        "HIT DICE:",
        "% IN LAIR:",
        "TREASURE TYPE:",
        "NO. OF ATTACKS:",
        "DAMAGE/ATTACK:",
        "SPECIAL ATTACKS:",
        "SPECIAL DEFENSES:",
        "MAGIC RESISTANCE:",
        "INTELLIGENCE:",
        "ALIGNMENT:",
        "SIZE:",
        "PSIONIC ABILITY:",
        "Attack/Defense Modes:"
    ]
    
    def __init__(self, markdown_file: str, output_file: str = None, book_name: str = None):
        """
        Args:
            markdown_file: Path to Docling markdown file
            output_file: Output JSON file (defaults to chunks_{basename}.json)
            book_name: Name of book for metadata (defaults to filename)
        """
        self.markdown_file = Path(markdown_file)
        
        if output_file:
            self.output_file = Path(output_file)
        else:
            basename = self.markdown_file.stem
            self.output_file = Path(f"chunks_{basename}.json")
        
        self.book_name = book_name or self.markdown_file.stem
        
        self.chunks: List[Dict[str, Any]] = []
        self.category_counter = 0
        self.monster_counter = 0
        self.discarded_counter = 0
    
    # ========================================================================
    # PHASE 1: INITIAL SPLITTING
    # ========================================================================
    
    def split_on_all_caps_headers(self, content: str) -> List[Dict[str, Any]]:
        """
        Split document on every '## <NAME>' where NAME is ALL CAPS.
        
        Note: Headers can appear mid-line (e.g., "...text. ## ANHKHEG")
        so we need to split on the pattern within content, not just at line starts.
        
        Returns list of raw chunks with:
            {
                'title': 'DEMON',
                'content': '## DEMON\n\nFull content...',
                'start_line': 629,
                'end_line': 874
            }
        """
        raw_chunks = []
        
        # Pattern: ## followed by name starting with ALL CAPS word(s)
        # Matches: "DEMON", "AERIAL SERVANT", "ANT, Giant", "APE (Gorilla)", etc.
        # Logic: Require 2+ chars from [A-Z\s] (ALL CAPS base), then optional mixed-case suffix
        # Does NOT match pure title case like "Succubus" (those are nested)
        # Match anywhere in text, not just at line start
        pattern = re.compile(r'## ([A-Z\s]{2,}[,\s\(\)A-Za-z0-9\-—\']*)(?=\n)')
        
        # Pattern to detect separator lines like "NAME1 — NAME2 — NAME3"
        separator_pattern = re.compile(r'^[A-Z][A-Z\s,\']+(?: — [A-Z][A-Z\s,\']+)+$')
        
        # Find all header matches with their positions
        matches = list(pattern.finditer(content))
        
        if not matches:
            return []
        
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start_pos = match.start()
            
            # Find end position (start of next header or end of content)
            if i < len(matches) - 1:
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)
            
            # Extract chunk content
            chunk_content = content[start_pos:end_pos]
            
            # Calculate line numbers
            start_line = content[:start_pos].count('\n') + 1
            end_line = content[:end_pos].count('\n')
            
            # Skip if this looks like a separator line
            first_line = chunk_content.split('\n')[0] if '\n' in chunk_content else chunk_content
            if separator_pattern.match(first_line.replace('## ', '').strip()):
                continue
            
            raw_chunks.append({
                'title': title,
                'content': chunk_content.strip(),
                'start_line': start_line,
                'end_line': end_line
            })
        
        return raw_chunks
    
    def merge_consecutive_category_headers(self, raw_chunks: List[Dict]) -> List[Dict]:
        """
        Handle Docling artifacts: merge consecutive ALL CAPS headers.
        
        Example: Two "## DRAGON" headers should become one chunk.
        """
        if not raw_chunks:
            return raw_chunks
        
        merged = []
        i = 0
        
        while i < len(raw_chunks):
            current = raw_chunks[i]
            
            # Look ahead for duplicate title
            j = i + 1
            while j < len(raw_chunks) and raw_chunks[j]['title'] == current['title']:
                # Merge content
                current['content'] += '\n' + raw_chunks[j]['content']
                current['end_line'] = raw_chunks[j]['end_line']
                j += 1
            
            merged.append(current)
            i = j
        
        if len(merged) < len(raw_chunks):
            print(f"  Merged {len(raw_chunks) - len(merged)} duplicate headers")
        
        return merged
    
    # ========================================================================
    # PHASE 2: CLASSIFICATION
    # ========================================================================
    
    def classify_chunk(self, raw_chunk: Dict) -> str:
        """
        Classify chunk as 'monster', 'category', or 'other'.
        
        Rules:
        1. Special case: EXPLANATORY NOTES → 'other'
        2. Has "FREQUENCY:" immediately after title → 'monster' (PRIORITY!)
        3. Has nested "## <Name>" + "FREQUENCY:" (at least 2) → 'category'
        4. Otherwise → 'other' (discard)
        
        Important: Check immediate FREQUENCY first to avoid misclassifying
        standalone monsters that are followed by other monsters in the same chunk.
        
        Note: Works for both ALL CAPS and Title Case headers now.
        """
        title = raw_chunk['title']
        content = raw_chunk['content']
        
        # Special case: Explanatory notes at the beginning
        if title == 'EXPLANATORY NOTES':
            return 'other'
        
        # Check if this chunk itself has FREQUENCY: immediately after title
        # This takes priority - if it has FREQUENCY, it's a monster (not a category)
        if self.has_immediate_frequency(content):
            return 'monster'
        
        # If no immediate FREQUENCY, check if it's a category with nested monsters
        # (requires at least 2 nested monsters to be a true category)
        if self.has_nested_monsters(content):
            return 'category'
        
        return 'other'
    
    def has_immediate_frequency(self, content: str) -> bool:
        """
        Check if FREQUENCY: appears in first few non-empty lines.
        """
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        # Check first 5 non-empty lines (skipping the header itself)
        for line in lines[1:6]:  # Skip line 0 which is the ## header
            if 'FREQUENCY:' in line:
                return True
        return False
    
    def has_nested_monsters(self, content: str) -> bool:
        """
        Check for "## <Name>" (title case) with FREQUENCY: nearby.
        
        Important: Excludes headers like "## General Characteristics:"
        which don't have FREQUENCY: and aren't monsters.
        
        Returns True only if at least 2 nested monsters found 
        (single monster should be treated as standalone).
        """
        # Split on ## headers
        sections = re.split(r'\n## ', content)
        
        monster_count = 0
        for section in sections[1:]:  # Skip first (category intro)
            # Check if this section has FREQUENCY: in first few lines
            lines = [l.strip() for l in section.split('\n')[:10] if l.strip()]
            has_freq = any('FREQUENCY:' in line for line in lines)
            
            # Check if header is title case (not all caps, not all lowercase)
            first_line = section.split('\n')[0] if section else ""
            # Title case: first letter caps, contains at least one lowercase
            is_title_case = (first_line and 
                           first_line[0].isupper() and
                           any(c.islower() for c in first_line))
            
            if has_freq and is_title_case:
                monster_count += 1
        
        # Must have at least 2 nested monsters to be a true category
        return monster_count >= 2
    
    # ========================================================================
    # PHASE 3: CATEGORY PROCESSING
    # ========================================================================
    
    def process_category(self, raw_chunk: Dict) -> Tuple[Dict, List[Dict]]:
        """
        Split category into:
        1. Category description chunk (everything before first monster)
        2. List of monster chunks (each "## <Name>" with FREQUENCY:)
        
        Returns (category_chunk, monster_chunks)
        """
        category_name = raw_chunk['title']
        content = raw_chunk['content']
        
        # Generate category ID
        category_id = self.generate_category_id(category_name)
        
        # Extract category description (before first monster)
        category_desc = self.extract_category_description(content)
        
        # Build category chunk
        category_chunk = {
            'name': category_name,
            'description': category_desc,
            'metadata': self.build_category_metadata(
                category_name, category_id, raw_chunk['start_line'], 
                raw_chunk['end_line'], len(category_desc)
            )
        }
        
        # Extract individual monsters
        monster_chunks = self.extract_monsters_from_category(
            content, category_name, category_id, raw_chunk['start_line']
        )
        
        return category_chunk, monster_chunks
    
    def extract_category_description(self, content: str) -> str:
        """
        Extract everything before the first "## <Name>" (title case) with FREQUENCY:.
        
        Includes: category intro + "## General Characteristics:" if present.
        Excludes: first actual monster entry.
        Strips the initial "## CATEGORY_NAME" header.
        """
        # Find the first monster entry (## with title case + FREQUENCY:)
        sections = re.split(r'\n(## [A-Z][^\n]*)\n', content)
        
        # Start with first section (before any ## headers)
        category_desc = sections[0] if sections else content
        
        # Check subsequent sections
        i = 1
        while i < len(sections) - 1:
            header = sections[i]
            section_content = sections[i + 1]
            
            # Check if this is a title case header
            header_text = header.replace('## ', '').strip()
            is_title_case = (header_text and 
                           header_text[0].isupper() and
                           any(c.islower() for c in header_text))
            
            if is_title_case:
                # Check if it has FREQUENCY: in first few lines
                lines = [l.strip() for l in section_content.split('\n')[:10] if l.strip()]
                has_freq = any('FREQUENCY:' in line for line in lines)
                
                if has_freq:
                    # This is a monster entry - stop here
                    break
                else:
                    # This is part of category description (like "General Characteristics")
                    category_desc += '\n' + header + '\n' + section_content
            
            i += 2
        
        # Strip the initial "## CATEGORY_NAME" header
        category_desc = re.sub(r'^##\s+[^\n]+\n+', '', category_desc.strip())
        
        return category_desc.strip()
    
    def extract_monsters_from_category(self, content: str, category_name: str, 
                                      category_id: str, start_line: int) -> List[Dict]:
        """
        Split category content on "## <Name>" + "FREQUENCY:" pattern.
        Each becomes a monster chunk with parent_category metadata.
        """
        monsters = []
        
        # Split on ## headers, keeping the headers
        sections = re.split(r'\n(## [A-Z][^\n]*)\n', content)
        
        # Process sections in pairs (header, content)
        i = 1
        current_line = start_line
        
        while i < len(sections) - 1:
            header = sections[i]
            section_content = sections[i + 1]
            
            # Extract title from header
            title = header.replace('## ', '').strip()
            
            # Check if title case
            is_title_case = (title and 
                           title[0].isupper() and
                           any(c.islower() for c in title))
            
            if is_title_case:
                # Check if has FREQUENCY:
                lines = [l.strip() for l in section_content.split('\n')[:10] if l.strip()]
                has_freq = any('FREQUENCY:' in line for line in lines)
                
                if has_freq:
                    # This is a monster entry
                    full_content = header + '\n' + section_content
                    
                    # Approximate line number
                    lines_before = '\n'.join(sections[:i+1]).count('\n')
                    monster_start_line = start_line + lines_before
                    
                    monster = self.process_monster(
                        title, full_content, monster_start_line,
                        parent_category=category_name,
                        parent_category_id=category_id
                    )
                    monsters.append(monster)
            
            i += 2
        
        return monsters
    
    # ========================================================================
    # PHASE 4: MONSTER PROCESSING
    # ========================================================================
    
    def process_monster(self, title: str, content: str, start_line: int,
                       parent_category: Optional[str] = None,
                       parent_category_id: Optional[str] = None) -> Dict:
        """
        Extract statistics and description from monster entry.
        
        Returns monster chunk with:
            {
                'name': 'Succubus',
                'statistics': {...},
                'description': 'These female demons...',
                'metadata': {...}
            }
        """
        # Find stats boundary
        stats_end, last_stat = self.find_stats_boundary(content)
        
        if stats_end == -1:
            print(f"WARNING: No stats found for {title}")
            stats_block = ""
            description = content
        else:
            stats_block = content[:stats_end]
            description = self.extract_description(content, stats_end)
        
        # Parse statistics
        statistics = self.extract_stats_universal(stats_block) if stats_block else {}
        
        # Build metadata
        metadata = self.build_monster_metadata(
            title, parent_category, parent_category_id,
            start_line, start_line + content.count('\n'),
            len(content), len(description)
        )
        
        return {
            'name': title,
            'statistics': statistics,
            'description': description.strip(),
            'metadata': metadata
        }
    
    def find_stats_boundary(self, content: str) -> Tuple[int, Optional[str]]:
        """
        Loop through STATS_ORDER to find LAST stat present.
        Then find first non-empty, non-image line after it that doesn't start with a stat name.
        
        Returns (end_position, last_stat_name)
        """
        if "FREQUENCY:" not in content:
            return -1, None
        
        last_stat_name = None
        last_stat_pos = -1
        
        # Find which stat appears LAST
        for stat_name in self.STATS_ORDER:
            pos = content.find(stat_name)
            if pos > last_stat_pos:
                last_stat_pos = pos
                last_stat_name = stat_name
        
        if last_stat_pos == -1:
            return -1, None
        
        # Find end of last stat's line (consume the entire stat line including its value)
        # Start from the position of the last stat
        value_start = last_stat_pos
        
        # Find the end of the line containing the last stat
        next_newline = content.find('\n', value_start)
        if next_newline == -1:
            next_newline = len(content)
        
        # Start searching from the next line after the last stat
        search_start = next_newline + 1
        
        # Find next non-empty, non-image, non-stat line
        remaining = content[search_start:]
        lines = remaining.split('\n')
        
        cumulative_pos = search_start
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                cumulative_pos += len(line) + 1
                continue
            
            # Skip image tags
            if stripped.startswith('<!--') and 'image' in stripped:
                cumulative_pos += len(line) + 1
                continue
            
            # Check if line starts with a stat name (without the colon for flexibility)
            starts_with_stat = any(
                stripped.startswith(stat.replace(':', '').strip()) or
                stripped.startswith(stat)
                for stat in self.STATS_ORDER
            )
            
            if starts_with_stat:
                # Still in stats block
                cumulative_pos += len(line) + 1
                continue
            
            # Found description start
            return cumulative_pos, last_stat_name
        
        # No clear boundary found, return conservative estimate
        return search_start + min(200, len(remaining)), last_stat_name
    
    def extract_description(self, content: str, stats_end: int) -> str:
        """
        Extract description: everything after stats_end.
        Clean up whitespace and image tags.
        Remove "## <NAME>" headers that sometimes appear at start.
        """
        description = content[stats_end:].strip()
        
        # Remove "## <NAME>" header if present at start
        # Example: "## AERIAL SERVANT\n\n" or "## Succubus\n\n"
        description = re.sub(r'^##\s+[^\n]+\n+', '', description)
        
        # Remove image tags
        description = re.sub(r'<!--\s*image\s*-->', '', description)
        
        # Clean up excessive whitespace
        description = re.sub(r'\n\n\n+', '\n\n', description)
        
        return description.strip()
    
    def extract_stats_universal(self, stats_block: str) -> Dict[str, str]:
        """
        Universal parser for all 3 formats (single-line, multi-line, table).
        
        Strategy:
        1. Remove table delimiters (|) and normalize whitespace
        2. Loop through STATS_ORDER and extract values between stat names
        3. Return dict with clean keys (lowercase, underscores)
        """
        stats = {}
        
        # Normalize: remove pipes, collapse whitespace
        normalized = stats_block.replace('|', ' ')
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Extract each stat
        for i, stat_name in enumerate(self.STATS_ORDER):
            if stat_name not in normalized:
                continue
            
            # Find start of value
            start = normalized.find(stat_name) + len(stat_name)
            
            # Find end: next stat or end of string
            end = len(normalized)
            for next_stat in self.STATS_ORDER[i+1:]:
                if next_stat in normalized[start:]:
                    end = normalized.find(next_stat, start)
                    break
            
            # Extract and clean value
            value = normalized[start:end].strip()
            
            # Create clean key
            key = self._clean_stat_key(stat_name)
            stats[key] = value
        
        return stats
    
    def _clean_stat_key(self, stat_name: str) -> str:
        """Convert 'FREQUENCY:' to 'frequency', '% IN LAIR:' to 'pct_in_lair'"""
        key = stat_name.replace(':', '').replace(' ', '_').replace('/', '_').lower()
        key = key.replace('%_', 'pct_')
        return key
    
    # ========================================================================
    # PHASE 5: METADATA & IDs
    # ========================================================================
    
    def generate_category_id(self, category_name: str) -> str:
        """Generate stable ID: 'demon_cat_001', 'dragon_cat_002'"""
        self.category_counter += 1
        clean_name = category_name.lower().replace(' ', '_').replace('-', '_')
        clean_name = clean_name.replace('—', '_')  # em-dash
        clean_name = re.sub(r'[^a-z0-9_]', '', clean_name)
        return f"{clean_name}_cat_{self.category_counter:03d}"
    
    def generate_monster_id(self, monster_name: str) -> str:
        """Generate stable ID: 'succubus_mon_001'"""
        self.monster_counter += 1
        clean_name = monster_name.lower().replace(' ', '_').replace('-', '_')
        clean_name = clean_name.replace('(', '').replace(')', '')
        clean_name = re.sub(r'[^a-z0-9_]', '', clean_name)
        return f"{clean_name}_mon_{self.monster_counter:03d}"
    
    def build_monster_metadata(self, name: str, parent_category: Optional[str],
                               parent_category_id: Optional[str], start_line: int,
                               end_line: int, char_count: int, 
                               desc_char_count: int) -> Dict:
        """Build metadata dict for monster chunk."""
        metadata = {
            'type': 'monster',
            'monster_id': self.generate_monster_id(name),
            'book': self.book_name,
            'start_line': start_line,
            'end_line': end_line,
            'char_count': char_count,
            'description_char_count': desc_char_count,
            'line_count': end_line - start_line
        }
        
        if parent_category:
            metadata['parent_category'] = parent_category
            metadata['parent_category_id'] = parent_category_id
        
        return metadata
    
    def build_category_metadata(self, name: str, category_id: str, 
                                start_line: int, end_line: int,
                                char_count: int) -> Dict:
        """Build metadata dict for category chunk."""
        return {
            'type': 'category',
            'category_id': category_id,
            'book': self.book_name,
            'start_line': start_line,
            'end_line': end_line,
            'char_count': char_count,
            'line_count': end_line - start_line
        }
    
    # ========================================================================
    # MAIN PIPELINE
    # ========================================================================
    
    def process(self):
        """Main processing pipeline."""
        print(f"Reading {self.markdown_file}...")
        
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Phase 1: Split
        print("\nPhase 1: Splitting on ALL CAPS headers...")
        raw_chunks = self.split_on_all_caps_headers(content)
        print(f"  Found {len(raw_chunks)} raw chunks")
        raw_chunks = self.merge_consecutive_category_headers(raw_chunks)
        print(f"  After merging: {len(raw_chunks)} chunks")
        
        # Phase 2: Classify
        print("\nPhase 2: Classifying chunks...")
        for raw_chunk in raw_chunks:
            chunk_type = self.classify_chunk(raw_chunk)
            raw_chunk['chunk_type'] = chunk_type
        
        categories = [c for c in raw_chunks if c['chunk_type'] == 'category']
        monsters = [c for c in raw_chunks if c['chunk_type'] == 'monster']
        others = [c for c in raw_chunks if c['chunk_type'] == 'other']
        
        print(f"  Categories: {len(categories)}")
        print(f"  Standalone Monsters: {len(monsters)}")
        print(f"  Other (discarded): {len(others)}")
        
        if others:
            print(f"\n  Discarded chunks:")
            for other in others[:10]:  # Show first 10
                print(f"    - {other['title']}")
            if len(others) > 10:
                print(f"    ... and {len(others) - 10} more")
        
        # Phase 3 & 4: Process
        print("\nPhase 3-4: Processing categories and monsters...")
        
        for cat_chunk in categories:
            cat, monsters_in_cat = self.process_category(cat_chunk)
            self.chunks.append(cat)
            self.chunks.extend(monsters_in_cat)
            print(f"  Category '{cat['name']}': 1 category + {len(monsters_in_cat)} monsters")
        
        for mon_chunk in monsters:
            monster = self.process_monster(
                mon_chunk['title'], 
                mon_chunk['content'],
                mon_chunk['start_line']
            )
            self.chunks.append(monster)
        
        print(f"\n✅ Created {len(self.chunks)} total chunks")
        print(f"   - {sum(1 for c in self.chunks if c.get('metadata', {}).get('type') == 'category')} categories")
        print(f"   - {sum(1 for c in self.chunks if c.get('metadata', {}).get('type') == 'monster')} monsters")
        
        # Save
        self.save_chunks()
    
    def save_chunks(self):
        """Save chunks to JSON file with statistics."""
        print(f"\nSaving to {self.output_file}...")
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.chunks, f, indent=2, ensure_ascii=False)
        
        # Statistics
        monsters = [c for c in self.chunks if c.get('metadata', {}).get('type') == 'monster']
        categories = [c for c in self.chunks if c.get('metadata', {}).get('type') == 'category']
        
        if monsters:
            char_counts = [c['metadata']['char_count'] for c in monsters]
            print(f"\nMonster chunk statistics:")
            print(f"  Count: {len(monsters)}")
            print(f"  Char count - Min: {min(char_counts)}, Max: {max(char_counts)}, Avg: {sum(char_counts)//len(char_counts)}")
            
            # Monsters with parent categories
            with_parent = sum(1 for m in monsters if 'parent_category' in m.get('metadata', {}))
            print(f"  Monsters in categories: {with_parent}")
            print(f"  Standalone monsters: {len(monsters) - with_parent}")
        
        if categories:
            print(f"\nCategory chunks: {len(categories)}")
            for cat in categories[:20]:  # Show first 20
                print(f"  - {cat['name']}")
            if len(categories) > 20:
                print(f"  ... and {len(categories) - 20} more")
        
        print(f"\n✅ Saved to {self.output_file}")


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/chunkers/monster_encyclopedia.py <markdown_file> [output_file] [book_name]")
        print("\nExamples:")
        print("  python src/chunkers/monster_encyclopedia.py data/markdown/Monster_Manual_(1e).md")
        print("  python src/chunkers/monster_encyclopedia.py data/markdown/Fiend_Folio.md data/chunks/chunks_ff.json 'Fiend Folio'")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    book_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not Path(markdown_file).exists():
        print(f"Error: File not found: {markdown_file}")
        sys.exit(1)
    
    chunker = MonsterEncyclopediaChunker(markdown_file, output_file, book_name)
    chunker.process()
    
    print("\n✅ Monster encyclopedia chunking complete!")


if __name__ == "__main__":
    main()
