# Remote Deployment: Problems and Solutions

**Target Architecture**: Deploy ChromaDB + D&D RAG system to public server (chroma.gravitycar.com)

**Goal**: Create a web interface on react.gravitycar.com that queries the remote D&D RAG system.

---

## Critical Infrastructure Questions

### 1. **Port Binding & ChromaDB Configuration**
**Problem**: Current setup uses `chroma_host_port=8060`, but hosting provider only allows ports 80/443.

**Status**: ✅ **SOLVED**

**SOLUTION IMPLEMENTED**:
- ✅ Created centralized configuration utility at `src/utils/config.py`
- ✅ Updated `docling_query.py` to use configuration from `.env`
- ✅ Updated `docling_embedder.py` to use configuration from `.env`
- ✅ Implemented flexible `.env` discovery (current dir + up to 2 parent directories)
- ✅ All hardcoded ChromaDB connection values removed
- ✅ Created `.env.production` with remote deployment configuration

**Remote Configuration** (`.env.production`):
```dotenv
gravitycar_openai_api_key=sk...YA
chroma_host_url=https://rag.gravitycar.com
chroma_host_port=80
chroma_data_path=/home/gravityc/rag/chroma/
```

**Deployment Architecture Decision**:
Given hosting provider constraints (Apache must handle ALL traffic, no custom ports), **Apache + WSGI + Embedded ChromaDB** is the recommended approach:

```
User → rag.gravitycar.com:80 → Apache (mod_wsgi) → Flask App → ChromaDB (embedded)
```

**Why This Architecture:**
- No custom ports needed (hosting provider restriction)
- Standard Python web deployment pattern
- ChromaDB embedded in Flask app (no separate service)
- Apache handles all HTTP/HTTPS termination
- Mature, well-supported technology stack

**Updated .env.production Strategy:**
```dotenv
gravitycar_openai_api_key=sk...YA
# No chroma_host_url needed (embedded ChromaDB)
# No chroma_host_port needed (embedded ChromaDB)
chroma_data_path=/home/gravityc/rag/chroma/
flask_app_mode=production
```

**Technical Details**:
- Flask app will use embedded ChromaDB via `chromadb.PersistentClient()`
- Apache serves Flask app via mod_wsgi
- All communication happens over standard HTTP ports
- ChromaDB data persisted to filesystem (no network layer needed)

**Next Actions for Remote Deployment**:
1. ✅ Remote `.env.production` configuration created  
2. ⏳ Create Flask wrapper around `docling_query.py`
3. ⏳ Update config utility to support embedded ChromaDB mode
4. ⏳ Configure Apache mod_wsgi for Python deployment

**Next Actions**:
1. ✅ Audit current scripts for hardcoded ChromaDB connection values
2. ⏳ Implement flexible `.env` discovery in scripts
3. ⏳ Choose final deployment architecture

---

### 2. **Resource Constraints & Memory Requirements**
**Problem**: `SentenceTransformer('all-mpnet-base-v2')` loads ~420MB of neural network weights during queries.

**Status**: ✅ **SOLVED** (Migration to OpenAI Embeddings API)

**SOLUTION IMPLEMENTED**:
- **Migration Plan**: Replace SentenceTransformer with OpenAI's `text-embedding-3-small` API
- **Memory Savings**: Eliminates 420MB model loading requirement on remote server
- **Compatibility**: OpenAI embeddings are 1536-dimensional vs current 768d (requires re-embedding)
- **Cost**: ~$0.00002 per 1K tokens (negligible for query volume)

**Technical Details**:
- Current: `SentenceTransformer('all-mpnet-base-v2')` → 768d embeddings → ChromaDB
- Future: `OpenAI.embeddings.create(model='text-embedding-3-small')` → 1536d embeddings → ChromaDB
- Impact: All existing collections need re-embedding with OpenAI model

**Migration Strategy**:
1. ✅ Update `docling_query.py` to use OpenAI embeddings API instead of SentenceTransformer
2. ⏳ Update `docling_embedder.py` to use OpenAI embeddings for new data
3. ⏳ Re-embed existing Monster Manual and Player's Handbook collections
4. ⏳ Export/import updated collections to remote server

**Memory Requirements After Migration**:
- Before: ~420MB (SentenceTransformer model) + Flask overhead
- After: ~50MB (Flask app only, no local models)

**Questions Resolved**:
- ✅ Memory constraints: Reduced from 420MB to ~50MB
- ✅ Computational power: Offloaded to OpenAI API
- ✅ Model consistency: OpenAI API eliminates version drift issues

---

### 3. **Data Export/Import Strategy**
**Problem**: Need to migrate ChromaDB data from local `/home/mike/projects/rag/chroma/` to remote server.

**Status**: � **IN PROGRESS** (Migration Strategy Updated)

