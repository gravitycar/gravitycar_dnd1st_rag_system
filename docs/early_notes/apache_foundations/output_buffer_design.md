# Output Buffer Design Decision Log

**Decision Date**: November 3, 2025  
**Context**: Refactoring print() statements for Flask REST API compatibility  
**Status**: ✅ Approved - Ready for Implementation

---

## Problem Statement

Current codebase has 200+ `print()` statements that write directly to stdout. This doesn't work in a web/API context where:
1. Output needs to be captured and returned as JSON
2. Different output types (answer, diagnostics, errors) need separate handling
3. CLI and Flask need to share the same underlying logic

---

## Solution: RAGOutput Class with Dependency Injection

### Core Design

```python
# src/utils/rag_output.py
class RAGOutput:
    """Output buffer for RAG queries."""
    
    def __init__(self):
        self.answer = None
        self.diagnostics = []
        self.errors = []
    
    def set_answer(self, text):
        """Store the LLM's response."""
        self.answer = text
    
    def info(self, msg):
        """Add diagnostic message."""
        self.diagnostics.append(msg)
    
    def error(self, msg):
        """Add error message."""
        self.errors.append(msg)
    
    def to_dict(self):
        """Convert to JSON-serializable dict."""
        return {
            'answer': self.answer,
            'diagnostics': self.diagnostics,
            'errors': self.errors
        }
```

### Integration Pattern: Dependency Injection

**Strategy**: Pass `RAGOutput` instance into `DnDRAG` class constructor.

```python
# DnDRAG.__init__() signature
def __init__(
    self,
    collection_name: str = None,
    model: str = "gpt-4o-mini",
    chroma_host: str = None,
    chroma_port: int = None,
    output: RAGOutput = None  # NEW: Optional output buffer
):
    self.output = output if output else RAGOutput()
    
    # Replace all print() with self.output.*()
    self.output.info("Initializing D&D RAG system...")
    self.output.info(f"  Collection: {collection_name}")
    # ... etc
```

**Why Dependency Injection?**
- ✅ **Explicit dependencies**: Clear what each class needs
- ✅ **Testable**: Can inject mock output buffer for unit tests
- ✅ **Flexible**: Works in CLI, Flask, and future contexts
- ✅ **No global state**: Each request/invocation gets its own instance

---

## Output Taxonomy: Three Buckets

| Bucket | Purpose | Example | CLI Behavior | API Behavior |
|--------|---------|---------|--------------|--------------|
| **answer** | LLM response | "A beholder has 45-75 HP..." | Always print | Always return |
| **diagnostics** | Execution context | "Retrieved 3 chunks in 0.15s" | Always print (default) | Always return (let client decide) |
| **errors** | Failures | "OpenAI API timeout" | Always print | Always return + HTTP 500 |

### Decision: Diagnostics Always Returned

