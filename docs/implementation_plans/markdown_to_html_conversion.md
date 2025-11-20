# Implementation Plan: Markdown to HTML Conversion for Web Client

## 1. Feature Overview

The Flask API currently returns OpenAI's Markdown-formatted responses directly to the web client. While this works well for CLI display (which expects Markdown), web clients need properly formatted HTML for rich rendering.

This feature will add automatic Markdown-to-HTML conversion for web responses while preserving the existing Markdown output for CLI users.

### Purpose
- **Web Environment**: Convert OpenAI's Markdown responses to HTML for proper browser rendering
- **CLI Environment**: Maintain current Markdown output for terminal display
- **Backwards Compatibility**: No changes to existing CLI functionality

### Problems Solved
1. **Poor Web Rendering**: Web clients currently receive raw Markdown and must handle conversion client-side
2. **Inconsistent Formatting**: Different clients may render Markdown differently
3. **Limited Styling**: Cannot apply D&D-themed CSS styling to raw Markdown
4. **Code Block Rendering**: Tables and code blocks in Markdown need proper HTML structure
5. **Client-Side Overhead**: Offloads Markdown parsing from client to server

---

## 2. Requirements

### Functional Requirements

**FR-1: Markdown Library Selection**
- Use Python `markdown` library (simple, battle-tested, 200KB)
- Support extensions for tables, code blocks, and fenced code
- No heavy dependencies (avoid pandoc, mistune, etc.)

**FR-2: HTML Conversion**
- Convert OpenAI's Markdown response to clean, semantic HTML
- Preserve all formatting (headings, lists, bold, italic, code blocks, tables)
- Apply D&D-themed CSS classes for styling hooks
- Sanitize output to prevent XSS (though OpenAI output is trusted)

**FR-3: Format Detection**
- Auto-detect request source (CLI vs web) via request headers
- CLI: Return Markdown (unchanged from current behavior)
- Web: Return HTML (new behavior)

**FR-4: Response Format**
- Keep existing JSON structure: `{answer, diagnostics, errors, meta}`
- Add `answer_format` field: `"markdown"` or `"html"`
- Web clients receive: `answer` = HTML string, `answer_format` = `"html"`
- CLI remains: `answer` = Markdown string, `answer_format` = `"markdown"`

**FR-5: CSS Styling (Optional)**
- Include inline CSS for basic D&D theming (brown parchment, serif fonts)
- OR return plain HTML and let client apply CSS
- Decision: Plain HTML (client applies styling for flexibility)

### Non-Functional Requirements

**NFR-1: Performance**
- Markdown-to-HTML conversion must add < 50ms latency
- Use efficient library (not regex-based parsers)

**NFR-2: Backwards Compatibility**
- Zero changes to CLI behavior
- Existing API clients work without modification (detect via headers)

**NFR-3: Testability**
- Unit tests for Markdown → HTML conversion
- Integration tests for Flask endpoint with format detection

**NFR-4: Security**
- HTML output must be safe (no script injection risk)
- Use markdown library's built-in sanitization

---

## 3. Design

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask API (/api/query)                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │  Request Handler      │
                │  - Validate token     │
                │  - Rate limit check   │
                │  - Execute RAG query  │
                └───────────┬───────────┘
                            │
                   ┌────────▼────────┐
                   │  Format Detector│
                   │  (User-Agent)   │
                   └────┬─────┬──────┘
                        │     │
            ┌───────────┘     └───────────┐
            │                              │
    ┌───────▼────────┐           ┌────────▼────────┐
    │  CLI Request   │           │  Web Request    │
    │  (curl/CLI)    │           │  (Browser/React)│
    └───────┬────────┘           └────────┬────────┘
            │                              │
            │                    ┌─────────▼─────────┐
            │                    │MarkdownToHTML     │
            │                    │ Converter         │
            │                    └─────────┬─────────┘
            │                              │
    ┌───────▼──────────────────────────────▼──────────┐
    │         Return JSON Response                    │
    │  {                                              │
    │    answer: "...",   (Markdown OR HTML)         │
    │    answer_format: "markdown" | "html",         │
    │    diagnostics: [...],                         │
    │    errors: [...],                              │
    │    meta: {...}                                 │
    │  }                                              │
    └─────────────────────────────────────────────────┘