**Current Local Data**:
- Collection: `dnd_monster_manual` (294 chunks, 768d embeddings)
- Collection: `dnd_players_handbook` (TBD chunks, 768d embeddings) 
- Embedding model: `all-mpnet-base-v2` (768d)

**Migration Strategy** (Updated for OpenAI Embeddings):
1. **Re-embed with OpenAI**: Use `text-embedding-3-small` (1536d) for consistency
2. **Export Options**:
   - **File System Copy**: `tar -czf chromadb_backup.tar.gz /home/mike/projects/rag/chroma/`
   - **ChromaDB CLI**: `chroma copy --source /local/path --destination /remote/path`
   - **Programmatic**: Python script using `collection.get()` and `collection.add()`
3. **Import to Remote**: Create new collections with OpenAI embeddings

**Embedding Migration Required**:
- Current collections use 768d embeddings (SentenceTransformer)
- Target collections need 1536d embeddings (OpenAI API)
- **Cannot mix embedding dimensions** in same collection
- Solution: Re-run embedding pipeline with OpenAI model before export

**Updated Workflow**:
```bash
# 1. Re-embed locally with OpenAI
python src/embedders/docling_embedder.py --openai data/chunks/chunks_Monster_Manual_(1e).json dnd_monster_manual_openai

# 2. Export collections
python scripts/export_collections.py dnd_monster_manual_openai

# 3. Transfer to remote
scp chromadb_export.tar.gz user@server:/home/gravityc/

# 4. Import on remote
python scripts/import_collections.py chromadb_export.tar.gz
```

**Questions to Resolve**:
- Do you want to keep both embedding approaches (SentenceTransformer local, OpenAI remote)?
- Should we migrate all collections or just create new ones?
- Timeline for re-embedding (Monster Manual ~10 minutes, API costs ~$1)?

---

### 4. **Security & API Key Management**
**Problem**: `.env` contains sensitive OpenAI API key. Remote server needs secure storage.

**Status**: � **IN PROGRESS**

**SOLUTION APPROACH**:
- ✅ Created `.env.production` with production configuration
- ✅ Config utility supports flexible `.env` discovery (outside web root)
- ⏳ Plan secure deployment of `.env.production` file

**Production Security Plan**:
1. **`.env.production` Placement**: Store in `/home/gravityc/.env` (outside web root)
2. **File Permissions**: `chmod 600 .env` (owner read/write only)
3. **API Key Rotation**: Consider rotating OpenAI API key for production
4. **Access Control**: Web API should include rate limiting and basic auth

**Questions to Resolve**:
- Do you need API authentication/rate limiting for the web interface?
- Should we implement request logging for monitoring?
- Do you want separate API keys for development vs production?

---

## Architecture & Implementation Questions

### 5. **Web API Wrapper Design**
**Problem**: Current `docling_query.py` is CLI-only. Need web API for remote access.

**Status**: ✅ **ARCHITECTURE DECIDED** (Flask + mod_wsgi + OpenAI Embeddings)

**SOLUTION APPROACH**:
- ✅ Chosen Flask + mod_wsgi deployment model
- ✅ Migration to OpenAI embeddings eliminates memory constraints
- ⏳ Create Flask wrapper around existing `DnDRAG` class
- ⏳ Design REST API endpoints for web interface

**Updated API Design Plan** (Memory-Optimized):
```python
# Flask app structure - lightweight without SentenceTransformer
from openai import OpenAI

@app.route('/api/query', methods=['POST'])
def query_dnd():
    # Use DnDRAG class with OpenAI embeddings (no local model loading)
    # Memory footprint: ~50MB instead of 470MB
    
@app.route('/api/collections', methods=['GET']) 
def list_collections():
    # Return available collections
    
@app.route('/api/health', methods=['GET'])
def health_check():
    # System status - can include OpenAI API connectivity check
```

**Memory Impact Analysis**:
| Component | Before (SentenceTransformer) | After (OpenAI API) |
|-----------|------------------------------|-------------------|
| Embedding Model | 420MB | 0MB |
| Flask App | 50MB | 50MB |
| ChromaDB Client | 20MB | 20MB |
| **Total** | **490MB** | **70MB** |

**Technical Updates Required**:
1. **Update `DnDRAG.__init__()`**: Remove SentenceTransformer initialization
2. **Update `DnDRAG.retrieve()`**: Replace `self.embedding_model.encode()` with OpenAI API calls
3. **Add OpenAI error handling**: Rate limits, API key validation, connectivity issues
4. **Update config utility**: Add OpenAI embedding model configuration

**API Considerations**:
- **Rate Limiting**: OpenAI has generous limits, but should implement app-level limiting
- **Caching**: Consider caching embedding results for common queries
- **Error Handling**: Graceful fallback if OpenAI API is unavailable
- **Cost Monitoring**: Track embedding API usage (typically <$1/month for expected load)

**Questions Resolved**:
- ✅ Memory constraints: Eliminated with API approach
- ✅ Deployment complexity: Standard Flask deployment, no model files
- ✅ Performance: API latency (~100ms) vs local model (~50ms) - acceptable tradeoff

