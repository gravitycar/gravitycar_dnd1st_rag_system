# OAuth2 Integration Architecture

**Decision Date**: November 3, 2025  
**Context**: Integration with api.gravitycar.com OAuth2 system  
**Status**: ✅ Approved - Ready for Implementation

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER'S BROWSER                               │
│                                                                 │
│  1. User logs in via Google OAuth                              │
│  2. Receives JWT token (stored in localStorage)                │
│  3. Makes requests with Authorization: Bearer <token>          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ All requests include:
                     │ - Authorization: Bearer <jwt_token>
                     │ - Origin: https://react.gravitycar.com
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│              react.gravitycar.com (ReactJS UI)                  │
│                                                                 │
│  D&D Chat Interface:                                            │
│  - User types question                                          │
│  - Displays RAG response                                        │
│  - Shows rate limit status (15 burst, 30/day)                  │
│  - Handles HTTP 429 (rate limit) gracefully                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ POST /api/query
                     │ Authorization: Bearer <jwt_token>
                     │ Origin: https://react.gravitycar.com
                     │ { "question": "What is a beholder?" }
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│           dndchat.gravitycar.com (Flask + DNDRag)               │
│                                                                 │
│  Flask Middleware Pipeline:                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. CORS Check                                            │  │
│  │    - Verify Origin header                                │  │
│  │    - Only allow react.gravitycar.com, www.gravitycar.com │  │
│  │    - Browser protection (not auth)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 2. Token Validation (with 5-minute cache)                │  │
│  │    - Extract Bearer token from Authorization header      │  │
│  │    - Check cache first (avoid API spam)                  │  │
│  │    - If not cached, validate with api.gravitycar.com     │  │
│  │    - Store user_id in Flask g object                     │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                 │
│               │ Cache miss? Validate token                      │
│               ↓                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │    GET https://api.gravitycar.com/auth/me                │  │
│  │    Authorization: Bearer <jwt_token>                     │  │
│  │    ↓                                                      │  │
│  │    Response: { "id": 123, "email": "..." }              │  │
│  │    Cache for 5 minutes (token TTL = 60 min)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 3. Budget Check                                          │  │
│  │    - Is daily $1.00 budget exceeded?                     │  │
│  │    - If yes: Return HTTP 503 (Service Unavailable)       │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4. Rate Limiting (per user_id)                           │  │
│  │    - Token bucket: 15 burst, 1/min refill               │  │
│  │    - Daily limit: 30 requests                            │  │
│  │    - If exceeded: Return HTTP 429 (Too Many Requests)    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 5. Process RAG Query                                     │  │
│  │    - DnDRAG.query(question)                              │  │
│  │    - Retrieve from ChromaDB                              │  │
│  │    - Generate with OpenAI GPT-4o-mini                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 6. Record Costs                                          │  │
│  │    - Track embedding + completion tokens                 │  │
│  │    - Update daily budget tracker                         │  │
│  │    - Send email if 80% or 100% of budget reached        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 7. Return Response                                       │  │
│  │    - answer: LLM response                                │  │
│  │    - meta: { user_id, rate_limit, cost }                │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                     ↑
                     │ Token validation request
                     │ (only on cache miss - ~12 times/hour per user)
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│          api.gravitycar.com (PHP OAuth2 API)                    │
│                                                                 │
│  GET /auth/me:                                                  │
│  - Validates JWT signature (HS256)                             │
│  - Checks token expiration (3600 sec TTL)                      │
│  - Loads user from database                                    │
│  - Verifies user.is_active = true                              │
│  - Returns: { id, email, username, first_name, last_name }     │
│                                                                 │
│  Error Responses:                                               │
│  - NO_TOKEN: Missing Authorization header                      │
│  - INVALID_TOKEN: Expired or malformed JWT                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Token Validation Strategy

### Why Cache for 5 Minutes?

**Problem**: Every request to DNDRag needs user_id for rate limiting  
**Naive approach**: Call `api.gravitycar.com/auth/me` on every request  
**Cost**: 30 requests/day × 2-5 users = 60-150 validation API calls/day  

**Optimized approach**: Cache validation results for 5 minutes

**Math**:
- Token TTL: 3600 seconds (1 hour)
- Cache TTL: 300 seconds (5 minutes)
- Validation calls per user: 12/hour (every 5 minutes)
- For 30 requests/day: Only ~6 validation calls (vs 30)
- **Savings**: 80% reduction in API calls

**Security**: Still validates 12 times per hour, catches:
- Token revocation within 5 minutes
- User account deactivation within 5 minutes
- Acceptable for 2-5 trusted users

### Token Validation Cache Implementation

