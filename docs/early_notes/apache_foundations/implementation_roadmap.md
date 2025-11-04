# Complete Implementation Roadmap

**Decision Date**: November 3, 2025  
**Context**: Multi-session plan for Apache deployment of DNDRag  
**Status**: ✅ Planning Complete - Ready to Execute

---

## Overview

This roadmap breaks the Apache deployment into 4 discrete sessions, each with clear deliverables and rollback points. Each session builds on the previous one, allowing you to test incrementally and catch issues early.

**Total Estimated Time**: 10-12 hours across 4 sessions  
**Complexity**: Moderate (existing RAG system + OAuth integration)  
**Risk**: Low (incremental approach with testing at each stage)

---

## Session 1: Output Buffer Refactoring (3-4 hours)

**Goal**: Replace 200+ print() statements with structured RAGOutput class

**Why First**: This change is prerequisite for Flask API (can't return dict with print() statements)

### Tasks

1. **Create RAGOutput class** (30 min)
   - File: `src/utils/rag_output.py`
   - Three buckets: answer, diagnostics, errors
   - Methods: `add_answer()`, `add_diagnostic()`, `add_error()`, `to_dict()`
   - Thread-safe: Not required (per-request instance)

2. **Update DnDRAG class** (90 min)
   - File: `src/query/docling_query.py`
   - Add `output: RAGOutput` parameter to `__init__()` (optional, defaults to None)
   - Replace ~70 print statements:
     - `print("Retrieving...")` → `output.add_diagnostic("Retrieving...")`
     - `print(f"Error: {e}")` → `output.add_error(f"Error: {e}")`
   - Change `query()` return type: `str` → `dict`
     - Return: `{"answer": str, "diagnostics": [...], "errors": [...]}`

3. **Update CLI entry points** (60 min)
   - File: `main.py`
     - Create RAGOutput instance
     - Pass to DnDRAG constructor
     - Handle dict return: `result['answer']`
     - Print diagnostics if `--debug` flag
   - File: `src/cli.py` (similar changes)

4. **Test thoroughly** (60 min)
   - Fighter XP Table test (acid test for end-to-end pipeline)
   - Monster comparison query ("owlbear vs orc")
   - Spell query ("What is magic missile?")
   - Interactive mode (verify user experience unchanged)
   - Debug mode (verify diagnostics printed correctly)

### Deliverables

- [ ] `src/utils/rag_output.py` created with RAGOutput class
- [ ] `src/query/docling_query.py` refactored (no print statements)
- [ ] `main.py` updated to handle dict return
- [ ] `src/cli.py` updated to handle dict return
- [ ] All tests pass (Fighter XP Table, monster comparison, spell query)
- [ ] Git commit: `feat: refactor output to RAGOutput class`

### Rollback Plan

If this session fails:
```bash
git checkout feature/apache~1  # Revert to before Session 1
```

---

## Session 2: Flask API + Rate Limiting (3-4 hours)

**Goal**: Create Flask REST API with OAuth2 validation and rate limiting

**Why Second**: Builds on RAGOutput refactoring from Session 1

### Tasks

1. **Create utility classes** (90 min)
   - File: `src/utils/rate_limiter.py`
     - TokenBucket class (token bucket algorithm)
     - Methods: `allow_request(user_id)` → `(bool, dict)`
   - File: `src/utils/cost_tracker.py`
     - CostTracker class (daily budget tracking)
     - Methods: `record_query()`, `is_budget_exceeded()`, `_send_alert()`
   - File: `src/utils/token_validator.py`
     - TokenValidator class (JWT validation with caching)
     - Methods: `validate_token(token)` → `user_info dict`
   - File: `src/utils/config.py`
     - Helper functions: `get_env_float()`, `get_env_int()`, `get_env_string()`

2. **Create Flask API** (90 min)
   - File: `src/api.py`
     - Flask app with CORS middleware
     - `@app.before_request`: Token validation + rate limiting
     - `@app.after_request`: CORS headers
     - Route: `POST /api/query` (main RAG endpoint)
     - Route: `GET /api/health` (health check, no auth)

3. **Update .env** (15 min)
   - Add OAuth2 config:
     ```
     API_GRAVITYCAR_BASE_URL=https://api.gravitycar.com
     TOKEN_CACHE_TTL=300
     ```
   - Add rate limiting config:
     ```
     DAILY_BUDGET_USD=1.00
     DAILY_USER_REQUEST_LIMIT=30
     TOKEN_BUCKET_CAPACITY=15
     TOKEN_REFILL_RATE=0.016667
     ```
   - Add email alerts config:
     ```
     ALERT_EMAIL=mike@example.com
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USER=...
     SMTP_PASS=...
     ```

4. **Test locally** (60 min)
   - Start Flask: `flask run --host=0.0.0.0 --port=5000`
   - Get JWT token from browser localStorage (after logging into react.gravitycar.com)
   - Test health endpoint:
     ```bash
     curl http://localhost:5000/api/health
     ```
   - Test query endpoint with valid token:
     ```bash
     curl -X POST http://localhost:5000/api/query \
       -H "Authorization: Bearer $TOKEN" \
       -H "Origin: http://localhost:3000" \
       -H "Content-Type: application/json" \
       -d '{"question": "What is a beholder?"}'
     ```
   - Test rate limiting (make 16 requests rapidly)
   - Test invalid token (should get HTTP 401)
   - Test wrong origin (should get HTTP 403)

### Deliverables

- [ ] `src/utils/rate_limiter.py` created
- [ ] `src/utils/cost_tracker.py` created
- [ ] `src/utils/token_validator.py` created
- [ ] `src/utils/config.py` created
- [ ] `src/api.py` created with Flask app
- [ ] `.env` updated with new config variables
- [ ] Local testing passes (all 6 test scenarios)
- [ ] Git commit: `feat: add Flask API with OAuth2 and rate limiting`

### Rollback Plan

If this session fails:
```bash
git checkout feature/apache~1  # Revert to after Session 1
# CLI still works, Flask API not deployed yet
```

---

## Session 3: Apache Deployment (2-3 hours)

**Goal**: Deploy Flask app to production with Apache + mod_wsgi

**Why Third**: Flask API tested locally in Session 2

### Tasks

1. **Prepare server** (30 min)
   - SSH to gravitycar.com
   - Install mod_wsgi: `sudo apt-get install libapache2-mod-wsgi-py3`
   - Enable modules: `sudo a2enmod ssl rewrite headers wsgi`
   - Clone/update git repo
   - Create virtualenv and install dependencies
   - Copy `.env` file (with production values)
   - Set file permissions (see apache_configuration.md)

2. **Create wsgi.py** (15 min)
   - File: `/home/mike/projects/gravitycar_dnd1st_rag_system/wsgi.py`
   - WSGI entry point for Apache
   - Loads .env, imports Flask app, validates environment

3. **Configure Apache virtual host** (30 min)
   - File: `/etc/apache2/sites-available/dndchat.gravitycar.com.conf`
   - Copy configuration from apache_configuration.md
   - Update paths to match server
   - Enable site: `sudo a2ensite dndchat.gravitycar.com.conf`
   - Test config: `sudo apache2ctl configtest`

4. **Generate SSL certificate** (15 min)
   - Run certbot: `sudo certbot --apache -d dndchat.gravitycar.com`
   - Verify DNS first: `dig dndchat.gravitycar.com A`
   - Follow certbot prompts
   - Verify cert installed: `sudo ls -l /etc/letsencrypt/live/dndchat.gravitycar.com/`

5. **Start and test** (60 min)
   - Reload Apache: `sudo systemctl reload apache2`
   - Check logs: `sudo tail -f /var/log/apache2/dndchat_error.log`
   - Test health: `curl https://dndchat.gravitycar.com/api/health`
   - Test query with real token (from browser)
   - Monitor worker processes: `ps aux | grep wsgi:dndchat`
   - Test graceful reload: `touch wsgi.py`

6. **Monitor for 1 hour** (60 min)
   - Watch logs for errors
   - Make 20-30 test queries
   - Verify rate limiting works
   - Check budget tracking
   - Verify token cache (should see reduced API calls)

### Deliverables

- [ ] mod_wsgi installed on server
- [ ] wsgi.py created
- [ ] Apache virtual host configured
- [ ] SSL certificate generated (Let's Encrypt)
- [ ] Service running: `https://dndchat.gravitycar.com/api/health` returns 200
- [ ] Query endpoint works with real JWT token
- [ ] Rate limiting enforced (test with 16+ requests)
- [ ] Git commit: `feat: add Apache deployment configuration`

### Rollback Plan

If deployment fails:
```bash
# On server
sudo a2dissite dndchat.gravitycar.com.conf
sudo systemctl reload apache2
# Service offline, no impact to other sites
```

---

## Session 4: React Integration + Polish (2-3 hours)

**Goal**: Connect React UI to DNDChat API and add monitoring

**Why Last**: Backend fully tested before touching frontend

### Tasks

1. **Create React API client** (60 min)
   - File: `react.gravitycar.com/src/api/dndchat.ts`
   - DnDChatAPI class with axios
   - Add Authorization header interceptor
   - Handle HTTP 429 (rate limit) gracefully
   - Handle HTTP 503 (budget exceeded) gracefully

2. **Create D&D Chat component** (90 min)
   - File: `react.gravitycar.com/src/components/DnDChat.tsx`
   - Text input for question
   - Display RAG answer
   - Show rate limit status (X remaining burst, Y remaining daily)
   - Show loading spinner (queries take 5-30 seconds)
   - Handle errors gracefully

3. **Add monitoring dashboard** (Optional, 60 min)
   - File: `src/admin/dashboard.py` (Flask Blueprint)
   - Route: `GET /admin/stats` (requires admin user)
   - Display:
     - Daily budget usage ($X / $1.00)
     - Requests today (N / 30 per user)
     - Top users by cost
     - Cache hit rate

4. **Test end-to-end** (30 min)
   - Login to react.gravitycar.com
   - Navigate to D&D Chat
   - Ask 5 test questions
   - Verify answers are correct
   - Verify rate limit status updates
   - Test burst (ask 15 questions rapidly)
   - Test rate limit (ask 16th question, should get friendly error)

### Deliverables

- [ ] DnDChatAPI class created in React
- [ ] DnDChat component created and integrated
- [ ] End-to-end flow works: React → DNDChat API → ChromaDB → OpenAI → React
- [ ] Rate limit UI shows remaining burst/daily
- [ ] Error handling polished (429, 503, network errors)
- [ ] Git commit (React repo): `feat: integrate D&D RAG chat`
- [ ] Git commit (DNDRag repo): `feat: add admin dashboard` (if implemented)

### Rollback Plan

If React integration fails:
```bash
# React rollback
git checkout main  # Revert React changes

# Backend still works
# Can test with curl or Postman
```

---

## Testing Strategy (Throughout All Sessions)

### The Fighter XP Table Test (Acid Test)

Run this test after **every session** to verify end-to-end pipeline integrity:

```bash
# Session 1 (CLI)
python src/query/docling_query.py dnd_unified \
  "How many experience points does a fighter need to become 9th level?"

# Session 2 (Flask local)
curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many experience points does a fighter need to become 9th level?"}'

# Session 3 (Flask production)
curl -X POST https://dndchat.gravitycar.com/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://react.gravitycar.com" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many experience points does a fighter need to become 9th level?"}'

# Session 4 (React UI)
# Ask question in UI, verify answer is "250,001 XP"
```

**Expected Answer**: "A fighter needs 250,001 experience points to become 9th level."

**If this fails at any stage, STOP and debug before proceeding.**

### Additional Test Queries

1. **Monster comparison** (tests entity-aware retrieval):
   ```
   "What is the difference between a red dragon and a white dragon?"
   ```

2. **Spell query** (tests spell detection):
   ```
   "What does the magic missile spell do?"
   ```

3. **Category query** (tests parent category injection):
   ```
   "Tell me about demons in D&D"
   ```

4. **Rate limit test** (tests token bucket):
   - Make 15 requests rapidly (should succeed)
   - Make 16th request (should get HTTP 429)
   - Wait 60 seconds
   - Make another request (should succeed)

---

## Monitoring & Maintenance (Post-Deployment)

### Daily Checks (First Week)

```bash
# Check daily budget usage
sudo grep "daily_cost" /var/log/apache2/dndchat_error.log | tail -n 5

# Check for errors
sudo grep -i error /var/log/apache2/dndchat_error.log | tail -n 20

# Check Apache worker status
ps aux | grep wsgi:dndchat

# Check SSL cert expiration
sudo certbot certificates
```

### Weekly Checks (Ongoing)

```bash
# Review cost trends
# (If you implement admin dashboard, use that instead)

# Check for security updates
sudo apt-get update
sudo apt-get upgrade

# Verify auto-renewal is working
sudo systemctl status certbot.timer
```

### Monthly Tasks

```bash
# Review rate limiting effectiveness
# - Are users hitting limits?
# - Are limits too strict or too loose?

# Update dependencies
cd /home/mike/projects/gravitycar_dnd1st_rag_system
source venv/bin/activate
pip list --outdated
# pip install --upgrade <package>

# Backup critical files
sudo tar -czf /backup/dndchat_$(date +%Y%m%d).tar.gz \
  /home/mike/projects/gravitycar_dnd1st_rag_system \
  /etc/apache2/sites-available/dndchat.gravitycar.com.conf \
  /etc/letsencrypt/live/dndchat.gravitycar.com/
```

---

## Success Criteria

### Session 1 Success
- ✅ CLI still works (no regressions)
- ✅ Fighter XP Table test passes
- ✅ `main.py` handles dict return correctly
- ✅ Debug mode shows diagnostics

### Session 2 Success
- ✅ Flask runs locally without errors
- ✅ Health endpoint returns 200
- ✅ Query endpoint returns structured JSON
- ✅ Token validation works with real JWT
- ✅ Rate limiting enforces 15-burst, 1/min refill
- ✅ Invalid tokens get HTTP 401

### Session 3 Success
- ✅ `https://dndchat.gravitycar.com/api/health` returns 200
- ✅ Query endpoint works from curl with real token
- ✅ SSL certificate is valid (A+ rating on SSL Labs)
- ✅ No errors in Apache logs for 1 hour
- ✅ Worker processes stay alive (no crashes)

### Session 4 Success
- ✅ Users can ask questions in React UI
- ✅ Answers display correctly (formatted, readable)
- ✅ Rate limit status visible to users
- ✅ Errors handled gracefully (friendly messages)
- ✅ No JavaScript console errors

---

## Risk Assessment & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Session 1 breaks CLI** | High | Low | Git rollback, comprehensive testing |
| **OAuth token validation fails** | High | Medium | Test with production API in Session 2 |
| **Apache permission errors** | Medium | Medium | Follow permission checklist carefully |
| **SSL cert generation fails** | Medium | Low | Verify DNS first, use certbot dry-run |
| **Rate limiting too strict** | Low | Medium | Start conservative, adjust based on feedback |
| **Budget exceeded** | Low | Low | $1/day very generous for 2-5 users |
| **ChromaDB connection fails** | High | Low | Verify ChromaDB running before deployment |

---

## Decision Points (Require Your Approval)

### Before Session 1
- [ ] Approved: RAGOutput class design (three-bucket taxonomy)
- [ ] Approved: Dependency injection pattern (output parameter)
- [ ] Approved: Dict return type from query()

### Before Session 2
- [ ] Approved: Token bucket parameters (15 burst, 1/min refill)
- [ ] Approved: Daily limits ($1.00 budget, 30 requests/user)
- [ ] Approved: Token cache TTL (5 minutes)

### Before Session 3
- [ ] Approved: mod_wsgi configuration (2 processes, 5 threads)
- [ ] Approved: File permissions (750 for code, 640 for .env)
- [ ] Approved: DNS record (dndchat.gravitycar.com CNAME)

### Before Session 4
- [ ] Approved: React integration approach (axios + interceptors)
- [ ] Approved: Error handling UX (friendly messages)
- [ ] Approved: Rate limit display to users

---

## Final Checklist (Before Declaring Victory)

- [ ] All 4 sessions completed
- [ ] Fighter XP Table test passes in production
- [ ] React UI can query DNDChat API
- [ ] Rate limiting enforced (tested with burst)
- [ ] Budget tracking active (tested with mock high costs)
- [ ] Email alerts configured (tested manually)
- [ ] SSL certificate valid and auto-renewing
- [ ] Apache logs show no errors for 24 hours
- [ ] 5 real users tested the system
- [ ] Documentation updated (README, setup guides)
- [ ] Monitoring dashboard accessible (if implemented)
- [ ] Backup strategy documented and tested
- [ ] Git branches merged to main

---

## Post-Launch Optimization (Optional Future Work)

### Performance
- [ ] Add Redis cache for token validation (faster than in-memory)
- [ ] Implement request queuing for burst traffic
- [ ] Add Prometheus metrics for monitoring
- [ ] Optimize ChromaDB query performance

### Features
- [ ] Add chat history (store previous Q&A in session)
- [ ] Add follow-up questions ("What about at 10th level?")
- [ ] Add spell slot calculator
- [ ] Add encounter difficulty calculator

### Security
- [ ] Add request signature validation (HMAC)
- [ ] Add rate limiting per IP (in addition to per user)
- [ ] Add DDoS protection (Cloudflare or fail2ban)
- [ ] Add honeypot endpoint to detect bots

---

## Estimated Timeline

| Session | Duration | Best Time | Dependencies |
|---------|----------|-----------|--------------|
| **Session 1** | 3-4 hours | Weekday evening | None |
| **Session 2** | 3-4 hours | Weekend morning | Session 1 complete |
| **Session 3** | 2-3 hours | Weekend afternoon | Session 2 tested locally |
| **Session 4** | 2-3 hours | Weekday evening | Session 3 deployed and stable |

**Total**: 10-14 hours across 2 weekends

**Suggested Schedule**:
- **Weekend 1**: Sessions 1-2 (local development and testing)
- **Mid-week**: Session 3 (production deployment during low traffic)
- **Weekend 2**: Session 4 (React integration and polish)

---

## Communication Plan

### Notify Users Before Deployment

**Email to 2-5 beta users**:
```
Subject: New D&D RAG Chat Feature - Beta Testing

Hi [Name],

I'm launching a new feature: an AI-powered D&D 1st Edition rules assistant!

You can now ask questions like:
- "How many XP does a fighter need for 9th level?"
- "What is a beholder?"
- "What's the difference between red and white dragons?"

Access: react.gravitycar.com (new D&D Chat tab)

Usage limits:
- 15 questions burst, then 1 per minute
- 30 questions per day

Let me know if you encounter any issues!

- Mike
```

### Announce Launch

**After Session 4 complete**:
```
Subject: D&D RAG Chat - Now Live!

The D&D rules assistant is now live at react.gravitycar.com!

Features:
✅ Instant answers from official rulebooks
✅ Compares monsters, spells, character classes
✅ Explains complex rules with examples
✅ Cites specific rules context

Try it out and send feedback!

- Mike
```

---

## Conclusion

You now have a complete, tested, production-ready plan for deploying your D&D RAG system with Apache, OAuth2 authentication, rate limiting, and cost tracking.

**Next Action**: Review this roadmap, approve the decision points, and schedule Session 1.

**Questions to Ask Yourself**:
1. Do I have 3-4 hours available for Session 1 this week?
2. Is my local ChromaDB running and tested?
3. Do I have access to a real JWT token from api.gravitycar.com?
4. Am I comfortable with the file permission changes in Session 3?
5. Do I want to implement the admin dashboard (Session 4 optional)?

When you're ready, I'll guide you through Session 1 step-by-step.

---

**Decision Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Last Updated**: November 3, 2025  
**Status**: ✅ Complete - Ready to Execute