```

### 3.2 Component Design

#### 3.2.1 MarkdownConverter Utility

**Purpose**: Convert Markdown strings to HTML

**Location**: `src/utils/markdown_converter.py`

**Interface**:
```python
class MarkdownConverter:
    """Convert Markdown to HTML for web display."""
    
    def __init__(self):
        """Initialize markdown parser with extensions."""
        
    def convert(self, markdown_text: str) -> str:
        """
        Convert Markdown to HTML.
        
        Args:
            markdown_text: Raw markdown string from OpenAI
            
        Returns:
            HTML string with proper structure
        """
        
    def is_web_request(self, request) -> bool:
        """
        Detect if request is from web client.
        
        Args:
            request: Flask request object
            
        Returns:
            True if web client, False if CLI
            
        Detection Strategy:
        - Check User-Agent header
        - Web clients: Mozilla, Chrome, Safari, React
        - CLI clients: curl, python-requests, httpie
        """
```

**Markdown Library Configuration**:
```python
import markdown

# Extensions for D&D content rendering
md = markdown.Markdown(extensions=[
    'tables',           # Support markdown tables (stat blocks)
    'fenced_code',      # Code blocks with ```
    'nl2br',            # Convert newlines to <br> (preserve formatting)
    'sane_lists',       # Better list handling
    'codehilite',       # Syntax highlighting for JSON tables
])
```

#### 3.2.2 Flask API Integration

**Modify**: `src/api.py` `/api/query` endpoint

**Changes**:
1. Import `MarkdownConverter`
2. After RAG query execution, detect format
3. Convert to HTML if web request
4. Add `answer_format` field to response

**Code Location** (line ~300 in `src/api.py`):
```python
# Current code (simplified):
result = rag_instance.query(question, k=k, debug=debug)
result['meta'] = {...}
return jsonify(result), 200

# New code:
from src.utils.markdown_converter import MarkdownConverter

converter = MarkdownConverter()

result = rag_instance.query(question, k=k, debug=debug)

# Format detection and conversion
if converter.is_web_request(request):
    result['answer'] = converter.convert(result['answer'])
    result['answer_format'] = 'html'
else:
    result['answer_format'] = 'markdown'

result['meta'] = {...}
return jsonify(result), 200
```

### 3.3 Format Detection Strategy

**Primary Method**: User-Agent Header Analysis

**Web Clients** (convert to HTML):
- Browsers: `Mozilla/5.0`, `Chrome/`, `Safari/`, `Edge/`
- React app: `axios/`, `fetch/`, custom header `X-Client: web`

**CLI Clients** (keep Markdown):
- curl: `curl/`
- Python requests: `python-requests/`
- httpie: `HTTPie/`
- Custom scripts: Any client without typical browser User-Agent

**Fallback**: Default to Markdown (safe, backwards compatible)

**Alternative Method** (if User-Agent unreliable):
- Add query parameter: `?format=html` (explicit override)
- Check custom header: `X-Response-Format: html`

### 3.4 HTML Output Format

**Structure**:
```html
<div class="dnd-answer">
  <h2>Headings become H2-H6</h2>
  <p>Paragraphs preserved</p>
  <ul><li>Lists formatted</li></ul>
  <table>
    <thead><tr><th>Header</th></tr></thead>
    <tbody><tr><td>Data</td></tr></tbody>
  </table>
  <pre><code class="language-json">
  {
    "json": "blocks preserved"
  }
  </code></pre>
</div>
```

**CSS Classes** (for client-side styling):
- `dnd-answer`: Wrapper div for all HTML content
- `dnd-table`: Applied to tables (stat blocks)
- `dnd-code`: Applied to code blocks (JSON tables)
- `dnd-heading`: Applied to headings

**Note**: CSS classes NOT included in MVP (plain HTML first, styling later)

---

## 4. Implementation Steps

### Phase 1: Core Conversion (2-3 hours)

**Step 1.1**: Install markdown library
```bash
# Add to requirements.txt and requirements-production.txt
echo "markdown==3.5.1" >> requirements.txt
echo "markdown==3.5.1" >> requirements-production.txt
pip install markdown==3.5.1
```

**Step 1.2**: Create `src/utils/markdown_converter.py`
- Implement `MarkdownConverter` class
- Configure markdown library with extensions
- Add `convert()` method
- Add `is_web_request()` method

**Step 1.3**: Add unit tests for converter
- Create `tests/test_markdown_converter.py`
- Test: Basic markdown → HTML conversion
- Test: Tables rendered correctly
- Test: Code blocks preserved
- Test: List formatting
- Test: Bold/italic/links
- Test: User-Agent detection logic

### Phase 2: API Integration (1-2 hours)

**Step 2.1**: Modify `src/api.py`
- Import `MarkdownConverter`
- Add format detection after query execution
- Convert to HTML for web requests
- Add `answer_format` field to response

**Step 2.2**: Test with curl (should remain Markdown)
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a beholder?"}'
```

