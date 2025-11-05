# Flask REST API Decision Log

**Decision Date**: November 3, 2025  
**Context**: Moving D&D 1st Edition RAG system to production with Apache web server  
**Status**: ✅ Approved

---

## Decision: Use Flask for REST API Layer

### Requirements
- Lightweight REST API for query endpoint
- No authentication needed (handled by Apache `.htaccess`)
- Basic routing (initially just `/api/query` POST endpoint)
- JSON request/response handling
- Must work with Apache mod_wsgi

### Why Flask?

**Strengths:**
- **Minimal footprint**: ~4.3MB (Flask 2.5MB + Werkzeug 1.8MB)
  - Only 0.86% of existing dependency footprint (~500MB for sentence-transformers)
- **Core functionality only**: HTTP parsing, routing, JSON serialization
- **No unnecessary features**: No ORM, no form validation, no admin panel
- **Battle-tested**: Used by millions of production deployments
- **Explicit over magic**: Clear, understandable code flow

**Perfect for our use case:**
- Single `/api/query` endpoint to start
- JSON-only API (no HTML templating needed)
- Low concurrent user count (2-5 expected)
- Already handle auth via Apache
- ChromaDB access via HTTP (no complex state management)

### Size Comparison

```
Current dependencies:     ~500MB (sentence-transformers, docling, chromadb)
Flask addition:           ~4.3MB
Percentage increase:      0.86%
```

### What Flask Handles For Us

1. **HTTP Request Parsing**
   - Headers, encoding, content-type negotiation
   - JSON parsing with error handling
   - Request validation

2. **Routing**
   - URL pattern matching
   - HTTP method filtering (GET, POST, etc.)
   - Decorator-based function mapping

3. **Response Building**
   - Automatic JSON serialization
   - Status code handling
   - Custom headers

4. **Error Handling**
   - Global exception catching
   - Custom error responses
   - Proper HTTP status codes

5. **Development Tools**
   - Built-in dev server with auto-reload
   - Interactive debugger
   - Pretty error pages

### Basic Implementation Pattern

```python
# src/api.py
from flask import Flask, request, jsonify
from .query.docling_query import DnDRAG

app = Flask(__name__)

# Initialize RAG system once (reused across requests)
rag = None

@app.before_first_request
def init_rag():
    global rag
    rag = DnDRAG(collection_name='dnd_unified')

@app.route('/health')
def health():
    return {'status': 'ok', 'service': 'dnd_rag'}

@app.route('/api/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'Missing required field: question'}), 400
        
        question = data['question']
        debug = data.get('debug', False)
        
        result = rag.query(question, debug=debug)
        
        return jsonify({
            'question': question,
            'answer': result.get('answer'),
            'chunks_used': result.get('chunks_used', 0),
            'diagnostics': result.get('diagnostics', []) if debug else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Query processing failed', 'details': str(e)}), 500
```

### Local Development Usage

```bash
# Install
pip install flask

# Run in debug mode
export FLASK_APP=src.api
export FLASK_ENV=development
python -m flask run --port 5000

# Test
curl http://localhost:5000/health

curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a beholder?", "debug": true}'
```

### Apache Integration (mod_wsgi)

```python
# wsgi.py (at project root)
from src.api import app as application
```

```apache
# In VirtualHost config
WSGIDaemonProcess dnd_rag \
    user=www-data \
    group=www-data \
    processes=2 \
    threads=5 \
    python-home=/home/mike/projects/gravitycar_dnd1st_rag_system/venv \
    python-path=/home/mike/projects/gravitycar_dnd1st_rag_system

WSGIProcessGroup dnd_rag
WSGIScriptAlias /api /path/to/wsgi.py
```

### Flask Features We'll Use

| Feature | Use Case | Priority |
|---------|----------|----------|
| **Core routing** | `/api/query`, `/health` endpoints | ✅ Required |
| **Request context (g)** | Request ID tracking, timing | ✅ Required |
| **Error handlers** | Graceful exception handling | ✅ Required |
| **Before/after request hooks** | Logging, metrics | ✅ Required |
| **flask-limiter extension** | Rate limiting (1 req/5sec) | ⚠️ Optional (Apache can handle) |
| **flask-cors extension** | CORS headers | ⚠️ Optional (Apache can handle) |

### Flask Features We Won't Use

- ❌ Jinja2 templating (API-only, no HTML)
- ❌ Static file serving (no CSS/JS)
- ❌ Session management (stateless API)
- ❌ Database integration (using ChromaDB)
- ❌ Form handling (JSON-only)

### Critical Refactor Required

**Current problem**: `DnDRAG.query()` prints to stdout instead of returning structured data

```python
# BAD (current):
def query(self, question, debug=False):
    print("Initializing...")  # Lost to stdout
    chunks = self._retrieve(question)
    print(f"Found {len(chunks)} chunks")  # Flask can't capture
    answer = self._generate_answer(chunks, question)
    print(answer)  # This is the answer!
    return answer

# GOOD (needed):
def query(self, question, debug=False):
    result = {
        'answer': None,
        'chunks_used': 0,
        'diagnostics': [],
        'error': None
    }
    
    try:
        if debug:
            result['diagnostics'].append("Initializing query...")
        
        chunks = self._retrieve(question)
        result['chunks_used'] = len(chunks)
        
        if debug:
            result['diagnostics'].append(f"Retrieved {len(chunks)} chunks")
        
        answer = self._generate_answer(chunks, question)
        result['answer'] = answer
        
    except Exception as e:
        result['error'] = str(e)
    
    return result
```

**Why this matters**: Flask needs to return JSON. Printing to stdout doesn't work in web context.

### Validation Tests

✅ **Q1: Do we need HTML pages?** No (API only)  
✅ **Q2: Do we need WebSockets/streaming?** No (simple request/response)  
✅ **Q3: Expect >100 concurrent users?** No (2-5 expected)  
✅ **Q4: Comfortable with decorators?** Yes  
✅ **Q5: Works with Apache mod_wsgi?** Yes (standard WSGI interface)

### Next Steps

1. **Refactor `DnDRAG.query()`** to return structured data (no print statements)
2. **Create `src/api.py`** with Flask wrapper
3. **Test locally** with `flask run`
4. **Create `wsgi.py`** entry point
5. **Configure Apache** virtual host with mod_wsgi daemon mode
6. **Add logging** (see Output Buffer decision doc)

### Related Decisions

- [Output Buffer Class](./output_buffer.md) - TBD
- [Rate Limiting Strategy](./rate_limiting.md) - TBD
- [Apache Configuration](./apache_config.md) - TBD

---

**Decision Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Last Updated**: November 3, 2025
