# Rate Limiting Configuration - Final Decisions

**Decision Date**: November 3, 2025  
**Context**: Finalized rate limiting and cost tracking configuration  
**Status**: ✅ Approved - Ready for Implementation

---

## Budget & Limits: Final Configuration

### Daily Budget
- **Global daily budget**: $1.00/day (configurable in `.env`)
- **Rationale**: Historical spend of $0.55 total validates this is generous
- **Per-user daily limit**: 30 requests/day (configurable in `.env`)

### Rate Limiting Strategy
**Token Bucket Configuration**:
- **Initial capacity**: 15 tokens (burst allowance)
- **Refill rate**: 1 token per 60 seconds
- **Effect**: User can ask 15 questions immediately, then limited to 1/minute

**User behavior modeling**:
```
Scenario 1: Casual user
- Asks 5 questions over 10 minutes
- Never hits limit
- Uses 5 tokens, has 10 remaining

Scenario 2: Engaged user  
- Asks 15 questions rapidly (uses burst)
- Then asks 10 more over next 15 minutes (1/minute)
- Comfortable experience, no frustration

Scenario 3: Power user / Potential abuser
- Burns through 15-token burst in 2 minutes
- Hits rate limit
- Can continue at 1/minute (sustainable)
- After 30 total queries, cut off for the day
```

---

## Environment Configuration

### New `.env` Variables

```bash
# Rate Limiting & Cost Tracking
RATE_LIMIT_DIR=data/user_requests  # Local: data/user_requests, Remote: /var/www/dnd-rag/data/user_requests
DAILY_BUDGET_USD=1.00           # Global daily budget
DAILY_USER_REQUEST_LIMIT=30     # Max requests per user per day
TOKEN_BUCKET_CAPACITY=15        # Initial burst allowance
TOKEN_REFILL_RATE=0.016667      # Tokens per second (1/60 = 1 per minute)
ALERT_EMAIL=your-email@example.com  # Where to send alerts
```

---

## Alert System

### When Alerts Are Triggered

| Trigger | Condition | Alert Message | Action |
|---------|-----------|---------------|--------|
| **Budget threshold** | 80% of daily budget used | "Warning: 80% of daily budget consumed ($0.80/$1.00)" | Email sent, continue service |
| **Budget exceeded** | 100% of daily budget reached | "CRITICAL: Daily budget exceeded ($1.00/$1.00). Service paused." | Email sent, HTTP 503 returned |
| **User limit reached** | User hits 30 requests/day | "User {user_id} reached daily limit (30 requests)" | Email sent, user gets HTTP 429 |
| **Suspicious pattern** | 3+ identical queries from one user | "Possible abuse detected from user {user_id}" | Email sent, continue service |

### Alert Email Format

```
Subject: [D&D RAG] Daily Budget Alert - 80% Consumed

Daily Budget Status Report
--------------------------
Date: 2025-11-03
Time: 14:32:15 UTC

Budget Information:
- Daily limit: $1.00
- Current spend: $0.80
- Remaining: $0.20
- Percentage: 80%

Top Users (by cost):
1. user_abc123: $0.35 (15 queries)
2. user_def456: $0.25 (10 queries)
3. user_ghi789: $0.20 (8 queries)

Action Required: None (informational)
Service Status: Operational

---
This is an automated alert from D&D RAG System
```

---

## Implementation Details

### Storage Architecture: Per-User Files

**Rationale**: With 2-5 users and Apache's multi-process architecture, storing each user's rate limit data in a separate file eliminates lock contention between different users while maintaining simplicity.

**Structure**:
```
data/user_requests/
├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.json  # User 1 (GUID from api.gravitycar.com)
├── b2c3d4e5-f6a7-8901-bcde-f12345678901.json  # User 2
└── c3d4e5f6-a7b8-9012-cdef-012345678912.json  # User 3
```

**Per-User File Format**:
```json
{
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "tokens": 8.5,
  "last_refill": 1699024583.234,
  "daily_count": 12,
  "daily_reset": "2025-11-03"
}
```

**Lock Contention Analysis**:
- **Between users**: Zero (separate files)
- **Same user**: Only possible with rapid double-click (~100ms interval)
- **Likelihood**: Essentially zero for human interaction
- **Handling**: Non-blocking lock with immediate fail-closed response

### Token Bucket Class

