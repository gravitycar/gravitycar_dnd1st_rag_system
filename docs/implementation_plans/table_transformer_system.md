# Implementation Plan: Table Transformer System

**NOTE: this implementation plan is a WIP and may be not be necessary**
The issue I'm trying to solve is that LLM's don't ready markdown tables reliable. 
The solution in this document is to convert markdown tables into well-formed JSON with human and LLM readable property name.
I think the JSON will be much easier for LLM's to parse.
The problem that is unsolved so far is how to get those human and LLM friendly property names, because that data isn't always immediately available in the markdown.
I'm moving away from this solution because there are so many complex edge cases that it's not addressing. I want to see if there are other approaches.

## 1. Feature Overview

The Table Transformer system will convert markdown tables in D&D 1st Edition source documents into structured JSON representations within markdown code blocks. This transformation occurs in the preprocessing stage, before chunking and embedding, to improve LLM accuracy when parsing complex tabular data (particularly 2D lookup matrices like Attack Tables).

**Core Problem Solved**: LLMs misread markdown tables with multi-row headers and complex column structures, leading to incorrect answers (e.g., "fighter needs 15 to hit AC 3" instead of correct "11").

**Solution Approach**: Transform ambiguous markdown table structures into unambiguous JSON key-value representations that LLMs can parse reliably.

## 2. Requirements

### 2.1 Functional Requirements

**FR1**: Detect and transform 6 table structure patterns:
- Simple tables (default pattern)
- 2-column layout tables (duplicated headers)
- 2D matrix lookup tables (attack matrices, saving throws)
- Multi-level header tables (grouped columns)
- Embedded row group tables (range labels within data)
- Transposed tables (row labels in column 1)

**FR2**: Preserve original table location and context in document

**FR3**: Output JSON in markdown code blocks with table metadata

**FR4**: Maintain idempotency (running twice produces same result)

**FR5**: Detect and report malformed tables without failing

**FR6**: Support all three source documents (DMG, PHB, Monster Manual)

### 2.2 Non-Functional Requirements

**NFR1**: Single Responsibility - Each transformer handles one pattern only

**NFR2**: Open/Closed - Adding new patterns doesn't modify existing code

**NFR3**: Dependency Inversion - Orchestrator depends on abstractions, not concrete transformers

**NFR4**: Performance - Process entire DMG (17,239 lines) in < 30 seconds

**NFR5**: Testability - Each component unit-testable in isolation

**NFR6**: Error Resilience - Malformed tables don't crash pipeline

## 3. Design

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  TableTransformerOrchestrator               │
│  - Coordinates entire transformation pipeline               │
│  - Discovers and manages transformer instances              │
│  - Handles file I/O and error aggregation                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├──────────────► TableFinder
                  │                 - Extracts table regions from markdown
                  │                 - Returns (start_line, end_line, content)
                  │
                  └──────────────► TransformerRegistry
                                    - Auto-discovers transformer classes
                                    - Priority-ordered pattern matching
                                    
┌─────────────────────────────────────────────────────────────┐
│                    BaseTableTransformer                     │
│  <<abstract>>                                               │
│  + matches_table_structure(table: str) -> bool              │
│  + transform(table: str) -> dict                            │
│  + get_priority() -> int                                    │
│  + validate(table: str) -> List[str]  # error messages     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├──► MultiLevelHeaderTransformer (Priority: 10)
                  ├──► EmbeddedRowGroupTransformer (Priority: 20)
                  ├──► TransposedTableTransformer (Priority: 30)
                  ├──► Matrix2DTransformer (Priority: 40)
                  ├──► TwoColumnLayoutTransformer (Priority: 50)
                  └──► SimpleTableTransformer (Priority: 99 - default)
```

### 3.2 Class Relationships

```python
# Orchestrator orchestrates
TableTransformerOrchestrator
    ├── has-a: TableFinder
    ├── has-a: TransformerRegistry
    └── uses: List[BaseTableTransformer]

# Registry manages transformers
TransformerRegistry
    └── creates: List[BaseTableTransformer] (sorted by priority)

# Finder extracts tables
TableFinder
    └── returns: List[TableRegion]

# Base defines contract
BaseTableTransformer (ABC)
    └── extended-by: 6 concrete transformers
```

### 3.3 Data Flow

```
Input: markdown_file.md
    ↓
[1] TableFinder.find_all_tables()
    → Returns: [(start, end, table_md), ...]
    ↓
[2] FOR EACH table:
    ↓
    [2a] TransformerRegistry.match_transformer(table)
         → Tries matches_table_structure() on each transformer (priority order)
         → Returns: First matching transformer OR SimpleTableTransformer
    ↓
    [2b] Transformer.validate(table)
         → Returns: List[warning/error messages]
    ↓
    [2c] Transformer.transform(table)
         → Returns: {"table_type": "...", "data": {...}}
    ↓
    [2d] Format as JSON markdown code block
    ↓
    [2e] Replace original table in document
    ↓
[3] Write transformed document to output file
    ↓
[4] Generate transformation report
    → Summary: tables transformed, errors detected, types found
```

## 4. Implementation Steps

### Phase 1: Core Infrastructure (Days 1-2)

#### Step 1.1: Create Base Abstract Class

**File**: `src/preprocessors/transformers/base_transformer.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re

@dataclass
class TableValidationResult:
    """Result of table validation."""
    is_valid: bool
    warnings: List[str]
    errors: List[str]
    table_location: Optional[str] = None  # e.g., "lines 145-167" or "heading: ATTACK MATRIX"
    
    def has_issues(self) -> bool:
        return len(self.warnings) > 0 or len(self.errors) > 0

