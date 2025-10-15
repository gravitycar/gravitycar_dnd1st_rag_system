# ChromaDB Setup Guide

Complete guide for installing, configuring, and managing ChromaDB for the D&D RAG system.

---

## What is ChromaDB?

**ChromaDB** is an open-source vector database designed for AI applications. It stores:
- **Document embeddings** (768-dimensional vectors)
- **Original text** (for retrieval)
- **Metadata** (page numbers, categories, statistics)
- **HNSW index** (for fast similarity search)

**Why ChromaDB?**
- ✅ Fast vector search (HNSW algorithm)
- ✅ Local or client-server deployment
- ✅ Python-native API
- ✅ No complex configuration
- ✅ Open source (Apache 2.0)

---

## Installation Options

### Option 1: Docker (Recommended)

**Pros**:
- Clean isolation
- Easy management
- Consistent across platforms

**Cons**:
- Requires Docker installation

#### Install Docker

**Linux (Ubuntu/Debian)**:
```bash
# Update package index
sudo apt update

# Install Docker
sudo apt install docker.io

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER

# Restart session or run:
newgrp docker

# Verify installation
docker --version
```

**macOS**:
```bash
# Using Homebrew
brew install --cask docker

# Or download Docker Desktop:
# https://www.docker.com/products/docker-desktop/

# Verify installation
docker --version
```

