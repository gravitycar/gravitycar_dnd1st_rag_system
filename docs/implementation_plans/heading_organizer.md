# Implementation Plan: Heading Organizer for Player's Handbook

## 1. Feature Overview

### Purpose
The Heading Organizer preprocesses the `Players_Handbook_(1e).md` file by restructuring its flat heading hierarchy into a properly nested hierarchy. This transformation enables the chunking pipeline to create semantic chunks that maintain proper parent-child relationships, improving retrieval accuracy in the RAG system.

### Problem Statement
Currently, all headings in the Player's Handbook markdown are level 2 (`##`), regardless of their semantic depth. For example:
- `## SPELL EXPLANATIONS` (major section)
- `## CLERIC SPELLS` (minor section within SPELL EXPLANATIONS)
- `## First Level Spells:` (sub-section within CLERIC SPELLS)
- `## Bless (Conjuration/Summoning) Reversible` (individual spell entry)

All four of these are `##` level headings, even though `Bless` is conceptually nested 4 levels deep. This flat structure prevents chunkers from understanding document hierarchy and creating proper parent-child relationships.

### Goals
1. Transform flat heading structure into hierarchical structure
2. Use Table of Contents (TOC) as authoritative source for major/minor section boundaries
3. Apply context-aware rules for heading levels within each section type
4. Create a new markdown file with corrected heading levels
5. Preserve all content exactly as-is (only modify heading markers)
6. Enable downstream chunkers to leverage heading hierarchy

