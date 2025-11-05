# Flask API Logging and Error Handling Improvements

**Date**: November 5, 2025  
**Status**: Implemented

---

## Summary of Changes

Enhanced Flask API with comprehensive logging and detailed error responses to improve debugging and provide better feedback to API clients.

---

## 1. Logging Improvements

### Added Structured Logging

```python
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Console output
        logging.FileHandler('flask.log')     # File output
    ]
)
logger = logging.getLogger(__name__)
```

### Logging Levels

| Level | When Used | Example |
|-------|-----------|---------|
| **INFO** | Normal operations | "Query completed in 3.45s", "User authenticated" |
| **WARNING** | Expected errors | "Rate limit exceeded", "Authentication failed" |
| **ERROR** | Unexpected errors | "Query processing failed", "Database connection error" |
| **DEBUG** | Detailed debugging | Request/response details, internal state |

### What Gets Logged

#### Startup
```
2025-11-05 08:55:40,737 - src.api - INFO - ================================================================================
2025-11-05 08:55:40,737 - src.api - INFO - Flask API Starting...
2025-11-05 08:55:40,737 - src.api - INFO - Environment: development
2025-11-05 08:55:40,737 - src.api - INFO - Auth API: http://localhost:8081
2025-11-05 08:55:40,737 - src.api - INFO - CORS Origins: http://localhost:3000,http://localhost:3001
2025-11-05 08:55:40,737 - src.api - INFO - ================================================================================
```

#### RAG Initialization
```
2025-11-05 08:55:41,757 - src.api - INFO - Initializing D&D RAG system...
Connecting to local ChromaDB (localhost:8060)
2025-11-05 08:55:42,074 - src.api - INFO - ✅ D&D RAG system initialized successfully
```

#### Successful Query
```
2025-11-05 09:10:23,456 - src.api - INFO - Query request received from 127.0.0.1
2025-11-05 09:10:23,457 - src.api - INFO - User authenticated: b25af775-7be1-4e9a-bd3b-641dfdd8c51c (mike@gravitycar.com)
2025-11-05 09:10:23,458 - src.api - INFO - Query from b25af775-7be1-4e9a-bd3b-641dfdd8c51c: 'What is a beholder?...' (debug=False, k=15)
2025-11-05 09:10:23,459 - src.api - DEBUG - Getting RAG instance...
2025-11-05 09:10:23,460 - src.api - INFO - Executing query for user b25af775-7be1-4e9a-bd3b-641dfdd8c51c...
2025-11-05 09:10:28,123 - src.api - INFO - Query completed in 4.66s - Tokens: 1187 (prompt: 863, completion: 324)
2025-11-05 09:10:28,124 - src.api - INFO - Cost: $0.000324 (daily total: $0.0009 / $1.00)
2025-11-05 09:10:28,125 - src.api - INFO - Request completed successfully for user b25af775-7be1-4e9a-bd3b-641dfdd8c51c in 4.67s
```

#### Authentication Failure
```
2025-11-05 09:15:12,345 - src.api - INFO - Query request received from 127.0.0.1
2025-11-05 09:15:12,346 - src.api - WARNING - Authentication failed from 127.0.0.1
```

#### Rate Limit Exceeded
```
2025-11-05 09:20:34,567 - src.api - WARNING - Rate limit exceeded for user b25af775-7be1-4e9a-bd3b-641dfdd8c51c: burst_exhausted
```

#### Budget Exceeded
```
2025-11-05 09:25:45,678 - src.api - WARNING - Budget exceeded for system ($1.0523 / $1.00)
```

#### Query Processing Error
```
2025-11-05 09:30:56,789 - src.api - ERROR - Query processing failed for user b25af775-7be1-4e9a-bd3b-641dfdd8c51c: Connection refused
2025-11-05 09:30:56,790 - src.api - ERROR - Traceback (most recent call last):
  File "/home/mike/projects/gravitycar_dnd1st_rag_system/src/api.py", line 195, in query
    rag_instance = get_rag()
  ...
ConnectionRefusedError: [Errno 111] Connection refused
```