**Step 2.3**: Test with browser User-Agent (should return HTML)
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
  -d '{"question": "What is a beholder?"}'
```

### Phase 3: Testing & Validation (1-2 hours)

**Step 3.1**: Integration tests
- Create `tests/test_api_markdown_html.py`
- Test CLI request → Markdown response
- Test Web request → HTML response
- Test fallback behavior (missing User-Agent)
- Test HTML sanitization

**Step 3.2**: Manual testing
- Query via CLI (`dnd-rag query`)
- Query via curl (both User-Agents)
- Query via Postman/Insomnia
- Inspect HTML output in browser console

**Step 3.3**: Performance testing
- Measure conversion latency (should be < 50ms)
- Test with large responses (2000+ tokens)
- Profile with cProfile if needed

### Phase 4: Documentation & Cleanup (1 hour)

**Step 4.1**: Update API documentation
- Document `answer_format` field
- Explain format detection logic
- Provide examples for both formats

**Step 4.2**: Update README
- Add note about HTML responses for web clients
- Document User-Agent detection

**Step 4.3**: Add logging
- Log format detection decisions (debug level)
- Track HTML conversion time in metrics

---

## 5. Testing Strategy

### Unit Tests

**Test File**: `tests/test_markdown_converter.py`

```python
def test_basic_conversion():
    """Test simple markdown to HTML."""
    converter = MarkdownConverter()
    markdown = "# Heading\n\nParagraph with **bold** text."
    html = converter.convert(markdown)
    assert "<h1>Heading</h1>" in html
    assert "<strong>bold</strong>" in html

def test_table_conversion():
    """Test markdown table to HTML table."""
    converter = MarkdownConverter()
    markdown = """
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
"""
    html = converter.convert(markdown)
    assert "<table>" in html
    assert "<thead>" in html
    assert "<tbody>" in html

def test_code_block_conversion():
    """Test fenced code blocks preserve JSON."""
    converter = MarkdownConverter()
    markdown = """
```json
{
  "monster": "beholder"
}
```
"""
    html = converter.convert(markdown)
    assert "<pre><code" in html
    assert '"monster": "beholder"' in html

def test_web_request_detection():
    """Test User-Agent parsing."""
    converter = MarkdownConverter()
    
    # Mock Flask request with web User-Agent
    class MockRequest:
        headers = {'User-Agent': 'Mozilla/5.0'}
    
    assert converter.is_web_request(MockRequest()) == True

def test_cli_request_detection():
    """Test CLI User-Agent detection."""
    converter = MarkdownConverter()
    
    class MockRequest:
        headers = {'User-Agent': 'curl/7.68.0'}
    
    assert converter.is_web_request(MockRequest()) == False
```

### Integration Tests

**Test File**: `tests/test_api_format_detection.py`

```python
def test_api_returns_markdown_for_cli(client, auth_token):
    """CLI requests get Markdown."""
    response = client.post('/api/query',
        json={'question': 'What is a beholder?'},
        headers={
            'Authorization': f'Bearer {auth_token}',
            'User-Agent': 'curl/7.68.0'
        }
    )
    data = response.get_json()
    assert data['answer_format'] == 'markdown'
    assert '**' in data['answer'] or '#' in data['answer']  # Has markdown syntax

def test_api_returns_html_for_web(client, auth_token):
    """Web requests get HTML."""
    response = client.post('/api/query',
        json={'question': 'What is a beholder?'},
        headers={
            'Authorization': f'Bearer {auth_token}',
            'User-Agent': 'Mozilla/5.0'
        }
    )
    data = response.get_json()
    assert data['answer_format'] == 'html'
    assert '<' in data['answer'] and '>' in data['answer']  # Has HTML tags
    assert '**' not in data['answer']  # No markdown syntax
