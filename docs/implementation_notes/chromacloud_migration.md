# ChromaCloud Migration & Hurricane Electric Deployment

**Status**: Ready for ChromaCloud testing  
**Date**: November 4, 2025

---

## Current State

### ✅ Completed
1. **Session 1**: Output Buffer Refactoring (committed f17a1c7)
2. **Session 2**: Flask API + Rate Limiting + OAuth2 (32 unit tests passing)
3. **ChromaDB Connector Updated**: Now supports both local and cloud modes
4. **ChromaCloud Connected**: Successfully tested connection (0 collections, as expected)

### 📦 Files Modified
- `src/utils/chromadb_connector.py` - Added ChromaCloud support with auto-detection
- `.env` - Added `chroma_cloud_database=adnd_1e`
- `.env.production` - Complete production configuration
- `scripts/upload_to_chromacloud.py` - Tool to migrate collections

---

## ChromaCloud Configuration

### Environment Variables
```bash
# Required for ChromaCloud
chroma_cloud_api_key=YOUR_CHROMACLOUD_API_KEY
chroma_cloud_tenant_id=YOUR_TENANT_ID
chroma_cloud_database=adnd_1e

# Auto-detection logic:
# If chroma_cloud_api_key + chroma_cloud_tenant_id are set → ChromaCloud mode
# If not set → Local HTTP mode (localhost:8060)
```

### How It Works
The `ChromaDBConnector` now automatically detects which mode to use:

**Local Mode** (development):
```bash
# Comment out cloud credentials in .env
# chroma_cloud_api_key=...
# chroma_cloud_tenant_id=...

# Connector uses local ChromaDB
connector = ChromaDBConnector()  # → HttpClient(localhost:8060)
```

**Cloud Mode** (production):
```bash
# Uncomment cloud credentials in .env
chroma_cloud_api_key=YOUR_CHROMACLOUD_API_KEY
chroma_cloud_tenant_id=YOUR_TENANT_ID
chroma_cloud_database=adnd_1e

# Connector uses ChromaCloud
connector = ChromaDBConnector()  # → CloudClient(tenant, database)
```

---

## Next Steps (In Order)

### Step 1: Upload Collection to ChromaCloud ⏳

**Upload the `adnd_1e` collection** (our only good collection):

```bash
# Activate venv
source venv/bin/activate

# Upload to ChromaCloud
python scripts/upload_to_chromacloud.py adnd_1e

# This will:
# 1. Connect to local ChromaDB (localhost:8060)
# 2. Fetch all documents from adnd_1e collection
# 3. Connect to ChromaCloud
# 4. Create adnd_1e collection in cloud
# 5. Upload all documents in batches
# 6. Verify counts match
```

**Expected Output**:
```
Uploading collection: adnd_1e
================================================================================

1. Connecting to LOCAL ChromaDB...
   Connected: ChromaDBConnector(host=http://localhost, port=8060)
   Found collection: adnd_1e (2213 documents)

2. Connecting to ChromaCloud...
   Connected: ChromaDBConnector(cloud, tenant=120ffaa8-32bf-4e7d-823d-c587bd8a5202, database=adnd_1e)

3. Creating cloud collection...
   Created: adnd_1e

4. Fetching data from local collection (2213 documents)...
   Fetched 2213 documents

5. Uploading to cloud (batch size: 100)...
   Uploaded batch 1/23 (100/2213 documents)
   Uploaded batch 2/23 (200/2213 documents)
   ...
   Uploaded batch 23/23 (2213/2213 documents)

6. Verification:
   Local:  2213 documents
   Cloud:  2213 documents
   ✅ SUCCESS: All documents uploaded!
```

### Step 2: Test Flask with ChromaCloud ⏳

**Test that queries work with cloud data**:

```bash
# Ensure cloud credentials are set in .env
# (They already are)

# Stop local ChromaDB (to force cloud usage)
pkill -f "chroma run"

# Start Flask
./scripts/start_flask.sh

# Test query
./scripts/test_flask_query.sh "Bearer YOUR_TOKEN" "What is a beholder?"

# Verify:
# - Query returns correct answer
# - Response time acceptable (should be fast, ChromaCloud is CDN-backed)
# - No errors in flask.log
```

### Step 3: Contact Hurricane Electric Support ⏳

**Send these questions to HE support**:

#### Question 1: Reverse Proxy Support
```
Does Hurricane Electric shared hosting support reverse proxy via .htaccess?
Specifically, do you have mod_proxy and mod_proxy_http enabled?

I need to proxy requests from:
  https://dndchat.gravitycar.com/api/* 
to:
  http://127.0.0.1:8000/*

If mod_proxy is not available, what is the recommended way to run a Python 
Flask application as a persistent background process on your shared hosting?
```