---

## 2. Enhanced Error Responses

### Before (Generic)
```json
{
  "error": "Query processing failed",
  "details": "Connection refused"
}
```

### After (Detailed)
```json
{
  "error": "Query processing failed",
  "error_type": "ConnectionRefusedError",
  "error_category": "database_error",
  "message": "Database connection failed. Please try again in a moment.",
  "details": "[Errno 111] Connection refused",
  "timestamp": "2025-11-05T09:30:56.790Z",
  "request_id": "b25af775-7be1-4e9a-bd3b-641dfdd8c51c_1762361456"
}
```

### Error Categories

| Category | Trigger | User Message |
|----------|---------|--------------|
| `database_error` | ChromaDB/chroma in error | "Database connection failed. Please try again in a moment." |
| `ai_service_error` | OpenAI/API in error | "AI service temporarily unavailable. Please try again." |
| `timeout_error` | "timeout" in error | "Request timed out. Please try a simpler query." |
| `internal_error` | Other exceptions | "An unexpected error occurred. Please try again." |

### All Error Response Fields

```typescript
interface ErrorResponse {
  error: string;              // Short error name
  error_type?: string;        // Python exception type (500 errors only)
  error_category?: string;    // Categorized error type (500 errors only)
  message?: string;           // User-friendly message
  details?: string;           // Technical details
  timestamp: string;          // ISO 8601 timestamp
  request_id?: string;        // Unique request identifier (500 errors only)
  path?: string;              // Request path (404 errors only)
  rate_info?: {               // Rate limit information (429 errors only)
    daily_remaining: number;
    retry_after: number | null;
  };
  budget_info?: {             // Budget information (503 errors only)
    daily_total: number;
    daily_budget: number;
    percent_used: number;
  };
}
```

---

## 3. Enhanced Success Responses

### Added Performance Metrics
```json
{
  "answer": "A beholder is...",
  "diagnostics": [...],
  "errors": [],
  "meta": {
    "user_id": "b25af775-7be1-4e9a-bd3b-641dfdd8c51c",
    "rate_limit": {
      "remaining_burst": 14,
      "daily_remaining": 29
    },
    "cost": {
      "query_cost": 0.000324,
      "daily_total": 0.0009,
      "daily_budget": 1.0
    },
    "performance": {
      "total_duration_seconds": 4.672,
      "query_duration_seconds": 4.663
    },
    "timestamp": "2025-11-05T09:10:28.125Z"
  },
  "usage": {
    "prompt_tokens": 863,
    "completion_tokens": 324,
    "total_tokens": 1187
  }
}
```

### Performance Metrics

| Metric | Description |
|--------|-------------|
| `total_duration_seconds` | Full request time (auth + rate check + query + response) |
| `query_duration_seconds` | RAG query time only (retrieve + generate) |

---

## 4. Enhanced Health Endpoint

### Before
```json
{
  "status": "ok",
  "service": "dnd_rag",
  "version": "1.0.0"
}
```

### After
```json
{
  "status": "ok",
  "service": "dnd_rag",
  "version": "1.0.0",
  "timestamp": "2025-11-05T09:00:00.000Z",
  "components": {
    "rag_system": "ok"
  }
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `ok` | All systems operational |
| `degraded` | RAG system failed to initialize |

---

## 5. Request/Response Logging Middleware

### Before Request
```python
@app.before_request
def log_request():
    """Log incoming requests."""
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")
```

### After Response
```python
@app.after_request
def log_response(response):
    """Log response status."""
    logger.debug(f"Response: {response.status_code}")
    return response
```

---

## 6. Usage Examples

### Viewing Logs

```bash
# Watch live logs
tail -f flask.log

# Search for errors
grep ERROR flask.log

# Search for specific user
grep "b25af775-7be1-4e9a-bd3b-641dfdd8c51c" flask.log