```

### Manual Testing Checklist

- [ ] CLI: `dnd-rag query` still outputs Markdown to terminal
- [ ] API: curl with curl User-Agent returns Markdown
- [ ] API: curl with Mozilla User-Agent returns HTML
- [ ] API: React client receives HTML (check browser network tab)
- [ ] HTML: Tables render correctly in browser
- [ ] HTML: Code blocks preserve JSON structure
- [ ] HTML: Lists are properly formatted
- [ ] Performance: Conversion adds < 50ms latency
- [ ] Backwards Compatibility: Old clients work without changes

---

## 6. Documentation

### API Response Documentation

**Update**: `docs/api_reference.md` (create if doesn't exist)

```markdown
### Query Response Format

**Endpoint**: `POST /api/query`

**Response** (JSON):
```json
{
  "answer": "string (Markdown or HTML depending on client)",
  "answer_format": "markdown | html",
  "diagnostics": ["string"],
  "errors": ["string"],
  "meta": {
    "user_id": "string",
    "rate_limit": {...},
    "cost": {...},
    "performance": {...},
    "timestamp": "ISO8601"
  }
}
```

**Format Detection**:
- **CLI Clients** (curl, python-requests, httpie): `answer_format: "markdown"`
- **Web Clients** (browsers, React, axios): `answer_format: "html"`
- Detection via `User-Agent` header
- Default: Markdown (backwards compatible)

**Example - CLI Request**:
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "What is a beholder?"}'
```
**Response**:
```json
{
  "answer": "A **beholder** is a floating, spherical creature...",
  "answer_format": "markdown"
}
```

**Example - Web Request**:
```javascript
fetch('/api/query', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'User-Agent': 'Mozilla/5.0'  // Automatically set by browser
  },
  body: JSON.stringify({question: 'What is a beholder?'})
})
```
**Response**:
```json
{
  "answer": "<p>A <strong>beholder</strong> is a floating...</p>",
  "answer_format": "html"
}
```
```

---

## 7. Risks and Mitigations

### Risk 1: User-Agent Unreliable
**Likelihood**: Medium  
**Impact**: Low  
**Mitigation**: 
- Fallback to Markdown (safe default)
- Add query parameter override: `?format=html`
- Add custom header: `X-Response-Format: html`

### Risk 2: HTML Injection / XSS
**Likelihood**: Low (OpenAI output is trusted)  
**Impact**: High  
**Mitigation**:
- Use markdown library's built-in sanitization
- OpenAI responses don't contain user input
- Future: Add HTML sanitization library (bleach) if needed

### Risk 3: Performance Degradation
**Likelihood**: Low  
**Impact**: Medium  
**Mitigation**:
- Benchmark markdown library (should be < 10ms)
- Cache converter instance (avoid re-initialization)
- Profile with large responses (2000+ tokens)

### Risk 4: Breaking CLI Clients
**Likelihood**: Low  
**Impact**: High  
**Mitigation**:
- Comprehensive testing before deployment
- Fallback to Markdown ensures backwards compatibility
- Monitor error rates after deployment

### Risk 5: Styling Conflicts
**Likelihood**: Medium  
**Impact**: Low  
**Mitigation**:
- Return plain HTML (no inline CSS)
- Let client apply D&D theming
- Optionally add CSS classes for hooks

---

## 8. Future Enhancements

### Phase 2: CSS Styling (Post-MVP)
- Add D&D-themed CSS classes
- Parchment background for stat blocks
- Fantasy fonts for headings
- Color-coded damage types

### Phase 3: Custom Rendering (Advanced)
- Detect stat blocks and render as special components
- Interactive dice roller for damage calculations
- Expandable spell/monster cards
- Cross-references to other entries

### Phase 4: Format Negotiation
- Accept `Accept: text/html` header (proper HTTP content negotiation)
- Support multiple output formats: HTML, PDF, Plain Text
- Add `?format=` query parameter for explicit override

---

## 9. Success Criteria

### Minimum Success
- ✅ Web clients receive valid HTML
- ✅ CLI clients still receive Markdown
- ✅ No breaking changes to existing API
- ✅ Conversion adds < 100ms latency

### Target Success
- ✅ Format detection works for 99% of clients
- ✅ HTML renders correctly in all major browsers
- ✅ Tables and code blocks properly formatted
- ✅ Conversion adds < 50ms latency
- ✅ Unit test coverage > 90%

