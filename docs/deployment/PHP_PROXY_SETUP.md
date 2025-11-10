# PHP Proxy Deployment Guide

## Overview

This deployment uses a **PHP script as a reverse proxy** to enable HTTPS for the Flask API without requiring mod_proxy or mod_wsgi Apache modules.

**Architecture:**
```
Browser (HTTPS) → Apache (Let's Encrypt SSL) → PHP Proxy Script → Flask (HTTP localhost:5000)
```

## Components

### 1. `api_proxy.php`
- Receives HTTPS requests from Apache
- Forwards to Flask on `http://127.0.0.1:5000`
- Returns Flask responses to client over HTTPS
- Handles headers, CORS, error cases

### 2. `.htaccess`
- Routes `/api/*` and `/health` to PHP proxy
- Sets security headers
- Handles CORS preflight (OPTIONS)

### 3. Flask Backend
- Runs on `127.0.0.1:5000` (HTTP only)
- Not exposed to internet (only Apache can reach it)
- Configured via `.env.dndchat.production`

## Deployment Steps

### 1. Deploy to Server
```bash
./scripts/deploy_to_production.sh dog.he.net gravityc
```

This will:
- Upload PHP proxy script
- Upload `.htaccess` configuration
- Deploy Flask application
- Start Flask on localhost:5000

### 2. Verify Deployment
```bash
chmod +x scripts/test_php_proxy.sh
./scripts/test_php_proxy.sh
```

Expected output:
```
✓ Flask is running
✓ Apache HTTPS is working
✓ Health endpoint works through PHP proxy
✓ CORS headers present
✓ SSL certificate is valid
```

### 3. Test from Browser
```bash
# Should return JSON with no SSL warnings
curl https://dndchat.gravitycar.com/health

# Expected:
{"status":"ok","service":"dnd_rag","version":"1.0.0",...}
```

### 4. Update React Frontend

Change API URL in your React app:

**Old (with port):**
```javascript
const API_URL = "https://dndchat.gravitycar.com:5000/api/query";
```

**New (no port):**
```javascript
const API_URL = "https://dndchat.gravitycar.com/api/query";
```

## Security Considerations

### ✅ Secure Aspects

1. **SSL Termination at Apache**
   - Let's Encrypt certificate (trusted by all browsers)
   - TLS 1.2+ encryption for client connections

2. **Localhost-Only Flask**
   - Flask binds to `127.0.0.1:5000`
   - Not accessible from internet
   - PHP proxy is the only entry point

3. **Token Security**
   - User tokens encrypted over internet (HTTPS)
   - Decrypted only at Apache (required to read request)
   - Forwarded to Flask via localhost (kernel memory, not network)

4. **X-Forwarded Headers**
   - PHP adds `X-Forwarded-For`, `X-Real-IP`
   - Flask can log original client IP
   - Useful for rate limiting, debugging

### ⚠️ Considerations

1. **PHP Overhead**
   - Each request processes through PHP (minimal ~5-10ms)
   - Acceptable for API usage patterns

2. **Error Handling**
   - If Flask crashes, PHP returns 502 Bad Gateway
   - Monitor Flask logs: `tail -f flask.log`

3. **Performance**
   - Flask keeps persistent connections to ChromaCloud
   - No startup penalty per request (unlike CGI)
   - Performance similar to mod_proxy

## Troubleshooting

### Flask Not Running
```bash
ssh gravityc@dog.he.net
cd /home/gravityc/public_html/dndchat.gravitycar.com
./scripts/start_flask.sh
```

### Check Flask Logs
```bash
ssh gravityc@dog.he.net "tail -50 /home/gravityc/public_html/dndchat.gravitycar.com/flask.log"
```

### Test PHP Proxy Directly
```bash
# From server
ssh gravityc@dog.he.net
cd /home/gravityc/public_html/dndchat.gravitycar.com
php api_proxy.php
```

### CORS Issues
If CORS errors occur:
1. Check `.htaccess` has correct origins
2. Verify Flask CORS config in `src/api.py`
3. Test with: `curl -I -H "Origin: https://react.gravitycar.com" https://dndchat.gravitycar.com/health`

### 502 Bad Gateway
- Flask is not running on localhost:5000
- Check: `curl -s http://localhost:5000/health`
- Restart Flask if needed

## Comparison to Alternatives

| Solution | SSL | Performance | Complexity | HE Support Needed |
|----------|-----|-------------|------------|-------------------|
| **PHP Proxy** | ✅ Trusted | Good | Low | ❌ None |
| mod_proxy | ✅ Trusted | Excellent | Low | ✅ Required |
| mod_wsgi | ✅ Trusted | Excellent | Medium | ✅ Required |
| Self-signed cert | ⚠️ Untrusted | Excellent | Low | ❌ None |
| Cloudflare | ✅ Trusted | Excellent | Low | ❌ None |

## Future Migration Path

If HE later enables mod_proxy_http:
1. Replace `.htaccess` with mod_proxy rules
2. Remove `api_proxy.php`
3. Keep Flask config unchanged (already localhost:5000)

If switching to Cloudflare:
1. Point DNS to Cloudflare
2. Keep current setup (works with Cloudflare)
3. Cloudflare adds CDN, DDoS protection

## Monitoring

### Health Check
```bash
# Automated monitoring
watch -n 30 'curl -s https://dndchat.gravitycar.com/health | jq'
```

### Request Logs
Flask logs all requests to `flask.log`:
```bash
tail -f flask.log | grep "Query request"
```

### Apache Access Logs
Check Apache logs for PHP proxy requests:
```bash
ssh gravityc@dog.he.net "tail -f /var/log/apache2/access.log | grep dndchat"
```

---

**Status:** Production Ready ✅  
**Last Updated:** November 9, 2025  
**Maintainer:** Mike (mike@gravitycar.com)