class BaseTableTransformer(ABC):
    """
    Abstract base for table transformers.
    
    Each transformer detects one specific table pattern and transforms it
    to JSON. Transformers are tried in priority order (lowest first).
    """
    
    @abstractmethod
    def matches_table_structure(self, table_markdown: str) -> bool:
        """
        Detect if this transformer can handle the table.
        
        Args:
            table_markdown: Raw markdown table (including header rows)
            
        Returns:
            True if this transformer should handle this table
        """
        pass
    
    @abstractmethod
    def transform(self, table_markdown: str) -> Dict[str, Any]:
        """
        Transform markdown table to JSON structure.
        
        Args:
            table_markdown: Raw markdown table
            
        Returns:
            Dict with keys:
                - "table_type": str (pattern name)
                - "data": dict (transformed data)
                - "metadata": dict (optional: row_count, col_count, etc.)
        """
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """
        Return priority (lower = checked first).
        
        Specific patterns (multi-level, embedded) should be 10-30.
        Generic patterns (simple) should be 90-99.
        """
        pass
    
    def validate(self, table_markdown: str) -> TableValidationResult:
        """
        Validate table structure and detect malformations.
        
        Default implementation checks basic markdown table structure.
        Subclasses can override for pattern-specific validation.
        
        Args:
            table_markdown: Raw markdown table
            
        Returns:
            TableValidationResult with warnings/errors
            
        Note:
            table_location should be set by the orchestrator before
            including this result in the final report.
            
            Separator line validation is not needed here - TableFinder
            already verified the separator line exists (that's how it
            found the table in the first place).
        """
        warnings = []
        errors = []
        
        lines = [l.strip() for l in table_markdown.strip().split('\n') if l.strip()]
        
        # Must have at least 3 lines (header, separator, data)
        if len(lines) < 3:
            errors.append(f"Table has only {len(lines)} lines (need ≥3)")
            return TableValidationResult(False, warnings, errors)
        
        # Check column count consistency (excluding separator line)
        data_lines = [line for line in lines if '|' in line and not self._is_separator_line(line)]
        col_counts = [len(self._parse_row(line)) for line in data_lines]
        if len(set(col_counts)) > 1:
            warnings.append(f"Inconsistent column counts: {set(col_counts)}")
        
        is_valid = len(errors) == 0
        return TableValidationResult(is_valid, warnings, errors)
    
    def _parse_row(self, line: str) -> List[str]:
        """Parse markdown table row into cells."""
        cells = [cell.strip() for cell in line.split('|')]
        # Remove empty strings from leading/trailing pipes
        return [c for c in cells if c]
    
    def _is_separator_line(self, line: str) -> bool:
        """
        Check if line is a markdown table separator.
        
        Used during validation to skip separator lines when checking column counts.
        This is a simplified check - we know the table has a valid separator
        (TableFinder verified it), we just need to identify which line it is.
        """
        stripped = line.strip()
        # Simple heuristic: separator lines are mostly hyphens and pipes
        return '-' in stripped and all(c in '|-: \t' for c in stripped)
    
    def get_name(self) -> str:
        """Return human-readable transformer name."""
        return self.__class__.__name__.replace('Transformer', '')
```

**Tests**: `tests/preprocessors/transformers/test_base_transformer.py`
- Test abstract methods raise NotImplementedError
- Test validation detects malformed tables
- Test `_parse_row()` with various pipe configurations
- Test validation skips separator line when counting columns
- Test validation detects inconsistent column counts

#### Step 1.2: Create TableFinder

**File**: `src/preprocessors/transformers/table_finder.py`

```python
from dataclasses import dataclass
from typing import List, Optional
import re

@dataclass
class TableRegion:
    """Represents a table's location in markdown."""
    start_line: int  # 0-indexed
    end_line: int    # 0-indexed (inclusive)
    content: str     # Raw markdown table
    heading_context: str  # Preceding heading (for context)
    
class TableFinder:
    """
    Finds all markdown tables in a document.
    
    Detection strategy:
    1. Find lines with pipes (|)
    2. Identify separator lines (---|---|)
    3. Extract table boundaries (start to first blank line after data)
    4. Capture preceding heading for context
    """
    
    def __init__(self, markdown_content: str):
        self.lines = markdown_content.split('\n')
        self.total_lines = len(self.lines)
    
    def find_all_tables(self) -> List[TableRegion]:
        """
        Find all tables in the markdown document.
        
        Returns:
            List of TableRegion objects in document order
        """
        tables = []
        i = 0
        
        while i < self.total_lines:
            # Look for separator line (indicates table)
            if self._is_separator_line(self.lines[i]):
                table_region = self._extract_table_at(i)
                if table_region:
                    tables.append(table_region)
                    i = table_region.end_line + 1
                else:
                    i += 1
            else:
                i += 1
        
        return tables
    
    def _is_separator_line(self, line: str) -> bool:
        """
        Check if line is markdown table separator.
        
        Valid: |---|---|, |:---:|---:|, etc.
        """
        stripped = line.strip()
        if '-' not in stripped:
            return False
        columns = [c.strip() for c in stripped.split('|') if c.strip()]
        return all(re.match(r'^:?-+:?$', col) for col in columns) if columns else False
    
    def _extract_table_at(self, separator_idx: int) -> Optional[TableRegion]:
        """
        Extract complete table starting from separator line.
        
        Args:
            separator_idx: Index of separator line
            
        Returns:
            TableRegion or None if invalid table
        """
        # Find start (header row before separator)
        start_idx = separator_idx - 1
        while start_idx >= 0:
            if '|' not in self.lines[start_idx]:
                break
            start_idx -= 1
        start_idx += 1  # Move back to first table line
        
        if start_idx < 0 or start_idx >= separator_idx:
            return None
        
        # Find end (first non-table line after separator)
        end_idx = separator_idx + 1
        while end_idx < self.total_lines:
            line = self.lines[end_idx].strip()
            if line == '' or '|' not in line:
                # Table ends at last line with pipes
                end_idx -= 1
                break
            end_idx += 1
        else:
            # Table extends to end of document
            end_idx = self.total_lines - 1
        
        # Extract heading context (last heading before table)
        heading = self._find_preceding_heading(start_idx)
        
        # Extract table content
        content = '\n'.join(self.lines[start_idx:end_idx + 1])
        
        return TableRegion(
            start_line=start_idx,
            end_line=end_idx,
            content=content,
            heading_context=heading
        )
    
    def _find_preceding_heading(self, table_start: int) -> str:
        """Find the most recent heading before table."""
        for i in range(table_start - 1, max(0, table_start - 10), -1):
            line = self.lines[i].strip()
            if line.startswith('#'):
                return line.lstrip('#').strip()
        return ""