### Stretch Success
- ✅ Custom header override works
- ✅ Query parameter override works
- ✅ D&D-themed CSS classes included
- ✅ Integration with React UI complete
- ✅ Zero user-reported issues in first week

---

## 10. Implementation Checklist

### Core Development
- [ ] Install `markdown==3.5.1` library
- [ ] Create `src/utils/markdown_converter.py`
- [ ] Implement `MarkdownConverter` class
- [ ] Implement `convert()` method
- [ ] Implement `is_web_request()` method
- [ ] Modify `src/api.py` to integrate converter
- [ ] Add `answer_format` field to response

### Testing
- [ ] Create `tests/test_markdown_converter.py`
- [ ] Unit tests for conversion (5+ test cases)
- [ ] Unit tests for User-Agent detection (3+ test cases)
- [ ] Create `tests/test_api_format_detection.py`
- [ ] Integration test: CLI → Markdown
- [ ] Integration test: Web → HTML
- [ ] Manual test: curl with CLI User-Agent
- [ ] Manual test: curl with Web User-Agent
- [ ] Performance test: Conversion < 50ms
- [ ] Regression test: Existing CLI commands work

### Documentation
- [ ] Create `docs/api_reference.md`
- [ ] Document `answer_format` field
- [ ] Document format detection logic
- [ ] Add examples for both formats
- [ ] Update README with new feature
- [ ] Add inline code comments
- [ ] Update `.github/copilot-instructions.md`

### Deployment
- [ ] Update `requirements.txt`
- [ ] Update `requirements-production.txt`
- [ ] Test in local development environment
- [ ] Test in staging environment (if exists)
- [ ] Deploy to production
- [ ] Monitor logs for errors
- [ ] Monitor performance metrics

---

## Appendix A: Code Examples

### Example 1: MarkdownConverter Implementation

```python
#!/usr/bin/env python3
"""
Markdown to HTML Converter for D&D RAG System.

Converts OpenAI's Markdown responses to HTML for web clients
while preserving Markdown output for CLI clients.
"""

import markdown
from flask import Request
from typing import Optional


class MarkdownConverter:
    """
    Convert Markdown to HTML for web display.
    
    Uses Python markdown library with extensions for:
    - Tables (stat blocks)
    - Fenced code blocks (JSON tables)
    - Newline to <br> conversion
    - Syntax highlighting
    """
    
    def __init__(self):
        """Initialize markdown parser with D&D-friendly extensions."""
        self.md = markdown.Markdown(extensions=[
            'tables',           # Support markdown tables
            'fenced_code',      # Code blocks with ```
            'nl2br',            # Convert newlines to <br>
            'sane_lists',       # Better list handling
            'codehilite',       # Syntax highlighting for JSON
        ])
    
    def convert(self, markdown_text: str) -> str:
        """
        Convert Markdown to HTML.
        
        Args:
            markdown_text: Raw markdown string from OpenAI
            
        Returns:
            HTML string with proper structure
        """
        if not markdown_text:
            return ""
        
        # Convert markdown to HTML
        html = self.md.convert(markdown_text)
        
        # Reset parser state for next conversion
        self.md.reset()
        
        return html
    
    def is_web_request(self, request: Request) -> bool:
        """
        Detect if request is from web client.
        
        Args:
            request: Flask request object
            
        Returns:
            True if web client (browser/React), False if CLI (curl/requests)
            
        Detection Strategy:
        1. Check User-Agent header
        2. Web clients: Mozilla, Chrome, Safari, Edge, axios
        3. CLI clients: curl, python-requests, httpie
        4. Default: False (Markdown - backwards compatible)
        """
        user_agent = request.headers.get('User-Agent', '').lower()
        
        # Web browser indicators
        web_indicators = [
            'mozilla',      # Most browsers
            'chrome',       # Chrome/Chromium
            'safari',       # Safari
            'edge',         # Edge
            'firefox',      # Firefox
            'axios',        # Axios (common in React apps)
            'fetch',        # Fetch API
        ]
        
        # CLI client indicators
        cli_indicators = [
            'curl',         # curl
            'python-requests',  # Python requests library
            'httpie',       # HTTPie CLI tool
            'wget',         # wget
            'postman',      # Postman (treat as CLI for now)
        ]
        
        # Check for CLI indicators first (explicit Markdown)
        for indicator in cli_indicators:
            if indicator in user_agent:
                return False
        
        # Check for web indicators
        for indicator in web_indicators:
            if indicator in user_agent:
                return True
        
        # Default to CLI (Markdown) for backwards compatibility
        return False
