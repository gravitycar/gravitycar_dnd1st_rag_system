# D&D RAG API Integration Guide for React UI

**Date**: November 4, 2025  
**API Version**: 1.0.0  
**Status**: Ready for local development

---

## 1. Connection Configuration (Local vs Remote)

### Local Development
```typescript
// src/config/api.ts
const API_CONFIG = {
  local: {
    baseUrl: 'http://localhost:5000',
    authUrl: 'http://localhost:8081',
    corsOrigin: 'http://localhost:3000'
  },
  production: {
    baseUrl: 'https://dndchat.gravitycar.com',
    authUrl: 'https://api.gravitycar.com',
    corsOrigin: 'https://react.gravitycar.com'
  }
};

// Auto-detect environment
const isDevelopment = window.location.hostname === 'localhost';
export const config = isDevelopment ? API_CONFIG.local : API_CONFIG.production;
```

### Environment Detection Strategy
```typescript
// Detect environment from hostname
if (window.location.hostname === 'localhost') {
  // Use local Flask (port 5000)
  apiUrl = 'http://localhost:5000';
} else if (window.location.hostname === 'react.gravitycar.com') {
  // Use production Flask
  apiUrl = 'https://dndchat.gravitycar.com';
}
```

---

## 2. API Endpoints

### Base URLs
- **Local**: `http://localhost:5000`
- **Production**: `https://dndchat.gravitycar.com` (when deployed)

### Available Endpoints

#### Health Check (No Auth Required)
```
GET /health
```

#### Query D&D Rules (Auth Required)
```
POST /api/query
```

---

## 3. Request Format

### Health Check Request
```typescript
// GET /health
// No headers required, no body

const response = await fetch('http://localhost:5000/health');
const data = await response.json();

// Response: { status: 'ok', service: 'dnd_rag', version: '1.0.0' }
```

### Query Request (Full Example)
```typescript
// POST /api/query

// Headers (REQUIRED)
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${jwtToken}`,  // From localStorage.getItem('auth_token')
  'Origin': 'http://localhost:3000'       // Auto-sent by browser
};

// Body (JSON)
const body = {
  question: "What is a beholder?",  // REQUIRED: User's question
  debug: false,                      // OPTIONAL: Show retrieval diagnostics (default: false)
  k: 15                             // OPTIONAL: Number of chunks to retrieve (default: 15)
};

// Full request
const response = await fetch('http://localhost:5000/api/query', {
  method: 'POST',
  headers: headers,
  body: JSON.stringify(body),
  credentials: 'include'  // Important for CORS
});

const data = await response.json();
```

### Getting the JWT Token
```typescript
// User logs in via your existing auth system (localhost:8081 or api.gravitycar.com)
// Token is stored in localStorage

const jwtToken = localStorage.getItem('auth_token');