#### Question 2: Long-Running Processes
```
I need to run a Python Flask application as a persistent background process 
that listens on port 8000 (localhost only). The process needs to:

1. Run continuously (not CGI)
2. Survive SSH disconnection
3. Restart automatically if it crashes

Is this supported on shared hosting? If yes, do you have any documentation
or recommended approach? If no, do you offer VPS hosting as an alternative?
```

#### Question 3: Subdomain Setup
```
I'd like to set up a new subdomain: dndchat.gravitycar.com

This subdomain needs to point to a Python Flask application. Can you:
1. Create the subdomain DNS record
2. Configure SSL certificate (Let's Encrypt)
3. Set up the document root

I already have api.gravitycar.com and react.gravitycar.com configured,
so I'm looking for the same setup for dndchat.gravitycar.com.
```

### Step 4: Deploy to Hurricane Electric (Pending HE Response) ⏸️

**Once HE confirms support**, we'll proceed with:

1. **If mod_proxy enabled**:
   - Deploy Flask app
   - Create `.htaccess` proxy rules
   - Test with production URLs

2. **If mod_proxy NOT enabled**:
   - Explore alternative approaches (CGI wrapper, external VPS, etc.)

3. **If background processes NOT allowed**:
   - Consider VPS alternative ($5-10/month DigitalOcean/Linode)

---

## Testing Checklist

Before deployment, verify these work with ChromaCloud:

- [ ] Upload `adnd_1e` collection to ChromaCloud
- [ ] Query returns correct answers (Fighter XP Table test)
- [ ] Entity-aware retrieval works (owlbear vs orc)
- [ ] Rate limiting enforced (15 burst test)
- [ ] Cost tracking records usage
- [ ] Token validation works with production API
- [ ] CORS headers correct for production origins
- [ ] Response time acceptable (<5 seconds for queries)

---

## Deployment Scenarios

### Scenario A: HE Supports mod_proxy (Ideal)
```
Architecture:
  User → Apache (.htaccess proxy) → Flask (port 8000) → ChromaCloud → OpenAI
  
Deployment Steps:
  1. Clone repo to ~/gravitycar_dnd1st_rag_system
  2. Create virtualenv and install dependencies
  3. Copy .env.production to .env
  4. Start Flask: nohup flask run --host=127.0.0.1 --port=8000 &
  5. Create .htaccess in ~/public_html/dndchat/
  6. Test: curl https://dndchat.gravitycar.com/api/health
```

### Scenario B: HE Does NOT Support mod_proxy (Workaround)
```
Architecture:
  User → Apache (CGI wrapper) → Flask (one-shot) → ChromaCloud → OpenAI
  
Deployment Steps:
  1. Same as Scenario A (steps 1-3)
  2. Create CGI wrapper script (slower, but works)
  3. Configure .htaccess for CGI execution
  4. Test with production URLs
  
Drawback: 5-10 second startup per request (not ideal)
```

### Scenario C: HE Blocks Background Processes (Alternative)
```
Architecture:
  User → VPS (Flask + Apache) → ChromaCloud → OpenAI
  
Cost: $5-10/month (DigitalOcean, Linode, Vultr)
Deployment: Use original Session 3 plan (full Apache control)
```

---

## Current Environment Status

### Local Development (.env)
```bash
# Uses ChromaCloud (cloud credentials set)
# Flask on port 5000
# OAuth validates with localhost:8081
# CORS allows localhost:3000,3001
```

### Production (.env.production)
```bash
# Uses ChromaCloud (cloud credentials set)
# Flask on port 8000
# OAuth validates with https://api.gravitycar.com
# CORS allows https://react.gravitycar.com
```

---

## Important Notes

1. **ChromaCloud Free Tier**: Should be sufficient for 2-5 users, low query volume
2. **Collection Migration**: Only upload `adnd_1e` (2213 documents), ignore other collections
3. **Local ChromaDB**: Keep running for local development, use cloud for production
4. **Deployment Blocked**: Waiting on HE support response for mod_proxy status

---

## Questions to Answer

- [ ] Does ChromaCloud query performance meet requirements? (test after Step 2)
- [ ] Does HE support mod_proxy? (ask support)
- [ ] Does HE allow background processes? (ask support)
- [ ] Can HE set up dndchat.gravitycar.com subdomain? (ask support)
- [ ] If HE blocks everything, are you willing to pay $5-10/mo for VPS? (decide after HE response)

---

**Next Action**: Run `python scripts/upload_to_chromacloud.py adnd_1e` to migrate collection
