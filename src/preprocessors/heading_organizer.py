#!/usr/bin/env python3
"""
Heading Organizer for Player's Handbook markdown files.

This module transforms flat heading hierarchies into properly nested
hierarchies based on the Table of Contents, enabling better chunking
and parent-child relationships in the RAG system.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any


class TOCParser:
    """Parses Players_Handbook_TOC.txt into structured section map."""
    
    def __init__(self, toc_file_path: str):
        """
        Initialize TOC parser.
        
        Args:
            toc_file_path: Path to the Table of Contents file
        """
        self.toc_file_path = Path(toc_file_path)
        self.major_sections: List[str] = []
        self.minor_sections: Dict[str, List[str]] = {}
        # Maps minor section name → its parent major section
        self.section_hierarchy: Dict[str, str] = {}
        
    def parse(self) -> None:
        """Parse TOC file and populate section maps."""
        if not self.toc_file_path.exists():
            raise FileNotFoundError(f"TOC file not found: {self.toc_file_path}")
        
        print(f"Parsing TOC: {self.toc_file_path}")
        
        current_major_section = None
        
        with open(self.toc_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            
            # Strip all dots and page numbers
            # Remove everything from first dot to end of line
            if '.' in line:
                # Find first dot, strip everything after it
                cleaned = line[:line.index('.')].rstrip()
            else:
                cleaned = line.rstrip()
            
            # Determine indentation level (from original line)
            indent_level = len(line) - len(line.lstrip())
            section_name = cleaned.strip()
            
            if not section_name:
                continue
            
            # Remove leading em-dash if present
            has_dash = section_name.startswith('—') or section_name.startswith('-')
            if has_dash:
                section_name = section_name.lstrip('—-').strip()
            
            # Major section: unindented and no leading dash
            if indent_level == 0 and not has_dash:
                self.major_sections.append(section_name)
                current_major_section = section_name
                self.minor_sections[section_name] = []
                print(f"  Major section: {section_name}")
            
            # Minor section: has dash OR is indented (belongs to last major)
            elif (has_dash or indent_level > 0) and current_major_section:
                self.minor_sections[current_major_section].append(section_name)
                self.section_hierarchy[section_name] = current_major_section
                print(f"    Minor section: {section_name} (under {current_major_section})")
        
        print(f"\nParsed {len(self.major_sections)} major sections, "
              f"{len(self.section_hierarchy)} minor sections")
    
    def is_major_section(self, heading: str) -> bool:
        """
        Check if heading is a major section.
        
        Args:
            heading: Heading text to check
            
        Returns:
            True if heading is a major section
        """
        normalized = heading.strip()
        return normalized in self.major_sections
    
    def is_minor_section(self, heading: str) -> bool:
        """
        Check if heading is a minor section.
        
        Args:
            heading: Heading text to check
            
        Returns:
            True if heading is a minor section
        """
        normalized = heading.strip()
        return normalized in self.section_hierarchy
    
    def get_parent_major_section(self, minor_section: str) -> Optional[str]:
        """
        Get parent major section for a minor section.
        
        Args:
            minor_section: Name of minor section
            
        Returns:
            Parent major section name, or None if not found
        """
        return self.section_hierarchy.get(minor_section)


class StateMachine:
    """Tracks context while processing document line-by-line."""
    
    def __init__(self, toc_parser: TOCParser):
        """
        Initialize state machine.
        
        Args:
            toc_parser: TOCParser instance with parsed section data
        """
        self.toc_parser = toc_parser
        self.current_major_section: Optional[str] = None
        self.current_minor_section: Optional[str] = None
        self.heading_level: int = 2
        self.in_spell_section: bool = False
        self.bump_next: bool = False  # For one-time level increase
    
    def enter_major_section(self, section_name: str) -> None:
        """
        Transition to new major section.
        
        Args:
            section_name: Name of major section
        """
        self.current_major_section = section_name
        self.current_minor_section = None
        self.in_spell_section = False
        self.heading_level = 2
        print(f"  → Entered major section: {section_name}")
    
    def enter_minor_section(self, section_name: str) -> None:
        """
        Transition to new minor section.
        
        Args:
            section_name: Name of minor section
        """
        self.current_minor_section = section_name
        self.in_spell_section = False
        self.heading_level = 3
        print(f"  → Entered minor section: {section_name}")
    
    def set_heading_level(self, level: int) -> None:
        """
        Explicitly set heading level.
        
        Args:
            level: Heading level to set
        """
        self.heading_level = level
        self.bump_next = False
    
    def bump_heading_level(self) -> None:
        """Increase heading level by 1 for next heading only."""
        self.bump_next = True
    
    def get_current_level(self) -> int:
        """
        Get heading level to apply, respecting bump flag.
        
        Returns:
            Heading level (auto-resets bump flag if set)
        """
        if self.bump_next:
            level = self.heading_level + 1
            self.bump_next = False
            return level
        return self.heading_level
    
    def enter_spell_section(self) -> None:
        """Enter spell listing section."""
        self.in_spell_section = True
        self.heading_level = 4  # "First Level Spells:" is level 4
        print(f"  → Entered spell section")


class HeadingRewriter:
    """Transforms heading levels in markdown document."""
    
    # Regex patterns for detecting heading types
    SPELL_NAME_PATTERN = re.compile(r'^## (.+?) \(([^)]+)\)(?:\s+Reversible)?$')
    SPELL_LEVEL_PATTERN = re.compile(
        r'^## (First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth) Level Spells:$'
    )
    NOTES_REGARDING_PATTERN = re.compile(r'^## Notes Regarding')
    MAJOR_SPELL_SECTION_PATTERN = re.compile(r'^## [A-Z\-]+ SPELLS')  # e.g., "DRUID SPELLS", "MAGIC-USER SPELLS"
    
    def __init__(self, state_machine: StateMachine, debug: bool = False):
        """
        Initialize heading rewriter.
        
        Args:
            state_machine: StateMachine instance for tracking context
            debug: Enable debug logging for heading transformations
        """
        self.state_machine = state_machine
        self.output_lines: List[str] = []
        self.debug = debug
        self.transformation_count = 0
    
    def process_line(self, line: str, line_num: int) -> None:
        """
        Process a single line, transforming headings as needed.
        
        Args:
            line: Line to process
            line_num: Line number (1-indexed)
        """
        if not line.startswith('##'):
            # Not a heading, pass through unchanged
            self.output_lines.append(line)
            return
        
        # Extract heading text
        heading_text = self._extract_heading_text(line)
        
        # Determine new heading level
        new_level = self._determine_heading_level(heading_text)
        
        # Update state machine with new level
        self._update_state(heading_text, new_level)
        
        # Rewrite heading with new level
        old_level = len(line) - len(line.lstrip('#'))
        new_line = self._rewrite_heading(line, new_level)
        self.output_lines.append(new_line)
        
        # Track transformations
        if old_level != new_level:
            self.transformation_count += 1
            if self.debug:
                print(f"  Line {line_num}: Level {old_level}→{new_level}: {heading_text[:50]}...")
    
    def _extract_heading_text(self, line: str) -> str:
        """
        Extract text portion of heading (remove ## markers).
        
        Args:
            line: Heading line
            
        Returns:
            Heading text without markers
        """
        return line.lstrip('#').strip()
    
    def _determine_heading_level(self, heading_text: str) -> int:
        """
        Apply rules to determine correct heading level.
        
        Args:
            heading_text: Heading text (without markers)
            
        Returns:
            Correct heading level (2-6)
        """
        sm = self.state_machine
        
        # Rule 1: Major section → level 2
        if sm.toc_parser.is_major_section(heading_text):
            return 2
        
        # Rule 2: Minor section → level 3
        if sm.toc_parser.is_minor_section(heading_text):
            return 3
        
        # Rule 2.5: Major spell section headers (e.g., "DRUID SPELLS") → level 3, exit spell section
        if self.MAJOR_SPELL_SECTION_PATTERN.match(f'## {heading_text}'):
            if sm.in_spell_section:
                sm.in_spell_section = False
            return 3
        
        # Rule 3: "Notes Regarding" → exit spell section if in one, then bump +1 from parent
        if self.NOTES_REGARDING_PATTERN.match(f'## {heading_text}'):
            # Exit spell section if in one
            if sm.in_spell_section:
                sm.in_spell_section = False
            # Determine parent level and bump
            parent_level = sm.heading_level
            return parent_level + 1
        
        # Rule 4: Spell level heading → level 4 + enter spell section
        if self._is_spell_level_heading(heading_text):
            return 4  # Will also set in_spell_section=True in _update_state
        
        # Rule 5: In spell section + spell name pattern → level 5
        if sm.in_spell_section and self.SPELL_NAME_PATTERN.match(f'## {heading_text}'):
            return 5
        
        # Rule 6: In spell section + not spell name → level 6 (sub-heading within spell)
        if sm.in_spell_section:
            return 6
        
        # Rule 7: In major section, not in minor section → level 3
        if sm.current_major_section and not sm.current_minor_section:
            return 3
        
        # Rule 8: In minor section → level 4
        if sm.current_minor_section:
            return 4
        
        # Fallback (shouldn't reach here)
        return 2
    
    def _is_spell_level_heading(self, heading_text: str) -> bool:
        """
        Check if heading matches spell level pattern.
        
        Args:
            heading_text: Heading text to check
            
        Returns:
            True if matches "First Level Spells:" pattern
        """
        return bool(self.SPELL_LEVEL_PATTERN.match(f'## {heading_text}'))
    
    def _update_state(self, heading_text: str, new_level: int) -> None:
        """
        Update state machine based on heading encountered.
        
        Args:
            heading_text: Heading text (without markers)
            new_level: The level assigned to this heading
        """
        sm = self.state_machine
        
        if sm.toc_parser.is_major_section(heading_text):
            sm.enter_major_section(heading_text)
        elif sm.toc_parser.is_minor_section(heading_text):
            sm.enter_minor_section(heading_text)
        elif self._is_spell_level_heading(heading_text):
            sm.enter_spell_section()
        else:
            # For all other headings, just update the level tracker
            sm.set_heading_level(new_level)
    
    def _rewrite_heading(self, original_line: str, new_level: int) -> str:
        """
        Rewrite heading with new level markers.
        
        Args:
            original_line: Original heading line
            new_level: New heading level
            
        Returns:
            Rewritten heading line
        """
        heading_text = self._extract_heading_text(original_line)
        new_markers = '#' * new_level
        return f'{new_markers} {heading_text}\n'
    
    def get_output(self) -> List[str]:
        """
        Get transformed lines.
        
        Returns:
            List of output lines
        """
        return self.output_lines


class InsanityTransformer:
    """Transforms insanity type descriptions into proper headings."""
    
    # Pattern to detect insanity descriptions at start of line
    # Matches lines starting with: <number(s) with optional spaces/periods>. <Insanity Name>: 
    # Examples: "1. Dipsomania:", "13. Paranoia:", "3. 1 3. Paranoia:" (malformed in PDF)
    # The pattern captures everything up to the insanity name
    INSANITY_PATTERN = re.compile(r'^([\d\s\.]+)\s+([A-Za-z\s\-]+):\s+(.*)$')
    
    def __init__(self, debug: bool = False):
        """
        Initialize insanity transformer.
        
        Args:
            debug: Enable debug logging
        """
        self.debug = debug
        self.transformation_count = 0
        self.in_insanity_section = False
    
    def _extract_number(self, number_str: str) -> str:
        """
        Extract the actual number from potentially malformed number strings.
        
        Examples:
            "1." → "1"
            "13." → "13"
            "3. 1 3." → "13" (OCR error: extra "3. " prefix)
        
        Args:
            number_str: Raw number string from regex capture
            
        Returns:
            Cleaned number string
        """
        # Handle malformed pattern like "3. 1 3." where there's a spurious "3. " prefix
        # Look for pattern: <digit>. <space> <actual number with optional spaces>
        malformed_match = re.search(r'^\d+\.\s+(\d+(?:\s+\d+)?)', number_str)
        if malformed_match:
            # Found malformed pattern - extract the actual number after first period
            # Remove any spaces within the number (e.g., "1 3" → "13")
            return malformed_match.group(1).replace(' ', '')
        
        # Simple case: just a number followed by period
        simple_match = re.match(r'^(\d+)', number_str)
        if simple_match:
            return simple_match.group(1)
        
        # Fallback: strip periods and spaces
        return number_str.strip('. ')
    
    def transform_insanity_types(self, lines: List[str]) -> List[str]:
        """
        Transform insanity type descriptions into level 4 headings.
        
        Processes lines in the INSANITY section, converting patterns like:
            1. Dipsomania: <description...>
        to:
            #### 1. Dipsomania:
            <description...>
        
        Args:
            lines: List of lines to process
            
        Returns:
            List of transformed lines
        """
        output_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Track when we enter the INSANITY section (### level)
            if line.startswith('### ') and 'INSANITY' in line:
                self.in_insanity_section = True
                if self.debug:
                    print(f"  → Entered INSANITY section at line {i}")
                output_lines.append(line)
                i += 1
                continue
            
            # Exit INSANITY section when we hit next level 2 or 3 heading
            if self.in_insanity_section and (line.startswith('## ') or line.startswith('### ')):
                self.in_insanity_section = False
                if self.debug:
                    print(f"  → Exited INSANITY section at line {i}")
                output_lines.append(line)
                i += 1
                continue
            
            # Only transform in INSANITY section
            if not self.in_insanity_section:
                output_lines.append(line)
                i += 1
                continue
            
            # Check if current line matches the insanity description pattern
            # (Don't require blank line before - entries run together in original)
            match = self.INSANITY_PATTERN.match(stripped)
            if match:
                number_raw = match.group(1).strip()
                number = self._extract_number(number_raw)
                insanity_name = match.group(2).strip()
                description_start = match.group(3).strip()
                
                # If previous line isn't blank, add one before the heading
                if len(output_lines) > 0 and output_lines[-1].strip() != '':
                    output_lines.append('\n')
                
                # Transform: <num>. <Name>: <desc> → #### <num>. <Name>:\n<desc>
                output_lines.append(f'#### {number}. {insanity_name}:\n')
                if description_start:
                    output_lines.append(f'{description_start}\n')
                
                self.transformation_count += 1
                if self.debug:
                    print(f"  → Transformed insanity: {number}. {insanity_name}")
                
                i += 1
                continue
            
            # No match, pass through unchanged
            output_lines.append(line)
            i += 1
        
        return output_lines


class MagicItemTransformer:
    """Transforms magic item descriptions into proper headings."""
    
    # Pattern to detect magic item names at start of line
    # Matches lines starting with: Capital letter followed by text and a colon
    # Examples: "Delusion:", "Animal Control:", "Extra-Healing:"
    ITEM_NAME_PATTERN = re.compile(r'^([A-Z][A-Za-z\s\-\']+):\s+(.*)$')
    
    def __init__(self, debug: bool = False):
        """
        Initialize magic item transformer.
        
        Args:
            debug: Enable debug logging
        """
        self.debug = debug
        self.transformation_count = 0
        self.in_magic_items_section = False
        self.in_subsection = False  # Track if we're in a subsection like "#### POTIONS"
    
    def transform_magic_items(self, lines: List[str]) -> List[str]:
        """
        Transform magic item descriptions into level 5 headings.
        
        Processes lines in the EXPLANATIONS AND DESCRIPTIONS OF MAGIC ITEMS section,
        converting patterns like:
            <Item Name>: <description...>
        to:
            ##### <Item Name>
            <description...>
        
        Only transforms items within subsections (after #### headings like POTIONS, SCROLLS, etc.)
        
        Args:
            lines: List of lines to process
            
        Returns:
            List of transformed lines
        """
        output_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Track when we enter the magic items section
            if 'EXPLANATIONS AND DESCRIPTIONS OF MAGIC ITEMS' in line:
                self.in_magic_items_section = True
                if self.debug:
                    print(f"  → Entered MAGIC ITEMS section at line {i}")
                output_lines.append(line)
                i += 1
                continue
            
            # Track when we enter a subsection like "#### POTIONS"
            if self.in_magic_items_section and line.startswith('#### '):
                self.in_subsection = True
                if self.debug:
                    print(f"  → Entered subsection: {stripped}")
                output_lines.append(line)
                i += 1
                continue
            
            # Exit magic items section when we hit next major/minor section (but not #### subsections)
            if self.in_magic_items_section and (line.startswith('## ') or line.startswith('### ')):
                self.in_magic_items_section = False
                self.in_subsection = False
                if self.debug:
                    print(f"  → Exited MAGIC ITEMS section at line {i}")
                output_lines.append(line)
                i += 1
                continue
            
            # Only transform in magic items subsections
            if not self.in_magic_items_section or not self.in_subsection:
                output_lines.append(line)
                i += 1
                continue
            
            # Check if current line matches the item name pattern
            # Must have a blank line before it (previous output line is blank)
            has_blank_before = len(output_lines) > 0 and output_lines[-1].strip() == ''
            
            if self.debug and has_blank_before and stripped and not line.startswith('#'):
                match_test = self.ITEM_NAME_PATTERN.match(stripped)
                if match_test:
                    print(f"  Line {i}: Potential item - '{stripped[:50]}...'")
                    print(f"    in_magic_items={self.in_magic_items_section}, in_subsection={self.in_subsection}")
            
            if has_blank_before:
                match = self.ITEM_NAME_PATTERN.match(stripped)
                if match:
                    item_name = match.group(1).strip()
                    description_start = match.group(2).strip()
                    
                    # Transform: <Item Name>: <desc> → ##### <Item Name>\n<desc>
                    output_lines.append(f'##### {item_name}\n')
                    if description_start:
                        output_lines.append(f'{description_start}\n')
                    
                    self.transformation_count += 1
                    if self.debug:
                        print(f"  → Transformed item: {item_name}")
                    
                    i += 1
                    continue
            
            # No match, pass through unchanged
            output_lines.append(line)
            i += 1
        
        return output_lines


class HeadingOrganizer:
    """Main orchestrator for heading reorganization."""
    
    def __init__(
        self,
        markdown_file: str,
        toc_file: str,
        output_file: str = None,
        create_backup: bool = True,
        debug: bool = False
    ):
        """
        Initialize heading organizer.
        
        Args:
            markdown_file: Path to markdown file to process
            toc_file: Path to Table of Contents file
            output_file: Output file path (default: adds "_organized" suffix)
            create_backup: Create backup if output file exists
            debug: Enable debug logging
        """
        self.markdown_file = Path(markdown_file)
        self.toc_file = Path(toc_file)
        self.debug = debug
        
        if output_file:
            self.output_file = Path(output_file)
        else:
            # Default: add "_organized" suffix
            stem = self.markdown_file.stem
            self.output_file = self.markdown_file.parent / f"{stem}_organized.md"
        
        self.create_backup = create_backup
        
        # Initialize components
        self.toc_parser = TOCParser(str(self.toc_file))
        self.toc_parser.parse()
        
        self.state_machine = StateMachine(self.toc_parser)
        self.heading_rewriter = HeadingRewriter(self.state_machine, debug=debug)
        self.insanity_transformer = InsanityTransformer(debug=debug)
        self.magic_item_transformer = MagicItemTransformer(debug=debug)
    
    def process(self) -> None:
        """Main processing pipeline."""
        print(f"\nReading {self.markdown_file}...")
        
        if not self.markdown_file.exists():
            raise FileNotFoundError(f"Markdown file not found: {self.markdown_file}")
        
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"Processing {len(lines)} lines...")
        
        # Phase 1: Reorganize headings
        for line_num, line in enumerate(lines, 1):
            self.heading_rewriter.process_line(line, line_num)
            
            # Progress indicator every 1000 lines
            if line_num % 1000 == 0:
                print(f"  Processed {line_num}/{len(lines)} lines...")
        
        # Phase 2: Transform insanity and magic item descriptions (DMG only)
        output_lines = self.heading_rewriter.get_output()
        if 'Dungeon_Master' in self.markdown_file.name or 'DMG' in self.markdown_file.name:
            print(f"\nTransforming insanity type descriptions...")
            output_lines = self.insanity_transformer.transform_insanity_types(output_lines)
            
            print(f"\nTransforming magic item descriptions...")
            output_lines = self.magic_item_transformer.transform_magic_items(output_lines)
        
        # Write output
        print(f"\nWriting output to {self.output_file}...")
        self._write_output(output_lines)
        
        print(f"\nValidating output...")
        self._validate_output(len(lines))
        
        print(f"\n✅ Heading organization complete!")
        print(f"   Heading transformations: {self.heading_rewriter.transformation_count}")
        if hasattr(self, 'insanity_transformer') and self.insanity_transformer.transformation_count > 0:
            print(f"   Insanity type transformations: {self.insanity_transformer.transformation_count}")
        if hasattr(self, 'magic_item_transformer') and self.magic_item_transformer.transformation_count > 0:
            print(f"   Magic item transformations: {self.magic_item_transformer.transformation_count}")
        self._print_statistics()
    
    def _write_output(self, output_lines: List[str]) -> None:
        """
        Write transformed lines to output file.
        
        Args:
            output_lines: Lines to write
        """
        if self.create_backup and self.output_file.exists():
            backup_file = self.output_file.with_suffix('.md.bak')
            print(f"  Creating backup: {backup_file}")
            self.output_file.rename(backup_file)
        
        # Ensure parent directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
    
    def _validate_output(self, expected_line_count: int) -> None:
        """
        Validate output file.
        
        Args:
            expected_line_count: Expected number of lines before transformations
        """
        with open(self.output_file, 'r', encoding='utf-8') as f:
            output_lines = f.readlines()
        
        actual_count = len(output_lines)
        
        # Calculate total transformations from all transformers
        total_transformations = 0
        transform_details = []
        
        # Insanity transformations add 2 lines each (blank line + heading split)
        if hasattr(self, 'insanity_transformer') and self.insanity_transformer.transformation_count > 0:
            insanity_additions = self.insanity_transformer.transformation_count * 2
            total_transformations += insanity_additions
            transform_details.append(f"{self.insanity_transformer.transformation_count} insanity ({insanity_additions} lines)")
        
        # Magic item transformations add 1 line each (heading split)
        if hasattr(self, 'magic_item_transformer') and self.magic_item_transformer.transformation_count > 0:
            total_transformations += self.magic_item_transformer.transformation_count
            transform_details.append(f"{self.magic_item_transformer.transformation_count} magic item")
        
        # If transformations occurred, line count will increase
        # (each transformation adds 1 line: item/insanity name becomes heading + description)
        if total_transformations > 0:
            expected_with_transforms = expected_line_count + total_transformations
            if actual_count != expected_with_transforms:
                print(f"  ⚠ Line count: expected {expected_with_transforms} "
                      f"(original {expected_line_count} + {total_transformations} transformations), "
                      f"got {actual_count}")
            else:
                detail_str = " + ".join(transform_details)
                print(f"  ✓ Line count correct: {actual_count} "
                      f"(original {expected_line_count} + {detail_str} transformations)")
        else:
            if actual_count != expected_line_count:
                raise ValueError(
                    f"Line count mismatch! Expected {expected_line_count}, "
                    f"got {actual_count}"
                )
            print(f"  ✓ Line count correct: {expected_line_count}")
    
    def _print_statistics(self) -> None:
        """Print statistics about heading transformations."""
        with open(self.output_file, 'r', encoding='utf-8') as f:
            output_lines = f.readlines()
        
        heading_counts = {}
        for line in output_lines:
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_counts[level] = heading_counts.get(level, 0) + 1
        
        print("\nHeading level distribution:")
        for level in sorted(heading_counts.keys()):
            count = heading_counts[level]
            print(f"  Level {level}: {count} headings")


def main():
    """Main entry point for standalone script execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Organize heading hierarchy in Player's Handbook markdown"
    )
    parser.add_argument(
        'markdown_file',
        help='Path to markdown file to process'
    )
    parser.add_argument(
        '--toc',
        default=None,
        help='Path to Table of Contents file (default: auto-detect)'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output file path (default: adds "_organized" suffix)'
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backup creation if output file exists'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Auto-detect TOC file if not specified
    toc_file = args.toc
    if not toc_file:
        markdown_path = Path(args.markdown_file)
        # Look for TOC in data/source_pdfs/notes/
        possible_toc = Path('data/source_pdfs/notes/Players_Handbook_TOC.txt')
        if possible_toc.exists():
            toc_file = str(possible_toc)
        else:
            print("Error: Could not auto-detect TOC file. Please specify with --toc")
            sys.exit(1)
    
    try:
        organizer = HeadingOrganizer(
            markdown_file=args.markdown_file,
            toc_file=toc_file,
            output_file=args.output,
            create_backup=not args.no_backup,
            debug=args.debug
        )
        organizer.process()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
