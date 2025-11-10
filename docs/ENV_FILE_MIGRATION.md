# Environment File Migration: `.env` → `.env.dndchat`

## Summary

To avoid conflicts with pre-existing `.env` files on the production server, the D&D RAG system now uses `.env.dndchat` for configuration.

## Changes Made

### 1. File Renaming
- **Local**: `.env.production` → `.env.dndchat`
- **Production**: `.env` → `~/.env.dndchat` (parent directory)

### 2. Updated Files

#### Python Code
- ✅ **`src/utils/config.py`**
  - `load_environment()` searches for `.env.dndchat` 
  - Searches: current dir → parent dir → grandparent dir
  - Supports both local development and production paths

#### Shell Scripts
- ✅ **`scripts/start_flask.sh`**
  - Checks `~/.env.dndchat` first (production)
  - Falls back to `.env.dndchat` (local)
  
- ✅ **`scripts/stop_flask.sh`**
  - Same dual-path logic

- ✅ **`scripts/deploy_to_production.sh`**
  - Uploads `.env.dndchat` instead of `.env.production`
  - Moves file to `~/.env.dndchat` on server (outside web root)
  - Sets proper permissions (600)

## File Paths

### Local Development
```
/home/mike/projects/gravitycar_dnd1st_rag_system/
├── .env.dndchat           # Configuration (local ChromaDB or ChromaCloud)
├── src/
│   └── ...
└── scripts/
    └── ...
```

### Production Server
```
/home/gravityc/
├── .env.dndchat           # Production configuration (ChromaCloud, API keys)
└── public_html/
    └── dndchat.gravitycar.com/
        ├── src/
        ├── scripts/
        └── venv/
```

**Security note**: `.env.dndchat` is stored **outside** the web-accessible `public_html` directory.

## How It Works

### 1. Config Loading (Python)
```python
# src/utils/config.py searches these paths in order:
search_paths = [
    Path.cwd(),              # Current directory
    Path.cwd().parent,       # Parent directory (production: /home/gravityc/)
    Path.cwd().parent.parent # Grandparent directory
]

for search_path in search_paths:
    env_file = search_path / ".env.dndchat"
    if env_file.exists():
        load_dotenv(env_file)
        break
```

### 2. Shell Script Loading
```bash
# All shell scripts use this pattern:
if [ -f ~/.env.dndchat ]; then
    source ~/.env.dndchat      # Production path
elif [ -f .env.dndchat ]; then
    source .env.dndchat        # Local path
fi
```

## Migration Checklist

- [x] Rename local file: `.env.production` → `.env.dndchat`
- [x] Update `config.py` to search for `.env.dndchat`
- [x] Update `start_flask.sh` with dual-path logic
- [x] Update `stop_flask.sh` with dual-path logic  
- [x] Update `deploy_to_production.sh` to:
  - Upload `.env.dndchat`
  - Move to `~/.env.dndchat` on server
  - Set chmod 600 permissions

## Deployment Impact

### Before Deployment
```bash
# Verify local file exists
ls -la .env.dndchat

# Verify content is correct
head .env.dndchat
```

### During Deployment
The deployment script will:
1. Upload `.env.dndchat` to server
2. Move it to `/home/gravityc/.env.dndchat`
3. Set permissions to 600 (owner read/write only)

### After Deployment
```bash
# Verify file placement
ssh gravityc@dog.he.net "ls -la ~/.env.dndchat"

# Verify Flask can find it
ssh gravityc@dog.he.net "cd /home/gravityc/public_html/dndchat.gravitycar.com && python3 -c 'from src.utils.config import config; config.print_config_summary()'"
```

## Backward Compatibility

The system is **NOT** backward compatible with old `.env` files. You must:
- Rename `.env` → `.env.dndchat` locally
- Rename `.env.production` → `.env.dndchat` if you had both
- Redeploy to update server-side configuration

## Security Notes

1. **File Permissions**: `.env.dndchat` is automatically set to 600 (owner read/write only)
2. **Location**: Stored outside web root (`/home/gravityc/` vs `/home/gravityc/public_html/`)
3. **Git Ignore**: `.env.dndchat` is in `.gitignore`

## Troubleshooting

### "No .env file found" Warning
**Cause**: File not in expected locations  
**Fix**: 
```bash
# Verify file exists
ls -la .env.dndchat          # Local
ls -la ~/.env.dndchat        # Production

# Check search paths
python3 -c "from src.utils.config import config; config.print_config_summary()"
```

### Flask Won't Start
**Cause**: Script can't find `.env.dndchat`  
**Fix**:
```bash
# Production
ls -la ~/.env.dndchat
chmod 600 ~/.env.dndchat

# Local
ls -la .env.dndchat
```

### ChromaDB Connection Failed
**Cause**: Wrong credentials or file not loaded  
**Fix**:
```bash
# Verify environment is loaded
python3 -c "import os; print(os.getenv('chroma_cloud_api_key'))"

# Check file content
head -5 ~/.env.dndchat  # Production
head -5 .env.dndchat    # Local
```

## Related Files

- `src/utils/config.py` - Configuration manager with `.env.dndchat` discovery
- `scripts/start_flask.sh` - Flask startup with dual-path env loading
- `scripts/stop_flask.sh` - Flask shutdown with dual-path env loading
- `scripts/deploy_to_production.sh` - Deployment automation
- `.gitignore` - Excludes `.env.dndchat` from version control

---

*Last Updated: November 10, 2025*  
*Version: 1.1*
