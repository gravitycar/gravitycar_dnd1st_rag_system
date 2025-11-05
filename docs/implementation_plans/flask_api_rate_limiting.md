# Flask API + Rate Limiting + OAuth2 - Implementation Plan

**Feature**: Flask REST API with OAuth2 Authentication and Rate Limiting  
**Status**: 📋 Planning Complete - Ready to Execute  
**Estimated Time**: 8.5-10.5 hours (includes unit tests + integration tests)  
**Priority**: Critical (Session 2 of Apache Deployment)  
**Created**: November 4, 2025  
**Updated**: November 4, 2025 (added unit tests + Task 2.1b for OpenAI token tracking)  
**Dependencies**: Session 1 (Output Buffer Refactoring) ✅ Complete

---

## 1. Feature Overview

### Purpose
Create a production-ready Flask REST API that wraps the D&D RAG system with:
1. **OAuth2 Authentication**: Validate JWT tokens from api.gravitycar.com
2. **Rate Limiting**: Token bucket (15 burst, 1/min refill, 30/day limit)
3. **Cost Tracking**: Daily budget enforcement ($1.00/day) with email alerts
4. **Structured Responses**: JSON format with answer/diagnostics/errors/metadata

This enables the React frontend to interact with the RAG system through a secure, rate-limited REST API.

### Problem Being Solved
- **Current state**: CLI-only RAG system, no web interface
- **Goal**: Production REST API accessible from react.gravitycar.com
- **Constraints**: 
  - Must prevent abuse (rate limiting + cost tracking)
  - Must validate user identity (OAuth2)
  - Must maintain backward compatibility with CLI

### Success Criteria
- [ ] Flask API runs locally and handles `/api/query` POST requests
- [ ] OAuth2 token validation works with real JWT from api.gravitycar.com
- [ ] Rate limiting enforces 15-burst, 1/min refill, 30/day limit
- [ ] Budget tracking triggers alerts at 80% and 100%
- [ ] CORS allows requests from react.gravitycar.com only
- [ ] Health endpoint returns 200 OK
- [ ] All 6 test scenarios pass (burst, rate limit, daily limit, budget, token validation, CORS)

---

## 2. Requirements

### Functional Requirements

**FR-1**: Flask app must expose two endpoints
- `GET /health`: Health check (no auth required)
- `POST /api/query`: RAG query endpoint (requires OAuth2 token)

**FR-2**: OAuth2 token validation
- Extract JWT from `Authorization: Bearer <token>` header
- Validate with `api.gravitycar.com/auth/me` endpoint
- Cache validation results for 5 minutes (reduces API calls by 80%)
- Extract user GUID for rate limiting

**FR-3**: Rate limiting per user
- Token bucket: 15 tokens capacity, 1 token/60s refill rate
- Daily limit: 30 requests per user per day
- Storage: Per-user JSON files in `data/user_requests/<user_guid>.json`
- File locking: fcntl (non-blocking, fail-closed)
- HTTP responses:
  - 429 Too Many Requests (rate limited)
  - Retry-After header when rate limited

**FR-4**: Cost tracking and budget enforcement
- Track OpenAI API costs (embedding + completion tokens)
- Daily budget: $1.00 (configurable via .env)
- Global kill switch: HTTP 503 when budget exceeded
- Email alerts: 80% warning, 100% critical
- Per-user cost tracking for reporting

**FR-5**: CORS configuration
- Allow origin: react.gravitycar.com, www.gravitycar.com
- Allow methods: GET, POST, OPTIONS
- Allow headers: Content-Type, Authorization
- Allow credentials: true
- Block all other origins

**FR-6**: Error handling
- Invalid token: HTTP 401 Unauthorized
- Rate limit exceeded: HTTP 429 Too Many Requests
- Budget exceeded: HTTP 503 Service Unavailable
- Internal errors: HTTP 500 Internal Server Error
- Missing required fields: HTTP 400 Bad Request

### Non-Functional Requirements

**NFR-1**: Performance
- Token validation cache hit rate: >80%
- API response time: <3 seconds (P95)
- Rate limiter overhead: <10ms per request

**NFR-2**: Reliability
- Graceful degradation if api.gravitycar.com is down (fail closed)
- File locking prevents race conditions (concurrent requests)
- Email alerts must not crash the app if SMTP fails

**NFR-3**: Security
- JWT tokens validated on every request (or from cache)
- CORS strictly enforced (browser protection)
- Secrets stored in .env (not committed to git)
- Rate limit files secured with 640 permissions

**NFR-4**: Maintainability
- Configuration via .env (no hardcoded values)
- Clear separation of concerns (validator, limiter, tracker, API)
- Comprehensive logging for debugging
- Type hints for all public methods

---

## 3. Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                 React Frontend (react.gravitycar.com)        │
│          POST /api/query with Authorization: Bearer <jwt>    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Flask API (dndchat.gravitycar.com)              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Middleware Pipeline:                                    │ │
│  │ 1. CORS Check → 2. Token Validation → 3. Budget Check │ │
│  │ 4. Rate Limiting → 5. RAG Query → 6. Cost Tracking    │ │
│  └────────────────────────────────────────────────────────┘ │
└──┬──────────────────┬──────────────────┬────────────────┬───┘
   │                  │                  │                │
   │ Validate Token   │ Check Budget     │ Record Costs   │ Query
   ▼                  ▼                  ▼                ▼
┌──────────┐    ┌─────────────┐    ┌──────────┐    ┌─────────┐
│ api.     │    │ CostTracker │    │  SMTP    │    │ DnDRAG  │
│gravitycar│    │ (in-memory) │    │  Server  │    │ + Chroma│
│  .com    │    └─────────────┘    └──────────┘    └─────────┘
└──────────┘
   (cached)
   
