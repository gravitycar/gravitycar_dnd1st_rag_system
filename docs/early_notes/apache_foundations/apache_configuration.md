# Apache Configuration for dndchat.gravitycar.com

**Decision Date**: November 3, 2025  
**Context**: Apache + mod_wsgi configuration for Flask RAG API  
**Status**: ✅ Approved - Ready for Implementation

---

## Architecture Summary

```
Internet → Apache (port 443) → mod_wsgi → Flask App → DNDRag → ChromaDB
                                                             → OpenAI API
```

**Key Components**:
- **Apache 2.4.52** (Ubuntu) - Reverse proxy + SSL termination
- **mod_wsgi** (daemon mode) - Python WSGI application server
- **Flask** - REST API wrapper
- **Let's Encrypt** - Free SSL certificate
- **ChromaDB** - Running on localhost:8060
- **OpenAI API** - External service

---

## Apache Virtual Host Configuration

### File: `/etc/apache2/sites-available/dndchat.gravitycar.com.conf`

```apache
<VirtualHost *:80>
    ServerName dndchat.gravitycar.com
    ServerAdmin mike@gravitycar.com

    # Redirect all HTTP to HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName dndchat.gravitycar.com
    ServerAdmin mike@gravitycar.com

    # SSL Configuration (Let's Encrypt)
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/dndchat.gravitycar.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/dndchat.gravitycar.com/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/dndchat_error.log
    CustomLog ${APACHE_LOG_DIR}/dndchat_access.log combined
    LogLevel info

    # WSGI Configuration
    WSGIDaemonProcess dndchat \
        user=www-data \
        group=www-data \
        processes=2 \
        threads=5 \
        python-path=/home/mike/projects/gravitycar_dnd1st_rag_system \
        python-home=/home/mike/projects/gravitycar_dnd1st_rag_system/venv \
        display-name=%{GROUP} \
        lang='en_US.UTF-8' \
        locale='en_US.UTF-8'

    WSGIProcessGroup dndchat
    WSGIApplicationGroup %{GLOBAL}
    
    # Mount Flask application at /api
    WSGIScriptAlias /api /home/mike/projects/gravitycar_dnd1st_rag_system/wsgi.py

    # Application directory permissions
    <Directory /home/mike/projects/gravitycar_dnd1st_rag_system>
        <IfVersion >= 2.4>
            Require all granted
        </IfVersion>
        <IfVersion < 2.4>
            Order allow,deny
            Allow from all
        </IfVersion>
    </Directory>

    # WSGI script permissions
    <Files wsgi.py>
        <IfVersion >= 2.4>
            Require all granted
        </IfVersion>
        <IfVersion < 2.4>
            Order allow,deny
            Allow from all
        </IfVersion>
    </Files>

    # Security Headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "no-referrer-when-downgrade"

    # CORS headers handled by Flask (don't set here)
    # Let Flask middleware control CORS for proper origin validation

    # Health check endpoint (no auth required)
    <Location /api/health>
        # Public endpoint
    </Location>

    # Query endpoint (requires OAuth token - validated by Flask)
    <Location /api/query>
        # Auth handled by Flask middleware
    </Location>
</VirtualHost>
```

---

## WSGI Entry Point

### File: `/home/mike/projects/gravitycar_dnd1st_rag_system/wsgi.py`