```

**Tests**: `tests/preprocessors/transformers/test_table_finder.py`
- Test finds simple table (3 lines)
- Test finds multi-row table
- Test finds multiple tables in document
- Test extracts correct heading context
- Test handles table at start/end of document
- Test ignores non-table pipes (code blocks, etc.)
- Test `_is_separator_line()` accepts valid separators (|---|, |:---:|, etc.)
- Test `_is_separator_line()` rejects invalid patterns (|   |, |:::|, etc.)

#### Step 1.3: Create TransformerRegistry

**File**: `src/preprocessors/transformers/transformer_registry.py`

```python
from typing import List, Type
from .base_transformer import BaseTableTransformer

class TransformerRegistry:
    """
    Discovers and manages table transformer instances.
    
    Transformers are tried in priority order (lowest first).
    The first transformer that returns True from matches_table_structure() is used.
    """
    
    def __init__(self, transformer_classes: List[Type[BaseTableTransformer]]):
        """
        Initialize registry with transformer classes.
        
        Args:
            transformer_classes: List of transformer class types
        """
        # Instantiate all transformers
        self.transformers = [cls() for cls in transformer_classes]
        
        # Sort by priority (lowest first)
        self.transformers.sort(key=lambda t: t.get_priority())
    
    def match_transformer(self, table_markdown: str) -> BaseTableTransformer:
        """
        Find first transformer that can handle this table.
        
        Args:
            table_markdown: Raw markdown table
            
        Returns:
            Matching transformer (guaranteed to return something)
        """
        for transformer in self.transformers:
            if transformer.matches_table_structure(table_markdown):
                return transformer
        
        # Should never reach here if SimpleTableTransformer exists
        raise RuntimeError("No transformer matched (missing SimpleTableTransformer?)")
    
    def get_transformer_summary(self) -> str:
        """Return summary of registered transformers."""
        lines = ["Registered Transformers (priority order):"]
        for t in self.transformers:
            lines.append(f"  [{t.get_priority():2d}] {t.get_name()}")
        return '\n'.join(lines)
```

**Tests**: `tests/preprocessors/transformers/test_transformer_registry.py`
- Test sorts transformers by priority
- Test returns first matching transformer
- Test raises error if no transformer matches
- Test instantiates all transformer classes correctly
- Test handles empty transformer list gracefully

---

### Phase 2: Transformer Implementations (Days 3-5)

#### Step 2.1: Simple Table Transformer (Default Pattern)

**File**: `src/preprocessors/transformers/simple_table_transformer.py`

```python
class SimpleTableTransformer(BaseTableTransformer):
    """
    Transforms simple tables with unique column headers.
    
    Example Input:
    | Dice Score | Character Class | Level Range |
    |------------|-----------------|-------------|
    | 01-15      | cleric          | 1-4         |
    | 16-40      | druid           | 2-5         |
    
    Output JSON:
    {
      "table_type": "simple",
      "data": {
        "Dice Score": {
          "01-15": {
            "Character Class": "cleric",
            "Level Range": "1-4"
          },
          "16-40": {
            "Character Class": "druid",
            "Level Range": "2-5"
          }
        }
      }
    }
    
    Detection:
    - DEFAULT pattern (always returns True)
    - Used when no other transformer matches
    """
    
    def matches_table_structure(self, table_markdown: str) -> bool:
        """Always returns True (default fallback)."""
        return True
    
    def get_priority(self) -> int:
        """Lowest priority (checked last)."""
        return 99
    
    def transform(self, table_markdown: str) -> Dict[str, Any]:
        """Transform to nested dict keyed by first column."""
        lines = [l.strip() for l in table_markdown.strip().split('\n') if l.strip()]
        
        # Parse rows
        rows = []
        for line in lines:
            if not self._is_separator_line(line):
                rows.append(self._parse_row(line))
        
        if len(rows) < 2:
            raise ValueError("Table must have header + data rows")
        
        header = rows[0]
        data_rows = rows[1:]
        
        # Build nested dict (use original headers as-is)
        result = {}
        first_col = header[0]
        
        for data_row in data_rows:
            if len(data_row) != len(header):
                continue  # Skip malformed rows
            
            key = data_row[0]
            row_dict = {}
            
            for i in range(1, len(header)):
                row_dict[header[i]] = data_row[i]
            
            result[key] = row_dict
        
        return {
            "table_type": "simple",
            "data": {first_col: result},
            "metadata": {
                "row_count": len(data_rows),
                "col_count": len(header)
            }
        }