```python
# src/utils/token_validator.py
import time
import requests
from threading import Lock
from typing import Optional, Dict
from flask import g, abort
import os

class TokenValidator:
    """Validate JWT tokens with api.gravitycar.com with caching."""
    
    def __init__(self, api_base_url: str, cache_ttl: int = 300):
        """
        Args:
            api_base_url: Base URL for api.gravitycar.com (e.g., https://api.gravitycar.com)
            cache_ttl: Cache TTL in seconds (default 300 = 5 minutes)
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, dict] = {}  # token -> {user_info, expires_at}
        self.lock = Lock()
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token and return user info.
        
        Args:
            token: JWT token (without "Bearer " prefix)
            
        Returns:
            User info dict: {"id": 123, "email": "...", "username": "...", ...}
            None if invalid
        """
        with self.lock:
            # Check cache first
            now = time.time()
            if token in self.cache:
                cached = self.cache[token]
                if cached['expires_at'] > now:
                    return cached['user_info']
                else:
                    # Expired - remove from cache
                    del self.cache[token]
            
            # Cache miss - validate with API
            try:
                response = requests.get(
                    f"{self.api_base_url}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5  # 5 second timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    user_info = data.get('data')
                    
                    if user_info:
                        # Cache the result
                        self.cache[token] = {
                            'user_info': user_info,
                            'expires_at': now + self.cache_ttl
                        }
                        return user_info
                
                # Invalid token - don't cache
                return None
                
            except requests.exceptions.RequestException as e:
                # API unavailable - log error but don't crash
                print(f"Error validating token with api.gravitycar.com: {e}")
                # Fail closed - reject request if we can't validate
                return None
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries (call periodically from background thread)."""
        with self.lock:
            now = time.time()
            expired_tokens = [
                token for token, data in self.cache.items()
                if data['expires_at'] <= now
            ]
            for token in expired_tokens:
                del self.cache[token]


# Global validator instance
_validator = None

def get_validator() -> TokenValidator:
    """Get or create the global TokenValidator instance."""
    global _validator
    if _validator is None:
        api_base_url = os.getenv('API_GRAVITYCAR_BASE_URL', 'https://api.gravitycar.com')
        cache_ttl = int(os.getenv('TOKEN_CACHE_TTL', '300'))  # 5 minutes default
        _validator = TokenValidator(api_base_url, cache_ttl)
    return _validator
```

### Flask Middleware Integration

```python
# src/api.py
from flask import Flask, request, jsonify, g, abort
from src.query.docling_query import DnDRAG
from src.utils.rag_output import RAGOutput
from src.utils.rate_limiter import TokenBucket
from src.utils.cost_tracker import CostTracker
from src.utils.token_validator import get_validator
from src.utils.config import get_env_float, get_env_int, get_env_string
import os

app = Flask(__name__)

# Initialize components
validator = get_validator()
limiter = TokenBucket(
    capacity=get_env_int('TOKEN_BUCKET_CAPACITY', 15),
    refill_rate=get_env_float('TOKEN_REFILL_RATE', 1/60),
    daily_limit=get_env_int('DAILY_USER_REQUEST_LIMIT', 30)
)
cost_tracker = CostTracker(
    daily_budget_usd=get_env_float('DAILY_BUDGET_USD', 1.0),
    alert_email=get_env_string('ALERT_EMAIL')
)

# Initialize RAG once at startup
rag = None

@app.before_first_request
def init_rag():
    global rag
    rag = DnDRAG()

# CORS configuration
ALLOWED_ORIGINS = [
    'https://react.gravitycar.com',
    'https://www.gravitycar.com',
    'http://localhost:3000',  # Local development
]

@app.before_request
def validate_request():
    """Middleware: CORS + Token validation for all requests."""
    
    # Skip validation for OPTIONS preflight requests
    if request.method == 'OPTIONS':
        return
    
    # 1. CORS Check (browser protection)
    origin = request.headers.get('Origin')
    if origin not in ALLOWED_ORIGINS:
        abort(403, description=f"Origin '{origin}' not allowed")
    
    # 2. Token Validation (real authentication)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        abort(401, description="Missing or invalid Authorization header")
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    user_info = validator.validate_token(token)
    
    if not user_info:
        abort(401, description="Invalid or expired token")
    
    # 3. Store user info in Flask g object (available to route handlers)
    g.user_id = user_info['id']
    g.user_email = user_info.get('email')
    g.user_name = user_info.get('username')

@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses."""
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '3600'  # Cache preflight for 1 hour
    return response

@app.route('/api/query', methods=['POST', 'OPTIONS'])
def query():
    """Main RAG query endpoint."""
    
    # Handle OPTIONS preflight
    if request.method == 'OPTIONS':
        return '', 204
    
    # Get user_id from g (set by validate_request middleware)
    user_id = g.user_id
    
    # Check global budget first
    budget_exceeded, budget_info = cost_tracker.is_budget_exceeded()
    if budget_exceeded:
        return jsonify({
            'error': 'Daily budget exceeded',
            'message': 'Service temporarily unavailable. Daily budget will reset at midnight UTC.',
            'budget_info': budget_info
        }), 503  # Service Unavailable
    
    # Check user rate limit
    allowed, rate_info = limiter.allow_request(str(user_id))
    if not allowed:
        response = jsonify({
            'error': rate_info['reason'],
            'message': rate_info['message'],
            'rate_info': {
                'daily_remaining': rate_info['daily_remaining'],
                'retry_after': rate_info.get('retry_after')
            }
        })
        response.status_code = 429  # Too Many Requests
        
        # Add Retry-After header if rate limited (not daily limit)
        if rate_info.get('retry_after'):
            response.headers['Retry-After'] = str(rate_info['retry_after'])
        
        return response
    
    try:
        data = request.get_json()
        question = data.get('question')
        debug = data.get('debug', False)
        
        if not question:
            return jsonify({'error': 'Missing required field: question'}), 400
        
        # Create output buffer
        output = RAGOutput()
        
        # Process query
        result = rag.query(question, k=15, debug=debug, output=output)
        
        # Extract token usage from OpenAI response
        # (You'll need to modify DnDRAG to return this info)
        embedding_tokens = result.get('embedding_tokens', 0)
        completion_tokens = result.get('completion_tokens', 0)
        
        # Record costs
        cost_info = cost_tracker.record_query(str(user_id), embedding_tokens, completion_tokens)
        
        # Add metadata to response
        result['meta'] = {
            'user_id': user_id,
            'user_email': g.user_email,
            'rate_limit': {
                'remaining_burst': rate_info['remaining_burst'],
                'daily_remaining': rate_info['daily_remaining']
            },
            'cost': {
                'query_cost': cost_info['query_cost'],
                'daily_total': cost_info['daily_cost'],
                'daily_budget': cost_info['daily_budget']
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Query processing failed',
            'details': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint (no auth required)."""
    return jsonify({
        'status': 'ok',
        'service': 'dndchat',
        'version': '1.0.0'
    }), 200

if __name__ == '__main__':
    # Development only - use mod_wsgi in production
    app.run(host='0.0.0.0', port=5000, debug=True)
```

