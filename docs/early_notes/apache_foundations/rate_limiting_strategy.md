# Rate Limiting & Abuse Prevention Strategy

**Decision Date**: November 3, 2025  
**Context**: Protecting RAG system from OpenAI API cost abuse  
**Status**: 🔍 Analysis - Needs Decision

---

## Threat Model: What We're Protecting Against

### Primary Threat: Cost Abuse
**Scenario**: Attacker authenticates (or bypasses auth) and floods API with queries to rack up OpenAI bills.

**Cost per query**:
- Embedding (text-embedding-3-small): ~$0.0001 per query
- GPT-4o-mini completion: ~$0.005-0.015 per query (depends on context size)
- **Total per query**: ~$0.005-0.02

**Attack economics**:
| Requests/Hour | Cost/Hour | Cost/Day | Cost/Month |
|---------------|-----------|----------|------------|
| 60 (1/min) | $0.30-1.20 | $7.20-28.80 | $216-864 |
| 600 (10/min) | $3-12 | $72-288 | $2,160-8,640 |
| 3,600 (1/sec) | $18-72 | $432-1,728 | $12,960-51,840 |

**Verdict**: Even moderate abuse (10 req/min) could cost $100-300/month. High-frequency abuse could bankrupt you.

---

## Your Current Defense: .htaccess + CORS

### What You Have
```apache
# Your described setup (assumed)
<Files "api.php">
    # HTTP Basic Auth or session-based auth
    Require valid-user
    
    # CORS - only allow requests from your main site
    Header set Access-Control-Allow-Origin "https://yourmainsite.com"
</Files>
```

### What This Protects Against
✅ **Casual scrapers**: Can't access API without credentials  
✅ **Cross-site attacks**: CORS blocks unauthorized domains  
✅ **Drive-by attacks**: No anonymous access

### What This DOESN'T Protect Against
❌ **Compromised credentials**: Attacker steals/guesses user password  
❌ **Session hijacking**: Attacker steals session cookie  
❌ **Insider threat**: Legitimate user abuses their access  
❌ **Client-side bypass**: Attacker modifies your frontend to remove rate limits

**Critical insight**: Authentication proves identity, but doesn't prevent abuse by authenticated users.

---

## Multi-Layered Defense Strategy

### Layer 1: Apache-Level Rate Limiting (Coarse Filter)
**Purpose**: Stop brute-force and obvious floods  
**Tool**: `mod_ratelimit` or `mod_evasive`

```apache
# In your VirtualHost config
<Location /api/query>
    # Limit bandwidth per connection
    SetOutputFilter RATE_LIMIT
    SetEnv rate-limit 50  # 50 KB/s max (throttles large responses)
    
    # Or use mod_evasive for request-based limiting
    DOSPageCount 10        # Max 10 requests per page per interval
    DOSPageInterval 60     # Interval in seconds
    DOSBlockingPeriod 300  # Block for 5 minutes
</Location>
```

**Pros**: 
- ✅ Fast (happens before Python code runs)
- ✅ No code changes needed
- ✅ Stops obvious floods