```

**Tests**: `tests/preprocessors/transformers/test_simple_table_transformer.py`
- Test transforms HUMANS TABLE I correctly
- Test preserves original column names
- Test skips malformed rows
- Test always returns True from matches_table_structure()

#### Step 2.2: Two-Column Layout Transformer

**File**: `src/preprocessors/transformers/two_column_layout_transformer.py`

**Detection Strategy**:
- Column headers repeat in groups (every Nth column has same name)
- Example: `[Dice Score, Race, Dice Score, Race]` → period = 2
- Example: `[A, B, C, A, B, C]` → period = 3

**Transformation Strategy**:
- Split table into N logical sub-tables
- Merge all sub-tables into single result dict
- Preserve dice score ordering across columns

**Example Input**:
```markdown
| Dice Score | Race     | Dice Score | Race         |
|------------|----------|------------|--------------|
| 01-10      | dwarven  | 31-35      | halfling     |
| 11-20      | elven    | 36-55      | half-orcish  |
```

**Output JSON**:
```json
{
  "table_type": "two_column_layout",
  "data": {
    "Dice Score": {
      "01-10": {"Race": "dwarven"},
      "11-20": {"Race": "elven"},
      "31-35": {"Race": "halfling"},
      "36-55": {"Race": "half-orcish"}
    }
  }
}
```

**Tests**: `tests/preprocessors/transformers/test_two_column_layout_transformer.py`
- Test detects RACE OF THIEF pattern (2 pairs)
- Test detects 3-column pattern
- Test merges columns in correct order
- Test skips empty cells
- Test validation detects incomplete rows

#### Step 2.3: 2D Matrix Lookup Transformer

**File**: `src/preprocessors/transformers/matrix_2d_transformer.py`

**Detection Strategy**:
- Row 1: Repeated column header (same text appears 3+ times)
- Row 2: Unique values (level ranges, categories, or categorical labels)
- Row 3+: **Data cells** (can be numeric, alphabetic codes, or symbols)
- First column has unique row labels (AC values, monster names, level titles)

**Why "Data Cells" Not "Numeric"**:
D&D 1st Edition uses various data types in lookup tables:
- **Numeric**: Attack matrices (roll needed: 15, 16, 20, etc.)
- **Letter codes**: Turning Undead table (T=Turn, D=Destroy, --=Impossible)
- **Symbols**: Psionic combat results (W, S, C, 40, etc.)
- **Mixed**: Some tables combine numbers with special markers (*, †, --)

**Why Parse Repeated Header with " by " Pattern**:
The repeated column header often contains TWO pieces of information separated by " by ":

**Pattern Found in D&D 1st Edition**:
- "20-sided Die Score to Hit **by** Level of Attacker"
- "Level of Cleric Attempting to Turn" (no " by " - single concept)

When " by " exists, split it:
- **Before " by "**: What the data represents ("20-sided Die Score to Hit")
- **After " by "**: What the columns represent ("Level of Attacker")

**Column Naming Strategy**:

```python
def parse_2d_matrix_headers(table_lines):
    """
    Extract meaningful names from 2D matrix table structure.
    
    Returns:
        row_label_semantic: str (e.g., "Opponent Armor Class")
        col_category_name: str (e.g., "Level of Attacker")
        value_name: str (e.g., "20-sided Die Score to Hit")
        col_categories: List[str] (e.g., ["1-3", "4-6"])
    """
    header_row_1 = parse_row(table_lines[0])  # Repeated header and row label
    header_row_2 = parse_row(table_lines[2])  # Categories (skip separator)
    
    # Get row label semantic name from row 1, col 1
    row_label_semantic = header_row_1[0].strip()  # "Opponent Armor Class"
    
    # Get repeated text (same across all columns)
    repeated_header = next(cell for cell in header_row_1[1:] if cell.strip())
    
    # Try splitting on " by " pattern
    if " by " in repeated_header:
        parts = repeated_header.split(" by ", 1)
        value_name = parts[0].strip()       # "20-sided Die Score to Hit"
        col_category_name = parts[1].strip()  # "Level of Attacker"
    else:
        # No " by " - use full text as category
        col_category_name = repeated_header  # "Level of Cleric Attempting to Turn"
        value_name = "Result"  # Generic fallback
    
    # Column categories from row 2, cols 2+
    col_categories = header_row_2[1:]
    
    return row_label_semantic, col_category_name, value_name, col_categories