**Questions to Resolve**:
- Should we implement embedding result caching to reduce API calls?
- Do you want API usage monitoring/logging?
- Preferred JSON format for query requests/responses?

---

### 6. **Development & Deployment Workflow**
**Problem**: Need strategy for ongoing development and deployment.

**Status**: 🔍 **NEEDS WORKFLOW**

**Options**:
- Keep developing locally, sync to production periodically
- Develop directly on remote server
- Set up CI/CD pipeline

**Questions**:
- How do you prefer to develop and deploy?
- Will you need automated deployment?
- How will you handle data updates (new PDFs, collections)?

---

### 7. **ChromaDB Deployment Strategy Deep Dive**
**Problem**: Multiple ways to deploy ChromaDB, each with tradeoffs.

**Status**: ✅ **DECIDED** (Apache + WSGI + Embedded ChromaDB)

**Chosen Architecture**: **Apache + mod_wsgi + Flask + Embedded ChromaDB**
```
User → rag.gravitycar.com:80 → Apache (mod_wsgi) → Flask App → ChromaDB (embedded)
```

**Why This Architecture:**
- Hosting provider only allows ports 80/443 (no custom ports)
- Standard Python web deployment pattern (mod_wsgi)
- ChromaDB embedded eliminates port requirements
- Apache handles all SSL/security concerns
- Simpler deployment (single Python process)

**Implementation Requirements:**
1. **Apache Configuration (mod_wsgi)**: 
   ```apache
   LoadModule wsgi_module modules/mod_wsgi.so
   
   <VirtualHost *:80>
       ServerName rag.gravitycar.com
       WSGIScriptAlias / /home/gravityc/app.wsgi
       WSGIDaemonProcess dndrag python-path=/home/gravityc/dnd_rag
       WSGIProcessGroup dndrag
   </VirtualHost>
   ```

2. **ChromaDB Configuration**:
   - Use `chromadb.PersistentClient(path="/home/gravityc/rag/chroma/")`
   - No network ports needed (embedded in Flask process)
   - Data persisted to filesystem

3. **Your Code Changes**: 
   - Modify config utility to support embedded ChromaDB mode
   - Create Flask wrapper around `docling_query.py`
   - Update `.env.production` to remove host/port settings

**Alternative Options Considered**:
| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **A: Apache + WSGI** | Standard practice, no ports needed | Requires Flask wrapper | ✅ **CHOSEN** |
| **B: Apache Reverse Proxy** | Clean separation | Requires custom ports | ❌ Not allowed |
| **C: CGI Scripts** | Simple | Slow, high overhead | ❌ Inefficient |

---

## Next Steps Recommendations

### Immediate Actions Needed:
1. ✅ **ChromaDB deployment strategy chosen** (Apache + WSGI + Embedded ChromaDB)
2. ✅ **Memory constraints resolved** (OpenAI embeddings API migration)
3. **Update `docling_query.py` to use OpenAI embeddings** - **PRIORITY**
4. **Update `docling_embedder.py` to use OpenAI embeddings**
5. **Re-embed existing collections** with OpenAI API (Monster Manual ~$1 cost)
6. **Create Flask wrapper for web API**
7. **Export/import updated collections** to remote server

### Information Gathering:
- Do you want to keep both embedding approaches (SentenceTransformer local, OpenAI remote)?
- Preferred embedding result caching strategy?
- API usage monitoring requirements?

### Apache Configuration Preview:
You'll need something like this in your Apache config:
```apache
LoadModule wsgi_module modules/mod_wsgi.so

<VirtualHost *:80>
    ServerName rag.gravitycar.com
    
    # WSGI Configuration  
    WSGIScriptAlias / /home/gravityc/dnd_rag/app.wsgi
    WSGIDaemonProcess dndrag python-path=/home/gravityc/dnd_rag
    WSGIProcessGroup dndrag
    
    # Static files (if needed)
    Alias /static /home/gravityc/dnd_rag/static
    
    # Security headers
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
</VirtualHost>
```

---

## Solution Tracking

### ✅ **SOLVED**
- **Port Binding & ChromaDB Configuration**: Centralized config utility with flexible .env discovery
- **ChromaDB Deployment Strategy**: Apache + WSGI + Embedded ChromaDB architecture chosen
- **Resource Constraints & Memory Requirements**: Migration to OpenAI embeddings API eliminates 420MB requirement

### 🔄 **IN PROGRESS** 
- **Security & API Key Management**: Production .env created, need secure deployment plan
- **Data Export/Import Strategy**: Migration strategy updated for OpenAI embeddings
- **Web API Wrapper Design**: Architecture decided, implementation pending

### 🔍 **NEEDS DECISION/RESEARCH**
- Development & Deployment Workflow

---

*Last Updated: October 15, 2025*  
*Next Review: After initial hosting assessment*