**Requirement**: Diagnostics should be:
1. **Printed by default in CLI** (user wants to see what's happening)
2. **Always returned in API response** (client decides whether to display)

```json
// API Response (happy path)
{
  "answer": "A beholder has 45-75 hit points...",
  "diagnostics": [
    "Initializing D&D RAG system...",
    "Retrieved 3 chunks in 0.15s",
    "Gap detection: cliff at position 5"
  ],
  "errors": []
}

// API Response (error path)
{
  "answer": null,
  "diagnostics": [
    "Initializing D&D RAG system...",
    "Connecting to ChromaDB..."
  ],
  "errors": [
    "Collection 'invalid_name' not found",
    "Available collections: dnd_unified, dnd_monster_manual"
  ]
}
```

---

## Refactoring Scope: What Changes Where

### Phase 1: Core Query Path (Session 1)
**Files to refactor**:
1. `src/utils/rag_output.py` - **CREATE NEW** (RAGOutput class)
2. `src/query/docling_query.py` - **UPDATE** (DnDRAG class)
   - `__init__()`: Add `output` parameter, replace ~10 print statements
   - `query()`: Replace ~15 print statements, return `output.to_dict()`
   - `retrieve()`: Replace ~40 print statements (in debug mode)
   - `_retrieve_base()`: Replace ~10 print statements
   - `_retrieve_with_filtering()`: Replace ~20 print statements

**Total print statements in DnDRAG**: ~70

### Files That Call DnDRAG
**Need updates to handle new return format**:
1. `main.py` - `cmd_query()` function
2. `src/cli.py` - `cmd_query()` function

**Update pattern**:
```python
# OLD
answer = rag.query(question)
print(answer)

# NEW
output_buffer = RAGOutput()
result = rag.query(question, output=output_buffer)

print(f"\nAnswer: {result['answer']}")
for msg in result['diagnostics']:
    print(msg)
if result['errors']:
    for err in result['errors']:
        print(f"ERROR: {err}")
```

### Phase 2: Other Modules (Session 2+)
**Defer to later** (lower priority, not critical for Flask):
- `src/converters/pdf_converter.py` (~45 prints)
- `src/transformers/table_transformer.py` (~25 prints)
- `src/embedders/*.py` (~20 prints across multiple files)

---

## sys.exit() Handling

**Decision**: ✅ No refactoring needed

**Analysis results** (from `sys_exit_analysis.md`):
- **Total sys.exit() calls**: 25 across 6 files
- **Location breakdown**:
  - 7 in CLI-only code (main.py, cli.py command functions)
  - 17 in CLI main() functions (docling_query.py, converters, chunkers, transformers)
  - 1 in KeyboardInterrupt handler (transformers/cli.py)
  - **0 in library code** (DnDRAG class, embedders, utils)

**Critical finding**: All `sys.exit()` calls are in CLI entry points that Flask will never execute.

**Flask code path**:
```python
# Flask imports only the class, not the main() function
from src.query.docling_query import DnDRAG  # ✅ Safe - no sys.exit() in class

# DnDRAG.__init__() raises exceptions (correct for library code)
# See docling_query.py line 58: `raise` statement used
```

**Verification**:
- `DnDRAG.__init__()`: Uses `raise` for errors (line 58)
- `DnDRAG.query()`: Returns strings/dicts, no sys.exit()
- All sys.exit() calls: In `if __name__ == "__main__"` blocks or CLI command functions

**Conclusion**: Proper separation of concerns already exists. No refactoring required.

---

## Flask Integration Preview

### How RAGOutput Works in Flask

```python
# src/api.py
from flask import Flask, request, jsonify
from src.query.docling_query import DnDRAG
from src.utils.rag_output import RAGOutput

app = Flask(__name__)

# Initialize RAG once (reused across requests)
rag = None

@app.before_first_request
def init_rag():
    global rag
    rag = DnDRAG()  # Uses default output (won't print to stdout)

@app.route('/api/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        question = data.get('question')
        debug = data.get('debug', False)
        
        # Create new output buffer for this request
        output = RAGOutput()
        
        # Query returns dict directly
        result = rag.query(question, k=15, debug=debug, output=output)
        
        # Result is already formatted
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'answer': null,
            'diagnostics': [],
            'errors': [str(e)]
        }), 500
```

**Key insight**: No need for Flask's `g` object! Each request creates its own `RAGOutput` instance and passes it in. Much simpler than singleton pattern.

---

## Downstream Classes Consideration

**Question**: What if classes called by `DnDRAG` also need output buffering?

**Current situation**: 
- `DnDRAG` calls `ChromaDBConnector` - has ~5 error prints
- `DnDRAG` calls `query_must_filter.satisfies_query_must()` - has ~10 debug prints

**Strategy**:
1. **Pass `self.output` down the call chain** where needed
2. **ALL print statements must be removed** from code paths that Flask executes
3. Refactor downstream classes incrementally as needed

**Analysis of downstream classes**:
- `ChromaDBConnector`: ✅ **Zero print statements** - No changes needed
- `query_must_filter.py`: 
  - Lines 244-259: Already gated by `if debug:` (called via DnDRAG's debug parameter)
  - Lines 267-322: Test code in `if __name__ == "__main__"` block (Flask never executes)
  - ✅ **Safe for Flask** - No ungated prints in library code

**Critical rule**: Any print() that could execute during a Flask request **must** be refactored to use `self.output` or removed.

**Example**:
```python
# In DnDRAG.retrieve()
def retrieve(self, query, k=15, debug=False):
    self.output.info("Starting retrieval...")
    
    # Pass output to helper functions
    results = self._retrieve_with_filtering(query, k, debug)
    # Helper function uses self.output internally
    
    return results
```

Most helper methods are internal to `DnDRAG`, so they can access `self.output` directly. No need to pass it everywhere.

---

## Testing Strategy

### Unit Tests (Future)
```python
# tests/test_rag_output.py
def test_rag_output_captures_diagnostics():
    output = RAGOutput()
    output.info("Test message")
    
    result = output.to_dict()
    assert "Test message" in result['diagnostics']
    assert result['answer'] is None
```

### Integration Test (Manual)
1. Run CLI query with new output buffer
2. Verify output looks identical to current behavior
3. Check that `result.to_dict()` contains all expected fields

---

## Migration Path: Print Statement Conversion

### Conversion Rules

```python
# Rule 1: Initialization messages
print(f"Initializing...") 
→ self.output.info("Initializing...")

# Rule 2: Progress updates
print(f"Retrieved {n} chunks")
→ self.output.info(f"Retrieved {n} chunks")

# Rule 3: Debug messages (conditional)
if debug:
    print(f"[DEBUG] Gap: {gap}")
→ if debug:
    self.output.info(f"[DEBUG] Gap: {gap}")

# Rule 4: Error messages
print(f"Error: {e}")
→ self.output.error(f"Error: {e}")

# Rule 5: The Answer (special case)
print(answer)
→ self.output.set_answer(answer)
```

### NOT Converting (Keep as print() for now)
- Startup banner messages (before DnDRAG is created)
- Progress bars in converters/embedders (not critical path)
- Test output in `if __name__ == "__main__"` blocks

---

## Implementation Checklist (For Later)

### Session 1: Core Query Path
- [ ] Create `src/utils/rag_output.py`
- [ ] Update `DnDRAG.__init__()` signature (+output parameter)
- [ ] Replace prints in `DnDRAG.__init__()` (~10 statements)
- [ ] Update `DnDRAG.query()` to return `output.to_dict()`
- [ ] Replace prints in `DnDRAG.query()` (~15 statements)
- [ ] Replace prints in `DnDRAG.retrieve()` methods (~40 statements)
- [ ] Test: CLI query works identically to current behavior
- [ ] Update `main.py` cmd_query() to handle dict return
- [ ] Update `src/cli.py` cmd_query() to handle dict return
- [ ] Test: Full CLI workflow with --debug flag

### Session 2: Flask Integration
- [ ] Create `src/api.py` with Flask app
- [ ] Add `/api/query` endpoint
- [ ] Add `/health` endpoint
- [ ] Test: Local Flask server with curl
- [ ] Create decision doc for rate limiting
- [ ] Create decision doc for Apache config

### Session 3: Polish & Deploy
- [ ] Refactor `sys.exit()` to exceptions
- [ ] Add request ID tracking (Flask `g` object)
- [ ] Add execution time tracking
- [ ] Create `wsgi.py` entry point
- [ ] Configure Apache virtual host
- [ ] Deploy and test

---

**Decision Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Last Updated**: November 3, 2025  
**Next Steps**: Answer Mike's question about Python web process architecture, then document rate limiting decisions