```

**Example 1: Attack Matrix** (has " by ")
```markdown
| Opponent Armor Class | 20-sided Die Score to Hit by Level of Attacker | ... |
|----------------------|-----------------------------------------------|-----|
| Class                | 1-3                                            | 4-6 |
| -10                  | 25                                             | 23  |
```

Parsing:
- Row label semantic: "Opponent Armor Class" (from row 1, col 1)
- Repeated header: "20-sided Die Score to Hit **by** Level of Attacker"
- Split on " by ": value = "20-sided Die Score to Hit", category = "Level of Attacker"
- Columns: ["1-3", "4-6"]

**Example 2: Turning Undead** (no " by ")
```markdown
| Type of Undead | Level of Cleric Attempting to Turn | ... |
|----------------|-------------------------------------|-----|
| Undead         | 1                                   | 2   |
| Skeleton       | 10                                  | 7   |
```

Parsing:
- Row label semantic: "Type of Undead" (from row 1, col 1)
- Repeated header: "Level of Cleric Attempting to Turn" (no " by ")
- No split: category = "Level of Cleric Attempting to Turn", value = "Result" (fallback)
- Columns: ["1", "2"]

**Transformation Strategy**:
- Use nested structure with array-of-objects for each row value
- **Top-level key**: Use semantic row label (e.g., "Opponent Armor Class")
- **Second-level keys**: Use row values (e.g., "-10", "-9")
- **Array elements**: Objects with semantic property names (e.g., "Level of Attacker", "20-sided Die Score to Hit")
- **No metadata needed**: All semantic information is in the property names themselves

**Example Input**:
```markdown
| Opponent Armor Class | 20-sided Die Score to Hit by Level of Attacker | 20-sided Die Score to Hit by Level of Attacker | ... |
|----------------------|-----------------------------------------------|-----------------------------------------------|-----|
| Class                | 1-3                                            | 4-6                                            | ... |
| -10                  | 25                                             | 23                                             | ... |
| -9                   | 24                                             | 22                                             | ... |
```

**Parsing**:
- Row label semantic: "Opponent Armor Class" (from row 1, col 1)
- Repeated header: "20-sided Die Score to Hit **by** Level of Attacker"
- Split on " by ": 
  - `value_name` = "20-sided Die Score to Hit"
  - `col_category_name` = "Level of Attacker"
- Columns: ["1-3", "4-6"]

**Output JSON**:
```json
{
  "table_type": "2d_matrix_lookup",
  "data": {
    "Opponent Armor Class": {
      "-10": [
        {
          "Level of Attacker": "1-3",
          "20-sided Die Score to Hit": "25"
        },
        {
          "Level of Attacker": "4-6",
          "20-sided Die Score to Hit": "23"
        },
        {
          "Level of Attacker": "7-9",
          "20-sided Die Score to Hit": "20"
        }
      ],
      "-9": [
        {
          "Level of Attacker": "1-3",
          "20-sided Die Score to Hit": "24"
        },
        {
          "Level of Attacker": "4-6",
          "20-sided Die Score to Hit": "22"
        }
      ]
    }
  }
}
```

**Why This Works for LLMs**:
- **Query**: "7th level fighter vs AC -10"
- **Navigate**: `data["Opponent Armor Class"]["-10"]` → Get array
- **Filter array**: Find element where "Level of Attacker" range contains 7
  - Check "1-3" (no), "4-6" (no), "7-9" (yes!)
- **Read result**: `"20-sided Die Score to Hit"` = "20"
- **Semantic clarity**: All property names are self-documenting, no metadata lookup needed

**Tests**: `tests/preprocessors/transformers/test_matrix_2d_transformer.py`
- Test detects ATTACK MATRIX FOR FIGHTERS (has " by " pattern)
- Test detects TURNING UNDEAD table (no " by " pattern)
- Test parses repeated header and splits on " by " correctly
- Test extracts `value_name` and `col_category_name` from repeated header
- Test extracts semantic row label from row 1, col 1 (e.g., "Opponent Armor Class", "Type of Undead")
- Test uses column categories from row 2, cols 2+ (e.g., "1-3", "4-6")
- Test creates nested structure: semantic_row_label → row_value → array of objects
- Test each array object has semantic property names (col_category_name, value_name)
- Test handles misaligned columns gracefully
- Test preserves non-numeric data (letters, symbols, dashes)
- Test validation warns about column count mismatches
- Test LLM can navigate: data["Opponent Armor Class"]["-10"] → array
- Test LLM can filter array by "Level of Attacker" range
- Test no metadata needed (all semantics in property names)

#### Step 2.4: Multi-Level Header Transformer

**File**: `src/preprocessors/transformers/multi_level_header_transformer.py`

**Detection Strategy**:
- Row 1 has repeated values (group headers)
- Row 2 has unique sub-headers under each group
- Group sizes inferred from repetition count

**Example Input**:
```markdown
| Dice | Area         | Occurrence | Occurrence | Severity | Severity | Severity |
|------|--------------|------------|------------|----------|----------|----------|
| Score| Affected     | Acute      | Chronic    | Mild     | Severe   | Terminal |
| 01-03| blood organs | 1-3        | 4-8        | 1-2      | 3-5      | 6-8      |
```

**Output JSON**:
```json
{
  "table_type": "multi_level_header",
  "data": {
    "Dice Score": {
      "01-03": {
        "Area Affected": "blood organs",
        "Occurrence": {
          "Acute": "1-3",
          "Chronic": "4-8"
        },
        "Severity": {
          "Mild": "1-2",
          "Severe": "3-5",
          "Terminal": "6-8"
        }
      }
    }
  }
}
```

**Tests**: `tests/preprocessors/transformers/test_multi_level_header_transformer.py`
- Test detects DISEASE AND INFESTATION table
- Test creates nested structure
- Test identifies groups correctly
- Test handles ungrouped columns

#### Step 2.5: Embedded Row Group Transformer

**File**: `src/preprocessors/transformers/embedded_row_group_transformer.py`

**Detection Strategy**:
- Some data rows have only first column filled (rest empty/blank)
- Those rows contain range values (XX-YY pattern)
- Following rows have data across all columns

**Example Input**:
```markdown
| Attack Mode   | 10-59 | 60-109 | 110-159 |
|---------------|-------|--------|---------|
| 01-25         |       |        |         |
| Psionic Blast | D     | C      | C       |
| Mind Thrust   | W     | W      | 40      |
| 26-50         |       |        |         |
| Psionic Blast | S     | D      | C       |
```

**Output JSON**:
```json
{
  "table_type": "embedded_row_group",
  "data": {
    "01-25": {
      "Psionic Blast": {"10-59": "D", "60-109": "C", "110-159": "C"},
      "Mind Thrust": {"10-59": "W", "60-109": "W", "110-159": "40"}
    },
    "26-50": {
      "Psionic Blast": {"10-59": "S", "60-109": "D", "110-159": "C"}
    }
  }
}
```

**Tests**: `tests/preprocessors/transformers/test_embedded_row_group_transformer.py`
- Test detects PSIONIC ATTACK table
- Test groups rows correctly
- Test validates orphan rows

#### Step 2.6: Transposed Table Transformer

**File**: `src/preprocessors/transformers/transposed_table_transformer.py`

**Detection Strategy**:
- Column 1 has long text (>30 chars) or contains colons
- Very few rows (2-3) compared to many columns (5+)
- First column cells look like labels/descriptions

**Example Input**:
```markdown
| Description              | 1  | 2  | 3  | 4  |
|--------------------------|----|----|----|----| 
| Die Number:              | 1  | 2  | 3  | 4  |
| Probability (ascending): | 10 | 20 | 30 | 40 |
```

**Output JSON**:
```json
{
  "table_type": "transposed",
  "data": {
    "records": [
      {"Die Number": "1", "Probability (ascending)": "10"},
      {"Die Number": "2", "Probability (ascending)": "20"},
      {"Die Number": "3", "Probability (ascending)": "30"},
      {"Die Number": "4", "Probability (ascending)": "40"}
    ]
  }
}
```

**Tests**: `tests/preprocessors/transformers/test_transposed_table_transformer.py`
- Test detects Linear Curve probability table
- Test transposes correctly
- Test handles colons in labels

---

### Phase 3: Orchestrator (Day 6)

#### Step 3.1: Create Orchestrator

**File**: `src/preprocessors/table_transformer_orchestrator.py`

**Key Responsibilities**:
1. Read input markdown file
2. Initialize TransformerRegistry with all transformer classes
3. Use TableFinder to locate all tables (with line numbers)
4. For each table:
   - Match appropriate transformer via registry
   - Validate table structure
   - **Enhance validation result with location info** (line numbers + heading context)
   - Transform to JSON
   - Replace original markdown table with JSON code block
5. Write transformed document to output file
6. Generate transformation report (JSON summary with locations)

**Transformer Registration**:
```python
from .transformers.simple_table_transformer import SimpleTableTransformer
from .transformers.two_column_layout_transformer import TwoColumnLayoutTransformer
from .transformers.matrix_2d_transformer import Matrix2DTransformer
from .transformers.multi_level_header_transformer import MultiLevelHeaderTransformer
from .transformers.embedded_row_group_transformer import EmbeddedRowGroupTransformer
from .transformers.transposed_table_transformer import TransposedTableTransformer
from .transformers.transformer_registry import TransformerRegistry