### Non-Goals
- **Not** modifying any content except heading markers (`##` → `###`, etc.)
- **Not** changing the chunking logic itself (that's a separate phase)
- **Not** handling other D&D books (only Player's Handbook initially)

---

## 2. Requirements

### Functional Requirements

**FR1: TOC Parsing**
- Parse `Players_Handbook_TOC.txt` to extract major and minor sections
- Identify section hierarchy (indentation indicates minor sections)
- Store section names and their nesting relationships

**FR2: State Machine Implementation**
- Track current major section
- Track current minor section  
- Track current heading level (with ability to bump for one operation)
- Track whether currently in a spell section
- Maintain line-by-line position in document

**FR3: Heading Level Rules**
Apply these rules in order:
1. Major section heading → level 2 (no change)
2. Minor section heading → level 3
3. "Notes Regarding" heading → level = current + 1 (bump)
4. Spell level heading (e.g., "First Level Spells:") → level 4 + enter spell section
5. Within spell section, spell name pattern → level 5
6. Within spell section, non-spell pattern → level = current + 1 (bump)
7. Heading in major section but not minor section → level 3
8. Heading in minor section → level 4

**FR4: Spell Name Pattern Detection**
Detect spell entries by pattern: `## <name> (<magic type>)`
- Examples: `Bless (Conjuration/Summoning)`, `Command (Enchantment/Charm)`
- May include "Reversible" suffix
- Parentheses contain spell school/type

**FR5: Output Generation**
- Create new markdown file with modified heading levels
- Preserve all other content exactly
- Maintain line breaks, spacing, and formatting

### Non-Functional Requirements

**NFR1: Performance**
- Process full Player's Handbook (~13,000 lines) in < 5 seconds

**NFR2: Correctness**
- Zero content loss (byte-for-byte identical except heading markers)
- Deterministic output (same input always produces same output)

**NFR3: Maintainability**
- Clear separation of concerns (TOC parser, state machine, heading transformer)
- Comprehensive logging for debugging
- Unit testable components

**NFR4: Safety**
- Never overwrite source file
- Create backup before any file operations
- Validate output file before declaring success

---

## 3. Design

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HeadingOrganizer                              │
│  (Main orchestrator)                                             │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌─────────────────┐
│ TOCParser    │ │ StateMachine │ │ HeadingRewriter │
│              │ │              │ │                 │
│ Parses TOC   │ │ Tracks:      │ │ Line-by-line    │
│ file into    │ │ - Major sect │ │ heading         │
│ structured   │ │ - Minor sect │ │ transformation  │
│ section map  │ │ - Level      │ │                 │
│              │ │ - In spell   │ │                 │
└──────────────┘ └──────────────┘ └─────────────────┘
```

### 3.2 Component Design

#### 3.2.1 TOCParser Class

```python
class TOCParser:
    """Parses Players_Handbook_TOC.txt into structured section map."""
    
    def __init__(self, toc_file_path: str):
        self.toc_file_path = Path(toc_file_path)
        self.major_sections: List[str] = []
        self.minor_sections: Dict[str, List[str]] = {}
        # Maps minor section name → its parent major section
        self.section_hierarchy: Dict[str, str] = {}
    
    def parse(self) -> None:
        """Parse TOC file and populate section maps."""
        # Algorithm:
        # 1. Read TOC line by line
        # 2. Strip dots and page numbers (only keep section name + indentation)
        # 3. Unindented ALL CAPS = major section
        # 4. Indented Initial Caps = minor section (belongs to last major)
        # 5. Track indentation level to determine hierarchy
        pass
    
    def is_major_section(self, heading: str) -> bool:
        """Check if heading is a major section."""
        return heading.strip() in self.major_sections
    
    def is_minor_section(self, heading: str) -> bool:
        """Check if heading is a minor section."""
        return heading.strip() in self.section_hierarchy
    
    def get_parent_major_section(self, minor_section: str) -> Optional[str]:
        """Get parent major section for a minor section."""
        return self.section_hierarchy.get(minor_section)
```

**Key Design Decisions:**
- TOC is authoritative source for section boundaries
- Strip all dots (`.`) and page numbers from TOC entries - only section names and indentation matter
- Use indentation (leading spaces) to determine hierarchy level
- Handle variations in capitalization/whitespace through normalization

#### 3.2.2 StateMachine Class

```python
class StateMachine:
    """Tracks context while processing document line-by-line."""
    
    def __init__(self, toc_parser: TOCParser):
        self.toc_parser = toc_parser
        self.current_major_section: Optional[str] = None
        self.current_minor_section: Optional[str] = None
        self.heading_level: int = 2
        self.in_spell_section: bool = False
        self.bump_next: bool = False  # For one-time level increase
    
    def enter_major_section(self, section_name: str) -> None:
        """Transition to new major section."""
        self.current_major_section = section_name
        self.current_minor_section = None
        self.in_spell_section = False
        self.heading_level = 2
    
    def enter_minor_section(self, section_name: str) -> None:
        """Transition to new minor section."""
        self.current_minor_section = section_name
        self.in_spell_section = False
        self.heading_level = 3
    
    def set_heading_level(self, level: int) -> None:
        """Explicitly set heading level."""
        self.heading_level = level
        self.bump_next = False
    
    def bump_heading_level(self) -> None:
        """Increase heading level by 1 for next heading only."""
        self.bump_next = True
    
    def get_current_level(self) -> int:
        """Get heading level to apply, respecting bump flag."""
        if self.bump_next:
            level = self.heading_level + 1
            self.bump_next = False
            return level
        return self.heading_level
    
    def enter_spell_section(self) -> None:
        """Enter spell listing section."""
        self.in_spell_section = True
        self.heading_level = 4  # "First Level Spells:" is level 4
```

**Key Design Decisions:**
- `bump_next` flag auto-resets after one use
- State transitions are explicit and logged
- Current level can be queried without modifying state

#### 3.2.3 HeadingRewriter Class

```python
class HeadingRewriter:
    """Transforms heading levels in markdown document."""
    
    SPELL_NAME_PATTERN = re.compile(r'^## (.+?) \(([^)]+)\)(?:\s+Reversible)?$')
    SPELL_LEVEL_PATTERN = re.compile(
        r'^## (First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth) Level Spells:$'
    )
    NOTES_REGARDING_PATTERN = re.compile(r'^## Notes Regarding')
    
    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        self.output_lines: List[str] = []
    
    def process_line(self, line: str, line_num: int) -> None:
        """Process a single line, transforming headings as needed."""
        if not line.startswith('##'):
            # Not a heading, pass through unchanged
            self.output_lines.append(line)
            return
        
        # Extract heading text
        heading_text = self._extract_heading_text(line)
        
        # Determine new heading level
        new_level = self._determine_heading_level(heading_text)
        
        # Update state machine
        self._update_state(heading_text)
        
        # Rewrite heading with new level
        new_line = self._rewrite_heading(line, new_level)
        self.output_lines.append(new_line)
    
    def _extract_heading_text(self, line: str) -> str:
        """Extract text portion of heading (remove ## markers)."""
        return line.lstrip('#').strip()
    
    def _determine_heading_level(self, heading_text: str) -> int:
        """Apply rules to determine correct heading level."""
        sm = self.state_machine
        
        # Rule 1: Major section
        if sm.toc_parser.is_major_section(heading_text):
            return 2
        
        # Rule 2: Minor section
        if sm.toc_parser.is_minor_section(heading_text):
            return 3
        
        # Rule 3: "Notes Regarding" → bump
        if self.NOTES_REGARDING_PATTERN.match(f'## {heading_text}'):
            sm.bump_heading_level()
            return sm.get_current_level()
        
        # Rule 4: Spell level heading (e.g., "First Level Spells:")
        if self._is_spell_level_heading(heading_text):
            return 4  # Will also set in_spell_section=True in _update_state
        
        # Rule 5: In spell section + spell name pattern
        if sm.in_spell_section and self.SPELL_NAME_PATTERN.match(f'## {heading_text}'):
            return 5
        
        # Rule 6: In spell section + not spell name → bump
        if sm.in_spell_section:
            sm.bump_heading_level()
            return sm.get_current_level()
        
        # Rule 7: In major section, not in minor section
        if sm.current_major_section and not sm.current_minor_section:
            return 3
        
        # Rule 8: In minor section
        if sm.current_minor_section:
            return 4
        
        # Fallback (shouldn't reach here)
        return 2
    
    def _is_spell_level_heading(self, heading_text: str) -> bool:
        """Check if heading matches spell level pattern."""
        return bool(self.SPELL_LEVEL_PATTERN.match(f'## {heading_text}'))
    
    def _update_state(self, heading_text: str) -> None:
        """Update state machine based on heading encountered."""
        sm = self.state_machine
        
        if sm.toc_parser.is_major_section(heading_text):
            sm.enter_major_section(heading_text)
        elif sm.toc_parser.is_minor_section(heading_text):
            sm.enter_minor_section(heading_text)
        elif self._is_spell_level_heading(heading_text):
            sm.enter_spell_section()
    
    def _rewrite_heading(self, original_line: str, new_level: int) -> str:
        """Rewrite heading with new level markers."""
        heading_text = self._extract_heading_text(original_line)
        new_markers = '#' * new_level
        return f'{new_markers} {heading_text}\n'
    
    def get_output(self) -> List[str]:
        """Get transformed lines."""
        return self.output_lines
```

**Key Design Decisions:**
- Regex patterns for spell detection are pre-compiled
- Rule application order matters (more specific rules first)
- State updates happen after level determination
- Original line preserved if not a heading

#### 3.2.4 HeadingOrganizer Class (Main)

```python
class HeadingOrganizer:
    """Main orchestrator for heading reorganization."""
    
    def __init__(
        self,
        markdown_file: str,
        toc_file: str,
        output_file: str = None,
        create_backup: bool = True
    ):
        self.markdown_file = Path(markdown_file)
        self.toc_file = Path(toc_file)
        
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
        self.heading_rewriter = HeadingRewriter(self.state_machine)
    
    def process(self) -> None:
        """Main processing pipeline."""
        print(f"Reading {self.markdown_file}...")
        
        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print(f"Processing {len(lines)} lines...")
        
        for line_num, line in enumerate(lines, 1):
            self.heading_rewriter.process_line(line, line_num)
            
            # Progress indicator every 1000 lines
            if line_num % 1000 == 0:
                print(f"  Processed {line_num}/{len(lines)} lines...")
        
        print(f"\nWriting output to {self.output_file}...")
        self._write_output()
        
        print(f"\nValidating output...")
        self._validate_output(len(lines))
        
        print(f"\n✅ Heading organization complete!")
        self._print_statistics()
    
    def _write_output(self) -> None:
        """Write transformed lines to output file."""
        if self.create_backup and self.output_file.exists():
            backup_file = self.output_file.with_suffix('.md.bak')
            print(f"Creating backup: {backup_file}")
            self.output_file.rename(backup_file)
        
        output_lines = self.heading_rewriter.get_output()
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
    
    def _validate_output(self, expected_line_count: int) -> None:
        """Validate output file."""
        with open(self.output_file, 'r', encoding='utf-8') as f:
            output_lines = f.readlines()
        
        if len(output_lines) != expected_line_count:
            raise ValueError(
                f"Line count mismatch! Expected {expected_line_count}, "
                f"got {len(output_lines)}"
            )
        
        print(f"  ✓ Line count correct: {expected_line_count}")
    
    def _print_statistics(self) -> None:
        """Print statistics about heading transformations."""
        output_lines = self.heading_rewriter.get_output()
        
        heading_counts = {}
        for line in output_lines:
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_counts[level] = heading_counts.get(level, 0) + 1
        
        print("\nHeading level distribution:")
        for level in sorted(heading_counts.keys()):
            count = heading_counts[level]
            print(f"  Level {level}: {count} headings")
```

### 3.3 Data Flow

```
1. Load TOC file → Parse into section maps
                    ↓
2. Initialize state machine with section maps
                    ↓
3. Read markdown file line-by-line
                    ↓
4. For each line:
   - If not heading → pass through unchanged
   - If heading:
     a. Determine new level (consult TOC + apply rules)
     b. Update state machine
     c. Rewrite heading with new level
                    ↓
5. Write all lines to output file
                    ↓
6. Validate output (line count, sample headings)
                    ↓
7. Print statistics
```

### 3.4 Special Cases & Edge Cases

**Special Case 1: SPELL EXPLANATIONS Major Section**
- Contains 4 minor sections: CLERIC SPELLS, DRUID SPELLS, MAGIC-USER SPELLS, ILLUSIONIST SPELLS
- Each minor section has spell level subsections ("First Level Spells:", etc.)
- Each spell level subsection contains individual spell entries

**Special Case 2: CHARACTER CLASSES Major Section**
- Contains minor sections: Cleric, Fighter, Magic-User, Thief, Monk, etc.
- Some character classes have sub-classes (Paladin under Fighter, Druid under Cleric)
- Sub-class headings should have the same level as their parent class (level 3, since they are minor sections in the TOC)

**Special Case 3: Notes Headings**
- Pattern: "Notes Regarding <topic>"
- Always bumped +1 from current level
- Example: "Notes Regarding Cleric Spells" should be one level deeper than "CLERIC SPELLS"

**Edge Case 1: Duplicate Heading Names**
- Some spell names appear in multiple sections (e.g., "Create Water" in both Cleric and Druid)
- State machine must use position context, not just heading text

**Edge Case 2: Irregular Capitalization**
- TOC may have "Clerics" while markdown has "CLERIC SPELLS"
- Need fuzzy matching or normalization

**Edge Case 3: Section Without TOC Entry**
- Some headings in markdown may not be in TOC (e.g., tables)
- Fallback rules handle these cases

---

## 4. Implementation Steps

### Phase 1: Foundation (Estimated: 2 hours)

**Step 1.1: Create File Structure**
- Create `src/preprocessors/` directory
- Create `src/preprocessors/__init__.py`
- Create `src/preprocessors/heading_organizer.py`

**Step 1.2: Implement TOCParser**
- Implement `__init__`, `parse`, section lookup methods
- Parse algorithm: strip all dots (`.`) and page numbers, extract section names and indentation
- Add logging for parsed sections (show indentation levels)
- Write unit tests for TOC parsing (including dot stripping)

**Step 1.3: Implement StateMachine**
- Implement state tracking and transitions
- Add debug logging for state changes
- Write unit tests for state transitions

**Deliverable:** `TOCParser` and `StateMachine` classes with unit tests

### Phase 2: Core Logic (Estimated: 3 hours)

**Step 2.1: Implement HeadingRewriter**
- Implement line processing loop
- Implement rule application logic
- Add detailed logging for each heading transformation

**Step 2.2: Test Rule Application**
- Create test markdown samples for each rule
- Verify correct heading levels are assigned
- Test edge cases (duplicate names, etc.)

**Step 2.3: Implement HeadingOrganizer**
- Wire up all components
- Add file I/O with error handling
- Implement validation logic

**Deliverable:** Complete `HeadingOrganizer` with rule-based rewriting

### Phase 3: Integration & Testing (Estimated: 2 hours)

**Step 3.1: Process Full Player's Handbook**
- Run on actual `Players_Handbook_(1e).md`
- Review output for correctness
- Fix any issues discovered

**Step 3.2: Verify Chunker Compatibility**
- Feed organized markdown to existing `PlayersHandbookChunker`
- Verify chunks have proper parent references
- Adjust if needed

**Step 3.3: Add CLI Integration**
- Add `organize` subcommand to both `main.py` and `cli.py`
- `main.py`: Add `cmd_organize()` function following existing pattern
- `cli.py`: Add `organize_main()` entry point for `dnd-organize` command
- Support command-line arguments (markdown file, TOC file, output file, flags)
- Add comprehensive help text and usage examples

**Deliverable:** Working end-to-end pipeline with CLI

### Phase 4: Documentation & Validation (Estimated: 1 hour)

**Step 4.1: Write Usage Documentation**
- Update README with organize command
- Document typical workflow
- Add before/after examples

**Step 4.2: Create Validation Script**
- Script to compare original vs organized (content-only)
- Statistical analysis of heading changes
- Sanity checks (e.g., no level 1 headings created)

**Step 4.3: Final Testing**
- Run full pipeline: organize → chunk → embed → query
- Verify query results improve
- Document any issues

**Deliverable:** Complete documentation and validation

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Test TOCParser:**
- `test_parse_major_sections`: Verify all major sections extracted
- `test_parse_minor_sections`: Verify minor sections and parent relationships
- `test_section_lookup`: Verify `is_major_section`, `is_minor_section` methods
- `test_dot_stripping`: Verify all dots and page numbers removed from TOC entries
- `test_indentation_detection`: Verify indentation correctly identifies hierarchy
- `test_whitespace_handling`: Verify trimming and normalization

**Test StateMachine:**
- `test_initial_state`: Verify default state
- `test_enter_major_section`: Verify state transitions
- `test_enter_minor_section`: Verify state transitions
- `test_bump_flag`: Verify bump resets after use
- `test_spell_section_entry`: Verify spell section state

**Test HeadingRewriter:**
- `test_non_heading_passthrough`: Verify non-headings unchanged
- `test_major_section_level`: Verify level 2 for major sections
- `test_minor_section_level`: Verify level 3 for minor sections
- `test_spell_name_level`: Verify level 5 for spells
- `test_spell_level_heading`: Verify level 4 for "First Level Spells:", etc.
- `test_notes_regarding_bump`: Verify +1 level for notes
- `test_fallback_rules`: Verify rules 7 and 8

### 5.2 Integration Tests

**Test Complete Document Processing:**
- `test_process_sample_document`: Small markdown sample with all heading types
- `test_line_count_preservation`: Verify no lines added/removed
- `test_content_preservation`: Verify only heading markers changed
- `test_output_file_creation`: Verify output file written correctly

### 5.3 End-to-End Tests

**Test Full Player's Handbook:**
- `test_players_handbook_organization`: Process full file
- `test_heading_distribution`: Verify expected counts at each level
- `test_spell_section_hierarchy`: Verify SPELL EXPLANATIONS section correct
- `test_character_classes_hierarchy`: Verify CHARACTER CLASSES section correct

### 5.4 Validation Tests

**Test Compatibility with Downstream:**
- `test_chunker_integration`: Verify chunker works with organized markdown
- `test_chunk_metadata`: Verify chunks have correct parent references
- `test_query_improvement`: Verify queries return better results (manual)

---

## 6. Documentation

### 6.1 User-Facing Documentation

**README Update:**
```markdown
### Organize Headings

Before chunking, organize the heading hierarchy:

```bash
python src/preprocessors/heading_organizer.py \
  data/markdown/Players_Handbook_(1e).md \
  data/source_pdfs/notes/Players_Handbook_TOC.txt \
  --output data/markdown/Players_Handbook_(1e)_organized.md
```

This transforms flat heading structure into hierarchical structure based on the Table of Contents.
```

**Usage Examples:**
```bash
# Basic usage (auto-detects TOC location)
dnd-organize data/markdown/Players_Handbook_(1e).md

# Specify custom output location
dnd-organize data/markdown/Players_Handbook_(1e).md \
  --output data/processed/organized.md

# Skip backup creation (use with caution)
dnd-organize data/markdown/Players_Handbook_(1e).md --no-backup

# Dry run (print changes without writing)
dnd-organize data/markdown/Players_Handbook_(1e).md --dry-run
```

### 6.2 Developer Documentation

**Architecture Document:**
- Component diagram
- Data flow diagram
- State machine diagram
- Rule priority matrix

**API Documentation:**
- Docstrings for all public methods
- Type hints for all parameters and returns
- Usage examples in docstrings

**Implementation Notes:**
- Why TOC is authoritative
- Why rules are ordered
- Why bump flag auto-resets
- Known limitations

### 6.3 Inline Documentation

**Code Comments:**
- Explain WHY, not WHAT
- Reference specification document
- Note any deviations from spec
- Mark TODOs and FIXMEs

---

## 7. Risks and Mitigations

### Risk 1: TOC Doesn't Match Markdown
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Fuzzy matching for section names
- Log warnings for unmatched sections
- Fallback to heuristic rules if TOC lookup fails

### Risk 2: Complex Nesting in CHARACTER CLASSES
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Special handling for sub-class pattern (Paladin, Druid, etc.)
- Extra logging in this section during development
- Manual verification of this section

### Risk 3: Performance on Large Files
**Impact:** Low  
**Probability:** Low  
**Mitigation:**
- Process line-by-line (no loading entire file into memory)
- Profile if issues arise
- Could optimize later if needed (13K lines is not large)

### Risk 4: Downstream Compatibility
**Impact:** High  
**Probability:** Low  
**Mitigation:**
- Test with existing chunker before finalizing
- Add rollback mechanism (keep original file)
- Version organized markdown files

### Risk 5: Edge Cases Break Rules
**Impact:** Medium  
**Probability:** Medium  
**Mitigation:**
- Comprehensive unit tests for edge cases
- Fallback to safe default (level 2 or 3)
- Log all rule application decisions for debugging

---

## 8. Future Enhancements

### Enhancement 1: Auto-TOC Generation
If TOC file missing or incomplete, generate one by analyzing heading patterns.

### Enhancement 2: Multi-Book Support
Extend to handle Dungeon Master's Guide, Unearthed Arcana, etc.

### Enhancement 3: Interactive Mode
Show proposed changes and ask for confirmation before writing.

### Enhancement 4: Diff Visualization
Generate HTML diff showing before/after heading changes.

### Enhancement 5: Configuration File
Allow custom rules via YAML/JSON config instead of hardcoding.

### Enhancement 6: Heading Validation
Check for common errors (e.g., skipped levels, orphaned sections).

---

## 9. Success Criteria

### Functional Success
- [ ] All major sections remain level 2
- [ ] All minor sections become level 3
- [ ] Spell entries become level 5
- [ ] No content loss (only heading markers changed)
- [ ] Output file passes validation

### Integration Success
- [ ] Existing chunker works with organized markdown
- [ ] Chunks have proper hierarchy metadata
- [ ] No chunker modifications required (ideal) or minimal (acceptable)

### Quality Success
- [ ] 100% unit test coverage for rule application
- [ ] All integration tests pass
- [ ] No manual fixes required after processing

### Performance Success
- [ ] Full Player's Handbook processed in < 5 seconds
- [ ] Memory usage < 100 MB

### Documentation Success
- [ ] README includes organize command
- [ ] Developer docs explain architecture
- [ ] Inline comments explain complex rules

---

## 10. Open Questions

### Question 1: Should we modify the existing markdown file or create a new one?
**Recommendation:** Create new file by default (safer), with option to overwrite.

### Question 2: How to handle sections not in TOC?
**Recommendation:** Use heuristic rules (e.g., if in major section but not minor, use level 3).

### Question 3: Should this be a separate script or integrated into chunker?
**Recommendation:** Separate script (follows Unix philosophy), with option to chain.

### Question 4: How to handle sub-sub-classes (if any)?
**Recommendation:** Not observed in current TOC; handle when discovered.

### Question 5: Should we version organized files?
**Recommendation:** Yes, include date/version in filename (e.g., `_organized_v1_2025-10-17.md`).

---

## 11. Implementation Checklist

- [ ] Phase 1: Foundation
  - [ ] Create file structure
  - [ ] Implement TOCParser
  - [ ] Implement StateMachine
  - [ ] Write unit tests
- [ ] Phase 2: Core Logic
  - [ ] Implement HeadingRewriter
  - [ ] Test rule application
  - [ ] Implement HeadingOrganizer
  - [ ] Write integration tests
- [ ] Phase 3: Integration
  - [ ] Process full Player's Handbook
  - [ ] Verify chunker compatibility
  - [ ] Add CLI integration
- [ ] Phase 4: Documentation
  - [ ] Write usage docs
  - [ ] Create validation script
  - [ ] Final testing
- [ ] Phase 5: Review
  - [ ] Code review
  - [ ] Documentation review
  - [ ] User acceptance testing

---

## 12. Appendix

### A. Example Transformations

**Before:**
```markdown
## SPELL EXPLANATIONS
## CLERIC SPELLS
## Notes Regarding Cleric Spells:
## First Level Spells:
## Bless (Conjuration/Summoning) Reversible
```

**After:**
```markdown
## SPELL EXPLANATIONS
### CLERIC SPELLS
#### Notes Regarding Cleric Spells:
#### First Level Spells:
##### Bless (Conjuration/Summoning) Reversible
```

### B. Rule Priority Matrix

| Priority | Rule Description | Example |
|----------|-----------------|---------|
| 1 | Major section | `## SPELL EXPLANATIONS` → level 2 |
| 2 | Minor section | `## CLERIC SPELLS` → level 3 |
| 3 | "Notes Regarding" | `## Notes Regarding Cleric Spells:` → bump |
| 4 | Spell level heading | `## First Level Spells:` → level 4 |
| 5 | Spell name (in spell section) | `## Bless (...)` → level 5 |
| 6 | Non-spell (in spell section) | `## Explanation/Description:` → bump |
| 7 | In major, not in minor | `## Starting Money` → level 3 |
| 8 | In minor section | `## The Monetary System` → level 4 |

### C. TOC Structure Excerpt

```
SPELL EXPLANATIONS (major, level 2)
    Clerics (minor, level 3)
    Druids (minor, level 3)
    Magic-Users (minor, level 3)
    Illusionists (minor, level 3)

CHARACTER CLASSES (major, level 2)
    Cleric (minor, level 3)
        Druid (sub-class in TOC, treat as minor, level 3)
    Fighter (minor, level 3)
        Paladin (sub-class in TOC, treat as minor, level 3)
        Ranger (sub-class in TOC, treat as minor, level 3)
    
Note: Sub-classes are indented in TOC but should be treated as 
minor sections (level 3) like their parent classes.
```

---

**Last Updated:** 2025-10-17  
**Version:** 1.0  
**Status:** Draft - Awaiting Review