// Example token format:
// "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJncmF2aXR5Y2FyIiwiYXVkIjoiZ3Jhdml0eWNhciIsImlhdCI6MTc2MjI4NTQ5NiwiZXhwIjoxNzYyMjg5MDk2LCJ1c2VyX2lkIjoiYjI1YWY3NzUtN2JlMS00ZTlhLWJkM2ItNjQxZGZkZDhjNTFjIiwiZW1haWwiOiJtaWtlQGdyYXZpdHljYXIuY29tIiwiYXV0aF9wcm92aWRlciI6ImxvY2FsIn0.fEnhUD-TsZ7ytRJewzmlnAuMhPOZabdCptfFfVFzyuU"
```

### Request Body Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `question` | string | ✅ Yes | - | The D&D rules question to answer |
| `debug` | boolean | ❌ No | false | If true, includes retrieval diagnostics in response |
| `k` | integer | ❌ No | 15 | Number of document chunks to retrieve (5-50 recommended) |

---

## 4. Response Formats

### Success Response (HTTP 200)
```json
{
  "answer": "A beholder is a floating spherical creature with a large central eye...",
  
  "diagnostics": [
    "Retrieving documents from collection: adnd_1e",
    "Query: What is a beholder?",
    "Retrieved 8 chunks (adaptive filtering applied)",
    "Generating answer with gpt-4o-mini..."
  ],
  
  "errors": [],
  
  "meta": {
    "user_id": "b25af775-7be1-4e9a-bd3b-641dfdd8c51c",
    "rate_limit": {
      "remaining_burst": 14,
      "daily_remaining": 29
    },
    "cost": {
      "query_cost": 0.000324,
      "daily_total": 0.0006,
      "daily_budget": 1.0
    }
  },
  
  "usage": {
    "prompt_tokens": 863,
    "completion_tokens": 324,
    "total_tokens": 1187
  }
}
```

### Error Responses

#### 400 Bad Request - Missing Question
```json
{
  "error": "Missing required field: question"
}
```

#### 400 Bad Request - Invalid JSON
```json
{
  "error": "Invalid JSON",
  "details": "Expecting value: line 1 column 1 (char 0)"
}
```

#### 401 Unauthorized - Missing Token
```json
{
  "error": "Missing Authorization header"
}
```

#### 401 Unauthorized - Invalid Token
```json
{
  "error": "Invalid or expired token"
}
```

#### 429 Rate Limit Exceeded - Burst Exhausted
```json
{
  "error": "burst_exhausted",
  "message": "Rate limit exceeded. Please wait 60 seconds before trying again.",
  "rate_info": {
    "daily_remaining": 25,
    "retry_after": 60
  }
}
```
**Headers**: `Retry-After: 60`

#### 429 Rate Limit Exceeded - Daily Limit
```json
{
  "error": "daily_limit_exceeded",
  "message": "Daily request limit exceeded (30 queries). Limit resets at midnight UTC.",
  "rate_info": {
    "daily_remaining": 0,
    "retry_after": null
  }
}
```

#### 503 Service Unavailable - Budget Exceeded
```json
{
  "error": "budget_exceeded",
  "message": "Daily budget exceeded. Service will resume at midnight UTC.",
  "budget_info": {
    "daily_total": 1.05,
    "daily_budget": 1.0,
    "percent_used": 105
  }
}
```

#### 500 Internal Server Error
```json
{
  "error": "Query processing failed",
  "details": "ChromaDB connection timeout"
}
```

---

## 5. Complete TypeScript Implementation

### API Client Class
```typescript
// src/api/dndRagClient.ts

export interface QueryRequest {
  question: string;
  debug?: boolean;
  k?: number;
}

export interface QueryResponse {
  answer: string;
  diagnostics: string[];
  errors: string[];
  meta: {
    user_id: string;
    rate_limit: {
      remaining_burst: number;
      daily_remaining: number;
    };
    cost: {
      query_cost: number;
      daily_total: number;
      daily_budget: number;
    };
  };
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface ErrorResponse {
  error: string;
  message?: string;
  details?: string;
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

export class DnDRagClient {
  private baseUrl: string;
  private getAuthToken: () => string | null;

  constructor(baseUrl: string, getAuthToken: () => string | null) {
    this.baseUrl = baseUrl;
    this.getAuthToken = getAuthToken;
  }

  /**
   * Check API health status
   */
  async health(): Promise<{ status: string; service: string; version: string }> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.status}`);
    }
    return response.json();
  }

  /**
   * Query the D&D RAG system
   */
  async query(request: QueryRequest): Promise<QueryResponse> {
    const token = this.getAuthToken();
    if (!token) {
      throw new Error('Authentication token not found. Please log in.');
    }

    const response = await fetch(`${this.baseUrl}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
      credentials: 'include',
    });

    const data = await response.json();

    if (!response.ok) {
      // Handle error responses
      const error = data as ErrorResponse;
      
      if (response.status === 429) {
        if (error.rate_info?.retry_after) {
          throw new Error(
            `Rate limit exceeded. Please wait ${error.rate_info.retry_after} seconds.`
          );
        } else {
          throw new Error('Daily request limit exceeded. Try again tomorrow.');
        }
      } else if (response.status === 503) {
        throw new Error('Daily budget exceeded. Service will resume at midnight UTC.');
      } else if (response.status === 401) {
        throw new Error('Authentication failed. Please log in again.');
      } else {
        throw new Error(error.message || error.error || 'Query failed');
      }
    }

    return data as QueryResponse;
  }
}
```

### React Hook Example
```typescript
// src/hooks/useDnDRag.ts
import { useState } from 'react';
import { DnDRagClient, QueryRequest, QueryResponse } from '../api/dndRagClient';

