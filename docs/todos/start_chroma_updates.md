# start_chroma.sh Updates

**Date**: October 15, 2025  
**Status**: ✅ Complete

---

## Changes Made

### 1. Environment Variable Support

The script now reads configuration from `.env` file:

**Variables Used**:
- `chroma_host_url` - ChromaDB host URL (default: `http://localhost`)
- `chroma_host_port` - ChromaDB port (default: `8060`)
- `chroma_data_path` - Data directory path (default: `.`)

**Loading Method**:
```bash
if [ -f .env ]; then
    set -a       # Automatically export all variables
    source .env  # Source the .env file
    set +a       # Disable auto-export
fi
```

### 2. API Version Upgrade

**Before**: v1 API (`/api/v1/heartbeat`)  
**After**: v2 API (`/api/v2/heartbeat`)

**Benefits**:
- Better API support
- More reliable heartbeat endpoint
- Returns JSON response: `{"nanosecond heartbeat": <timestamp>}`

### 3. Relative Log Path

**Before**: `/home/mike/projects/rag/chroma/chroma.log` (absolute path)  
**After**: `chroma.log` (relative path)

**Benefits**:
- Works regardless of project location
- More portable across systems
- Follows best practices

### 4. Host URL Extraction

Added logic to extract hostname from full URL:

```bash
# Extract just the host from URL (remove http:// or https://)
CHROMA_HOST=$(echo ${CHROMA_HOST_URL} | sed 's~http[s]*://~~')
```

**Why**: The `chroma run` command expects just the hostname (e.g., `localhost`), not a full URL (e.g., `http://localhost`)

---

## Updated Script

```bash
#!/usr/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Set defaults if not in .env
CHROMA_HOST_URL=${chroma_host_url:-http://localhost}
CHROMA_PORT=${chroma_host_port:-8060}
CHROMA_PATH=${chroma_data_path:-.}
LOG_FILE="chroma.log"

# Extract just the host from URL (remove http:// or https://)
CHROMA_HOST=$(echo ${CHROMA_HOST_URL} | sed 's~http[s]*://~~')

# Check if ChromaDB is already running
if curl -s ${CHROMA_HOST_URL}:${CHROMA_PORT}/api/v2/heartbeat > /dev/null 2>&1; then
    echo "ChromaDB is already running on ${CHROMA_HOST}:${CHROMA_PORT}"
    exit 0
fi

# Start ChromaDB as background process
echo "Starting ChromaDB server..."
echo "  Host: ${CHROMA_HOST}"
echo "  Port: ${CHROMA_PORT}"
echo "  Data path: ${CHROMA_PATH}"
nohup chroma run --host ${CHROMA_HOST} --port ${CHROMA_PORT} --path ${CHROMA_PATH} > ${LOG_FILE} 2>&1 &

# Wait for startup (give it 5 seconds)
sleep 5

# Verify it started
if curl -s ${CHROMA_HOST_URL}:${CHROMA_PORT}/api/v2/heartbeat > /dev/null 2>&1; then
    echo "✓ ChromaDB started successfully on ${CHROMA_HOST}:${CHROMA_PORT}"
    echo "  Logs: ${LOG_FILE}"
else
    echo "✗ Failed to start ChromaDB"
    echo "  Check logs: ${LOG_FILE}"
    exit 1
fi
```

---

## Testing

### Test 1: Already Running Check ✅

```bash
$ ./scripts/start_chroma.sh
ChromaDB is already running on localhost:8060
```

**Result**: ✅ Correctly detects running instance

### Test 2: v2 API Heartbeat ✅

```bash
$ curl -s http://localhost:8060/api/v2/heartbeat
{"nanosecond heartbeat":1760549457931875211}
```

**Result**: ✅ v2 API working correctly

### Test 3: Environment Variables ✅

**From .env**:
```
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/
```

**Script Output**:
```
Starting ChromaDB server...
  Host: localhost
  Port: 8060
  Data path: /home/mike/projects/rag/chroma/
```

**Result**: ✅ Variables loaded and parsed correctly

---

## Compatibility

### .env File Format

The script expects these variable names (snake_case):
```bash
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/
```

**Note**: Variable names are case-sensitive

### Defaults

If `.env` is missing or variables are not set:
- Host URL: `http://localhost`
- Port: `8060`
- Data path: `.` (current directory)

### Shell Compatibility

- ✅ Bash (#!/usr/bin/bash)
- ✅ Should work with sh/dash (uses POSIX-compatible syntax)

---

## Documentation Updates Needed

### chromadb_setup.md

Update the script example to show new features:

**Add section**:
```markdown
### Environment Variables

Configure ChromaDB via `.env` file:

```bash
# ChromaDB Configuration
chroma_host_url=http://localhost
chroma_host_port=8060
chroma_data_path=/home/mike/projects/rag/chroma/
```

The startup script automatically reads these values.
```

### installation.md

Update the startup instructions:

**Before**:
```bash
./scripts/start_chroma.sh
```

**After**:
```bash
# Configure in .env first (optional)
# Then start ChromaDB
./scripts/start_chroma.sh

# Verify with v2 API
curl http://localhost:8060/api/v2/heartbeat
```

---

## Benefits

1. **Portability**: No hardcoded paths or ports
2. **Flexibility**: Easy to change configuration without editing script
3. **Consistency**: Uses same .env file as Python scripts
4. **Modern**: Uses v2 API with better support
5. **Maintainability**: Relative paths work anywhere

---

## Related Files

- `.env` - Configuration file (must exist or defaults are used)
- `chroma.log` - Log output (relative to working directory)
- `scripts/start_chroma.sh` - This script

---

**Author**: Mike (GravityCar)  
**Last Updated**: October 15, 2025  
**Version**: 2.0 (v2 API + .env support)