---

## React Frontend Integration

### Example API Call from React

```typescript
// react.gravitycar.com/src/api/dndchat.ts
import axios from 'axios';

const DNDCHAT_API_BASE = process.env.REACT_APP_DNDCHAT_API || 'https://dndchat.gravitycar.com';

export class DnDChatAPI {
  private api;

  constructor() {
    this.api = axios.create({
      baseURL: DNDCHAT_API_BASE,
      timeout: 30000, // 30 second timeout for LLM generation
    });

    // Add auth token to all requests
    this.api.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle rate limiting gracefully
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 429) {
          const retryAfter = error.response.headers['retry-after'];
          const message = error.response.data.message || 'Rate limit exceeded';
          
          // Show user-friendly message
          console.warn(`Rate limited. ${message}. Retry after ${retryAfter} seconds.`);
        }
        return Promise.reject(error);
      }
    );
  }

  async query(question: string, debug: boolean = false) {
    const response = await this.api.post('/api/query', {
      question,
      debug,
    });
    return response.data;
  }
}

// Usage in React component:
// const dndChat = new DnDChatAPI();
// const result = await dndChat.query("What is a beholder?");
// console.log(result.answer); // LLM response
// console.log(result.meta.rate_limit); // { remaining_burst: 14, daily_remaining: 29 }
```

---

## Security Considerations

### What We Protect Against

| Threat | Protection | How |
|--------|-----------|-----|
| **Unauthenticated access** | ✅ Token validation | Every request validated with api.gravitycar.com |
| **Expired tokens** | ✅ Cache TTL + JWT expiry | Cache expires after 5 min, JWT after 60 min |
| **Revoked tokens** | ⚠️ 5-minute window | User deactivation takes up to 5 min to propagate |
| **XSS token theft** | ✅ CORS + Browser protection | CORS prevents malicious sites from stealing tokens |
| **Direct API abuse** | ✅ Token required | Can't query without valid JWT from api.gravitycar.com |
| **Rate limit bypass** | ✅ Per-user tracking | Rate limits tied to user.id (immutable) |
| **Cost abuse** | ✅ Budget limits | $1/day global + 30 req/day per user |

### What We DON'T Protect Against (Acceptable Risks)

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **User shares token** | Another person uses their quota | 2-5 trusted users, low risk |
| **Token stolen** | Attacker has 60-min window | Use HTTPS, refresh tokens hourly |
| **API.gravitycar.com down** | DNDRag can't validate tokens | Fail closed (reject all requests) |
| **Cache invalidation delay** | Deactivated user has 5-min window | Acceptable for trusted users |

### Defense in Depth Layers