```python
# src/utils/rate_limiter.py
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
        Args:
            capacity: Max tokens (burst allowance) - default 15
            refill_rate: Tokens per second - default 1/60 (1 per minute)
            daily_limit: Max requests per user per day - default 30
            data_dir: Directory to store user rate limit files (from .env)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.daily_limit = daily_limit
        
        # Get data directory from .env
        if data_dir is None:
            data_dir = os.getenv('RATE_LIMIT_DIR', 'data/user_requests')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get path to user's rate limit file."""
        # Sanitize user_id (GUIDs are safe, but be defensive)
        safe_id = user_id.replace('/', '_').replace('\\', '_')
        return self.data_dir / f"{safe_id}.json"
    
    def allow_request(self, user_id: str) -> Tuple[bool, dict]:
        """
        Check if request allowed for user.
        
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
                            'message': 'Another request is being processed. Please wait a moment and try again.',
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

### Cost Tracker Class

```python
# src/utils/cost_tracker.py
import time
from threading import Lock
from typing import Dict, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class CostTracker:
    """Track OpenAI API costs with daily budget limit and email alerts."""
    
    def __init__(self, daily_budget_usd: float = 1.0, alert_email: str = None):
        """
        Args:
            daily_budget_usd: Maximum daily spend in USD
            alert_email: Email address for alerts (from .env)
        """
        self.daily_budget = daily_budget_usd
        self.alert_email = alert_email
        self.current_day = time.strftime('%Y-%m-%d')
        self.daily_cost = 0.0
        self.user_costs: Dict[str, float] = {}
        self.alert_80_sent = False  # Track if 80% alert sent today
        self.lock = Lock()
    
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
            
            # Calculate cost (OpenAI pricing for gpt-4o-mini and text-embedding-3-small)
            embedding_cost = (embedding_tokens / 1_000_000) * 0.02  # $0.02 per 1M tokens
            completion_cost = (completion_tokens / 1_000_000) * 0.15  # $0.15 per 1M tokens
            query_cost = embedding_cost + completion_cost
            
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
        # Get SMTP config from environment
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

### Flask Integration

```python
# src/api.py (excerpt showing integration)
from flask import Flask, request, jsonify, g
from src.query.docling_query import DnDRAG
from src.utils.rag_output import RAGOutput
from src.utils.rate_limiter import TokenBucket
from src.utils.cost_tracker import CostTracker
from src.utils.token_validator import TokenValidator
from src.utils.config import get_env_float, get_env_int, get_env_string
import os

app = Flask(__name__)

# Initialize rate limiter and cost tracker from .env
limiter = TokenBucket(
    capacity=get_env_int('TOKEN_BUCKET_CAPACITY', 15),
    refill_rate=get_env_float('TOKEN_REFILL_RATE', 1/60),
    daily_limit=get_env_int('DAILY_USER_REQUEST_LIMIT', 30),
    data_dir=get_env_string('RATE_LIMIT_DIR')  # Per-user file storage
)

cost_tracker = CostTracker(
    daily_budget_usd=get_env_float('DAILY_BUDGET_USD', 1.0),
    alert_email=get_env_string('ALERT_EMAIL')
)

# Initialize token validator for OAuth2
token_validator = TokenValidator(
    api_base_url=get_env_string('AUTH_API_URL', 'https://api.gravitycar.com'),
    cache_ttl=300  # 5 minutes
)

# Initialize RAG once
rag = None

@app.before_first_request
def init_rag():
    global rag
    rag = DnDRAG()

@app.route('/api/query', methods=['POST'])
def query():
    # Extract and validate bearer token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401
    
    token = auth_header.split(' ', 1)[1]
    
    # Validate token with api.gravitycar.com and get user info
    user_info = token_validator.validate(token)
    if not user_info:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    # Extract user GUID from api.gravitycar.com response
    user_id = user_info['id']  # GUID format: a1b2c3d4-e5f6-7890-abcd-ef1234567890
    
    # Check global budget first
    budget_exceeded, budget_info = cost_tracker.is_budget_exceeded()
    if budget_exceeded:
        return jsonify({
            'error': 'Daily budget exceeded',
            'message': 'Service temporarily unavailable. Daily budget will reset at midnight UTC.',
            'budget_info': budget_info
        }), 503  # Service Unavailable
    
    # Check user rate limit (uses per-user file: data/user_requests/<user_id>.json)
    allowed, rate_info = limiter.allow_request(user_id)
    if not allowed:
        response = jsonify({
            'error': rate_info['reason'],
            'message': rate_info['message'],
            'rate_info': {
                'daily_remaining': rate_info.get('daily_remaining'),
                'retry_after': rate_info.get('retry_after')
            }
        })
        response.status_code = 429  # Too Many Requests
        
        # Add Retry-After header if rate limited (not daily limit or concurrent request)
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
        cost_info = cost_tracker.record_query(user_id, embedding_tokens, completion_tokens)
        
        # Add metadata to response
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
```

---

## Updated `.env` File

```bash
# OpenAI Configuration
openai_api_key=sk-...

# ChromaDB Configuration
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/

# Default Collection
default_collection_name=dnd_unified

# OAuth2 Configuration
AUTH_API_URL=https://api.gravitycar.com

# Rate Limiting & Cost Tracking
RATE_LIMIT_DIR=data/user_requests  # Local dev; Remote: /var/www/dnd-rag/data/user_requests
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
```

---

## Testing Strategy

### Test 1: Burst Capacity
```bash
# Should succeed (within burst limit)
# Note: With OAuth2, need valid bearer token
TOKEN="your-test-token-here"

for i in {1..15}; do
    curl -X POST http://localhost:5000/api/query \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{"question": "What is a beholder?"}' &
done

# Expected: All 15 succeed
# Result: Creates/updates data/user_requests/<user-guid>.json
```