# Search for rate limit events
grep "Rate limit exceeded" flask.log

# View last 50 lines
tail -50 flask.log
```

### Debugging with Request ID

When a 500 error occurs, the client receives a `request_id`:
```json
{
  "error": "Query processing failed",
  "request_id": "b25af775-7be1-4e9a-bd3b-641dfdd8c51c_1762361456",
  ...
}
```

Find the corresponding error in logs:
```bash
# Extract timestamp from request_id (1762361456)
date -d @1762361456
# Output: 2025-11-05 09:30:56 UTC

# Search logs around that time
grep -A 20 "1762361456" flask.log
```

---

## 7. Client-Side Error Handling

### Updated TypeScript Interface

```typescript
interface ErrorResponse {
  error: string;
  error_type?: string;        // NEW: Exception type
  error_category?: string;    // NEW: Categorized error
  message?: string;
  details?: string;
  timestamp: string;          // NEW: ISO timestamp
  request_id?: string;        // NEW: Unique identifier
  path?: string;
  rate_info?: {
    daily_remaining: number;
    retry_after: number | null;
  };
  budget_info?: {
    daily_total: number;
    daily_budget: number;
    percent_used: number;
  };
}
```

### Improved Error Display

```typescript
function handleError(error: ErrorResponse) {
  // Use user-friendly message if available
  const displayMessage = error.message || error.error;
  
  // Show request_id for 500 errors (user can report this)
  if (error.request_id) {
    console.error('Request ID for support:', error.request_id);
  }
  
  // Log technical details for debugging
  if (error.details) {
    console.error('Technical details:', error.details);
  }
  
  // Show appropriate UI based on error category
  switch (error.error_category) {
    case 'database_error':
      showRetryButton('Database temporarily unavailable');
      break;
    case 'ai_service_error':
      showRetryButton('AI service temporarily unavailable');
      break;
    case 'timeout_error':
      showMessage('Try a simpler question');
      break;
    default:
      showGenericError(displayMessage);
  }
}
```

---

## 8. Benefits

### For Developers

✅ **Comprehensive logging** - Every request tracked with context  
✅ **Error tracebacks** - Full stack traces for 500 errors  
✅ **Performance metrics** - Identify slow queries  
✅ **Request IDs** - Correlate client errors with server logs  
✅ **Structured data** - Easy to grep/parse logs  

### For Users

✅ **Clear error messages** - User-friendly explanations  
✅ **Actionable feedback** - Know when to retry vs. change query  
✅ **Transparent costs** - See API usage and costs  
✅ **Performance visibility** - Response time metrics  
✅ **Better debugging** - Request IDs for support tickets  

---

## 9. Log Rotation (Recommended)

Flask logs can grow large. Configure log rotation:

```bash
# Install logrotate (if not already installed)
sudo apt-get install logrotate

# Create logrotate config
sudo nano /etc/logrotate.d/flask-dnd-rag
```

**Content**:
```
/home/mike/projects/gravitycar_dnd1st_rag_system/flask.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

This keeps 7 days of logs, compresses old logs, and doesn't fail if the log is missing.

---

## 10. Next Steps

### Recommended Enhancements

1. **Structured logging (JSON)** - Use python-json-logger for machine-readable logs
2. **Log aggregation** - Send logs to ELK stack or CloudWatch
3. **Metrics dashboard** - Grafana dashboard for real-time monitoring
4. **Alert rules** - Alert on high error rates or budget exceeded
5. **Request tracing** - Add distributed tracing (OpenTelemetry)

### Production Considerations

- **Log level**: Switch to WARNING or ERROR in production
- **PII redaction**: Don't log sensitive user data
- **Log retention**: Define retention policy (30-90 days)
- **Monitoring**: Set up uptime monitoring and alerting

---

**Status**: ✅ Implemented and tested  
**Files Modified**: `src/api.py` (added logging throughout)  
**Breaking Changes**: None (response format extended, not changed)