**Cons**:
- ⚠️ Coarse-grained (can't distinguish query types)
- ⚠️ Per-IP (multiple users behind NAT get shared limit)

---

### Layer 2: Application-Level Rate Limiting (Smart Filter)
**Purpose**: Per-user limits with grace period for legitimate bursts  
**Tool**: Python token bucket or sliding window

#### Option A: Token Bucket (Recommended)
**Concept**: Each user gets a "bucket" of tokens. Each query costs 1 token. Bucket refills slowly.

```python
# src/utils/rate_limiter.py
import time
from collections import defaultdict
from threading import Lock

class TokenBucket:
    """Thread-safe token bucket rate limiter."""
    
    def __init__(self, capacity=10, refill_rate=1/60):
        """
        Args:
            capacity: Max tokens (burst allowance)
            refill_rate: Tokens per second (1/60 = 1 per minute)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets = defaultdict(lambda: {'tokens': capacity, 'last_refill': time.time()})
        self.lock = Lock()
    
    def allow_request(self, user_id: str) -> tuple[bool, dict]:
        """
        Check if request is allowed for user.
        
        Returns:
            (allowed: bool, info: dict with remaining tokens and retry_after)
        """
        with self.lock:
            bucket = self.buckets[user_id]
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - bucket['last_refill']
            refill_amount = elapsed * self.refill_rate
            bucket['tokens'] = min(self.capacity, bucket['tokens'] + refill_amount)
            bucket['last_refill'] = now
            
            # Check if request allowed
            if bucket['tokens'] >= 1.0:
                bucket['tokens'] -= 1.0
                return True, {
                    'remaining': int(bucket['tokens']),
                    'retry_after': None
                }
            else:
                # Calculate when next token available
                tokens_needed = 1.0 - bucket['tokens']
                retry_after = int(tokens_needed / self.refill_rate)
                return False, {
                    'remaining': 0,
                    'retry_after': retry_after
                }

# In Flask app
from src.utils.rate_limiter import TokenBucket

# Create limiter (shared across requests in this worker)
limiter = TokenBucket(capacity=10, refill_rate=1/60)  # 10 burst, 1 per minute

@app.route('/api/query', methods=['POST'])
def query():
    # Get user ID from session/auth
    user_id = request.headers.get('X-User-ID') or request.remote_addr
    
    # Check rate limit
    allowed, info = limiter.allow_request(user_id)
    
    if not allowed:
        return jsonify({
            'error': 'Rate limit exceeded',
            'retry_after': info['retry_after']
        }), 429  # HTTP 429 Too Many Requests
    
    # Process request normally
    # ...
```

**Why token bucket?**
- ✅ Allows bursts (user can ask 10 questions quickly if they haven't used the app in a while)
- ✅ Smooth refill (no "wait exactly 60 seconds" frustration)
- ✅ Simple to implement
- ✅ Self-healing (doesn't require cleanup of old entries)

#### Option B: Sliding Window (Alternative)
Track requests in a time window (e.g., last 60 seconds). More complex but more accurate.

---

### Layer 3: Cost Tracking & Budget Limits (Kill Switch)
**Purpose**: Absolute safety net - stop ALL requests if daily budget exceeded  
**Tool**: Track actual OpenAI costs in real-time

```python
# src/utils/cost_tracker.py
import time
from threading import Lock

class CostTracker:
    """Track OpenAI API costs with daily budget limit."""
    
    def __init__(self, daily_budget_usd=10.0):
        self.daily_budget = daily_budget_usd
        self.current_day = time.strftime('%Y-%m-%d')
        self.daily_cost = 0.0
        self.lock = Lock()
    
    def record_query(self, embedding_tokens: int, completion_tokens: int):
        """
        Record cost of a query.
        
        Args:
            embedding_tokens: Tokens used for embedding
            completion_tokens: Tokens used for completion
        """
        with self.lock:
            # Reset if new day
            today = time.strftime('%Y-%m-%d')
            if today != self.current_day:
                self.current_day = today
                self.daily_cost = 0.0
            
            # Calculate cost (OpenAI pricing)
            embedding_cost = (embedding_tokens / 1_000_000) * 0.02  # $0.02 per 1M tokens
            completion_cost = (completion_tokens / 1_000_000) * 0.15  # $0.15 per 1M tokens (gpt-4o-mini)
            
            self.daily_cost += embedding_cost + completion_cost
    
    def is_budget_exceeded(self) -> tuple[bool, dict]:
        """Check if daily budget exceeded."""
        with self.lock:
            exceeded = self.daily_cost >= self.daily_budget
            return exceeded, {
                'daily_cost': round(self.daily_cost, 4),
                'daily_budget': self.daily_budget,
                'remaining': round(self.daily_budget - self.daily_cost, 4)
            }

# In Flask app
cost_tracker = CostTracker(daily_budget_usd=10.0)

@app.route('/api/query', methods=['POST'])
def query():
    # Check budget before processing
    exceeded, budget_info = cost_tracker.is_budget_exceeded()
    if exceeded:
        return jsonify({
            'error': 'Daily budget exceeded',
            'budget_info': budget_info
        }), 503  # Service Unavailable
    
    # Process query
    result = rag.query(question, ...)
    
    # Record costs (extract from OpenAI response)
    cost_tracker.record_query(
        embedding_tokens=...,  # From OpenAI API response
        completion_tokens=...
    )
    
    return jsonify(result)
```

**Why cost tracking?**
- ✅ **Failsafe**: Even if rate limiting fails, you're protected
- ✅ **Visibility**: Know your actual daily spend
- ✅ **Predictable**: Budget is explicit, not guessed from request rates

---

### Layer 4: Query Complexity Analysis (Advanced)
**Purpose**: Detect and throttle suspicious patterns  
**Examples**:
- Same query repeated 100 times → Likely a bot
- Random gibberish queries → Testing/probing
- Extremely long queries → Trying to maximize costs

```python
import hashlib
from collections import defaultdict

class QueryAnalyzer:
    """Detect suspicious query patterns."""
    
    def __init__(self):
        self.query_hashes = defaultdict(int)  # hash -> count
        self.user_queries = defaultdict(list)  # user_id -> [query hashes]
    
    def is_suspicious(self, user_id: str, query: str) -> tuple[bool, str]:
        """
        Check if query exhibits suspicious patterns.
        
        Returns:
            (suspicious: bool, reason: str)
        """
        # Check 1: Duplicate queries (exact match)
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        
        if query_hash in self.user_queries[user_id]:
            count = self.user_queries[user_id].count(query_hash)
            if count >= 3:
                return True, f"Duplicate query detected ({count} times)"
        
        self.user_queries[user_id].append(query_hash)
        
        # Check 2: Extremely long queries (cost amplification)
        if len(query) > 500:
            return True, "Query exceeds 500 characters"
        
        # Check 3: Random characters (gibberish detection)
        alpha_ratio = sum(c.isalpha() for c in query) / len(query)
        if alpha_ratio < 0.5:
            return True, "Query appears to be gibberish"
        
        return False, ""
```

---

## Recommended Configuration

### For Your Use Case (2-5 expected users, abuse prevention)

| Layer | Setting | Reasoning |
|-------|---------|-----------|
| **Apache** | 20 requests/minute per IP | Stops brute force, allows legitimate bursts |
| **Token Bucket** | Capacity: 5, Refill: 1/60s | User can ask 5 quick questions, then 1/minute |
| **Daily Budget** | $5/day | ~250-1000 queries/day depending on complexity |
| **Query Analysis** | Max 500 chars, 3 duplicate limit | Stops obvious abuse patterns |

**Cost math**:
- Normal user: 10 queries/day = $0.05-0.20/day
- Power user: 50 queries/day = $0.25-1.00/day  
- **Budget covers 5-10 power users comfortably**

### Configuration Examples

```python
# Conservative (tighter limits)
limiter = TokenBucket(capacity=3, refill_rate=1/120)  # 3 burst, 1 every 2 minutes
cost_tracker = CostTracker(daily_budget_usd=3.0)

# Moderate (recommended)
limiter = TokenBucket(capacity=5, refill_rate=1/60)  # 5 burst, 1 per minute
cost_tracker = CostTracker(daily_budget_usd=5.0)

# Generous (for testing)
limiter = TokenBucket(capacity=10, refill_rate=1/30)  # 10 burst, 1 every 30 seconds
cost_tracker = CostTracker(daily_budget_usd=10.0)
```

---

## Alternative Approaches

### Option 1: OpenAI API Key Quotas (External)
Set spending limits directly in OpenAI dashboard:
- **Hard limit**: $50/month (OpenAI stops API after this)
- **Soft limit**: $10/month (OpenAI sends email alert)

**Pros**: 
- ✅ Absolute protection
- ✅ No code needed

**Cons**:
- ❌ All-or-nothing (your app breaks when limit hit)
- ❌ Monthly granularity (can't do daily budgets)

### Option 2: Captcha on API (User-Hostile)
Require solving captcha every N requests.

**Verdict**: ❌ Don't do this. Ruins user experience for minimal benefit.

### Option 3: Paid Tier (Long-Term)
Charge users for API access (even $1/month filters out most abuse).

**Verdict**: ✅ Eventually, but not for MVP.

---

## What NOT To Do

### ❌ Client-Side Rate Limiting Only
```javascript
// BAD - Attacker can disable this
let lastRequest = 0;
function query() {
    if (Date.now() - lastRequest < 60000) {
        alert("Please wait 1 minute");
        return;
    }
    // Send request
}
```
**Why this fails**: Attacker bypasses your frontend entirely with curl/Postman.

### ❌ Relying on CORS Alone
CORS is enforced by browsers. curl/Python requests ignore it completely.

### ❌ Blocking After Abuse Detected
By the time you notice $100 in charges, the damage is done. **Prevent, don't react.**

---

## Implementation Priority

### Phase 1 (MVP - Session 2)
1. ✅ **Token bucket rate limiter** in Flask
   - 5 tokens, refill 1/60s
   - Return HTTP 429 with `Retry-After` header
2. ✅ **Daily cost budget** kill switch
   - $5/day limit
   - Return HTTP 503 when exceeded

**Time to implement**: 1-2 hours  
**Protection level**: 95% (stops all but determined attackers)

### Phase 2 (Polish - Session 3)
3. ⚠️ **Apache mod_evasive** configuration
   - 20 requests/minute per IP
4. ⚠️ **Query pattern analysis**
   - Detect duplicates and gibberish

**Time to implement**: 1 hour  
**Protection level**: 99% (only sophisticated attacks get through)

### Phase 3 (Monitoring - Post-Launch)
5. 📊 **Cost tracking dashboard**
   - Track daily spend by user
   - Alert when approaching budget
6. 📊 **OpenAI API monitoring**
   - Set hard limit in OpenAI dashboard
   - Email alerts at 80% budget

---

## Testing Your Defenses

### Manual Test (Before Launch)
```bash
# Test rate limiting
for i in {1..20}; do
    curl -X POST http://localhost:5000/api/query \
      -H "Content-Type: application/json" \
      -d '{"question": "What is a beholder?"}' &
done

# Expected: First 5 succeed, rest get HTTP 429
```

### Load Test (Simulate Attack)
```python
# test_abuse.py
import requests
import time

for i in range(100):
    response = requests.post(
        'http://localhost:5000/api/query',
        json={'question': f'Test query {i}'}
    )
    print(f"{i}: HTTP {response.status_code}")
    if response.status_code == 429:
        print(f"  Rate limited! Retry after: {response.json().get('retry_after')}s")
        break
    time.sleep(0.1)
```

---

## Monitoring & Alerts

### What to Track
```python
# src/utils/metrics.py
class MetricsCollector:
    def __init__(self):
        self.total_requests = 0
        self.rate_limited_requests = 0
        self.daily_cost = 0.0
        self.users = set()
    
    def log_request(self, user_id, cost, rate_limited):
        self.total_requests += 1
        if rate_limited:
            self.rate_limited_requests += 1
        self.daily_cost += cost
        self.users.add(user_id)
    
    def get_stats(self):
        return {
            'total_requests': self.total_requests,
            'rate_limited': self.rate_limited_requests,
            'rate_limit_percentage': (self.rate_limited_requests / max(self.total_requests, 1)) * 100,
            'daily_cost': round(self.daily_cost, 2),
            'unique_users': len(self.users)
        }

# Add endpoint to view metrics
@app.route('/admin/metrics')
@requires_admin  # Add auth check
def metrics():
    return jsonify(metrics_collector.get_stats())
```

### Alert Thresholds
- ⚠️ **>10% requests rate-limited**: Limits may be too tight
- 🚨 **>80% daily budget used**: Approaching limit
- 🚨 **Same user >50% of requests**: Potential abuse

---

## Final Recommendation

**Use a layered approach**:

1. **Token Bucket** (capacity=5, 1/minute refill) → Primary defense
2. **Daily Budget** ($5/day) → Failsafe
3. **Apache rate limit** (20/minute) → Coarse filter
4. **OpenAI hard limit** ($50/month) → Absolute ceiling

**This gives you**:
- ✅ 99% protection from abuse
- ✅ Good UX for legitimate users (5-question burst allowed)
- ✅ Predictable costs ($3-5/day max)
- ✅ Multiple failsafes (if one fails, others catch it)

**Cost**: ~$90-150/month worst case (budget limits enforced)  
**Legitimate use**: ~$10-30/month (2-5 users, 10-20 queries/day each)

---

## Questions for You

1. **What's your comfortable monthly budget?** $20? $50? $100?
   - This determines daily budget ($budget / 30)

2. **How many legitimate users do you expect?**
   - This helps calibrate token bucket capacity

3. **What's acceptable wait time for power users?**
   - 1 query/minute? 1 every 2 minutes?

4. **Do you want user-specific budgets** (some users get more queries)?
   - Requires database to track per-user limits

5. **How should the frontend handle rate limits?**
   - Show countdown timer? Disable submit button? Queue requests?

Answer these and I'll refine the configuration for your specific needs.

---

**Decision Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Last Updated**: November 3, 2025  
**Status**: Awaiting user decisions on budget and limits