```python
#!/usr/bin/env python3
"""
WSGI entry point for Apache mod_wsgi.

This file is executed by Apache to start the Flask application.
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

# Load environment variables from .env
from dotenv import load_dotenv
env_path = project_root / '.env'
load_dotenv(env_path)

# Import Flask application
from src.api import app as application

# Verify critical environment variables
required_vars = [
    'openai_api_key',
    'chroma_host_url',
    'chroma_host_port',
    'API_GRAVITYCAR_BASE_URL',
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Log startup (will appear in Apache error log)
print(f"[WSGI] DNDChat API starting...", file=sys.stderr)
print(f"[WSGI] Project root: {project_root}", file=sys.stderr)
print(f"[WSGI] ChromaDB: {os.getenv('chroma_host_url')}:{os.getenv('chroma_host_port')}", file=sys.stderr)
print(f"[WSGI] OAuth API: {os.getenv('API_GRAVITYCAR_BASE_URL')}", file=sys.stderr)
print(f"[WSGI] Collection: {os.getenv('default_collection_name', 'dnd_unified')}", file=sys.stderr)
print(f"[WSGI] Daily budget: ${os.getenv('DAILY_BUDGET_USD', '1.00')}", file=sys.stderr)
print(f"[WSGI] DNDChat API ready", file=sys.stderr)
```

---

## mod_wsgi Configuration Explained

### Daemon Process Configuration

```apache
WSGIDaemonProcess dndchat \
    user=www-data \              # Run as www-data (standard Apache user)
    group=www-data \             # Run as www-data group
    processes=2 \                # 2 worker processes
    threads=5 \                  # 5 threads per process = 10 concurrent requests
    python-path=/home/mike/... \ # Add project root to Python path
    python-home=/home/mike/.../venv \  # Use virtualenv Python
    display-name=%{GROUP} \      # Show as "dndchat" in process list
    lang='en_US.UTF-8' \         # UTF-8 encoding for text
    locale='en_US.UTF-8'
```

**Why 2 processes × 5 threads?**
- **Total capacity**: 10 concurrent requests
- **User load**: 2-5 users, burst of 15 requests = max 5 concurrent (worst case)
- **Headroom**: 2x capacity for spikes
- **Memory**: ~200MB per process × 2 = 400MB total
- **Isolation**: If one process crashes, the other continues serving

**Why daemon mode?**
- **Persistent workers**: Processes stay alive between requests (fast)
- **Graceful reload**: `touch wsgi.py` reloads without downtime
- **Resource isolation**: Doesn't interfere with other Apache virtual hosts
- **Better logging**: Separate error logs per daemon

### Process vs Thread Trade-offs

| Configuration | Pros | Cons | Best For |
|--------------|------|------|----------|
| **2 proc × 5 thread** | Balanced, fault-tolerant | Moderate memory | Production (chosen) |
| **1 proc × 10 thread** | Lower memory (200MB) | Single point of failure | Testing |
| **4 proc × 2 thread** | Max fault tolerance | High memory (800MB) | High-traffic sites |

---

## File Permissions & Ownership

### Required Permissions

```bash
# Project directory - readable by www-data
sudo chown -R mike:www-data /home/mike/projects/gravitycar_dnd1st_rag_system
sudo chmod -R 750 /home/mike/projects/gravitycar_dnd1st_rag_system

# .env file - readable by www-data, not world-readable (contains secrets)
sudo chmod 640 /home/mike/projects/gravitycar_dnd1st_rag_system/.env

# wsgi.py - executable by www-data
sudo chmod 750 /home/mike/projects/gravitycar_dnd1st_rag_system/wsgi.py

# Python source files - readable by www-data
sudo find /home/mike/projects/gravitycar_dnd1st_rag_system/src -type f -name "*.py" -exec chmod 640 {} \;
sudo find /home/mike/projects/gravitycar_dnd1st_rag_system/src -type d -exec chmod 750 {} \;

# Virtualenv - readable by www-data
sudo chmod -R 750 /home/mike/projects/gravitycar_dnd1st_rag_system/venv

# ChromaDB data - writable by www-data (if storing data locally)
# NOTE: Your ChromaDB is at /home/mike/projects/rag/chroma/ - ensure www-data can read
sudo chown -R mike:www-data /home/mike/projects/rag/chroma/
sudo chmod -R 770 /home/mike/projects/rag/chroma/

# Apache log directory - writable by www-data (already configured)
ls -l /var/log/apache2/dndchat_*.log
```