const isDevelopment = window.location.hostname === 'localhost';
const API_BASE_URL = isDevelopment 
  ? 'http://localhost:5000' 
  : 'https://dndchat.gravitycar.com';

const client = new DnDRagClient(
  API_BASE_URL,
  () => localStorage.getItem('auth_token')
);

export function useDnDRag() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<QueryResponse | null>(null);

  const query = async (question: string, debug = false, k = 15) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await client.query({ question, debug, k });
      setResponse(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { query, loading, error, response };
}
```

### React Component Example
```typescript
// src/components/DnDChat.tsx
import React, { useState } from 'react';
import { useDnDRag } from '../hooks/useDnDRag';

export function DnDChat() {
  const [question, setQuestion] = useState('');
  const { query, loading, error, response } = useDnDRag();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    
    try {
      await query(question);
      setQuestion(''); // Clear input on success
    } catch (err) {
      // Error is already set in hook
      console.error('Query failed:', err);
    }
  };

  return (
    <div className="dnd-chat">
      <h2>D&D 1st Edition Rules Assistant</h2>
      
      <form onSubmit={handleSubmit}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about D&D 1st Edition rules..."
          rows={3}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Thinking...' : 'Ask'}
        </button>
      </form>

      {error && (
        <div className="error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {response && (
        <div className="response">
          <div className="answer">
            <h3>Answer:</h3>
            <p>{response.answer}</p>
          </div>

          <div className="meta">
            <div className="rate-limit">
              <strong>Rate Limit:</strong>
              <span>Burst: {response.meta.rate_limit.remaining_burst}/15</span>
              <span>Daily: {response.meta.rate_limit.daily_remaining}/30</span>
            </div>
            
            <div className="cost">
              <strong>Cost:</strong>
              <span>Query: ${response.meta.cost.query_cost.toFixed(6)}</span>
              <span>Today: ${response.meta.cost.daily_total.toFixed(4)} / ${response.meta.cost.daily_budget.toFixed(2)}</span>
            </div>
          </div>

          {response.diagnostics && response.diagnostics.length > 0 && (
            <details className="diagnostics">
              <summary>Diagnostics ({response.diagnostics.length})</summary>
              <ul>
                {response.diagnostics.map((diag, i) => (
                  <li key={i}>{diag}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## 6. Error Handling Best Practices

### User-Friendly Error Messages
```typescript
function formatErrorMessage(response: ErrorResponse, statusCode: number): string {
  switch (statusCode) {
    case 429:
      if (response.rate_info?.retry_after) {
        return `You've asked too many questions too quickly. Please wait ${response.rate_info.retry_after} seconds.`;
      } else {
        return `You've reached your daily limit of 30 questions. Try again tomorrow!`;
      }
    
    case 503:
      return `We've hit our daily budget limit. The service will be back at midnight UTC.`;
    
    case 401:
      return `Your session expired. Please log in again.`;
    
    case 400:
      return `Invalid request: ${response.error}`;
    
    default:
      return `Something went wrong: ${response.message || response.error}`;
  }
}
```

### Retry Logic for Rate Limits
```typescript
async function queryWithRetry(
  client: DnDRagClient, 
  request: QueryRequest, 
  maxRetries = 1
): Promise<QueryResponse> {
  try {
    return await client.query(request);
  } catch (error) {
    if (error instanceof Error && error.message.includes('wait')) {
      // Extract retry_after from error message or response
      const match = error.message.match(/wait (\d+) seconds/);
      if (match && maxRetries > 0) {
        const retryAfter = parseInt(match[1]);
        console.log(`Retrying in ${retryAfter} seconds...`);
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        return queryWithRetry(client, request, maxRetries - 1);
      }
    }
    throw error;
  }
}
```

---

## 7. Testing Your Integration

### Test Cases

#### 1. Health Check
```bash
curl http://localhost:5000/health
```
**Expected**: `{ "status": "ok", "service": "dnd_rag", "version": "1.0.0" }`

#### 2. Valid Query
```bash
./scripts/test_flask_query.sh "Bearer YOUR_TOKEN" "What is a beholder?"
```
**Expected**: HTTP 200 with answer

#### 3. Missing Token
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
```
**Expected**: HTTP 401 with "Missing Authorization header"

#### 4. Rate Limit Test
```bash
# Make 16 requests rapidly
for i in {1..16}; do
  ./scripts/test_flask_query.sh "Bearer TOKEN" "Test $i"
done
```
**Expected**: First 15 succeed (200), 16th fails (429)

#### 5. Invalid JSON
```bash
curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d 'invalid json'
```
**Expected**: HTTP 400 with "Invalid JSON"

---

## 8. Important Notes

### CORS Configuration
- **Local**: Flask allows `http://localhost:3000` and `http://localhost:3001`
- **Production**: Flask will allow `https://react.gravitycar.com`
- Browser automatically sends `Origin` header - don't override it

### Token Expiration
- JWT tokens expire after 1 hour (check `exp` claim)
- Handle 401 errors by redirecting to login
- Consider refreshing token proactively before expiration

### Rate Limiting Strategy
- **15 burst capacity**: Users can ask 15 questions immediately
- **1 per minute refill**: After burst, 1 token refills every 60 seconds
- **30 daily limit**: Hard cap of 30 questions per user per day
- Resets at midnight UTC

### Query Performance
- **Typical response time**: 3-8 seconds
- **Fast queries** (simple monster lookup): 2-3 seconds
- **Slow queries** (complex comparison): 8-15 seconds
- Show loading indicator to user during query

### Debug Mode
- Set `debug: true` in request to see retrieval diagnostics
- Useful for understanding why certain answers were generated
- Shows document chunks retrieved and adaptive filtering decisions

---

## 9. Quick Start Checklist

For UI development, you need:

- [ ] Flask running locally: `./scripts/start_flask.sh`
- [ ] ChromaDB running (or ChromaCloud configured)
- [ ] Valid JWT token from `localStorage.getItem('auth_token')`
- [ ] React dev server on port 3000
- [ ] TypeScript interfaces for request/response types
- [ ] Error handling for all HTTP status codes (200, 400, 401, 429, 503, 500)
- [ ] Loading state while query is processing
- [ ] Display for rate limit and cost information
- [ ] User-friendly error messages

---

## 10. Example Test Flow

```typescript
// 1. Check if API is available
const health = await client.health();
console.log('API Status:', health.status); // "ok"

// 2. Submit a query
const response = await client.query({
  question: "What is a beholder?",
  debug: false,
  k: 15
});

// 3. Display answer
console.log('Answer:', response.answer);

// 4. Show rate limit status
console.log('Remaining queries today:', response.meta.rate_limit.daily_remaining);

// 5. Show cost
console.log('Query cost:', response.meta.cost.query_cost);
```

---

## 11. HTTP Status Codes Summary

| Status | Meaning | Response Fields | User Action |
|--------|---------|----------------|-------------|
| **200** | Success | answer, diagnostics, errors, meta, usage | Display answer |
| **400** | Bad Request | error, details | Show error message |
| **401** | Unauthorized | error | Redirect to login |
| **429** | Rate Limit | error, message, rate_info | Show wait time or daily limit message |
| **500** | Server Error | error, details | Show generic error, retry later |
| **503** | Budget Exceeded | error, message, budget_info | Show budget exceeded message |

---

**Ready for UI Development!** All Flask endpoints are working and tested. Start with the health check, then implement the query interface.
