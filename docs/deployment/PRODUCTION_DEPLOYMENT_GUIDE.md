# Production Deployment Guide
## D&D 1st Edition RAG System → dndchat.gravitycar.com

**Last Updated**: November 10, 2025  
**Architecture**: Apache + PHP Proxy + Flask + ChromaCloud  
**Deployment Time**: ~30 minutes

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Local Embedding to ChromaCloud](#phase-1-local-embedding-to-chromacloud)
4. [Phase 2: Automated Deployment](#phase-2-automated-deployment)
5. [Phase 3: Verification & Testing](#phase-3-verification--testing)
6. [Common Operations](#common-operations)
7. [Troubleshooting](#troubleshooting)
8. [Security Model](#security-model)

---

## Architecture Overview

### Production Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRODUCTION ENVIRONMENT                        │
│                    dndchat.gravitycar.com                        │
└─────────────────────────────────────────────────────────────────┘

┌────────────────┐     HTTPS (443)     ┌────────────────┐
│  React Client  │ ──────────────────► │ Apache 2.4.52  │
│ react.gravitycar│                     │ Let's Encrypt  │
│ .com           │                     │ SSL (Trusted)  │
└────────────────┘                     └────────┬───────┘
                                               │
                                               │ HTTP (localhost)
                                               ▼
                                      ┌────────────────┐
                                      │ api_proxy.php  │
                                      │ (CORS handler) │
                                      └────────┬───────┘
                                               │
                                               │ HTTP (127.0.0.1:5000)
                                               ▼
                                      ┌────────────────┐
                                      │ Flask + Gunicorn│
                                      │ (4 workers)    │
                                      │ localhost only │
                                      └────────┬───────┘
                                               │
                   ┌───────────────────────────┼───────────────────┐
                   │                           │                   │
                   │ HTTPS                     │ HTTPS             │ HTTPS
                   ▼                           ▼                   ▼
          ┌────────────────┐         ┌─────────────┐     ┌─────────────┐
          │  ChromaCloud   │         │  OpenAI API │     │  Auth API   │
          │  Collection:   │         │  GPT-4o-mini│     │  api.gravitycar│
          │  adnd_1e       │         │  Embeddings │     │  .com       │
          └────────────────┘         └─────────────┘     └─────────────┘
```

### Why PHP Proxy?

**Hurricane Electric Hosting Constraints:**
- ❌ No `mod_proxy_http` module available
- ❌ No `mod_wsgi` module available (confirmed by HE support)
- ❌ No access to SSL private keys (can't run Flask with SSL directly)
- ✅ Only port 5000 exposed for custom services
- ✅ Apache with Let's Encrypt SSL (trusted certificate)
- ✅ PHP available for CGI scripts

**Solution**: PHP reverse proxy
- Apache terminates SSL with Let's Encrypt (trusted, no browser warnings)
- PHP forwards requests to Flask on localhost (secure, kernel IPC)
- Flask runs HTTP-only, bound to 127.0.0.1 (not accessible from internet)
- CORS handled by PHP (Flask headers stripped to prevent duplicates)

### Request Flow

```
1. Browser sends HTTPS request to https://dndchat.gravitycar.com/api/query
   ↓
2. Apache receives on port 443, validates SSL certificate
   ↓
3. Apache .htaccess routes /api/* to api_proxy.php
   ↓
4. PHP proxy:
   - Handles OPTIONS preflight (returns 200 with CORS headers)
   - Forwards POST/GET to http://127.0.0.1:5000 via cURL
   - Strips Flask's CORS headers from response
   - Adds its own CORS headers
   - Returns response to browser
   ↓
5. Flask processes request:
   - Validates JWT token (from api.gravitycar.com)
   - Checks rate limit (15 burst, 30 daily)
   - Queries ChromaCloud for relevant D&D rule chunks
   - Generates answer with OpenAI GPT-4o-mini
   - Returns JSON response
   ↓
6. Browser receives HTTPS response with single CORS header
```

---

## Prerequisites

### 1. Local Machine Setup

**Required:**
- ✅ Python 3.10+ with virtualenv activated
- ✅ Project cloned: `/home/mike/projects/gravitycar_dnd1st_rag_system`
- ✅ All 3 chunk files generated:
  - `data/chunks/chunks_Monster_Manual_(1e).json` (294 chunks)
  - `data/chunks/chunks_Players_Handbook_(1e)_organized.json` (735 chunks)
  - `data/chunks/chunks_DMG_with_query_must.json` (1,184 chunks)
- ✅ `.env.dndchat.production` configured with:
  - ChromaCloud credentials (tenant ID, database, API key)
  - OpenAI API key
  - Auth API URL: `https://api.gravitycar.com`
  - CORS origins: `https://react.gravitycar.com,https://gravitycar.com`
  - Flask host: `127.0.0.1` (localhost only)
  - Flask port: `5000`

**Verify:**
```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check chunk files exist
ls -lh data/chunks/chunks_*.json

# Verify .env.dndchat.production exists
cat .env.dndchat.production | grep -E "chroma_cloud|openai|FLASK_HOST"
```

### 2. Hurricane Electric Server Access

**Required:**
- ✅ SSH access: `ssh gravityc@dog.he.net`
- ✅ Subdomain configured: `dndchat.gravitycar.com`
- ✅ Document root: `/home/gravityc/public_html/dndchat.gravitycar.com`
- ✅ Let's Encrypt SSL certificate (automatically managed by HE)
- ✅ Python 3.10+ available on server
- ✅ Apache 2.4+ with `.htaccess` support
- ✅ PHP available for CGI execution

**Verify:**
```bash
# Test SSH connection
ssh gravityc@dog.he.net "python3 --version && php --version"

# Check if subdomain directory exists
ssh gravityc@dog.he.net "ls -la /home/gravityc/public_html/ | grep dndchat"
```

### 3. ChromaCloud Account

**Required:**
- ✅ Tenant ID: `120ffaa8-32bf-4e7d-823d-c587bd8a5202`
- ✅ Database: `adnd_1e`
- ✅ API Key: (in `.env.dndchat.production`)

**Verify:**
```bash
# Test ChromaCloud connectivity (after embedding)
source venv/bin/activate
dnd-rag collections
# Should show: adnd_1e collection
```

---

## Phase 1: Local Embedding to ChromaCloud

**⚠️ CRITICAL**: This step MUST be done from your LOCAL machine BEFORE deployment.  
**Time**: ~15 minutes  
**Cost**: ~$0.12 USD

### Step 1.1: Activate Virtual Environment

```bash
cd /home/mike/projects/gravitycar_dnd1st_rag_system
source venv/bin/activate
```

### Step 1.2: Verify ChromaCloud Configuration

Edit `.env` (local, NOT `.env.dndchat.production`) and temporarily enable ChromaCloud:

```bash
nano .env
```

**Uncomment these lines:**
```dotenv
chroma_cloud_api_key=YOUR_CHROMACLOUD_API_KEY
chroma_cloud_tenant_id=YOUR_TENANT_ID
chroma_cloud_database=adnd_1e
```

**Save and exit** (Ctrl+O, Enter, Ctrl+X)

### Step 1.3: Embed Books to ChromaCloud

**Option A: Automated Script (Recommended)**

```bash
# Make script executable (if not already)
chmod +x scripts/embed_to_chromacloud.sh

# Run automated embedding
./scripts/embed_to_chromacloud.sh
```

**Option B: Manual Embedding**

```bash
# Monster Manual (~2 min, $0.02)
dnd-embed data/chunks/chunks_Monster_Manual_\(1e\).json adnd_1e

# Player's Handbook (~5 min, $0.04)
dnd-embed data/chunks/chunks_Players_Handbook_\(1e\)_organized.json adnd_1e

# Dungeon Master's Guide (~8 min, $0.06)
dnd-embed data/chunks/chunks_DMG_with_query_must.json adnd_1e
```

**Expected Output (each book):**
```
Embedding progress: 100%|████████████████| 294/294 [02:15<00:00]
✅ Successfully embedded 294 chunks to ChromaCloud collection 'adnd_1e'
```

### Step 1.4: Verify Embeddings

```bash
# List collections
dnd-rag collections
# Expected output:
# Collections in ChromaCloud:
#   - adnd_1e (2213 documents)

# Test query
dnd-query adnd_1e "What is a beholder?" --debug
# Expected: Detailed beholder description from Monster Manual
```

### Step 1.5: Disable ChromaCloud in Local .env

**Re-comment the ChromaCloud lines** to return to local ChromaDB:

```bash
nano .env
```

**Comment out these lines:**
```dotenv
# chroma_cloud_api_key=YOUR_CHROMACLOUD_API_KEY
# chroma_cloud_tenant_id=YOUR_TENANT_ID
# chroma_cloud_database=adnd_1e
```

**✅ Phase 1 Complete!** ChromaCloud now has all D&D books embedded.

---

## Phase 2: Automated Deployment

**Time**: ~5-10 minutes  
**What it does**: Uploads code, creates venv, configures PHP proxy, starts Flask

### Step 2.1: Verify Deployment Script

```bash
# Make script executable (if not already)
chmod +x scripts/deploy_to_production.sh

# Review what will be deployed (optional)
cat scripts/deploy_to_production.sh | grep "cp.*TEMP_DIR"
```

**Files included in deployment:**
- ✅ `src/api.py` - Flask REST API
- ✅ `src/query/` - Query engine and adaptive filtering
- ✅ `src/utils/` - ChromaDB connector, rate limiter, cost tracker, token validator
- ✅ `scripts/` - setup_venv.sh, start_flask.sh, stop_flask.sh
- ✅ `.env.dndchat.production` → `~/.env.dndchat` (secured outside web root)
- ✅ `api_proxy.php` - PHP reverse proxy
- ✅ `.htaccess.production` → `.htaccess` - Apache routing rules
- ✅ `requirements.txt` - Python dependencies
- ✅ `pyproject.toml` - Package configuration

**Files excluded (not needed on server):**
- ❌ chunkers/ - Only needed for local PDF processing
- ❌ converters/ - Only needed for local PDF → Markdown
- ❌ embedders/ - Only needed for local embedding to ChromaCloud
- ❌ preprocessors/ - Only needed for local data preparation
- ❌ transformers/ - Only needed for local data transformation

### Step 2.2: Run Deployment Script

```bash
./scripts/deploy_to_production.sh dog.he.net gravityc
```

**What happens:**
1. ✅ Checks local prerequisites (.env.dndchat.production, src/, scripts/)
2. ✅ Tests SSH connectivity
3. ✅ Creates remote directory: `/home/gravityc/public_html/dndchat.gravitycar.com`
4. ✅ Creates deployment tarball with query-only modules
5. ✅ Uploads tarball via SCP
6. ✅ Extracts files on remote server
7. ✅ Moves `.env.dndchat` to `~/.env.dndchat` (outside public_html, chmod 600)
8. ✅ Sets file permissions (scripts executable)
9. ✅ Runs `setup_venv.sh` (creates venv, installs dependencies)
10. ✅ Installs package in development mode (`pip install -e .`)
11. ✅ Verifies ChromaCloud connectivity from server
12. ✅ Starts Flask server with `start_flask.sh` (HTTP, localhost:5000)
13. ✅ Runs integration tests (health check, collections list)
14. ✅ Prints deployment summary

**Expected Output (final):**
```
✓ =========================================
✓   Deployment Complete!
✓ =========================================

Server Details:
  • Host: dog.he.net
  • Directory: /home/gravityc/public_html/dndchat.gravitycar.com
  • Flask Port: 5000 (localhost only)
  • ChromaDB: ChromaCloud

Useful Commands:
  • View logs: ssh gravityc@dog.he.net 'tail -f /home/gravityc/public_html/dndchat.gravitycar.com/flask.log'
  • Restart Flask: ssh gravityc@dog.he.net 'cd /home/gravityc/public_html/dndchat.gravitycar.com && ./scripts/stop_flask.sh && ./scripts/start_flask.sh'
```

**✅ Phase 2 Complete!** Code deployed, Flask running, Apache + PHP proxy configured.

---

## Phase 3: Verification & Testing

**Time**: ~5 minutes

### Step 3.1: Test Health Endpoint (Local Server)

```bash
# SSH into server
ssh gravityc@dog.he.net

# Navigate to project directory
cd /home/gravityc/public_html/dndchat.gravitycar.com

# Test Flask health endpoint (localhost)
curl http://localhost:5000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "service": "dnd_rag",
  "version": "1.0.0"
}
```

### Step 3.2: Test Health Endpoint (HTTPS via PHP Proxy)

```bash
# From your LOCAL machine (not SSH)
curl https://dndchat.gravitycar.com/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "service": "dnd_rag",
  "version": "1.0.0"
}
```

**If this fails**, run the PHP proxy test script:
```bash
# From your local project directory
./scripts/test_php_proxy.sh
```

### Step 3.3: Test CORS Headers

```bash
# Test OPTIONS preflight
curl -X OPTIONS https://dndchat.gravitycar.com/api/query \
  -H "Origin: https://react.gravitycar.com" \
  -v 2>&1 | grep -i access-control
```

**Expected Output:**
```
< Access-Control-Allow-Origin: https://react.gravitycar.com
< Access-Control-Allow-Methods: GET, POST, OPTIONS
< Access-Control-Allow-Headers: Content-Type, Authorization
< Access-Control-Allow-Credentials: true
```

**⚠️ Important**: Should see SINGLE `Access-Control-Allow-Origin` header, not duplicates.

### Step 3.4: Test Query Endpoint (with JWT token)

**From React frontend:**
1. Visit `https://react.gravitycar.com`
2. Log in via OAuth2 (should receive JWT token)
3. Submit query: "What is a beholder?"
4. Check browser Network tab for:
   - ✅ Request to `https://dndchat.gravitycar.com/api/query` (no port)
   - ✅ Status: 200 OK
   - ✅ Single `Access-Control-Allow-Origin` header in response
   - ✅ JSON response with `answer`, `meta`, `usage` fields

**OR** test with curl (if you have a valid JWT token):

```bash
# Replace YOUR_JWT_TOKEN with actual token from localStorage
curl -X POST https://dndchat.gravitycar.com/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Origin: https://react.gravitycar.com" \
  -d '{"question": "What is a beholder?"}'
```

**Expected Response:**
```json
{
  "answer": "A beholder is a floating spherical creature...",
  "diagnostics": [...],
  "errors": [],
  "meta": {
    "user_id": "...",
    "rate_limit": {
      "remaining_burst": 14,
      "daily_remaining": 29
    },
    "cost": {
      "query_cost": 0.000324,
      "daily_total": 0.000324,
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

### Step 3.5: Check Flask Logs

```bash
# SSH into server (if not already)
ssh gravityc@dog.he.net

# View recent logs
tail -50 /home/gravityc/public_html/dndchat.gravitycar.com/flask.log

# OR continuously monitor logs
tail -f /home/gravityc/public_html/dndchat.gravitycar.com/flask.log
```

**Look for:**
- ✅ No errors or exceptions
- ✅ "Flask API Starting..." messages
- ✅ "Booting worker" messages (4 workers)
- ✅ Query requests logged with response times

**✅ Phase 3 Complete!** Deployment verified and operational.

---

## Common Operations

### Restart Flask Server

```bash
ssh gravityc@dog.he.net
cd /home/gravityc/public_html/dndchat.gravitycar.com
./scripts/stop_flask.sh
./scripts/start_flask.sh
```

### View Logs

```bash
# Recent logs
ssh gravityc@dog.he.net 'tail -50 /home/gravityc/public_html/dndchat.gravitycar.com/flask.log'

# Live monitoring
ssh gravityc@dog.he.net 'tail -f /home/gravityc/public_html/dndchat.gravitycar.com/flask.log'

# Search for errors
ssh gravityc@dog.he.net 'grep -i error /home/gravityc/public_html/dndchat.gravitycar.com/flask.log | tail -20'
```

### Check Flask Status

```bash
# Check if Flask process is running
ssh gravityc@dog.he.net 'ps aux | grep gunicorn'

# Check health endpoint
ssh gravityc@dog.he.net 'curl -s http://localhost:5000/health'
```

### Update Code (Redeploy)

```bash
# From local machine
./scripts/deploy_to_production.sh dog.he.net gravityc

# The script will:
# 1. Stop Flask
# 2. Upload new code
# 3. Restart Flask
```

### Update Environment Variables

```bash
# SSH into server
ssh gravityc@dog.he.net

# Edit .env.dndchat (outside web root)
nano ~/.env.dndchat

# After editing, restart Flask
cd /home/gravityc/public_html/dndchat.gravitycar.com
./scripts/stop_flask.sh
./scripts/start_flask.sh
```

### Auto-Restart on Server Reboot

```bash
# SSH into server
ssh gravityc@dog.he.net

# Edit crontab
crontab -e

# Add this line:
@reboot cd /home/gravityc/public_html/dndchat.gravitycar.com && ./scripts/start_flask.sh

# Save and exit
```

---

## Troubleshooting

### 1. Flask Not Starting

**Symptom**: `curl http://localhost:5000/health` fails

**Diagnosis:**
```bash
ssh gravityc@dog.he.net
cd /home/gravityc/public_html/dndchat.gravitycar.com

# Check if process is running
ps aux | grep gunicorn

# Check logs for errors
tail -50 flask.log

# Check if port is in use
netstat -tuln | grep 5000
```

**Solutions:**
- **Port already in use**: `./scripts/stop_flask.sh` then `./scripts/start_flask.sh`
- **Python errors**: Check `flask.log` for traceback, fix code, redeploy
- **Missing dependencies**: `source venv/bin/activate && pip install -r requirements.txt`
- **ChromaCloud connection failed**: Verify `~/.env.dndchat` has correct credentials

### 2. HTTPS Request Returns 404

**Symptom**: `curl https://dndchat.gravitycar.com/health` returns 404

**Diagnosis:**
```bash
ssh gravityc@dog.he.net
cd /home/gravityc/public_html/dndchat.gravitycar.com

# Check if .htaccess exists
ls -la .htaccess

# Check if api_proxy.php exists
ls -la api_proxy.php

# Check Apache error logs (if accessible)
tail -50 ~/error_log
```

**Solutions:**
- **Missing .htaccess**: Redeploy with `./scripts/deploy_to_production.sh`
- **Missing api_proxy.php**: Redeploy with `./scripts/deploy_to_production.sh`
- **Apache not reading .htaccess**: Contact HE support (requires `AllowOverride All`)

### 3. CORS Errors in Browser

**Symptom**: Browser console shows "blocked by CORS policy"

**Diagnosis:**
```bash
# Test CORS headers
curl -X OPTIONS https://dndchat.gravitycar.com/api/query \
  -H "Origin: https://react.gravitycar.com" \
  -v 2>&1 | grep -i access-control
```

**Solutions:**
- **Missing CORS headers**: Check `api_proxy.php` has CORS handling code
- **Wrong origin**: Verify `https://react.gravitycar.com` is in allowed origins
- **Duplicate headers**: Ensure PHP strips Flask's CORS headers (check line ~145 in `api_proxy.php`)

### 4. Duplicate CORS Headers

**Symptom**: Browser shows "header contains multiple values"

**Diagnosis:**
```bash
curl -v https://dndchat.gravitycar.com/health 2>&1 | grep -i access-control-allow-origin
```

**Expected**: Single `Access-Control-Allow-Origin` header  
**If duplicate**: Flask and PHP both setting headers

**Solution:**
Verify `api_proxy.php` line ~145 has:
```php
if (strpos($header_lower, 'access-control-') === 0) {
    continue; // Skip Flask's CORS headers
}
```

If missing, redeploy or manually edit `api_proxy.php` on server.

### 5. 401 Unauthorized Errors

**Symptom**: Query returns "Invalid or expired token"

**Diagnosis:**
- Check if JWT token is valid (check expiration time)
- Verify AUTH_API_URL in `~/.env.dndchat` is correct
- Test token validation endpoint

**Solutions:**
- **Expired token**: Log in again to get new token
- **Wrong AUTH_API_URL**: Update `~/.env.dndchat` and restart Flask
- **Token validator error**: Check Flask logs for details

### 6. 429 Rate Limit Exceeded

**Symptom**: "Rate limit exceeded. Please wait 60 seconds"

**Explanation**: User hit burst limit (15 queries) or daily limit (30 queries)

**Solutions:**
- **Burst limit**: Wait 60 seconds, then retry (1 token refills per minute)
- **Daily limit**: Wait until midnight UTC for reset
- **Increase limits**: Edit rate limits in `src/utils/rate_limiter.py`, redeploy

### 7. 503 Budget Exceeded

**Symptom**: "Daily budget exceeded. Service will resume at midnight UTC."

**Explanation**: Total OpenAI costs exceeded $1.00 daily budget

**Solutions:**
- **Wait**: Budget resets at midnight UTC
- **Increase budget**: Edit `DAILY_BUDGET` in `~/.env.dndchat`, restart Flask
- **Optimize costs**: Reduce `k` parameter (fewer chunks retrieved)

### 8. ChromaCloud Connection Fails

**Symptom**: "ChromaCloud connection failed" in logs

**Diagnosis:**
```bash
ssh gravityc@dog.he.net
cd /home/gravityc/public_html/dndchat.gravitycar.com
source venv/bin/activate

# Test ChromaCloud connection
python3 -c "
from src.utils.chromadb_connector import ChromaDBConnector
connector = ChromaDBConnector()
print(connector.list_collections())
"
```

**Solutions:**
- **Wrong credentials**: Verify `~/.env.dndchat` has correct `chroma_cloud_*` values
- **Network issue**: Test outbound HTTPS: `curl https://api.trychroma.com/api/v1/version`
- **Collection missing**: Re-run Phase 1 embedding from local machine

---

## Security Model

### SSL/TLS Termination

```
Internet (HTTPS) → Apache (Let's Encrypt SSL) → PHP (HTTP localhost) → Flask (HTTP 127.0.0.1)
                   ↑ Encryption ends here       ↑ Localhost traffic (kernel IPC, not network)
```

**Why Flask doesn't need SSL:**
- Apache terminates SSL with trusted Let's Encrypt certificate
- PHP → Flask communication is localhost-only (127.0.0.1)
- Localhost traffic never touches network interface (kernel memory only)
- Flask bound to 127.0.0.1 means not accessible from internet

**Why this is secure:**
- ✅ Traffic encrypted over internet (HTTPS to Apache)
- ✅ Trusted certificate (Let's Encrypt, no browser warnings)
- ✅ Flask not exposed to internet (localhost binding)
- ✅ PHP proxy validates origin before forwarding

### Environment File Security

```bash
# .env.dndchat stored OUTSIDE web root
/home/gravityc/
├── public_html/
│   └── dndchat.gravitycar.com/  # Web-accessible
│       ├── api_proxy.php
│       ├── .htaccess
│       └── src/
└── .env.dndchat  # NOT web-accessible (chmod 600)
```

**Why:**
- ❌ If `.env.dndchat` was in `public_html/`, it could be downloaded via HTTP
- ✅ Stored in parent directory, Apache cannot serve it
- ✅ `chmod 600` means only owner can read (not group/world)

### CORS Policy

**Allowed Origins:**
- `https://react.gravitycar.com` - React frontend
- `https://gravitycar.com` - Marketing site

**Blocked:**
- All other origins (prevents cross-site attacks)

**Headers:**
- `Access-Control-Allow-Credentials: true` - Allows cookies/auth headers
- `Access-Control-Allow-Methods: GET, POST, OPTIONS` - Limited methods
- `Access-Control-Allow-Headers: Content-Type, Authorization` - Limited headers

### Rate Limiting

**Per-User Limits:**
- 15 burst capacity (immediate queries)
- 1 token refill per 60 seconds
- 30 daily limit (hard cap)

**Why:**
- Prevents abuse (spam, denial of service)
- Controls OpenAI API costs
- Fair usage across users

### Cost Controls

**Daily Budget: $1.00 USD**
- Tracks OpenAI API costs per user
- Service returns 503 when budget exceeded
- Resets at midnight UTC

**Why:**
- Prevents runaway costs
- Predictable monthly expense (~$30/month)
- User quota enforcement

---

## File Locations Reference

### Local Development
```
/home/mike/projects/gravitycar_dnd1st_rag_system/
├── .env                          # Local config (ChromaDB localhost)
├── .env.dndchat.production       # Production config (ChromaCloud)
├── api_proxy.php                 # PHP reverse proxy
├── .htaccess.production          # Apache config template
├── src/
│   ├── api.py                   # Flask REST API
│   ├── query/                   # Query engine
│   └── utils/                   # Shared utilities
├── scripts/
│   ├── deploy_to_production.sh  # Automated deployment
│   ├── start_flask.sh           # Flask startup (HTTP)
│   ├── stop_flask.sh            # Flask shutdown
│   └── test_php_proxy.sh        # Proxy verification
└── data/chunks/                 # Embedded book chunks (local only)
```

### Production Server
```
/home/gravityc/
├── .env.dndchat                 # Production config (chmod 600, outside web root)
└── public_html/dndchat.gravitycar.com/
    ├── api_proxy.php            # PHP reverse proxy
    ├── .htaccess                # Apache routing rules
    ├── flask.log                # Flask application logs
    ├── gunicorn.pid             # Gunicorn process ID
    ├── src/
    │   ├── api.py              # Flask REST API
    │   ├── query/              # Query engine
    │   └── utils/              # Shared utilities
    ├── scripts/
    │   ├── start_flask.sh      # Flask startup
    │   └── stop_flask.sh       # Flask shutdown
    └── venv/                   # Python virtual environment
```

---

## Quick Reference

### URLs

| Environment | Base URL | Health Check |
|-------------|----------|--------------|
| **Local** | `http://localhost:5000` | `http://localhost:5000/health` |
| **Production** | `https://dndchat.gravitycar.com` | `https://dndchat.gravitycar.com/health` |

**⚠️ Important**: Production URLs have **NO PORT** (standard HTTPS 443)

### SSH Commands

```bash
# Connect to server
ssh gravityc@dog.he.net

# Restart Flask
ssh gravityc@dog.he.net 'cd /home/gravityc/public_html/dndchat.gravitycar.com && ./scripts/stop_flask.sh && ./scripts/start_flask.sh'

# View logs
ssh gravityc@dog.he.net 'tail -f /home/gravityc/public_html/dndchat.gravitycar.com/flask.log'

# Check status
ssh gravityc@dog.he.net 'curl -s http://localhost:5000/health'
```

### Deployment Commands

```bash
# Full automated deployment
./scripts/deploy_to_production.sh dog.he.net gravityc

# Test PHP proxy after deployment
./scripts/test_php_proxy.sh

# Embed books to ChromaCloud (run once)
./scripts/embed_to_chromacloud.sh
```

---

**Last Updated**: November 10, 2025  
**Maintainer**: Mike @ GravityCar  
**Support**: Check `flask.log` for errors, or contact HE support for server issues