### Security Considerations

**Why not 777 (world-readable)?**
- ❌ `.env` contains API keys (OpenAI, SMTP passwords)
- ❌ Source code may contain business logic you don't want public
- ✅ Only www-data (Apache) and mike (owner) need access

**Why 750 (owner:rwx, group:r-x, world:none)?**
- ✅ Mike can edit files (owner rwx)
- ✅ Apache can read/execute (group r-x)
- ✅ Other users can't see anything (world ---)

---

## Let's Encrypt SSL Setup

### Initial Certificate Generation

```bash
# Install certbot (if not already installed)
sudo apt-get update
sudo apt-get install certbot python3-certbot-apache

# Generate certificate for dndchat.gravitycar.com
sudo certbot --apache -d dndchat.gravitycar.com

# Follow prompts:
# 1. Enter email for renewal notifications
# 2. Agree to terms of service
# 3. Choose whether to redirect HTTP to HTTPS (Yes - recommended)

# Certbot will:
# - Verify domain ownership via HTTP challenge
# - Generate certificate files in /etc/letsencrypt/live/dndchat.gravitycar.com/
# - Automatically configure Apache SSL settings
# - Set up auto-renewal cron job
```

### Auto-Renewal (Automatic)

Certbot installs a systemd timer that runs twice daily:

```bash
# Check renewal timer status
sudo systemctl status certbot.timer

# Test renewal (dry run)
sudo certbot renew --dry-run

# Manual renewal (if needed)
sudo certbot renew
```

**Renewal process**:
1. Certbot checks if cert expires in < 30 days
2. If yes, requests renewal from Let's Encrypt
3. Downloads new certificate
4. Reloads Apache gracefully (no downtime)

### Certificate Files

```
/etc/letsencrypt/live/dndchat.gravitycar.com/
├── fullchain.pem   → Public certificate + intermediate CA chain
├── privkey.pem     → Private key (keep secret!)
├── cert.pem        → Public certificate only
└── chain.pem       → Intermediate CA chain only
```

**Used by Apache**:
- `SSLCertificateFile`: fullchain.pem (public cert + chain)
- `SSLCertificateKeyFile`: privkey.pem (private key)

---

## DNS Configuration

### Required DNS Records

```
# A record pointing to your server's IP
dndchat.gravitycar.com.  IN  A  123.456.789.101

# Or CNAME if using same IP as main domain
dndchat.gravitycar.com.  IN  CNAME  gravitycar.com.
```

**Verify DNS propagation**:
```bash
# Check A record
dig dndchat.gravitycar.com A

# Check from multiple locations
nslookup dndchat.gravitycar.com
host dndchat.gravitycar.com
```

**Wait for propagation**: 5 minutes to 48 hours (usually < 1 hour)

---

## Deployment Steps

### Step 1: Install Dependencies on Server

```bash
# SSH to gravitycar.com server
ssh mike@gravitycar.com

# Install mod_wsgi for Python 3
sudo apt-get update
sudo apt-get install libapache2-mod-wsgi-py3

# Enable required Apache modules
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers
sudo a2enmod wsgi

# Restart Apache to load modules
sudo systemctl restart apache2
```

### Step 2: Deploy Application Code

```bash
# On server: Clone or update repository
cd /home/mike/projects
git clone https://github.com/gravitycar/gravitycar_dnd1st_rag_system.git
# OR if already cloned:
cd gravitycar_dnd1st_rag_system
git pull origin feature/apache

# Create virtualenv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install Flask python-dotenv requests  # Add Flask dependencies

# Copy .env file (from secure location or create)
cp /secure/location/.env .env
chmod 640 .env

# Set permissions
sudo chown -R mike:www-data /home/mike/projects/gravitycar_dnd1st_rag_system
sudo chmod -R 750 /home/mike/projects/gravitycar_dnd1st_rag_system
sudo chmod 640 .env
```