1. **CORS** (Browser layer) - Prevents XSS attacks from random domains
2. **JWT Validation** (Authentication layer) - Verifies user identity
3. **Rate Limiting** (Abuse prevention layer) - Prevents quota exhaustion
4. **Budget Tracking** (Cost protection layer) - Prevents runaway costs
5. **HTTPS** (Transport layer) - Prevents token interception
6. **Apache mod_wsgi** (Process isolation layer) - Crashes don't affect other services

---

## Updated `.env` Configuration

```bash
# OpenAI Configuration
openai_api_key=sk-...

# ChromaDB Configuration
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/

# Default Collection
default_collection_name=dnd_unified

# OAuth2 Integration
API_GRAVITYCAR_BASE_URL=https://api.gravitycar.com
TOKEN_CACHE_TTL=300  # 5 minutes in seconds

# Rate Limiting & Cost Tracking
DAILY_BUDGET_USD=1.00
DAILY_USER_REQUEST_LIMIT=30
TOKEN_BUCKET_CAPACITY=15
TOKEN_REFILL_RATE=0.016667  # 1/60 = 1 token per minute

# Email Alerts
ALERT_EMAIL=mike@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=dnd-rag@yourdomain.com

# Local Development Overrides
# (Uncomment when running locally)
# API_GRAVITYCAR_BASE_URL=http://localhost:8080
# TOKEN_CACHE_TTL=60  # Shorter cache for testing
```

---

## Local Development Strategy

### Problem: How to Test OAuth Locally?

**Option 1: Use Production api.gravitycar.com** (Recommended)
```bash
# .env.local
API_GRAVITYCAR_BASE_URL=https://api.gravitycar.com  # Production API
TOKEN_CACHE_TTL=60  # Shorter cache for faster testing

# Local Flask
$ source venv/bin/activate
$ export FLASK_APP=src/api.py
$ export FLASK_ENV=development
$ flask run --host=0.0.0.0 --port=5000

# Test with curl
$ TOKEN="your_jwt_token_from_browser_localStorage"
$ curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a beholder?"}'
```

**Option 2: Mock Validator for Unit Tests**
```python
# tests/test_api.py
import pytest
from unittest.mock import Mock, patch
from src.api import app

@pytest.fixture
def mock_validator():
    with patch('src.api.validator') as mock:
        # Mock successful validation
        mock.validate_token.return_value = {
            'id': 123,
            'email': 'test@example.com',
            'username': 'testuser'
        }
        yield mock

def test_query_endpoint_with_valid_token(mock_validator):
    client = app.test_client()
    
    response = client.post('/api/query',
        json={'question': 'What is a beholder?'},
        headers={
            'Authorization': 'Bearer fake_token_for_testing',
            'Origin': 'http://localhost:3000'
        })
    
    assert response.status_code == 200
    assert 'answer' in response.json
```

---

## Implementation Checklist

### Phase 1: Token Validation (Session 2)
- [ ] Create `src/utils/token_validator.py` with TokenValidator class
- [ ] Add OAuth2 config to `.env` (API_GRAVITYCAR_BASE_URL, TOKEN_CACHE_TTL)
- [ ] Add `validate_request()` middleware to `src/api.py`
- [ ] Add CORS headers to `src/api.py`
- [ ] Test with real JWT token from api.gravitycar.com
- [ ] Verify cache is working (watch logs for "cache hit" vs "API call")

### Phase 2: Error Handling (Session 2)
- [ ] Handle api.gravitycar.com downtime gracefully
- [ ] Add retry logic with exponential backoff (optional)
- [ ] Log validation failures for debugging
- [ ] Add `/api/health` endpoint for monitoring

### Phase 3: React Integration (Session 3)
- [ ] Create `DnDChatAPI` class in React app
- [ ] Add Authorization header interceptor
- [ ] Handle HTTP 429 (rate limit) gracefully
- [ ] Display rate limit info to user
- [ ] Add loading state for 30-second LLM generation

### Phase 4: Testing (Session 3)
- [ ] Unit tests for TokenValidator (mock api.gravitycar.com)
- [ ] Integration test with real api.gravitycar.com
- [ ] Test token expiration (wait 60 minutes)
- [ ] Test cache expiration (wait 5 minutes)
- [ ] Test rate limiting with real user tokens

---

## Next Steps

Now that OAuth2 integration is defined, we can finalize:

1. **Apache Configuration**: Virtual host for `dndchat.gravitycar.com`
2. **mod_wsgi Setup**: WSGI daemon process configuration
3. **Let's Encrypt SSL**: Certificate for dndchat.gravitycar.com subdomain
4. **Deployment Script**: Automated deployment from git

Ready to document Apache configuration?

---

**Decision Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Last Updated**: November 3, 2025  
**Status**: ✅ Finalized - Ready for Apache Config