┌─────────────────────────────────────────────────────────────┐
│          Rate Limiter (file-based, per-user)                 │
│  data/user_requests/                                         │
│  ├── <user-guid-1>.json  (user 1's token bucket state)     │
│  ├── <user-guid-2>.json  (user 2's token bucket state)     │
│  └── <user-guid-3>.json  (user 3's token bucket state)     │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

**Flow 1: Successful Query**
```
1. React sends POST /api/query with JWT token
2. Flask extracts token from Authorization header
3. TokenValidator checks cache → cache hit (no API call)
4. Extract user_id from cached user info
5. CostTracker checks daily budget → $0.45/$1.00 (OK)
6. TokenBucket checks user's rate limit → 8.5 tokens remaining (OK)
7. Decrement 1 token from bucket, save to file
8. DnDRAG.query() executes (retrieve + generate)
9. CostTracker records tokens used (embedding + completion)
10. Return JSON: {answer, meta: {user_id, rate_limit, cost}}
```

**Flow 2: Rate Limited**
```
1. React sends POST /api/query
2-4. Token validation succeeds
5. CostTracker checks budget → OK
6. TokenBucket checks rate limit → 0.3 tokens remaining (< 1.0)
7. Calculate retry_after = (1.0 - 0.3) / refill_rate = 42 seconds
8. Return HTTP 429 with Retry-After: 42 header
9. React shows: "Rate limit reached. Try again in 42 seconds."
```

**Flow 3: Budget Exceeded**
```
1. React sends POST /api/query
2-4. Token validation succeeds
5. CostTracker checks budget → $1.02/$1.00 (EXCEEDED)
6. Send email alert (if not already sent)
7. Return HTTP 503 Service Unavailable
8. React shows: "Service temporarily unavailable. Budget will reset at midnight UTC."
```

**Flow 4: Invalid Token**
```
1. React sends POST /api/query with expired/invalid JWT
2. Flask extracts token
3. TokenValidator checks cache → cache miss
4. Call api.gravitycar.com/auth/me → HTTP 401
5. Return HTTP 401 Unauthorized
6. React redirects to login page
```

### Data Models

**Request Format** (POST /api/query):
```json
{
  "question": "What is a beholder?",
  "debug": false,
  "k": 15
}
```

**Response Format** (HTTP 200):
```json
{
  "answer": "A beholder is a floating sphere...",
  "diagnostics": [],
  "errors": [],
  "meta": {
    "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "rate_limit": {
      "remaining_burst": 7,
      "daily_remaining": 18,
      "refill_rate": 0.016667
    },
    "cost": {
      "query_cost": 0.000234,
      "daily_total": 0.045678,
      "daily_budget": 1.00
    }
  }
}
```

**Error Response Format** (HTTP 429):
```json
{
  "error": "rate_limited",
  "message": "Rate limit exceeded. Please wait 42 seconds.",
  "rate_info": {
    "remaining_burst": 0,
    "daily_remaining": 18,
    "retry_after": 42
  }
}
```

**Per-User Rate Limit File** (`data/user_requests/<guid>.json`):
```json
{
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tokens": 8.5,
  "last_refill": 1699024583.234,
  "daily_count": 12,
  "daily_reset": "2025-11-04"
}
```

---

## 4. Implementation Steps

### Environment Configuration Strategy

**Local vs Production**: This implementation uses environment variables to distinguish between local development and production:

| Configuration | Local | Production |
|--------------|-------|------------|
| **React UI** | `http://localhost:3000` | `https://react.gravitycar.com` |
| **PHP API** | `http://localhost:8081` | `https://api.gravitycar.com` |
| **Flask RAG API** | `http://localhost:5000` | `https://dndchat.gravitycar.com` |

**Key Environment Variables**:
- `AUTH_API_URL`: Where to validate JWT tokens (localhost:8081 vs api.gravitycar.com)
- `CORS_ORIGINS`: Comma-separated list of allowed origins (localhost:3000 vs react.gravitycar.com)
- `FLASK_ENV`: `development` or `production`

**Setup**:
1. Create `.env` for local development (localhost URLs)
2. Create `.env.production` for production (gravitycar.com URLs)
3. In production deployment (Apache), copy `.env.production` to `.env` or set environment variables in Apache config

This ensures the same codebase works in both environments without modification.

---

### Step 1: Create Utility Classes (2 hours)

#### Task 1.1: TokenValidator Class (45 min)

**File**: `src/utils/token_validator.py`

**Code**:
```python
#!/usr/bin/env python3
"""
OAuth2 JWT token validator with caching.

Validates JWT tokens with api.gravitycar.com and caches results
for 5 minutes to reduce API calls by 80%.
"""

import time
import requests
from threading import Lock
from typing import Optional, Dict
import os


class TokenValidator:
    """Validate JWT tokens with api.gravitycar.com with caching."""
    
    def __init__(self, api_base_url: str, cache_ttl: int = 300):
        """
        Initialize token validator.
        
        Args:
            api_base_url: Base URL for api.gravitycar.com
            cache_ttl: Cache TTL in seconds (default 300 = 5 minutes)
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, dict] = {}  # token -> {user_info, expires_at}
        self.lock = Lock()
    
    def validate(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token and return user info.
        
        Args:
            token: JWT token (without "Bearer " prefix)
            
        Returns:
            User info dict: {"id": "guid-string", "email": "...", ...}
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
                    timeout=5
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
                
                return None
                
            except requests.exceptions.RequestException as e:
                print(f"Error validating token: {e}")
                return None
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        with self.lock:
            now = time.time()
            expired_tokens = [
                token for token, data in self.cache.items()
                if data['expires_at'] <= now
            ]
            for token in expired_tokens:
                del self.cache[token]
```

**Validation**:
```bash
# Test import
python -c "from src.utils.token_validator import TokenValidator; print('✅ Import success')"

# Test basic functionality (mock)
python -c "
from src.utils.token_validator import TokenValidator
validator = TokenValidator('https://api.gravitycar.com', cache_ttl=60)
# Would need real token to test fully
print('✅ TokenValidator instantiated')
"
```

#### Task 1.2: TokenBucket Rate Limiter (45 min)

**File**: `src/utils/rate_limiter.py`

**Code**:
```python
#!/usr/bin/env python3
"""
Token bucket rate limiter with per-user file storage.

Uses fcntl for file locking to prevent race conditions.
Each user gets their own JSON file to eliminate cross-user contention.
"""

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Tuple


class TokenBucket:
    """Per-user file-based rate limiter with fcntl locking."""
    
    def __init__(
        self, 
        capacity: int = 15, 
        refill_rate: float = 1/60, 
        daily_limit: int = 30,
        data_dir: str = None
    ):
        """
        Initialize token bucket rate limiter.
        
        Args:
            capacity: Max tokens (burst allowance) - default 15
            refill_rate: Tokens per second - default 1/60 (1 per minute)
            daily_limit: Max requests per user per day - default 30
            data_dir: Directory to store user rate limit files
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.daily_limit = daily_limit
        
        if data_dir is None:
            data_dir = os.getenv('RATE_LIMIT_DIR', 'data/user_requests')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get path to user's rate limit file."""
        safe_id = user_id.replace('/', '_').replace('\\', '_')
        return self.data_dir / f"{safe_id}.json"
    
    def allow_request(self, user_id: str) -> Tuple[bool, dict]:
        """
        Check if request allowed for user.
        
        Args:
            user_id: User identifier (GUID from api.gravitycar.com)
            
        Returns:
            (allowed: bool, info: dict)
            
        info dict contains:
            - allowed: bool
            - reason: str (if denied)
            - remaining_burst: int (tokens left)
            - daily_remaining: int (requests left today)
            - retry_after: int (seconds until next token, if rate limited)
            - message: str (human-readable explanation)
        """
        user_file = self._get_user_file(user_id)
        
        try:
            # Read current state (create if doesn't exist)
            if user_file.exists():
                with open(user_file, 'r') as f:
                    # Try to acquire exclusive lock (non-blocking)
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except IOError:
                        # File is locked - concurrent request from same user
                        return False, {
                            'allowed': False,
                            'reason': 'concurrent_request',
                            'message': 'Another request is being processed. Please wait and try again.',
                            'retry_after': 1
                        }
                    
                    try:
                        data = json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            else:
                # New user - initialize
                data = {
                    'user_id': user_id,
                    'tokens': self.capacity,
                    'last_refill': time.time(),
                    'daily_count': 0,
                    'daily_reset': time.strftime('%Y-%m-%d')
                }
            
            # Process rate limit logic
            now = time.time()
            today = time.strftime('%Y-%m-%d')
            
            # Reset daily counter if new day
            if data['daily_reset'] != today:
                data['daily_count'] = 0
                data['daily_reset'] = today
                data['tokens'] = self.capacity
                data['last_refill'] = now
            
            # Check daily limit first
            if data['daily_count'] >= self.daily_limit:
                return False, {
                    'allowed': False,
                    'reason': 'daily_limit_exceeded',
                    'daily_remaining': 0,
                    'retry_after': None,
                    'message': f'Daily limit of {self.daily_limit} requests exceeded. Try again tomorrow.'
                }
            
            # Refill tokens based on elapsed time
            elapsed = now - data['last_refill']
            refill_amount = elapsed * self.refill_rate
            data['tokens'] = min(self.capacity, data['tokens'] + refill_amount)
            data['last_refill'] = now
            
            # Check token availability
            if data['tokens'] >= 1.0:
                data['tokens'] -= 1.0
                data['daily_count'] += 1
                
                # Write updated state with exclusive lock
                with open(user_file, 'w') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(data, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                return True, {
                    'allowed': True,
                    'remaining_burst': int(data['tokens']),
                    'daily_remaining': self.daily_limit - data['daily_count'],
                    'retry_after': None
                }
            else:
                # Rate limited - calculate wait time
                tokens_needed = 1.0 - data['tokens']
                retry_after = int(tokens_needed / self.refill_rate)
                
                return False, {
                    'allowed': False,
                    'reason': 'rate_limited',
                    'remaining_burst': 0,
                    'daily_remaining': self.daily_limit - data['daily_count'],
                    'retry_after': retry_after,
                    'message': f'Rate limit exceeded. Please wait {retry_after} seconds.'
                }
        
        except Exception as e:
            # Fail closed on any error (deny request)
            return False, {
                'allowed': False,
                'reason': 'system_error',
                'message': f'Rate limiting system error: {str(e)}',
                'retry_after': 5
            }
```

**Validation**:
```bash
# Test import
python -c "from src.utils.rate_limiter import TokenBucket; print('✅ Import success')"

# Test basic functionality
python -c "
from src.utils.rate_limiter import TokenBucket
limiter = TokenBucket(capacity=15, refill_rate=1/60, daily_limit=30)
allowed, info = limiter.allow_request('test-user-123')
print(f'✅ TokenBucket working: allowed={allowed}, info={info}')
"

# Check file created
ls -l data/user_requests/
```

#### Task 1.3: CostTracker Class (30 min)

**File**: `src/utils/cost_tracker.py`

**Code**:
```python
#!/usr/bin/env python3
"""
OpenAI API cost tracker with daily budget enforcement and email alerts.

Tracks costs in-memory (resets on app restart), triggers alerts at
80% and 100% of daily budget.
"""

import time
from threading import Lock
from typing import Dict, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class CostTracker:
    """Track OpenAI API costs with daily budget limit and email alerts."""
    
    # OpenAI pricing per 1M tokens (as of November 2025)
    # Source: https://openai.com/pricing
    # Note: Update these when OpenAI changes pricing
    PRICING = {
        'gpt-4o-mini': {
            'input': 0.15,   # $0.15 per 1M input tokens
            'output': 0.60   # $0.60 per 1M output tokens
        },
        'gpt-4o': {
            'input': 2.50,   # $2.50 per 1M input tokens
            'output': 10.00  # $10.00 per 1M output tokens
        },
        'gpt-4-turbo': {
            'input': 10.00,  # $10.00 per 1M input tokens
            'output': 30.00  # $30.00 per 1M output tokens
        },
        'gpt-4': {
            'input': 30.00,  # $30.00 per 1M input tokens
            'output': 60.00  # $60.00 per 1M output tokens
        },
        'gpt-3.5-turbo': {
            'input': 0.50,   # $0.50 per 1M input tokens
            'output': 1.50   # $1.50 per 1M output tokens
        }
    }
    
    def __init__(self, daily_budget_usd: float = 1.0, alert_email: str = None, model: str = 'gpt-4o-mini'):
        """
        Initialize cost tracker.
        
        Args:
            daily_budget_usd: Maximum daily spend in USD
            alert_email: Email address for alerts (from .env)
            model: OpenAI model name (for pricing lookup)
        """
        self.daily_budget = daily_budget_usd
        self.alert_email = alert_email
        self.model = model
        self.current_day = time.strftime('%Y-%m-%d')
        self.daily_cost = 0.0
        self.user_costs: Dict[str, float] = {}
        self.alert_80_sent = False
        self.lock = Lock()
        
        # Validate model pricing is available
        if model not in self.PRICING:
            available = ', '.join(self.PRICING.keys())
            raise ValueError(f"Unknown model '{model}'. Available: {available}")
    
    def record_query(self, user_id: str, embedding_tokens: int, completion_tokens: int) -> dict:
        """
        Record cost of a query.
        
        Args:
            user_id: User identifier
            embedding_tokens: Tokens used for embedding
            completion_tokens: Tokens used for completion
            
        Returns:
            dict with cost details and alert status
        """
        with self.lock:
            # Reset if new day
            today = time.strftime('%Y-%m-%d')
            if today != self.current_day:
                self.current_day = today
                self.daily_cost = 0.0
                self.user_costs = {}
                self.alert_80_sent = False
            
            # Get pricing for current model
            pricing = self.PRICING.get(self.model)
            if not pricing:
                # Fallback to gpt-4o-mini pricing if model not found
                pricing = self.PRICING['gpt-4o-mini']
                print(f"Warning: No pricing for model '{self.model}', using gpt-4o-mini rates")
            
            # Calculate cost using model-specific pricing
            # Note: prompt_tokens = input to GPT (context + question)
            #       completion_tokens = output from GPT (the answer)
            # Embedding API costs are negligible (query is short, ~$0.02 per 1M tokens)
            input_cost = (embedding_tokens / 1_000_000) * pricing['input']
            output_cost = (completion_tokens / 1_000_000) * pricing['output']
            query_cost = input_cost + output_cost
            
            # Update totals
            self.daily_cost += query_cost
            self.user_costs[user_id] = self.user_costs.get(user_id, 0.0) + query_cost
            
            # Check alert thresholds
            budget_percentage = (self.daily_cost / self.daily_budget) * 100
            
            result = {
                'query_cost': round(query_cost, 6),
                'daily_cost': round(self.daily_cost, 4),
                'daily_budget': self.daily_budget,
                'remaining': round(self.daily_budget - self.daily_cost, 4),
                'percentage': round(budget_percentage, 1)
            }
            
            # Send 80% warning (once per day)
            if budget_percentage >= 80 and not self.alert_80_sent:
                self._send_alert('warning', result)
                self.alert_80_sent = True
            
            # Send 100% critical alert (every time)
            if budget_percentage >= 100:
                self._send_alert('critical', result)
            
            return result
    
    def is_budget_exceeded(self) -> Tuple[bool, dict]:
        """Check if daily budget exceeded."""
        with self.lock:
            exceeded = self.daily_cost >= self.daily_budget
            return exceeded, {
                'daily_cost': round(self.daily_cost, 4),
                'daily_budget': self.daily_budget,
                'remaining': round(self.daily_budget - self.daily_cost, 4),
                'percentage': round((self.daily_cost / self.daily_budget) * 100, 1)
            }
    
    def _send_alert(self, alert_type: str, cost_info: dict):
        """Send email alert (internal method)."""
        if not self.alert_email:
            return
        
        # Get top users by cost
        top_users = sorted(self.user_costs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        if alert_type == 'warning':
            subject = f"[D&D RAG] Warning: 80% Daily Budget Consumed"
            body = f"""Daily Budget Status Report
--------------------------
Date: {time.strftime('%Y-%m-%d')}
Time: {time.strftime('%H:%M:%S UTC')}

Budget Information:
- Daily limit: ${self.daily_budget:.2f}
- Current spend: ${cost_info['daily_cost']:.4f}
- Remaining: ${cost_info['remaining']:.4f}
- Percentage: {cost_info['percentage']:.1f}%

Top Users (by cost):
"""
            for i, (user_id, cost) in enumerate(top_users, 1):
                body += f"{i}. {user_id}: ${cost:.4f}\n"
            
            body += "\nAction Required: None (informational)\nService Status: Operational"
        
        else:  # critical
            subject = f"[D&D RAG] CRITICAL: Daily Budget Exceeded"
            body = f"""CRITICAL ALERT - Service Paused
--------------------------
Date: {time.strftime('%Y-%m-%d')}
Time: {time.strftime('%H:%M:%S UTC')}

Budget Information:
- Daily limit: ${self.daily_budget:.2f}
- Current spend: ${cost_info['daily_cost']:.4f}
- Overage: ${cost_info['daily_cost'] - self.daily_budget:.4f}
- Percentage: {cost_info['percentage']:.1f}%

Top Users (by cost):
"""
            for i, (user_id, cost) in enumerate(top_users, 1):
                body += f"{i}. {user_id}: ${cost:.4f}\n"
            
            body += "\nAction Required: Review usage patterns\nService Status: HTTP 503 (Service Unavailable)"
        
        try:
            self._send_email(subject, body)
        except Exception as e:
            # Don't crash app if email fails
            print(f"Warning: Failed to send alert email: {e}")
    
    def _send_email(self, subject: str, body: str):
        """Send email via SMTP (requires SMTP config in .env)."""
        smtp_host = os.getenv('SMTP_HOST', 'localhost')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASS')
        from_email = os.getenv('SMTP_FROM', 'dnd-rag@yourdomain.com')
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = self.alert_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)
```

**Important Notes**:
1. **Pricing Updates**: When OpenAI changes pricing, update the `PRICING` dictionary in the `CostTracker` class
2. **Model Changes**: To change models, update `OPENAI_MODEL` in `.env` (pricing will automatically adjust)
3. **Unknown Models**: If model not in PRICING dict, falls back to gpt-4o-mini rates with warning
4. **Pricing Source**: Always verify rates at https://openai.com/pricing before updating

**Validation**:
```bash
# Test import
python -c "from src.utils.cost_tracker import CostTracker; print('✅ Import success')"

# Test basic functionality with gpt-4o-mini (no email)
python -c "
from src.utils.cost_tracker import CostTracker
tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
info = tracker.record_query('test-user', embedding_tokens=100, completion_tokens=500)
print(f'✅ CostTracker working: cost={info[\"query_cost\"]}, daily={info[\"daily_cost\"]}')
print(f'   Model: gpt-4o-mini, Input: 100 tokens, Output: 500 tokens')
"

# Test with different model (gpt-4o - more expensive)
python -c "
from src.utils.cost_tracker import CostTracker
tracker_expensive = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o')
info = tracker_expensive.record_query('test-user', embedding_tokens=100, completion_tokens=500)
print(f'✅ gpt-4o pricing: cost={info[\"query_cost\"]}, daily={info[\"daily_cost\"]}')
print(f'   Should be ~16x more expensive than gpt-4o-mini')
"
```

### Step 2: Create Flask Application (2 hours)

#### Task 2.1: Create Flask App Structure (60 min)

**File**: `src/api.py`

**Code** (Part 1 - Initialization):
```python
#!/usr/bin/env python3
"""
Flask REST API for D&D 1st Edition RAG system.

Provides OAuth2-authenticated query endpoint with rate limiting
and cost tracking.
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import sys

# Import RAG system and utilities
from .query.docling_query import DnDRAG
from .utils.rag_output import RAGOutput
from .utils.token_validator import TokenValidator
from .utils.rate_limiter import TokenBucket
from .utils.cost_tracker import CostTracker
from .utils.config import get_env_float, get_env_int, get_env_string

# Note: These helpers will be added to existing src/utils/config.py

# Create Flask app
app = Flask(__name__)

# Configure CORS from environment variable
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000')
cors_origins_list = [origin.strip() for origin in cors_origins.split(',')]

CORS(app, 
     origins=cors_origins_list,
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)

# Initialize global components
token_validator = TokenValidator(
    api_base_url=os.getenv('AUTH_API_URL'),
    cache_ttl=int(os.getenv('TOKEN_CACHE_TTL', '300'))
)

rate_limiter = TokenBucket(
    capacity=get_env_int('TOKEN_BUCKET_CAPACITY', 15),
    refill_rate=get_env_float('TOKEN_REFILL_RATE', 1/60),
    daily_limit=get_env_int('DAILY_USER_REQUEST_LIMIT', 30),
    data_dir=os.getenv('RATE_LIMIT_DIR', 'data/user_requests')
)

cost_tracker = CostTracker(
    daily_budget_usd=get_env_float('DAILY_BUDGET_USD', 1.0),
    alert_email=os.getenv('ALERT_EMAIL'),
    model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # Get model from config
)

# Initialize RAG system (reused across requests)
rag = None

@app.before_first_request
def init_rag():
    """Initialize RAG system on first request."""
    global rag
    try:
        rag = DnDRAG()
        print("✅ D&D RAG system initialized")
    except Exception as e:
        print(f"❌ Failed to initialize RAG system: {e}")
        sys.exit(1)
```

**Code** (Part 2 - Helper Functions):
```python
def extract_token() -> str:
    """Extract JWT token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ', 1)[1]


def validate_user() -> dict:
    """
    Validate JWT token and return user info.
    
    Returns:
        User info dict with 'id' key
        
    Aborts with HTTP 401 if invalid token
    """
    token = extract_token()
    if not token:
        return jsonify({'error': 'Missing Authorization header'}), 401
    
    user_info = token_validator.validate(token)
    if not user_info:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    return user_info
```

**Code** (Part 3 - Endpoints):
```python
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (no auth required)."""
    return jsonify({
        'status': 'ok',
        'service': 'dnd_rag',
        'version': '1.0.0'
    }), 200


@app.route('/api/query', methods=['POST'])
def query():
    """
    Query the D&D RAG system.
    
    Requires:
        - Authorization: Bearer <jwt_token> header
        - JSON body: {"question": str, "debug": bool (optional), "k": int (optional)}
        
    Returns:
        JSON: {answer, diagnostics, errors, meta}
        HTTP 200: Success
        HTTP 400: Bad request (missing question)
        HTTP 401: Unauthorized (invalid token)
        HTTP 429: Rate limit exceeded
        HTTP 503: Budget exceeded
        HTTP 500: Internal error
    """
    # 1. Validate token
    user_info = validate_user()
    if isinstance(user_info, tuple):  # Error response
        return user_info
    
    user_id = user_info['id']
    
    # 2. Check budget
    budget_exceeded, budget_info = cost_tracker.is_budget_exceeded()
    if budget_exceeded:
        return jsonify({
            'error': 'budget_exceeded',
            'message': 'Daily budget exceeded. Service will resume at midnight UTC.',
            'budget_info': budget_info
        }), 503
    
    # 3. Check rate limit
    allowed, rate_info = rate_limiter.allow_request(user_id)
    if not allowed:
        response = jsonify({
            'error': rate_info['reason'],
            'message': rate_info['message'],
            'rate_info': {
                'daily_remaining': rate_info.get('daily_remaining'),
                'retry_after': rate_info.get('retry_after')
            }
        })
        response.status_code = 429
        
        if rate_info.get('retry_after'):
            response.headers['Retry-After'] = str(rate_info['retry_after'])
        
        return response
    
    # 4. Parse request
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing JSON body'}), 400
        
        question = data.get('question')
        if not question:
            return jsonify({'error': 'Missing required field: question'}), 400
        
        debug = data.get('debug', False)
        k = data.get('k', 15)
        
    except Exception as e:
        return jsonify({'error': 'Invalid JSON', 'details': str(e)}), 400
    
    # 5. Execute query
    try:
        # Create fresh output buffer
        rag.output = RAGOutput()
        
        result = rag.query(question, k=k, debug=debug)
        
        # Extract token counts from OpenAI response
        # Note: DnDRAG.query() needs to be updated to return usage info
        # in the result dict under result['usage']
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        
        # 6. Record costs
        cost_info = cost_tracker.record_query(user_id, prompt_tokens, completion_tokens)
        
        # 7. Add metadata to response
        result['meta'] = {
            'user_id': user_id,
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


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # For local development only
    app.run(debug=True, host='0.0.0.0', port=5000)
```

**Validation**:
```bash
# Test Flask starts locally
export FLASK_APP=src.api
python -m flask run --port 5000

# In another terminal, test health endpoint
curl http://localhost:5000/health
# Expected: {"status":"ok","service":"dnd_rag","version":"1.0.0"}
```

#### Task 2.1b: Update DnDRAG to Return Token Usage (15 min)

**CRITICAL**: The Flask API needs actual token counts from OpenAI, not estimates!

**Problem**: Currently `DnDRAG.query()` only returns the answer. OpenAI provides token usage in the response object (`response.usage`), but we're not capturing it.

**Solution**: Update `src/query/docling_query.py` to:
1. Capture token usage from OpenAI response in `generate()` method
2. Store usage in output buffer
3. Include usage in `query()` return dict

**File**: `src/query/docling_query.py`

**Changes Required**:

1. **Update `generate()` method** (around line 600):

```python
# BEFORE (current code):
def generate(self, query: str, context: str, max_tokens: int = 800):
    # ... system_prompt and user_prompt code ...
    
    response = self.openai_client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.1
    )
    
    return response.choices[0].message.content

# AFTER (new code):
def generate(self, query: str, context: str, max_tokens: int = 800):
    # ... system_prompt and user_prompt code ...
    
    response = self.openai_client.chat.completions.create(
        model=self.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.1
    )
    
    # Return both content and token usage
    return {
        'content': response.choices[0].message.content,
        'usage': {
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'total_tokens': response.usage.total_tokens
        }
    }
```

2. **Update `query()` method** (around line 690):

```python
# BEFORE (current code):
answer = self.generate(question, context)

self.output.info(f"\n{'='*80}")
self.output.info("ANSWER:")
self.output.info(f"{'='*80}")
self.output.info(answer)
self.output.info(f"{'='*80}\n")

self.output.set_answer(answer)
return self.output.to_dict()

# AFTER (new code):
generation_result = self.generate(question, context)
answer = generation_result['content']
usage = generation_result['usage']

self.output.info(f"\n{'='*80}")
self.output.info("ANSWER:")
self.output.info(f"{'='*80}")
self.output.info(answer)
self.output.info(f"{'='*80}\n")

# Store answer and usage
self.output.set_answer(answer)
result_dict = self.output.to_dict()
result_dict['usage'] = usage  # Add usage to output

return result_dict
```

**Why This Matters**:
- **Accurate cost tracking**: Actual token counts vs rough estimates
- **Budget enforcement**: Real costs prevent unexpected overruns
- **Usage analytics**: Track which queries are expensive
- **Debugging**: See exact token consumption per query

**Validation**:
```bash
# Test that usage is returned
python -c "
from src.query.docling_query import DnDRAG
from src.utils.rag_output import RAGOutput

rag = DnDRAG(collection_name='dnd_monster_manual', output=RAGOutput())
result = rag.query('What is a beholder?', k=5)

# Check for usage in result
if 'usage' in result:
    print(f'✅ Token usage captured: {result[\"usage\"]}')
else:
    print('❌ ERROR: No usage in result')
"
```

#### Task 2.2: Update .env Configuration (15 min)

**File**: `.env` (update existing file)

Add these lines:

**For Local Development** (`.env` or `.env.local`):
```bash
# Environment
FLASK_ENV=development

# OAuth2 Configuration (LOCAL)
AUTH_API_URL=http://localhost:8081
TOKEN_CACHE_TTL=300

# CORS Configuration (LOCAL)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Rate Limiting
RATE_LIMIT_DIR=data/user_requests
TOKEN_BUCKET_CAPACITY=15
TOKEN_REFILL_RATE=0.016667
DAILY_USER_REQUEST_LIMIT=30

# OpenAI Configuration
OPENAI_MODEL=gpt-4o-mini

# Cost Tracking
DAILY_BUDGET_USD=1.00
ALERT_EMAIL=your-email@example.com

# Email Configuration (optional - for alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=dnd-rag@yourdomain.com
```

**For Production** (`.env.production`):
```bash
# Environment
FLASK_ENV=production

# OAuth2 Configuration (PRODUCTION)
AUTH_API_URL=https://api.gravitycar.com
TOKEN_CACHE_TTL=300

# CORS Configuration (PRODUCTION)
CORS_ORIGINS=https://react.gravitycar.com,https://www.gravitycar.com

# Rate Limiting
RATE_LIMIT_DIR=data/user_requests
TOKEN_BUCKET_CAPACITY=15
TOKEN_REFILL_RATE=0.016667
DAILY_USER_REQUEST_LIMIT=30

# OpenAI Configuration
OPENAI_MODEL=gpt-4o-mini

# Cost Tracking
DAILY_BUDGET_USD=1.00
ALERT_EMAIL=your-production-email@example.com

# Email Configuration (optional - for alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-gmail@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=dnd-rag@gravitycar.com
```

**Note**: In production, copy `.env.production` to `.env` or set environment variables directly in Apache.

**Validation**:
```bash
# Verify .env loads correctly
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print(f'FLASK_ENV: {os.getenv(\"FLASK_ENV\")}')
print(f'AUTH_API_URL: {os.getenv(\"AUTH_API_URL\")}')
print(f'CORS_ORIGINS: {os.getenv(\"CORS_ORIGINS\")}')
print(f'TOKEN_BUCKET_CAPACITY: {os.getenv(\"TOKEN_BUCKET_CAPACITY\")}')
print(f'DAILY_BUDGET_USD: {os.getenv(\"DAILY_BUDGET_USD\")}')
print('✅ .env configuration loaded')
"

# Expected output (local):
# FLASK_ENV: development
# AUTH_API_URL: http://localhost:8081
# CORS_ORIGINS: http://localhost:3000,http://localhost:3001
# ...
```

#### Task 2.3: Update Config Module with Type-Safe Helpers (15 min)

**File**: `src/utils/config.py` (add to existing ConfigManager class)

**Note**: We already have a `ConfigManager` class in `src/utils/config.py`. Add these type-safe helper methods to the existing class.

**Changes Required**:

Add these new methods to the `ConfigManager` class (after existing methods, before the global singleton):

```python
    def get_env_string(self, key: str, default: str = None) -> str:
        """
        Get string environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            str: Environment variable value or default
        """
        return os.getenv(key, default)
    
    def get_env_int(self, key: str, default: int) -> int:
        """
        Get integer environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            int: Environment variable value or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            print(f"Warning: Invalid integer value for {key}, using default {default}")
            return default
    
    def get_env_float(self, key: str, default: float) -> float:
        """
        Get float environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            float: Environment variable value or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            print(f"Warning: Invalid float value for {key}, using default {default}")
            return default
    
    def get_env_bool(self, key: str, default: bool) -> bool:
        """
        Get boolean environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            bool: True if value is 'true', '1', 'yes', 'on' (case-insensitive)
        """
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
```

**Also add convenience functions** (after existing convenience functions):

```python
def get_env_string(key: str, default: str = None) -> str:
    """Convenience function for getting string environment variable."""
    return config.get_env_string(key, default)


def get_env_int(key: str, default: int) -> int:
    """Convenience function for getting integer environment variable."""
    return config.get_env_int(key, default)


def get_env_float(key: str, default: float) -> float:
    """Convenience function for getting float environment variable."""
    return config.get_env_float(key, default)


def get_env_bool(key: str, default: bool) -> bool:
    """Convenience function for getting boolean environment variable."""
    return config.get_env_bool(key, default)
```

**Usage in Flask API** (`src/api.py`):

```python
from .utils.config import get_env_float, get_env_int, get_env_string

# Instead of direct os.getenv calls, use type-safe helpers:
rate_limiter = TokenBucket(
    capacity=get_env_int('TOKEN_BUCKET_CAPACITY', 15),
    refill_rate=get_env_float('TOKEN_REFILL_RATE', 1/60),
    daily_limit=get_env_int('DAILY_USER_REQUEST_LIMIT', 30),
    data_dir=get_env_string('RATE_LIMIT_DIR', 'data/user_requests')
)

cost_tracker = CostTracker(
    daily_budget_usd=get_env_float('DAILY_BUDGET_USD', 1.0),
    alert_email=get_env_string('ALERT_EMAIL'),
    model=get_env_string('OPENAI_MODEL', 'gpt-4o-mini')
)
```

**Validation**:
```bash
# Test the new methods
python -c "
from src.utils.config import config
from dotenv import load_dotenv

load_dotenv()

# Test type-safe getters
print(f'✅ String: {config.get_env_string(\"FLASK_ENV\", \"development\")}')
print(f'✅ Int: {config.get_env_int(\"TOKEN_BUCKET_CAPACITY\", 15)}')
print(f'✅ Float: {config.get_env_float(\"DAILY_BUDGET_USD\", 1.0)}')
print(f'✅ Bool: {config.get_env_bool(\"DEBUG\", False)}')
"
```

### Step 3: Install Dependencies (15 min)

**Task 3.1**: Update requirements.txt

```bash
# Add to requirements.txt
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
```

**Task 3.2**: Install dependencies

```bash
source venv/bin/activate
pip install flask flask-cors requests
pip freeze > requirements.txt
```

### Step 4: Unit Tests (2 hours)

**Critical**: Unit tests ensure security, cost control, and reliability before deployment.

#### Task 4.1: TokenValidator Unit Tests (30 min)

**File**: `tests/test_token_validator.py`

```python
#!/usr/bin/env python3
"""Unit tests for TokenValidator."""

import pytest
import time
from unittest.mock import Mock, patch
from src.utils.token_validator import TokenValidator


class TestTokenValidator:
    """Test OAuth2 token validation with caching."""
    
    def test_valid_token_success(self):
        """Test validation with valid token."""
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'id': 'user-123',
                'email': 'test@example.com'
            }
        }
        
        with patch('requests.get', return_value=mock_response):
            user_info = validator.validate('fake-token')
        
        assert user_info is not None
        assert user_info['id'] == 'user-123'
        assert user_info['email'] == 'test@example.com'
    
    def test_invalid_token_returns_none(self):
        """Test validation with invalid token."""
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('requests.get', return_value=mock_response):
            user_info = validator.validate('invalid-token')
        
        assert user_info is None
    
    def test_cache_hit_no_api_call(self):
        """Test that cached tokens don't make API calls."""
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        # First call - cache miss
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'id': 'user-123', 'email': 'test@example.com'}
        }
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            validator.validate('token-abc')
            assert mock_get.call_count == 1
            
            # Second call - cache hit (no API call)
            validator.validate('token-abc')
            assert mock_get.call_count == 1  # Still 1, not 2
    
    def test_cache_expiration(self):
        """Test that expired cache entries are removed."""
        validator = TokenValidator('https://api.example.com', cache_ttl=1)  # 1 second TTL
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'id': 'user-123'}
        }
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # First call
            validator.validate('token-abc')
            assert mock_get.call_count == 1
            
            # Wait for cache to expire
            time.sleep(1.5)
            
            # Second call - cache expired, should make API call
            validator.validate('token-abc')
            assert mock_get.call_count == 2
    
    def test_api_timeout_returns_none(self):
        """Test that API timeouts fail gracefully."""
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        with patch('requests.get', side_effect=Exception('Connection timeout')):
            user_info = validator.validate('token-abc')
        
        assert user_info is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

#### Task 4.2: TokenBucket Unit Tests (45 min)

**File**: `tests/test_rate_limiter.py`

```python
#!/usr/bin/env python3
"""Unit tests for TokenBucket rate limiter."""

import pytest
import time
import json
import tempfile
from pathlib import Path
from src.utils.rate_limiter import TokenBucket


class TestTokenBucket:
    """Test token bucket rate limiting."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for rate limit files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_first_request_allowed(self, temp_dir):
        """Test that first request is allowed."""
        limiter = TokenBucket(capacity=15, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        allowed, info = limiter.allow_request('user-123')
        
        assert allowed is True
        assert info['allowed'] is True
        assert info['remaining_burst'] == 14  # Started with 15, used 1
        assert info['daily_remaining'] == 29  # Started with 30, used 1
    
    def test_burst_capacity_exhaustion(self, temp_dir):
        """Test that burst capacity is enforced."""
        limiter = TokenBucket(capacity=3, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        
        # Use all 3 tokens
        for i in range(3):
            allowed, info = limiter.allow_request('user-123')
            assert allowed is True
        
        # 4th request should fail
        allowed, info = limiter.allow_request('user-123')
        assert allowed is False
        assert info['reason'] == 'rate_limited'
        assert 'retry_after' in info
    
    def test_token_refill(self, temp_dir):
        """Test that tokens refill over time."""
        limiter = TokenBucket(capacity=5, refill_rate=2, daily_limit=30, data_dir=temp_dir)  # 2 tokens/sec
        
        # Use all 5 tokens
        for i in range(5):
            limiter.allow_request('user-123')
        
        # Wait for 1 token to refill (0.5 seconds)
        time.sleep(0.6)
        
        # Should succeed now
        allowed, info = limiter.allow_request('user-123')
        assert allowed is True
    
    def test_daily_limit_enforcement(self, temp_dir):
        """Test that daily limit is enforced."""
        limiter = TokenBucket(capacity=5, refill_rate=10, daily_limit=3, data_dir=temp_dir)
        
        # Use 3 requests (daily limit)
        for i in range(3):
            allowed, info = limiter.allow_request('user-123')
            assert allowed is True
        
        # 4th request should fail with daily_limit_exceeded
        allowed, info = limiter.allow_request('user-123')
        assert allowed is False
        assert info['reason'] == 'daily_limit_exceeded'
        assert info['daily_remaining'] == 0
    
    def test_daily_reset(self, temp_dir):
        """Test that daily counter resets on new day."""
        limiter = TokenBucket(capacity=5, refill_rate=1, daily_limit=3, data_dir=temp_dir)
        
        # Use all daily requests
        for i in range(3):
            limiter.allow_request('user-123')
        
        # Manually update the file to previous day
        user_file = Path(temp_dir) / 'user-123.json'
        with open(user_file, 'r') as f:
            data = json.load(f)
        
        data['daily_reset'] = '2020-01-01'  # Old date
        
        with open(user_file, 'w') as f:
            json.dump(data, f)
        
        # Next request should succeed (new day)
        allowed, info = limiter.allow_request('user-123')
        assert allowed is True
        assert info['daily_remaining'] == 2  # Reset to daily limit - 1
    
    def test_per_user_isolation(self, temp_dir):
        """Test that users have independent rate limits."""
        limiter = TokenBucket(capacity=2, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        
        # User 1 exhausts their tokens
        limiter.allow_request('user-1')
        limiter.allow_request('user-1')
        allowed, _ = limiter.allow_request('user-1')
        assert allowed is False
        
        # User 2 should still have tokens
        allowed, info = limiter.allow_request('user-2')
        assert allowed is True
        assert info['remaining_burst'] == 1
    
    def test_file_creation(self, temp_dir):
        """Test that user rate limit files are created."""
        limiter = TokenBucket(capacity=15, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        limiter.allow_request('user-abc')
        
        user_file = Path(temp_dir) / 'user-abc.json'
        assert user_file.exists()
        
        with open(user_file, 'r') as f:
            data = json.load(f)
        
        assert data['user_id'] == 'user-abc'
        assert 'tokens' in data
        assert 'daily_count' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

#### Task 4.3: CostTracker Unit Tests (45 min)

**File**: `tests/test_cost_tracker.py`

```python
#!/usr/bin/env python3
"""Unit tests for CostTracker."""

import pytest
from unittest.mock import Mock, patch
from src.utils.cost_tracker import CostTracker


class TestCostTracker:
    """Test OpenAI cost tracking and budget enforcement."""
    
    def test_cost_calculation_gpt4o_mini(self):
        """Test cost calculation for gpt-4o-mini."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        # 1000 input tokens, 500 output tokens
        info = tracker.record_query('user-123', embedding_tokens=1000, completion_tokens=500)
        
        # Expected: (1000/1M * $0.15) + (500/1M * $0.60) = $0.00015 + $0.0003 = $0.00045
        expected_cost = (1000 / 1_000_000 * 0.15) + (500 / 1_000_000 * 0.60)
        assert abs(info['query_cost'] - expected_cost) < 0.000001
    
    def test_cost_calculation_gpt4o(self):
        """Test cost calculation for gpt-4o (more expensive)."""
        tracker = CostTracker(daily_budget_usd=10.0, alert_email=None, model='gpt-4o')
        
        # 1000 input tokens, 500 output tokens
        info = tracker.record_query('user-123', embedding_tokens=1000, completion_tokens=500)
        
        # Expected: (1000/1M * $2.50) + (500/1M * $10.00) = $0.0025 + $0.005 = $0.0075
        expected_cost = (1000 / 1_000_000 * 2.50) + (500 / 1_000_000 * 10.00)
        assert abs(info['query_cost'] - expected_cost) < 0.000001
    
    def test_unknown_model_fallback(self):
        """Test that unknown models fall back to gpt-4o-mini pricing."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='unknown-model')
        
        # Should use gpt-4o-mini pricing
        info = tracker.record_query('user-123', embedding_tokens=1000, completion_tokens=500)
        
        expected_cost = (1000 / 1_000_000 * 0.15) + (500 / 1_000_000 * 0.60)
        assert abs(info['query_cost'] - expected_cost) < 0.000001
    
    def test_daily_cost_accumulation(self):
        """Test that daily costs accumulate correctly."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        # First query
        info1 = tracker.record_query('user-123', embedding_tokens=1000, completion_tokens=500)
        cost1 = info1['query_cost']
        
        # Second query
        info2 = tracker.record_query('user-456', embedding_tokens=2000, completion_tokens=1000)
        cost2 = info2['query_cost']
        
        # Daily total should be sum of both
        assert abs(info2['daily_cost'] - (cost1 + cost2)) < 0.000001
    
    def test_budget_not_exceeded_initially(self):
        """Test that budget is not exceeded initially."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        exceeded, info = tracker.is_budget_exceeded()
        
        assert exceeded is False
        assert info['daily_cost'] == 0.0
        assert info['remaining'] == 1.0
    
    def test_budget_exceeded_detection(self):
        """Test that budget exceeded is detected."""
        tracker = CostTracker(daily_budget_usd=0.01, alert_email=None, model='gpt-4o-mini')
        
        # Record expensive queries (inflated token counts)
        for i in range(10):
            tracker.record_query(f'user-{i}', embedding_tokens=10000, completion_tokens=50000)
        
        exceeded, info = tracker.is_budget_exceeded()
        
        assert exceeded is True
        assert info['daily_cost'] > info['daily_budget']
        assert info['percentage'] > 100
    
    def test_per_user_cost_tracking(self):
        """Test that per-user costs are tracked."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        # User 1 makes 2 queries
        tracker.record_query('user-1', embedding_tokens=1000, completion_tokens=500)
        tracker.record_query('user-1', embedding_tokens=1000, completion_tokens=500)
        
        # User 2 makes 1 query
        tracker.record_query('user-2', embedding_tokens=1000, completion_tokens=500)
        
        # Check user_costs dict
        assert 'user-1' in tracker.user_costs
        assert 'user-2' in tracker.user_costs
        assert tracker.user_costs['user-1'] > tracker.user_costs['user-2']
    
    def test_80_percent_alert_triggered(self):
        """Test that 80% warning alert is triggered once."""
        mock_send = Mock()
        
        tracker = CostTracker(daily_budget_usd=0.01, alert_email='test@example.com', model='gpt-4o-mini')
        tracker._send_email = mock_send
        
        # Record queries to hit 80%
        for i in range(5):
            tracker.record_query(f'user-{i}', embedding_tokens=2000, completion_tokens=8000)
            
            if tracker.daily_cost >= 0.008:  # 80% of $0.01
                break
        
        # Should have sent warning email (once)
        assert mock_send.call_count >= 1
        assert 'Warning' in mock_send.call_args[0][0]
    
    def test_100_percent_alert_triggered(self):
        """Test that 100% critical alert is triggered."""
        mock_send = Mock()
        
        tracker = CostTracker(daily_budget_usd=0.01, alert_email='test@example.com', model='gpt-4o-mini')
        tracker._send_email = mock_send
        
        # Record queries to exceed budget
        for i in range(10):
            tracker.record_query(f'user-{i}', embedding_tokens=2000, completion_tokens=8000)
        
        # Should have sent critical email
        assert mock_send.call_count >= 1
        assert 'CRITICAL' in str(mock_send.call_args)


if __name == '__main__':
    pytest.main([__file__, '-v'])
```

#### Task 4.4: Config Helper Unit Tests (30 min)

**File**: `tests/test_config_helpers.py`

```python
#!/usr/bin/env python3
"""Unit tests for config helper functions."""

import pytest
import os
from src.utils.config import ConfigManager


class TestConfigHelpers:
    """Test type-safe environment variable helpers."""
    
    def test_get_env_string_returns_value(self):
        """Test getting string environment variable."""
        os.environ['TEST_STRING'] = 'hello'
        config = ConfigManager()
        
        result = config.get_env_string('TEST_STRING')
        assert result == 'hello'
        
        del os.environ['TEST_STRING']
    
    def test_get_env_string_returns_default(self):
        """Test string default when not found."""
        config = ConfigManager()
        result = config.get_env_string('NONEXISTENT_VAR', 'default_value')
        assert result == 'default_value'
    
    def test_get_env_int_returns_value(self):
        """Test getting integer environment variable."""
        os.environ['TEST_INT'] = '42'
        config = ConfigManager()
        
        result = config.get_env_int('TEST_INT', 0)
        assert result == 42
        assert isinstance(result, int)
        
        del os.environ['TEST_INT']
    
    def test_get_env_int_invalid_returns_default(self):
        """Test integer default when value is invalid."""
        os.environ['TEST_INT'] = 'not_a_number'
        config = ConfigManager()
        
        result = config.get_env_int('TEST_INT', 99)
        assert result == 99
        
        del os.environ['TEST_INT']
    
    def test_get_env_float_returns_value(self):
        """Test getting float environment variable."""
        os.environ['TEST_FLOAT'] = '3.14'
        config = ConfigManager()
        
        result = config.get_env_float('TEST_FLOAT', 0.0)
        assert abs(result - 3.14) < 0.001
        assert isinstance(result, float)
        
        del os.environ['TEST_FLOAT']
    
    def test_get_env_float_invalid_returns_default(self):
        """Test float default when value is invalid."""
        os.environ['TEST_FLOAT'] = 'not_a_float'
        config = ConfigManager()
        
        result = config.get_env_float('TEST_FLOAT', 1.5)
        assert result == 1.5
        
        del os.environ['TEST_FLOAT']
    
    def test_get_env_bool_true_values(self):
        """Test boolean true values."""
        config = ConfigManager()
        
        for true_val in ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']:
            os.environ['TEST_BOOL'] = true_val
            result = config.get_env_bool('TEST_BOOL', False)
            assert result is True, f"Failed for value: {true_val}"
        
        del os.environ['TEST_BOOL']
    
    def test_get_env_bool_false_values(self):
        """Test boolean false values."""
        config = ConfigManager()
        
        for false_val in ['false', 'False', '0', 'no', 'off', 'anything_else']:
            os.environ['TEST_BOOL'] = false_val
            result = config.get_env_bool('TEST_BOOL', True)
            assert result is False, f"Failed for value: {false_val}"
        
        del os.environ['TEST_BOOL']
    
    def test_get_env_bool_default(self):
        """Test boolean default when not found."""
        config = ConfigManager()
        result = config.get_env_bool('NONEXISTENT_BOOL', True)
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

#### Task 4.5: Run All Unit Tests

```bash
# Run all unit tests
pytest tests/test_token_validator.py -v
pytest tests/test_rate_limiter.py -v
pytest tests/test_cost_tracker.py -v
pytest tests/test_config_helpers.py -v

# Or run all at once
pytest tests/test_token_validator.py tests/test_rate_limiter.py tests/test_cost_tracker.py tests/test_config_helpers.py -v

# Expected: All tests pass ✅
```

**Success Criteria**:
- [ ] TokenValidator: 6 tests pass
- [ ] TokenBucket: 8 tests pass
- [ ] CostTracker: 10 tests pass
- [ ] Config Helpers: 10 tests pass
- [ ] Total: 34 unit tests pass

### Step 5: Integration Testing (2 hours)

#### Integration Test 1: Health Check (5 min)

```bash
# Start Flask
export FLASK_APP=src.api
python -m flask run --port 5000

# Test health endpoint
curl http://localhost:5000/health

# Expected:
# {"status":"ok","service":"dnd_rag","version":"1.0.0"}
```

#### Integration Test 2: Token Validation (15 min)

**Requires**: Real JWT token from api.gravitycar.com

```bash
# Get token from api.gravitycar.com (login via browser, copy token from localStorage)
TOKEN="your-jwt-token-here"

# Test with valid token
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "What is a beholder?"}'

# Expected: HTTP 200 with answer

# Test with invalid token
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token" \
  -d '{"question": "What is a beholder?"}'

# Expected: HTTP 401 Unauthorized
```

#### Integration Test 3: Rate Limiting - Burst Capacity (15 min)

```bash
# Test burst allowance (should succeed for first 15 requests)
TOKEN="your-jwt-token-here"

for i in {1..15}; do
  echo "Request $i:"
  curl -X POST http://localhost:5000/api/query \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"question\": \"Test query $i\"}" \
    -w "\nHTTP Status: %{http_code}\n\n" &
done

wait

# Expected: All 15 requests succeed (HTTP 200)
# Check file: cat data/user_requests/<your-guid>.json
# Should show tokens ≈ 0
```

#### Integration Test 4: Rate Limiting - Throttle (15 min)

```bash
# 16th request should fail (no tokens left)
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "Test query 16"}' \
  -w "\nHTTP Status: %{http_code}\n"

# Expected: HTTP 429 with retry_after in response

# Wait 60 seconds, then retry (should succeed)
sleep 60

curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "Test query 17"}' \
  -w "\nHTTP Status: %{http_code}\n"

# Expected: HTTP 200 (token refilled)
```

#### Integration Test 5: Daily Limit (15 min)

**Note**: This test requires modifying the daily limit temporarily

```bash
# Temporarily set daily limit to 5 in .env
# DAILY_USER_REQUEST_LIMIT=5

# Restart Flask, make 5 requests
for i in {1..5}; do
  curl -X POST http://localhost:5000/api/query \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"question\": \"Test $i\"}" \
    -w "\nHTTP Status: %{http_code}\n"
  sleep 12  # Wait for token refill
done

# 6th request should fail
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "Test 6"}' \
  -w "\nHTTP Status: %{http_code}\n"

# Expected: HTTP 429 with reason: 'daily_limit_exceeded'

# Restore DAILY_USER_REQUEST_LIMIT=30 in .env
```

#### Integration Test 6: Budget Enforcement (15 min)

**Note**: This test uses mock costs to trigger budget limit

```python
# test_budget_limit.py
from src.utils.cost_tracker import CostTracker

# Create tracker with low budget
tracker = CostTracker(daily_budget_usd=0.01, alert_email=None)

# Simulate 10 expensive queries
for i in range(10):
    info = tracker.record_query(
        f'user_{i}',
        embedding_tokens=10000,  # Inflated
        completion_tokens=50000   # Inflated
    )
    print(f"Query {i+1}: ${info['daily_cost']:.4f}/${info['daily_budget']:.2f}")
    
    exceeded, budget_info = tracker.is_budget_exceeded()
    if exceeded:
        print("❌ Budget exceeded!")
        break
```

Run:
```bash
python test_budget_limit.py

# Expected output shows budget exceeded after ~2-3 queries
```

#### Integration Test 7: CORS (15 min)

**Note**: CORS origins depend on your `.env` configuration.

**Local Development** (with `CORS_ORIGINS=http://localhost:3000`):
```bash
# Test from allowed origin (local React dev server)
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000" \
  -d '{"question": "What is a beholder?"}' \
  -v

# Check response headers for:
# Access-Control-Allow-Origin: http://localhost:3000

# Test from disallowed origin
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://evil.com" \
  -d '{"question": "What is a beholder?"}' \
  -v

# Expected: No Access-Control-Allow-Origin header (browser would block)
```

**Production** (with `CORS_ORIGINS=https://react.gravitycar.com`):
```bash
# Test from production origin
curl -X POST https://dndchat.gravitycar.com/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://react.gravitycar.com" \
  -d '{"question": "What is a beholder?"}' \
  -v

# Check response headers for:
# Access-Control-Allow-Origin: https://react.gravitycar.com
```

#### Integration Test 8: Debug Mode (10 min)

```bash
# Test with debug=true
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "What is a beholder?", "debug": true}' | jq .

# Expected: Response includes 'diagnostics' array with execution details
```

### Step 6: Documentation (30 min)

#### Task 6.1: Create API Documentation

**File**: `docs/api/REST_API.md`

```markdown
# D&D RAG REST API Documentation

## Base URLs

### Local Development
- **Flask API**: `http://localhost:5000`
- **React UI**: `http://localhost:3000`
- **PHP Auth API**: `http://localhost:8081`

### Production
- **Flask API**: `https://dndchat.gravitycar.com`
- **React UI**: `https://react.gravitycar.com`
- **PHP Auth API**: `https://api.gravitycar.com`

## Authentication
All endpoints except `/health` require OAuth2 JWT token:

```
Authorization: Bearer <jwt_token>
```

**Token Source**:
- **Local**: Obtain from `http://localhost:8081` (PHP API)
- **Production**: Obtain from `https://api.gravitycar.com` via Google OAuth

## Endpoints

### GET /health
Health check endpoint.

**No authentication required**

**Response**:
```json
{
  "status": "ok",
  "service": "dnd_rag",
  "version": "1.0.0"
}
```

### POST /api/query
Query the D&D RAG system.

**Authentication required**

**Request Body**:
```json
{
  "question": "What is a beholder?",
  "debug": false,
  "k": 15
}
```

**Response (HTTP 200)**:
```json
{
  "answer": "A beholder is a floating sphere...",
  "diagnostics": [],
  "errors": [],
  "meta": {
    "user_id": "a1b2c3d4-...",
    "rate_limit": {
      "remaining_burst": 7,
      "daily_remaining": 18
    },
    "cost": {
      "query_cost": 0.000234,
      "daily_total": 0.045678,
      "daily_budget": 1.00
    }
  }
}
```

**Error Responses**:

| Code | Reason | Response |
|------|--------|----------|
| 400 | Bad request | `{"error": "Missing required field: question"}` |
| 401 | Unauthorized | `{"error": "Invalid or expired token"}` |
| 429 | Rate limited | `{"error": "rate_limited", "message": "...", "rate_info": {...}}` |
| 503 | Budget exceeded | `{"error": "budget_exceeded", "budget_info": {...}}` |
| 500 | Internal error | `{"error": "Query processing failed", "details": "..."}` |

## Rate Limits
- **Burst**: 15 requests
- **Sustained**: 1 request per minute
- **Daily**: 30 requests per user

## CORS
Allowed origins:
- `https://react.gravitycar.com`
- `https://www.gravitycar.com`
- `http://localhost:3000` (development)

## Cost Tracking

### Current Model
- Default: `gpt-4o-mini` (configurable via `OPENAI_MODEL` env var)

### Pricing (as of November 2025)
| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4-turbo | $10.00 | $30.00 |
| gpt-4 | $30.00 | $60.00 |
| gpt-3.5-turbo | $0.50 | $1.50 |

**Note**: Pricing is configured in `src/utils/cost_tracker.py`. Update the `PRICING` dictionary when OpenAI changes rates.

### Maintenance: Updating Pricing

When OpenAI changes pricing (check https://openai.com/pricing):

1. Edit `src/utils/cost_tracker.py`
2. Update the `PRICING` dictionary in `CostTracker` class
3. Restart Flask API
4. Update this documentation

No code changes needed when switching models - just update `OPENAI_MODEL` in `.env`.
```

#### Task 6.2: Update Main README

Add to `README.md`:

```markdown
## REST API

The D&D RAG system is accessible via REST API at `https://dndchat.gravitycar.com`.

See [API Documentation](docs/api/REST_API.md) for details.

### Quick Start (Local)

```bash
# Start Flask API
export FLASK_APP=src.api
python -m flask run --port 5000

# Test health
curl http://localhost:5000/health

# Query (requires JWT token)
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "What is a beholder?"}'
```
```

---

## 5. Testing Strategy

### Unit Tests (Automated - Step 4)

**34 unit tests** covering core functionality:

1. **TokenValidator** (6 tests):
   - Valid token success
   - Invalid token returns None
   - Cache hit avoids API call
   - Cache expiration
   - API timeout handling
   - Concurrent request handling

2. **TokenBucket** (8 tests):
   - First request allowed
   - Burst capacity exhaustion
   - Token refill over time
   - Daily limit enforcement
   - Daily reset logic
   - Per-user isolation
   - File creation
   - File locking

3. **CostTracker** (10 tests):
   - Cost calculation (gpt-4o-mini)
   - Cost calculation (gpt-4o)
   - Unknown model fallback
   - Daily cost accumulation
   - Budget not exceeded initially
   - Budget exceeded detection
   - Per-user cost tracking
   - 80% warning alert
   - 100% critical alert
   - Email failure handling

4. **Config Helpers** (10 tests):
   - String getter with value
   - String getter with default
   - Integer getter with value
   - Integer invalid value default
   - Float getter with value
   - Float invalid value default
   - Boolean true values
   - Boolean false values
   - Boolean default
   - Type safety validation

**Test Execution**:
```bash
pytest tests/test_token_validator.py tests/test_rate_limiter.py tests/test_cost_tracker.py tests/test_config_helpers.py -v
```

### Integration Tests (Manual - Step 5)

All tests documented in Step 5, covering:
1. Health check ✅
2. Token validation ✅
3. Rate limiting (burst) ✅
4. Rate limiting (throttle) ✅
5. Daily limit ✅
6. Budget enforcement ✅
7. CORS ✅
8. Debug mode ✅

### Regression Tests (After Completion)

**Fighter XP Table Test** (acid test):
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "How many experience points does a fighter need to become 9th level?"}'

# Expected: "A fighter needs 250,001 experience points..."
```

**Monster Comparison Test** (entity-aware retrieval):
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "What is the difference between a red dragon and a white dragon?"}'

# Expected: Answer mentions both dragons with specific differences
```

---

## 6. Rollback Plan

### If Flask API Fails to Start

```bash
# Check logs for errors
python -m flask run --port 5000

# If import errors, check dependencies
pip list | grep flask

# If ChromaDB connection fails, check ChromaDB is running
curl http://localhost:8060/api/v2/heartbeat

# If all else fails, rollback
git checkout feature/apache~1
```

### If Rate Limiting Breaks

```bash
# Check rate limit files
ls -l data/user_requests/
cat data/user_requests/*.json

# Delete all rate limit files to reset
rm data/user_requests/*.json

# Restart Flask
```

### If OAuth2 Validation Fails

```bash
# Test api.gravitycar.com directly
curl https://api.gravitycar.com/auth/me \
  -H "Authorization: Bearer $TOKEN"

# If API is down, temporarily disable auth for testing
# (DON'T deploy to production without auth!)
```

---

## 7. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **api.gravitycar.com down** | High | Low | Fail closed, cache reduces dependency |
| **Rate limit files corrupted** | Medium | Low | Fail closed, easy to delete and reset |
| **Budget exceeded unexpectedly** | Low | Medium | Start with $1/day, monitor closely |
| **CORS misconfiguration** | High | Low | Test thoroughly with curl -v |
| **Flask crashes on startup** | High | Low | Test locally first, check logs |
| **Email alerts fail** | Low | Low | Don't crash app, just log warning |

---

## 8. Success Metrics

### Quantitative Metrics
- [ ] All 34 unit tests pass ✅
- [ ] All 8 integration test scenarios pass ✅
- [ ] Test coverage >80% for utility classes
- [ ] Token validation cache hit rate >80%
- [ ] Rate limiter overhead <10ms per request
- [ ] API response time <3 seconds (P95)

### Qualitative Metrics
- [ ] Code is readable and well-documented
- [ ] Configuration via .env (no hardcoded values)
- [ ] Clear separation of concerns (validator, limiter, tracker, API)
- [ ] Comprehensive error handling
- [ ] Unit tests demonstrate correctness

### Acceptance Criteria

**Must Have**:
- [ ] **All 34 unit tests pass** ⚠️ CRITICAL
- [ ] Health endpoint returns 200
- [ ] Query endpoint works with valid JWT
- [ ] Rate limiting enforced correctly
- [ ] Budget tracking works with actual token counts
- [ ] **CORS configured via environment variable** (localhost:3000 for local, react.gravitycar.com for prod)
- [ ] **Auth API URL configured via environment variable** (localhost:8081 for local, api.gravitycar.com for prod)
- [ ] Fighter XP Table test passes
- [ ] All 8 integration test scenarios pass

**Should Have**:
- [ ] Token validation cache working (verify in logs)
- [ ] Email alerts configured (test manually)
- [ ] API documentation complete
- [ ] `.env` and `.env.production` files documented
- [ ] Unit test coverage report generated

**Nice to Have**:
- [ ] Performance benchmarks documented
- [ ] Admin dashboard for viewing stats
- [ ] Request logging middleware

---

## 9. Implementation Checklist

### Pre-Implementation
- [ ] Session 1 (Output Buffer) complete ✅
- [ ] Read flask.md thoroughly
- [ ] Read rate_limiting_final.md thoroughly
- [ ] Read oauth_integration.md thoroughly
- [ ] Review this implementation plan
- [ ] Verify ChromaDB is running
- [ ] **Configure .env for local development** (localhost:3000, localhost:8081)
- [ ] Get real JWT token from localhost:8081 (or api.gravitycar.com) for testing
- [ ] Backup code: `git branch backup-before-session-2`

### Implementation (Follow Steps 1-6)
- [ ] Step 1.1: Create TokenValidator class (45 min)
- [ ] Step 1.2: Create TokenBucket class (45 min)
- [ ] Step 1.3: Create CostTracker class (30 min)
- [ ] Step 2.1: Create Flask app structure (60 min)
- [ ] **Step 2.1b: Update DnDRAG to return token usage (15 min)** ⚠️ CRITICAL
- [ ] Step 2.2: Update .env configuration (15 min)
- [ ] Step 2.3: Update config helper module (15 min)
- [ ] Step 3: Install dependencies (15 min)
- [ ] Step 4: Unit tests - 34 tests (2 hours) ⚠️ CRITICAL
  - [ ] Step 4.1: TokenValidator tests (30 min)
  - [ ] Step 4.2: TokenBucket tests (45 min)
  - [ ] Step 4.3: CostTracker tests (45 min)
  - [ ] Step 4.4: Config helper tests (30 min)
  - [ ] Step 4.5: Run all unit tests (verify 34 pass)
- [ ] Step 5: Integration testing - all 8 scenarios (2 hours)
- [ ] Step 6: Documentation (30 min)

### Post-Implementation
- [ ] All 34 unit tests pass ✅
- [ ] All 8 integration test scenarios pass ✅
- [ ] Fighter XP Table test passes
- [ ] Git commit: `git commit -m "feat: add Flask API with OAuth2 and rate limiting"`
- [ ] Update copilot-instructions.md with Flask API info
- [ ] Mark Session 2 as complete in implementation_roadmap.md
- [ ] Ready for Session 3 (Apache Deployment)

---

## 10. Next Steps (After Completion)

### Immediate
1. Commit changes to git
2. Update implementation roadmap status
3. Review Session 3 (Apache Deployment) prerequisites

### Session 3 Prerequisites
- [ ] Flask API tested locally ✅
- [ ] All test scenarios passing ✅
- [ ] Real JWT token works ✅
- [ ] Rate limiting works ✅
- [ ] Budget tracking works ✅

### Future Enhancements (Not in This Session)
- Admin dashboard for viewing stats
- Request logging middleware
- Prometheus metrics
- Redis cache for token validation
- WebSocket support for streaming responses

---

**Implementation Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Status**: 📋 Planning Complete - Ready to Execute  
**Created**: November 4, 2025  
**Estimated Time**: 6-8 hours  
**Next Action**: Review plan, then begin Step 1