### Step 3: Create wsgi.py

```bash
# Create WSGI entry point (see content above)
nano wsgi.py
chmod 750 wsgi.py
```

### Step 4: Configure Apache Virtual Host

```bash
# Create virtual host config
sudo nano /etc/apache2/sites-available/dndchat.gravitycar.com.conf
# Paste configuration from above

# Enable site
sudo a2ensite dndchat.gravitycar.com.conf

# Test configuration
sudo apache2ctl configtest
# Should output: Syntax OK

# If errors, check:
# - Python paths are correct
# - wsgi.py exists and is executable
# - Permissions are correct
```

### Step 5: Generate SSL Certificate

```bash
# Run certbot (see Let's Encrypt section above)
sudo certbot --apache -d dndchat.gravitycar.com

# Verify certificate was generated
sudo ls -l /etc/letsencrypt/live/dndchat.gravitycar.com/
```

### Step 6: Start Service

```bash
# Reload Apache to apply changes
sudo systemctl reload apache2

# Check for errors
sudo tail -f /var/log/apache2/dndchat_error.log

# Test health endpoint
curl https://dndchat.gravitycar.com/api/health
# Expected: {"status": "ok", "service": "dndchat", "version": "1.0.0"}
```

### Step 7: Test with Real Token

```bash
# Get JWT token from browser localStorage (after logging in to react.gravitycar.com)
# Or extract from browser DevTools → Application → Local Storage → auth_token

TOKEN="your_jwt_token_here"

# Test query endpoint
curl -X POST https://dndchat.gravitycar.com/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: https://react.gravitycar.com" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a beholder?"}'

# Expected: JSON response with answer, meta, etc.
```

---

## Monitoring & Debugging

### Log Files

```bash
# Apache error log (WSGI errors, Python exceptions)
sudo tail -f /var/log/apache2/dndchat_error.log

# Apache access log (HTTP requests)
sudo tail -f /var/log/apache2/dndchat_access.log

# Filter for errors only
sudo grep -i error /var/log/apache2/dndchat_error.log

# Filter for 500 errors
sudo grep " 500 " /var/log/apache2/dndchat_access.log
```

### Common Issues & Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| **502 Bad Gateway** | WSGI daemon crashed | Check dndchat_error.log for Python errors |
| **503 Service Unavailable** | Daily budget exceeded | Check cost_tracker, reset at midnight |
| **Permission denied** | www-data can't read files | Fix permissions: `chmod -R 750 project/` |
| **Module not found** | Wrong virtualenv path | Update `python-home` in WSGIDaemonProcess |
| **ChromaDB connection failed** | ChromaDB not running | Start ChromaDB: `./scripts/start_chroma.sh` |
| **Token validation fails** | api.gravitycar.com unreachable | Check network, API status |

### Graceful Reload (Zero Downtime)

```bash
# After code changes, reload workers without downtime
touch /home/mike/projects/gravitycar_dnd1st_rag_system/wsgi.py

# This tells mod_wsgi to:
# 1. Spawn new worker processes
# 2. Wait for in-flight requests to finish on old workers
# 3. Shut down old workers
# 4. Route new requests to new workers

# Verify reload in logs
sudo tail -f /var/log/apache2/dndchat_error.log
# Should see: [WSGI] DNDChat API starting...
```

### Performance Monitoring

```bash
# Watch worker processes
watch -n 1 'ps aux | grep -E "(apache2|dndchat)" | grep -v grep'

# Expected output:
# www-data 12345  0.5  2.1  Python (wsgi:dndchat) - process 0
# www-data 12346  0.3  2.0  Python (wsgi:dndchat) - process 1

# Monitor memory usage
watch -n 1 'ps aux | grep "wsgi:dndchat" | awk "{sum+=\$6} END {print \"Total: \" sum/1024 \" MB\"}"'

# Check Apache status (if mod_status enabled)
curl http://localhost/server-status
```