**Windows**:
- Download Docker Desktop: [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
- Install and enable WSL2 integration

#### Run ChromaDB Container

```bash
# Pull ChromaDB image
docker pull chromadb/chroma

# Run ChromaDB (foreground)
docker run -p 8060:8000 chromadb/chroma

# Or run as background service
docker run -d -p 8060:8000 --name chroma chromadb/chroma

# Or with persistent data
docker run -d -p 8060:8000 \
  -v /home/mike/projects/rag/chroma:/chroma/chroma \
  --name chroma \
  chromadb/chroma

# Verify running
curl http://localhost:8060/api/v1/heartbeat
# Should return: {}
```

#### Manage Container

```bash
# Stop ChromaDB
docker stop chroma

# Start ChromaDB
docker start chroma

# Restart ChromaDB
docker restart chroma

# View logs
docker logs chroma

# Remove container
docker rm -f chroma
```

### Option 2: Provided Script (Easiest)

Use the included startup script:

```bash
# Make executable (if not already)
chmod +x scripts/start_chroma.sh

# Run ChromaDB
./scripts/start_chroma.sh

# The script:
# 1. Checks if ChromaDB is already running
# 2. Starts ChromaDB as background process
# 3. Verifies connection
# 4. Shows logs location
```

**Script contents**:
```bash
#!/bin/bash
# Start ChromaDB server as background process

cd /home/mike/projects/rag/chroma

# Check if already running
if curl -s http://localhost:8060/api/v1/heartbeat > /dev/null 2>&1; then
    echo "ChromaDB is already running"
    exit 0
fi

# Start ChromaDB
echo "Starting ChromaDB..."
nohup chroma run --path . --port 8060 > chroma.log 2>&1 &

# Wait for startup
sleep 2

# Verify
if curl -s http://localhost:8060/api/v1/heartbeat > /dev/null 2>&1; then
    echo "ChromaDB started successfully on port 8060"
else
    echo "Failed to start ChromaDB"
    exit 1
fi
```

### Option 3: Pip Install (Advanced)

**Pros**:
- No Docker required
- Direct Python integration

**Cons**:
- More complex dependency management
- Potential conflicts

#### Install ChromaDB

```bash
# Activate virtual environment
source venv/bin/activate

# Install ChromaDB (already in requirements.txt)
pip install chromadb==1.1.1
```

#### Run ChromaDB Server

```bash
# Navigate to project directory
cd /home/mike/projects/rag/chroma

# Start ChromaDB server
chroma run --path . --port 8060

# Or as background process
nohup chroma run --path . --port 8060 > chroma.log 2>&1 &

# Verify
curl http://localhost:8060/api/v1/heartbeat
```

---

## Configuration

### Port Configuration

**Default**: 8060 (ChromaDB default is 8000, but we use 8060 to avoid conflicts)

**Change Port**:

1. **Update .env**:
```bash
CHROMA_PORT=9000
```

2. **Update startup command**:
```bash
# Docker
docker run -p 9000:8000 chromadb/chroma

# Direct
chroma run --path . --port 9000
```

3. **Verify**:
```bash
curl http://localhost:9000/api/v1/heartbeat
```

### Data Directory

ChromaDB stores data in the directory specified by `--path`:

```bash
chroma run --path /home/mike/projects/rag/chroma --port 8060
```

**Structure**:
```
/home/mike/projects/rag/chroma/
├── chroma.sqlite3                    # Metadata database
├── [GUID-1]/                         # Collection 1 data
├── [GUID-2]/                         # Collection 2 data
└── ...
```

**Storage Size**:
- ~150 MB per collection (Monster Manual: 512 chunks)
- ~250 MB per collection (Player's Handbook: 843 chunks)

### Authentication (Optional)

ChromaDB supports authentication for production:

```bash
# Generate token
export CHROMA_SERVER_AUTH_CREDENTIALS="admin:secure_password"

# Start with auth
chroma run --path . --port 8060
```

**Update client code**:
```python
import chromadb
from chromadb.config import Settings

client = chromadb.HttpClient(
    host='localhost',
    port=8060,
    settings=Settings(
        chroma_client_auth_provider="basic",
        chroma_client_auth_credentials="admin:secure_password"
    )
)
```

---

## Verification

### Check if Running

```bash
# HTTP request
curl http://localhost:8060/api/v1/heartbeat

# Expected: {}
# If not running: connection refused
```

### List Collections

```bash
# Using provided script
python scripts/list_chromadb_collections.py

# Output:
# Connected to ChromaDB at localhost:8060
# Collections:
# - dnd_monster_manual (512 chunks)
# - dnd_players_handbook (843 chunks)
```

### Query a Collection

```python
import chromadb

client = chromadb.HttpClient(host='localhost', port=8060)
collection = client.get_collection(name='dnd_monster_manual')

# Get collection info
print(f"Collection: {collection.name}")
print(f"Count: {collection.count()}")

# Sample query
results = collection.query(
    query_texts=["beholder"],
    n_results=3
)

print(f"Results: {len(results['documents'][0])}")
```

---

## Collection Management

### List All Collections

```bash
python scripts/list_chromadb_collections.py
```

**Or programmatically**:
```python
import chromadb

client = chromadb.HttpClient(host='localhost', port=8060)
collections = client.list_collections()

for coll in collections:
    print(f"{coll.name} ({coll.count()} chunks)")
```

### Create Collection

Collections are created automatically by the embedder:

```bash
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Monster_Manual_(1e).json \
  dnd_monster_manual
```

**Or programmatically**:
```python
import chromadb

client = chromadb.HttpClient(host='localhost', port=8060)

# Create collection
collection = client.create_collection(
    name="my_collection",
    metadata={"hnsw:space": "cosine"}  # Cosine similarity
)

# Add documents
collection.add(
    documents=["text 1", "text 2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    ids=["id1", "id2"]
)
```

### Delete Collection

```python
import chromadb

client = chromadb.HttpClient(host='localhost', port=8060)

# Delete collection
client.delete_collection(name="dnd_monster_manual")

# Verify deletion
collections = client.list_collections()
print([c.name for c in collections])
```

**Warning**: This permanently deletes all data in the collection!

### Re-embed Collection

To re-process and overwrite a collection:

```bash
# The embedder automatically deletes and recreates
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Monster_Manual_(1e).json \
  dnd_monster_manual
```

---

## Performance Tuning

### HNSW Index Settings

ChromaDB uses **HNSW (Hierarchical Navigable Small World)** for fast vector search.

**Default settings** (good for most use cases):
```python
collection = client.create_collection(
    name="my_collection",
    metadata={
        "hnsw:space": "cosine",        # Cosine similarity
        "hnsw:construction_ef": 100,   # Build quality
        "hnsw:search_ef": 100,         # Search quality
        "hnsw:M": 16                   # Connections per node
    }
)
```

**Higher quality** (slower build, faster search):
```python
metadata={
    "hnsw:construction_ef": 200,  # Higher = better quality, slower build
    "hnsw:search_ef": 200,        # Higher = better recall, slower search
    "hnsw:M": 32                  # More connections = better recall, more memory
}
```

**For our use case** (default is fine):
- Small dataset (500-1000 chunks per collection)
- High-quality embeddings (all-mpnet-base-v2)
- Fast queries already (<100ms)

### Memory Usage

**Estimate**:
```
Memory = num_chunks × (embedding_dim × 4 bytes + metadata_size + index_overhead)
```

**Example** (Monster Manual):
- 512 chunks
- 768 dimensions × 4 bytes = 3 KB per embedding
- Metadata: ~500 bytes per chunk
- Index: ~30% overhead
- **Total**: ~2.5 MB in memory

**For multiple collections**:
- ChromaDB loads collections on demand
- Inactive collections paged to disk
- No memory issues for typical use

### Disk Space

**Per collection**:
- Embeddings: `num_chunks × embedding_dim × 4 bytes`
- Metadata: `num_chunks × 500 bytes`
- Index: ~30% overhead

**Example**:
- Monster Manual (512 chunks): ~150 MB
- Player's Handbook (843 chunks): ~250 MB

**Total project**: ~400 MB for 2 books

---

## Backup and Restore

### Backup

**Option 1**: Copy entire data directory

```bash
# Stop ChromaDB (if running)
docker stop chroma

# Copy data
cp -r /home/mike/projects/rag/chroma /path/to/backup/

# Restart ChromaDB
docker start chroma
```

**Option 2**: Export collections to JSON

```bash
# Export each collection
python scripts/export_collection.py dnd_monster_manual > backup_mm.json
python scripts/export_collection.py dnd_players_handbook > backup_ph.json
```

**Sample export script** (`scripts/export_collection.py`):
```python
import chromadb
import json
import sys

collection_name = sys.argv[1]

client = chromadb.HttpClient(host='localhost', port=8060)
collection = client.get_collection(name=collection_name)

# Get all data
results = collection.get(include=['documents', 'metadatas', 'embeddings'])

# Export to JSON
data = {
    'name': collection_name,
    'documents': results['documents'],
    'metadatas': results['metadatas'],
    'embeddings': results['embeddings'],
    'ids': results['ids']
}

print(json.dumps(data, indent=2))
```

### Restore

**Option 1**: Copy data directory back

```bash
# Stop ChromaDB
docker stop chroma

# Restore data
cp -r /path/to/backup/chroma /home/mike/projects/rag/

# Start ChromaDB
docker start chroma
```

**Option 2**: Re-run embedding pipeline

```bash
# Re-chunk and re-embed
python src/chunkers/monster_encyclopedia.py data/markdown/Monster_Manual_(1e).md
python src/embedders/docling_embedder.py data/chunks/chunks_Monster_Manual_(1e).json dnd_monster_manual
```

---

## Troubleshooting

### ChromaDB Won't Start

**Error**: "Address already in use"

**Solution**: Port 8060 is already in use

```bash
# Check what's using port 8060
lsof -i :8060

# Kill process
kill -9 [PID]

# Or use different port
docker run -p 9000:8000 chromadb/chroma
```

**Error**: "Permission denied"

**Solution**: Add user to docker group

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Connection Refused

**Symptom**: `requests.exceptions.ConnectionError`

**Solutions**:

1. **Check if ChromaDB is running**:
```bash
curl http://localhost:8060/api/v1/heartbeat
```

2. **Start ChromaDB**:
```bash
./scripts/start_chroma.sh
```

3. **Check port configuration**:
```bash
# In .env
cat .env | grep CHROMA_PORT

# Should match running instance
```

### Collection Not Found

**Symptom**: `chromadb.errors.InvalidCollectionException`

**Solutions**:

1. **List available collections**:
```bash
python scripts/list_chromadb_collections.py
```

2. **Create collection**:
```bash
python src/embedders/docling_embedder.py \
  data/chunks/chunks_Monster_Manual_(1e).json \
  dnd_monster_manual
```

3. **Check collection name spelling**

### Slow Queries

**Symptom**: Queries take > 1 second

**Solutions**:

1. **Check collection size**:
```python
collection.count()  # Should be < 10,000 for fast queries
```

2. **Increase `search_ef`**:
```python
collection.modify(metadata={"hnsw:search_ef": 200})
```

3. **Check ChromaDB logs**:
```bash
docker logs chroma
```

### Data Corruption

**Symptom**: Errors reading collections, crashes

**Solutions**:

1. **Delete and recreate collection**:
```python
client.delete_collection(name="dnd_monster_manual")
# Re-run embedder
```

2. **Restore from backup**:
```bash
cp -r /path/to/backup/chroma /home/mike/projects/rag/
```

3. **Nuclear option - delete all data**:
```bash
# Stop ChromaDB
docker stop chroma

# Delete data
rm -rf /home/mike/projects/rag/chroma/chroma.sqlite3
rm -rf /home/mike/projects/rag/chroma/[GUID directories]

# Restart ChromaDB
docker start chroma

# Re-embed everything
python src/embedders/docling_embedder.py ...
```

---

## Production Deployment

For production use:

### 1. Use Docker Compose

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  chroma:
    image: chromadb/chroma
    container_name: chroma
    ports:
      - "8060:8000"
    volumes:
      - /home/mike/projects/rag/chroma:/chroma/chroma
    restart: unless-stopped
    environment:
      - CHROMA_SERVER_AUTH_CREDENTIALS=admin:secure_password
```

**Start**:
```bash
docker-compose up -d
```

### 2. Enable Authentication

See [Authentication](#authentication-optional) section above.

### 3. Setup Monitoring

**Health check endpoint**:
```bash
curl http://localhost:8060/api/v1/heartbeat
```

**Monitor with cron**:
```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:8060/api/v1/heartbeat || systemctl restart chromadb
```

### 4. Regular Backups

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
cp -r /home/mike/projects/rag/chroma /backups/chroma_$DATE
```

---

## Next Steps

After ChromaDB is running:

1. **[Installation Guide](installation.md)**: Setup Python environment
2. **[Main README](../../README.md)**: Run the full pipeline
3. **[DnD RAG Documentation](../implementations/DnDRAG.md)**: Understand query system

---

**Recommended Setup**: Docker with automated script  
**Default Port**: 8060  
**Data Location**: `/home/mike/projects/rag/chroma/`  
**Last Updated**: 2025-01-XX  
**Version**: 1.0