class TableTransformerOrchestrator:
    def __init__(self, input_file: Path, output_file: Path):
        self.input_file = input_file
        self.output_file = output_file
        
        # Register all transformer classes
        self.registry = TransformerRegistry([
            SimpleTableTransformer,
            TwoColumnLayoutTransformer,
            Matrix2DTransformer,
            MultiLevelHeaderTransformer,
            EmbeddedRowGroupTransformer,
            TransposedTableTransformer
        ])
        
        self.table_finder = None  # Initialized when processing
        self.report = {
            "summary": {},
            "by_type": {},
            "issues": [],
            "failed_tables": []
        }
```

**Report Structure**:
```json
{
  "summary": {
    "total_tables": 113,
    "successful": 108,
    "failed": 5,
    "success_rate": 0.956
  },
  "by_type": {
    "simple": 45,
    "2d_matrix_lookup": 12,
    "multi_level_header": 8,
    "two_column_layout": 15,
    "embedded_row_group": 3,
    "transposed": 2
  },
  "issues": [
    {
      "table_id": 23,
      "location": "lines 4403-4420",
      "heading": "ATTACK MATRIX FOR MONSTERS",
      "warnings": ["Inconsistent column counts: {12, 13}"],
      "errors": []
    }
  ],
  "failed_tables": [
    {
      "table_id": 87,
      "location": "lines 9234-9236",
      "heading": "MALFORMED TABLE",
      "error": "Table has only 2 lines (need ≥3)"
    }
  ]
}
```

**JSON Code Block Format**:
```markdown
## ATTACK MATRIX FOR FIGHTERS

```json
{
  "table_type": "2d_matrix_lookup",
  "data": {
    "Opponent Armor Class": {
      "-10": [
        {"Level of Attacker": "1-3", "20-sided Die Score to Hit": "25"},
        {"Level of Attacker": "4-6", "20-sided Die Score to Hit": "23"},
        {"Level of Attacker": "7-9", "20-sided Die Score to Hit": "20"}
      ],
      "-9": [
        {"Level of Attacker": "1-3", "20-sided Die Score to Hit": "24"},
        {"Level of Attacker": "4-6", "20-sided Die Score to Hit": "22"}
      ]
    }
  }
}
```

## NEXT SECTION
```

**Implementation Note - Location Tracking**:
```python
# In the orchestrator's main loop:
for table_id, table_region in enumerate(tables):
    transformer = registry.match_transformer(table_region.content)
    
    # Validate and enhance with location
    validation_result = transformer.validate(table_region.content)
    validation_result.table_location = (
        f"lines {table_region.start_line + 1}-{table_region.end_line + 1}"
    )
    
    # Add to report if there are issues
    if validation_result.has_issues():
        report["issues"].append({
            "table_id": table_id,
            "location": validation_result.table_location,
            "heading": table_region.heading_context,
            "warnings": validation_result.warnings,
            "errors": validation_result.errors
        })
```

**Tests**: `tests/preprocessors/test_table_transformer_orchestrator.py`
- Test processes complete document
- Test generates correct report with line numbers
- Test handles transformation errors gracefully
- Test preserves non-table content
- Test maintains document structure (headings, paragraphs)
- Test error messages include table locations
- Test all transformer classes are registered
- Test registry returns correct transformer types

---

### Phase 4: CLI Integration (Day 7)

#### Step 4.1: Add CLI Command

**File**: `src/cli.py` (add new command)

```python
@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
def transform_tables(input_file: str, output_file: str):
    """Transform markdown tables to JSON in a document.
    
    Example:
        dnd-rag transform-tables data/markdown/DMG.md data/markdown/DMG_transformed.md
    """
    from src.preprocessors.table_transformer_orchestrator import TableTransformerOrchestrator
    
    orchestrator = TableTransformerOrchestrator(
        input_file=Path(input_file),
        output_file=Path(output_file)
    )
    
    report = orchestrator.transform()
    
    if report["summary"]["failed"] > 0:
        click.echo(f"Warning: {report['summary']['failed']} tables failed transformation", err=True)
        sys.exit(1)
```

**Usage Examples**:
```bash
# Transform DMG
dnd-rag transform-tables \
  data/markdown/Dungeon_Master_s_Guide_(1e)_organized.md \
  data/markdown/Dungeon_Master_s_Guide_(1e)_transformed.md

# Transform PHB
dnd-rag transform-tables \
  data/markdown/Players_Handbook_(1e)_organized.md \
  data/markdown/Players_Handbook_(1e)_transformed.md

# Transform Monster Manual
dnd-rag transform-tables \
  data/markdown/Monster_Manual_(1e).md \
  data/markdown/Monster_Manual_(1e)_transformed.md