### Test 2: Rate Limiting
```bash
# Should hit rate limit on 16th request
TOKEN="your-test-token-here"

for i in {1..20}; do
    curl -X POST http://localhost:5000/api/query \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{"question": "Test query '$i'"}' 
    sleep 0.5
done

# Expected: First 15 succeed, 16-20 get HTTP 429 with reason: 'rate_limited'
```

### Test 3: Daily Limit
```bash
# Simulate 30 requests (should cut off at 30)
TOKEN="your-test-token-here"

for i in {1..35}; do
    curl -X POST http://localhost:5000/api/query \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d '{"question": "Test '$i'"}'
    sleep 4  # Wait for token refill
done

# Expected: First 30 succeed, 31-35 get HTTP 429 with reason: 'daily_limit_exceeded'
```

### Test 4: Concurrent Request Detection
```python
# test_concurrent_lock.py
import threading
import requests
import time

def make_request(request_num, token):
    response = requests.post(
        'http://localhost:5000/api/query',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        },
        json={'question': f'Test query {request_num}'}
    )
    print(f"Request {request_num}: {response.status_code} - {response.json().get('error', 'OK')}")

# Simulate near-simultaneous requests from same user
token = "your-test-token-here"
threads = [threading.Thread(target=make_request, args=(i, token)) for i in range(3)]

for t in threads:
    t.start()
for t in threads:
    t.join()

# Expected: 1-2 succeed, others get HTTP 429 with reason: 'concurrent_request'
# (Exact behavior depends on timing - file lock is very fast)
```

### Test 5: File Inspection
```bash
# View user's rate limit file
cat data/user_requests/a1b2c3d4-e5f6-7890-abcd-ef1234567890.json

# Expected output:
# {
#   "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "tokens": 8.5,
#   "last_refill": 1699024583.234,
#   "daily_count": 12,
#   "daily_reset": "2025-11-03"
# }
```

### Test 6: Budget Limit (Mock)
```python
# test_budget.py
from src.utils.cost_tracker import CostTracker

tracker = CostTracker(daily_budget_usd=0.01)  # Very low budget for testing

# Simulate expensive queries
for i in range(10):
    tracker.record_query(f'user_{i}', 
                        embedding_tokens=10000,  # Inflated for testing
                        completion_tokens=50000)
    
    exceeded, info = tracker.is_budget_exceeded()
    print(f"Query {i}: Budget exceeded = {exceeded}, Cost = ${info['daily_cost']:.4f}")
    
    if exceeded:
        print("Budget limit reached!")
        break
```

---

## File Permissions & Deployment

### Local Development
```bash
# Create rate limit directory
mkdir -p data/user_requests

# Permissions automatically set by Python (644 for files, 755 for directory)
```

### Remote Server (Apache)
```bash
# Create rate limit directory with Apache ownership
sudo mkdir -p /var/www/dnd-rag/data/user_requests
sudo chown www-data:www-data /var/www/dnd-rag/data/user_requests
sudo chmod 755 /var/www/dnd-rag/data/user_requests

# Update .env on remote
echo "RATE_LIMIT_DIR=/var/www/dnd-rag/data/user_requests" >> /var/www/dnd-rag/.env
```

### File Lock Behavior
- **Non-blocking lock**: Uses `fcntl.LOCK_EX | fcntl.LOCK_NB`
- **Lock scope**: Per-user file (no cross-user contention)
- **Lock duration**: ~5-10ms (read + write + compute)
- **Failure mode**: Fail-closed with HTTP 429 and `concurrent_request` reason

---

## Implementation Priority

### Phase 1 (Session 2 - Core Functionality)
1. ✅ Create `src/utils/rate_limiter.py` with TokenBucket class (per-user file storage)
2. ✅ Create `src/utils/cost_tracker.py` with CostTracker class
3. ✅ Create `src/utils/token_validator.py` for OAuth2 validation
4. ✅ Add new .env variables (RATE_LIMIT_DIR, AUTH_API_URL)
5. ✅ Create `src/utils/config.py` helper functions for reading .env
6. ✅ Integrate into Flask app with bearer token extraction

**Time**: 2-3 hours  
**Deliverable**: Working rate limiting + cost tracking in Flask with OAuth2

### Phase 2 (Session 3 - Email Alerts)
6. ⚠️ Configure SMTP settings
7. ⚠️ Test email alerts
8. ⚠️ Add admin dashboard to view stats

**Time**: 1-2 hours  
**Deliverable**: Email alerts working

### Phase 3 (Testing)
9. 📊 Run all 4 test scenarios
10. 📊 Monitor in production for 1 week

---

## Next Step: Apache Configuration

Now that rate limiting is defined, we need to discuss:

1. **mod_wsgi vs mod_proxy_uwsgi**: Which deployment pattern?
2. **Virtual host configuration**: Domain/subdomain setup
3. **SSL/HTTPS**: Let's Encrypt or self-signed?
4. **Process management**: How many workers? Thread vs process mode?
5. **.htaccess authentication**: HTTP Basic or session-based?

Ready to dive into Apache configuration?

---

**Decision Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Last Updated**: November 3, 2025  
**Status**: ✅ Finalized - Ready for Apache Config Discussion
