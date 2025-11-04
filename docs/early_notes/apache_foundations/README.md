# Apache Deployment Planning - Index

**Status**: ✅ Planning Complete  
**Last Updated**: November 3, 2025  
**Decision Owner**: Mike

---

## Document Overview

This directory contains all architectural decisions and implementation plans for deploying the D&D 1st Edition RAG system to production with Apache web server.

### Quick Links

1. **[Flask Decision](./flask.md)** - Why Flask? Framework selection rationale
2. **[Output Buffer Design](./output_buffer_design.md)** - RAGOutput class with dependency injection
3. **[Rate Limiting Strategy](./rate_limiting_strategy.md)** - Token bucket + cost tracking (initial design)
4. **[Rate Limiting Final](./rate_limiting_final.md)** - Finalized config ($1/day, 15 burst, 30/day per user)
5. **[OAuth Integration](./oauth_integration.md)** - Token validation with api.gravitycar.com
6. **[Apache Configuration](./apache_configuration.md)** - Virtual host, mod_wsgi, SSL setup
7. **[Implementation Roadmap](./implementation_roadmap.md)** - 4-session execution plan

---

## Read in This Order

### For High-Level Understanding
1. Read **Implementation Roadmap** first - gives you the big picture
2. Skim **Flask Decision** - understand why Flask was chosen
3. Review **OAuth Integration** - understand auth flow

### For Implementation
1. **Session 1**: Read **Output Buffer Design** in detail
2. **Session 2**: Read **Rate Limiting Final** + **OAuth Integration** in detail
3. **Session 3**: Read **Apache Configuration** in detail
4. **Session 4**: Refer back to **Implementation Roadmap** for React integration

### For Troubleshooting
- **Auth issues?** → OAuth Integration (token validation section)
- **Rate limit issues?** → Rate Limiting Final (testing strategy)
- **Apache errors?** → Apache Configuration (monitoring & debugging)
- **Permission errors?** → Apache Configuration (file permissions)

---

## Key Decisions Summary

### Architecture
- **Framework**: Flask (lightweight, 4.3MB, battle-tested)
- **Deployment**: Apache mod_wsgi daemon mode (2 processes, 5 threads)
- **Authentication**: OAuth2 JWT tokens via api.gravitycar.com
- **Rate Limiting**: Token bucket (15 burst, 1/min refill) + daily cap (30/day)
- **Cost Protection**: $1.00/day budget with email alerts

### Security
- **Token Validation**: Cached 5 minutes (reduces API calls by 80%)
- **CORS**: Only allows react.gravitycar.com + www.gravitycar.com
- **SSL**: Let's Encrypt (auto-renewing)
- **Defense in Depth**: CORS + Token + Rate Limit + Budget + HTTPS

### Infrastructure
- **Domain**: dndchat.gravitycar.com (separate subdomain)
- **ChromaDB**: localhost:8060 (not exposed to internet)
- **OpenAI**: gpt-4o-mini + text-embedding-3-small
- **Workers**: 10 concurrent requests (2 processes × 5 threads)

---

## Configuration Quick Reference

### Environment Variables (`.env`)

```bash
# OpenAI
openai_api_key=sk-...

# ChromaDB
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/

# OAuth2
API_GRAVITYCAR_BASE_URL=https://api.gravitycar.com
TOKEN_CACHE_TTL=300  # 5 minutes

# Rate Limiting
DAILY_BUDGET_USD=1.00
DAILY_USER_REQUEST_LIMIT=30
TOKEN_BUCKET_CAPACITY=15
TOKEN_REFILL_RATE=0.016667  # 1/60

# Email Alerts
ALERT_EMAIL=mike@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
```

### Apache Virtual Host

**Path**: `/etc/apache2/sites-available/dndchat.gravitycar.com.conf`

Key settings:
- **Daemon**: 2 processes, 5 threads
- **Python**: `/home/mike/projects/gravitycar_dnd1st_rag_system/venv`
- **WSGI**: `/home/mike/projects/gravitycar_dnd1st_rag_system/wsgi.py`
- **SSL**: Let's Encrypt cert for dndchat.gravitycar.com

### File Permissions

```bash
# Project directory
chmod 750 /home/mike/projects/gravitycar_dnd1st_rag_system
chown mike:www-data /home/mike/projects/gravitycar_dnd1st_rag_system

# .env file (contains secrets)
chmod 640 .env

# ChromaDB data (shared resource)
chmod 770 /home/mike/projects/rag/chroma/
chown mike:www-data /home/mike/projects/rag/chroma/
```

---

## Implementation Phases