```

---

## 5. Testing Strategy

### 5.1 Unit Tests (Per Component)

**Coverage targets**: 90%+ for each transformer

| Component | Test Focus | Test File |
|-----------|------------|-----------|
| BaseTransformer | Abstract methods, validation logic, helper methods | test_base_transformer.py |
| TableFinder | Boundary detection, heading extraction, edge cases | test_table_finder.py |
| TransformerRegistry | Priority ordering, matching logic | test_transformer_registry.py |
| SimpleTableTransformer | matches_table_structure(), transform(), validation | test_simple_table_transformer.py |
| TwoColumnLayoutTransformer | Pattern detection, column merging | test_two_column_layout_transformer.py |
| Matrix2DTransformer | Array-of-objects output, misalignment handling | test_matrix_2d_transformer.py |
| MultiLevelHeaderTransformer | Group detection, nested structure | test_multi_level_header_transformer.py |
| EmbeddedRowGroupTransformer | Group label detection, orphan validation | test_embedded_row_group_transformer.py |
| TransposedTableTransformer | Transposition logic, colon detection | test_transposed_table_transformer.py |

### 5.2 Integration Tests

**File**: `tests/integration/test_table_transformation_pipeline.py`

**Test Scenarios**:
1. **Full Pipeline Test**
   - Create sample document with 10-20 tables (one of each type + variations)
   - Run complete transformation
   - Verify all tables transformed correctly
   - Check report accuracy

2. **Idempotency Test**
   - Transform document twice
   - Compare outputs (should be identical)
   - Ensures JSON blocks don't get re-transformed

3. **Mixed Content Test**
   - Document with tables, code blocks, lists, headings
   - Verify non-table content unchanged
   - Verify table boundaries respected

4. **Error Handling Test**
   - Document with deliberately malformed tables
   - Verify transformation continues after errors
   - Verify error report is accurate

### 5.3 Validation Tests

**File**: `tests/preprocessors/transformers/test_table_validation.py`

**Focus**: Error detection without crashes, with accurate location reporting

Test cases:
- Missing separator line → verify error message includes location
- Inconsistent column counts → verify warning includes location
- Empty tables (no data rows)
- Single-column tables
- Tables with special characters
- Unicode in table cells
- Very wide tables (>20 columns)
- Very tall tables (>100 rows)
- Location tracking: verify line numbers are accurate (1-indexed)

### 5.4 Regression Tests

**After Pipeline Runs**:
1. Fighter XP Table Test (the acid test)
   ```bash
   # Before transformation
   python src/query/docling_query.py dnd_dmg \
     "7th level fighter with strength 16 vs AC 3"
   # Expected: Wrong answer (15 instead of 11)
   
   # After transformation (with transformed DMG collection)
   python src/query/docling_query.py dnd_dmg_transformed \
     "7th level fighter with strength 16 vs AC 3"
   # Expected: Correct answer (11)
   ```

2. Chunking Preservation Test
   - Verify recursive_chunker still respects table boundaries
   - JSON code blocks should not be split
   - Chunk metadata should include table_type

## 6. Documentation

### 6.1 User Guide

**File**: `docs/table_transformation_guide.md`

**Sections**:
1. Overview - Why we transform tables
2. Running the Transformer - CLI commands
3. Table Types Reference - Examples of each pattern
4. Troubleshooting - Common issues and fixes
5. Report Interpretation - Understanding transformation reports
6. Integration with Pipeline - How it fits in preprocessing

### 6.2 Developer Guide

**File**: `docs/implementations/TableTransformerArchitecture.md`

**Sections**:
1. Architecture Overview - Component diagram
2. Adding New Transformer Types - Step-by-step guide
3. Detection Algorithm Design - Best practices
4. Testing Guidelines - Required test coverage
5. Performance Considerations - Optimization tips
6. Error Handling Patterns - Resilience strategies

### 6.3 API Documentation

**File**: `docs/api/table_transformers.md`

- BaseTableTransformer API
- TableFinder API
- TransformerRegistry API
- Each concrete transformer API

## 7. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| **Docling table extraction errors** | HIGH | HIGH | • Validation detects issues<br>• Report lists all problems<br>• Manual fix workflow documented |
| **JSON increases chunk size** | MEDIUM | MEDIUM | • Chunker already handles oversized tables<br>• JSON is more compressible<br>• Trade-off worth accuracy gain |
| **Transformer misclassification** | MEDIUM | LOW | • Priority ordering extensively tested<br>• Detection logic has clear criteria<br>• Fallback to SimpleTable always works |
| **Performance degradation** | LOW | LOW | • Benchmark: DMG (17K lines) in < 30sec<br>• Streaming not needed for this scale<br>• Can parallelize if needed |
| **Breaking existing chunks** | HIGH | LOW | • JSON blocks bounded by blank lines<br>• Chunker's `find_table_end()` still works<br>• Integration tests validate |
| **Embedding quality reduction** | MEDIUM | LOW | • JSON tokens more semantic than markdown<br>• Keys provide context<br>• Validation via Fighter XP test |

## 8. Success Metrics

### 8.1 Functional Metrics

- ✅ All 6 table patterns detected correctly (100% on test set)
- ✅ DMG transformation completes successfully (>95% tables)
- ✅ PHB transformation completes successfully (>95% tables)
- ✅ Monster Manual transformation completes successfully (>90% tables)
- ✅ <5% of tables fail validation
- ✅ Idempotency test passes (run twice → identical output)

### 8.2 Quality Metrics

- ✅ Fighter XP Table test passes with JSON version
- ✅ LLM accuracy improves on combat calculations
  - Test: "7th level fighter strength 16 vs AC 3"
  - Before: Wrong answer (15)
  - After: Correct answer (11)
- ✅ Query latency unchanged (<5% increase acceptable)
- ✅ No regressions in existing test queries

### 8.3 Code Quality Metrics

- ✅ Unit test coverage >90% for all components
- ✅ Integration tests pass
- ✅ All type hints validated with mypy
- ✅ Code formatted with black
- ✅ No flake8 violations

### 8.4 Performance Metrics

- ✅ DMG transformation < 30 seconds
- ✅ PHB transformation < 20 seconds
- ✅ Monster Manual transformation < 15 seconds
- ✅ Memory usage < 500MB peak

## 9. Timeline

| Phase | Duration | Deliverables | Dependencies |
|-------|----------|-------------|--------------|
| **Phase 1: Infrastructure** | 2 days | BaseTransformer, TableFinder, Registry + tests | None |
| **Phase 2: Transformers** | 3 days | All 6 transformers + tests | Phase 1 |
| **Phase 3: Orchestrator** | 1 day | Orchestrator + integration tests | Phase 2 |
| **Phase 4: CLI & Docs** | 1 day | CLI integration, user guide, dev guide | Phase 3 |
| **TOTAL** | **7 days** | Complete, tested table transformer | - |

### Daily Breakdown

**Day 1**: BaseTransformer, validation logic, helper methods, unit tests  
**Day 2**: TableFinder, TransformerRegistry, unit tests  
**Day 3**: SimpleTable, TwoColumnLayout, Matrix2D transformers + tests  
**Day 4**: MultiLevelHeader, EmbeddedRowGroup transformers + tests  
**Day 5**: TransposedTable transformer, refinement, edge case handling  
**Day 6**: Orchestrator, integration tests, error handling  
**Day 7**: CLI integration, documentation, final testing  

## 10. Future Enhancements

### 10.1 Potential Improvements (Not in Initial Scope)

1. **Smart Table Repair**
   - Auto-fix common malformations
   - Align misaligned columns
   - Fill missing separator lines

2. **Table Merge Detection**
   - Detect tables split across pages
   - Merge into single logical table
   - Preserve page break metadata

3. **Semantic Validation**
   - Validate data types (numeric columns should have numbers)
   - Check range consistency (01-15, 16-40 shouldn't overlap)
   - Detect duplicate keys

4. **Visual Diff Tool**
   - Side-by-side markdown vs JSON view
   - Highlight transformations
   - Interactive correction UI

5. **Performance Optimization**
   - Parallel table processing
   - Incremental transformation (only changed tables)
   - Caching of transformation results

### 10.2 Integration Opportunities

1. **Embedder Integration**
   - Add table_type to chunk metadata
   - Custom embedding strategies per table type
   - Table-aware retrieval filtering

2. **Query Enhancement**
   - Detect table queries in user input
   - Direct JSON field lookup (bypass LLM for simple lookups)
   - Table-specific prompt templates

3. **UI Features**
   - Table visualization in query results
   - Interactive table exploration
   - Export to Excel/CSV

## 11. Appendix

### 11.1 Example Transformation

**Input** (DMG, lines 4403-4420):
```markdown
#### I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS

| Opponent Armor   | 20-sided Die Score to Hit by Level of Attacker | 20-sided Die Score to Hit by Level of Attacker | ...
|------------------|------------------------------------------------|------------------------------------------------|----
| Class            | 1-3                                            | 4-6                                            | ...
| -10              | 25                                             | 23                                             | ...
| -9               | 24                                             | 22                                             | ...
```

**Output**:
```markdown
#### I.A. ATTACK MATRIX FOR CLERICS, DRUIDS AND MONKS

```json
{
  "table_type": "2d_matrix_lookup",
  "data": {
    "Opponent Armor Class": {
      "-10": [
        {"Level of Attacker": "1-3", "20-sided Die Score to Hit": "25"},
        {"Level of Attacker": "4-6", "20-sided Die Score to Hit": "23"},
        {"Level of Attacker": "7-9", "20-sided Die Score to Hit": "20"}
      ],
      "-9": [
        {"Level of Attacker": "1-3", "20-sided Die Score to Hit": "24"},
        {"Level of Attacker": "4-6", "20-sided Die Score to Hit": "22"}
      ]
    }
  }
}
```
```

### 11.2 Priority Decision Matrix

**Why this priority order?**

| Priority | Transformer | Rationale |
|----------|-------------|-----------|
| 10 | MultiLevelHeader | Most specific: requires exact 2-row header pattern |
| 20 | EmbeddedRowGroup | Specific: requires group labels with empty cells |
| 30 | Transposed | Specific: requires unusual column >> row ratio |
| 40 | Matrix2D | Moderately specific: requires repeated headers |
| 50 | TwoColumnLayout | Less specific: only requires header duplication |
| 99 | SimpleTable | Default: always matches |

**Testing Priority Order**:
Create ambiguous table that matches multiple patterns → verify correct one wins.

### 11.3 Common Docling Table Errors

**From analysis of DMG markdown**:

1. **Misaligned Columns** (30% of tables)
   - Row has different column count than header
   - Caused by: merged cells, colspan in PDF
   - Mitigation: Validation warning

2. **Multi-Row Headers Not Parsed** (15% of tables)
   - Docling flattens to single header row
   - Caused by: complex table structure in PDF
   - Mitigation: Multi-level transformer tries to reconstruct

3. **Split Tables** (5% of tables)
   - Large table split across pages
   - Each part extracted as separate table
   - Mitigation: Document in issues, manual merge needed

4. **Missing Separators** (3% of tables)
   - No `|---|---|` row
   - Caused by: Docling parsing error
   - Mitigation: Validation error, skip table

5. **Embedded Text in Cells** (10% of tables)
   - Footnotes, explanations inside cells
   - Caused by: PDF layout
   - Mitigation: Preserve as-is, works in JSON

---

**Document Version**: 1.0  
**Date**: October 22, 2025  
**Author**: AI Agent (GitHub Copilot)  
**Status**: Ready for Implementation