```

### Example 2: Flask API Integration

```python
# src/api.py - Modified query endpoint

from src.utils.markdown_converter import MarkdownConverter

# Initialize converter once (module level)
markdown_converter = MarkdownConverter()

@app.route('/api/query', methods=['POST', 'OPTIONS'])
def query():
    """Query the D&D RAG system with Markdown/HTML format detection."""
    
    # ... existing code (auth, rate limiting, query execution) ...
    
    # Execute query
    try:
        rag_instance = get_rag()
        rag_instance.output = RAGOutput()
        
        result = rag_instance.query(question, k=k, debug=debug)
        
        # === NEW: Format detection and conversion ===
        if markdown_converter.is_web_request(request):
            # Convert Markdown to HTML for web clients
            result['answer'] = markdown_converter.convert(result['answer'])
            result['answer_format'] = 'html'
            
            if debug:
                logger.debug(f"Converted response to HTML for web client (User-Agent: {request.headers.get('User-Agent', 'unknown')})")
        else:
            # Keep Markdown for CLI clients
            result['answer_format'] = 'markdown'
            
            if debug:
                logger.debug(f"Returning Markdown for CLI client (User-Agent: {request.headers.get('User-Agent', 'unknown')})")
        # === END NEW CODE ===
        
        # Add metadata
        result['meta'] = {
            'user_id': user_id,
            'rate_limit': {...},
            'cost': {...},
            'performance': {...},
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        # ... existing error handling ...
```

---

## Appendix B: Dependencies

### Required Package

**Library**: `markdown`  
**Version**: `3.5.1` (latest stable as of Nov 2024)  
**Size**: ~200KB (very lightweight)  
**License**: BSD (permissive)

**Installation**:
```bash
pip install markdown==3.5.1
```

**Add to**:
- `requirements.txt` (development)
- `requirements-production.txt` (production servers)

**Why markdown library?**
- Battle-tested (10+ years in production)
- Pure Python (no C dependencies)
- Lightweight (~200KB vs pandoc ~50MB)
- Extensible (plugins for tables, code blocks, etc.)
- Fast (< 10ms for typical responses)
- Well-documented
- Active maintenance

**Alternatives Considered**:
- ❌ `mistune`: Faster but less feature-rich
- ❌ `pandoc`: Overkill (50MB, requires separate install)
- ❌ `commonmark`: Stricter spec but less flexible
- ❌ `mistletoe`: Good but less mature

---

## Appendix C: Example Outputs

### Example 1: Beholder Query (Markdown → HTML)

**Input** (Markdown from OpenAI):
```markdown
# Beholder

A **beholder** is a floating, spherical creature with a large central eye and many smaller eyestalks.

## Abilities
- **Central Eye**: Anti-magic cone
- **Eye Rays**: Various magical effects
- **Levitation**: Natural flight

## Statistics
| Attribute | Value |
|-----------|-------|
| AC        | 0/2/7 |
| HD        | 45-75 hp |
| THAC0     | 10    |
```

**Output** (HTML):
```html
<h1>Beholder</h1>
<p>A <strong>beholder</strong> is a floating, spherical creature with a large central eye and many smaller eyestalks.</p>

<h2>Abilities</h2>
<ul>
<li><strong>Central Eye</strong>: Anti-magic cone</li>
<li><strong>Eye Rays</strong>: Various magical effects</li>
<li><strong>Levitation</strong>: Natural flight</li>
</ul>

<h2>Statistics</h2>
<table>
<thead>
<tr>
<th>Attribute</th>
<th>Value</th>
</tr>
</thead>
<tbody>
<tr>
<td>AC</td>
<td>0/2/7</td>
</tr>
<tr>
<td>HD</td>
<td>45-75 hp</td>
</tr>
<tr>
<td>THAC0</td>
<td>10</td>
</tr>
</tbody>
</table>
```

---

*Last Updated: November 19, 2025*  
*Version: 1.0 (Initial Draft)*  
*Status: Ready for Review*