---

## Backup & Disaster Recovery

### Critical Files to Backup

```bash
# Configuration
/etc/apache2/sites-available/dndchat.gravitycar.com.conf

# Application code (or use Git)
/home/mike/projects/gravitycar_dnd1st_rag_system/

# Environment secrets
/home/mike/projects/gravitycar_dnd1st_rag_system/.env

# SSL certificates (auto-renewed, but backup just in case)
/etc/letsencrypt/live/dndchat.gravitycar.com/

# ChromaDB data (vector embeddings)
/home/mike/projects/rag/chroma/
```

### Quick Recovery Steps

```bash
# 1. Restore code from Git
cd /home/mike/projects
git clone https://github.com/gravitycar/gravitycar_dnd1st_rag_system.git
cd gravitycar_dnd1st_rag_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Restore .env from secure backup
cp /backup/.env .env
chmod 640 .env

# 3. Restore Apache config
sudo cp /backup/dndchat.gravitycar.com.conf /etc/apache2/sites-available/
sudo a2ensite dndchat.gravitycar.com.conf

# 4. Restore SSL cert (or regenerate with certbot)
sudo certbot --apache -d dndchat.gravitycar.com

# 5. Reload Apache
sudo systemctl reload apache2
```

---

## Local Development vs Production

### Local Development (Ubuntu laptop)

```bash
# .env.local
API_GRAVITYCAR_BASE_URL=https://api.gravitycar.com  # Use production API
TOKEN_CACHE_TTL=60  # Shorter cache for testing
chroma_host_url=http://localhost
chroma_host_port=8060

# Run Flask directly (not Apache)
source venv/bin/activate
export FLASK_APP=src/api.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000

# Test with curl
curl -X POST http://localhost:5000/api/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:3000" \
  -H "Content-Type: application/json" \
  -d '{"question": "Test query"}'
```

### Production (gravitycar.com server)

```bash
# .env (production)
API_GRAVITYCAR_BASE_URL=https://api.gravitycar.com
TOKEN_CACHE_TTL=300  # 5 minutes
chroma_host_url=http://localhost
chroma_host_port=8060

# Run via Apache mod_wsgi (daemon mode)
sudo systemctl status apache2
# Should show: active (running)

# Access via HTTPS
curl https://dndchat.gravitycar.com/api/health
```

---

## Security Checklist

- [ ] SSL certificate installed and auto-renewing
- [ ] HTTP redirects to HTTPS (no plaintext traffic)
- [ ] .env file has 640 permissions (not world-readable)
- [ ] API keys in .env, not hardcoded
- [ ] CORS validation in Flask middleware
- [ ] Token validation on every request
- [ ] Rate limiting enforced (15 burst, 30/day)
- [ ] Budget tracking active ($1/day limit)
- [ ] Email alerts configured for budget/limit events
- [ ] Apache security headers enabled (X-Frame-Options, etc.)
- [ ] www-data user has minimal permissions (no root)
- [ ] ChromaDB not exposed to internet (localhost only)
- [ ] Firewall allows only 80/443 (not 8060 for ChromaDB)
- [ ] Regular security updates: `sudo apt-get update && sudo apt-get upgrade`

---

## Next Steps

1. **Implement Token Validator**: Create `src/utils/token_validator.py`
2. **Create Flask API**: Create `src/api.py` with middleware
3. **Test Locally**: Verify OAuth flow works with api.gravitycar.com
4. **Deploy to Server**: Follow deployment steps above
5. **Monitor for 1 Week**: Watch logs, costs, rate limits
6. **Integrate with React**: Update react.gravitycar.com to call DNDChat API

---

**Decision Owner**: Mike  
**Reviewer**: GitHub Copilot (Mentor Mode)  
**Last Updated**: November 3, 2025  
**Status**: ✅ Finalized - Ready for Implementation