### Phase 1: Output Buffer (Session 1)
**Time**: 3-4 hours  
**Goal**: Replace print() statements with RAGOutput class  
**Deliverable**: CLI returns dict instead of string

### Phase 2: Flask API (Session 2)
**Time**: 3-4 hours  
**Goal**: Create REST API with OAuth + rate limiting  
**Deliverable**: Flask runs locally, validates tokens

### Phase 3: Apache Deployment (Session 3)
**Time**: 2-3 hours  
**Goal**: Deploy to production with mod_wsgi + SSL  
**Deliverable**: https://dndchat.gravitycar.com/api/health returns 200

### Phase 4: React Integration (Session 4)
**Time**: 2-3 hours  
**Goal**: Connect React UI to DNDChat API  
**Deliverable**: End-to-end flow works in browser

---

## Testing Checkpoints

### After Each Session

Run the **Fighter XP Table Test** (acid test):

```bash
# Expected answer: "250,001 XP"
# Question: "How many experience points does a fighter need to become 9th level?"

# Session 1 (CLI)
python main.py query "How many experience points does a fighter need to become 9th level?"

# Session 2 (Flask local)
curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "..."}'

# Session 3 (Flask production)
curl -X POST https://dndchat.gravitycar.com/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "..."}'
```

**If this test fails at any stage, STOP and debug before proceeding.**

---

## Common Issues & Solutions

| Issue | Document | Section |
|-------|----------|---------|
| "Permission denied" | apache_configuration.md | File Permissions & Ownership |
| "Invalid token" | oauth_integration.md | Token Validation Strategy |
| "Rate limit exceeded" | rate_limiting_final.md | Testing Strategy |
| "Budget exceeded" | rate_limiting_final.md | Cost Tracker Class |
| "ChromaDB connection failed" | apache_configuration.md | Common Issues & Solutions |
| "502 Bad Gateway" | apache_configuration.md | Monitoring & Debugging |

---

## Rollback Strategy

Each session has a git commit checkpoint:

```bash
# View commits
git log --oneline feature/apache

# Rollback to specific session
git checkout <commit-hash>

# Or rollback 1 session
git checkout HEAD~1
```

**Rollback is safe** - each session builds on the previous, no destructive changes.

---

## Success Metrics

### Technical Metrics
- [ ] End-to-end latency < 30 seconds (95th percentile)
- [ ] Uptime > 99.9% (< 1 hour downtime per month)
- [ ] Rate limit violations < 5% of requests
- [ ] Daily budget never exceeded
- [ ] SSL certificate valid (A+ rating)

### User Experience Metrics
- [ ] Answers are accurate (Fighter XP Table test passes)
- [ ] Response time feels fast (< 10 sec for simple queries)
- [ ] Error messages are friendly (not technical jargon)
- [ ] Rate limits don't frustrate users (15 burst sufficient)
- [ ] Users understand quota remaining (visible in UI)

---

## Timeline

**Total Time**: 10-14 hours across 2-3 weeks

**Suggested Schedule**:
- **Week 1, Weekend**: Sessions 1-2 (local dev, 6-8 hours)
- **Week 2, Midweek**: Session 3 (production deploy, 2-3 hours)
- **Week 2, Weekend**: Session 4 (React integration, 2-3 hours)
- **Week 3**: Monitor, adjust, polish

---

## Next Steps

1. **Review** all documents in this directory
2. **Approve** decision points in implementation_roadmap.md
3. **Schedule** Session 1 (need 3-4 uninterrupted hours)
4. **Prepare** environment:
   - [ ] ChromaDB running locally
   - [ ] Virtual environment activated
   - [ ] Git branch `feature/apache` checked out
   - [ ] JWT token from api.gravitycar.com available for testing
5. **Execute** Session 1 (with mentor mode guidance)

---

## Questions Before Starting?

Consider these before Session 1:

1. **Do I understand the OAuth flow?** (See oauth_integration.md)
2. **Am I comfortable with the rate limits?** (See rate_limiting_final.md)
3. **Do I have server access for Session 3?** (SSH to gravitycar.com)
4. **Is my DNS ready?** (dndchat.gravitycar.com CNAME or A record)
5. **Do I have backup of current system?** (Git tag + .env backup)

If you answered "yes" to all 5, you're ready to begin!

---

**Status**: ✅ Planning Phase Complete  
**Next Action**: Review documents → Approve decisions → Schedule Session 1

**Mentor Available For**:
- Session 1 guidance (step-by-step code changes)
- Debugging issues (check logs, fix permissions)
- Architecture questions (why this approach vs alternatives)
- Code review (ensure quality before commit)

Let's build this! 🚀
