#!/bin/bash
################################################################################
# Production Deployment Script
# D&D RAG System → dndchat.gravitycar.com
#
# This script automates deployment to Hurricane Electric hosting.
# It handles file uploads, environment setup, and Flask initialization.
#
# PREREQUISITES (run these manually BEFORE this script):
#   1. Embed all books to ChromaCloud from LOCAL machine into single collection:
#      - dnd-embed data/chunks/chunks_Monster_Manual_\(1e\).json adnd_1e
#      - dnd-embed data/chunks/chunks_Players_Handbook_\(1e\)_organized.json adnd_1e
#      - dnd-embed data/chunks/chunks_DMG_with_query_must.json adnd_1e
#   2. Verify ChromaCloud has the adnd_1e collection:
#      - dnd-rag collections
#
# USAGE:
#   ./scripts/deploy_to_production.sh [SSH_HOST] [SSH_USER]
#
# EXAMPLES:
#   ./scripts/deploy_to_production.sh dndchat.gravitycar.com gravityc
#   ./scripts/deploy_to_production.sh 192.168.1.100 mike
#
################################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REMOTE_DIR="/home/gravityc/public_html/dndchat.gravitycar.com"  # Absolute path for Hurricane Electric subdomain

################################################################################
# Helper Functions
################################################################################

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

print_banner() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  D&D RAG Production Deployment${NC}"
    echo -e "${BLUE}  Target: $SSH_HOST${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

check_local_prerequisites() {
    log_info "Checking local prerequisites..."
    
    # Check if .env.dndchat.production exists (production config)
    if [ ! -f "$PROJECT_ROOT/.env.dndchat.production" ]; then
        log_error ".env.dndchat.production not found!"
        log_error "This file contains production configuration (ChromaCloud credentials, etc.)"
        log_error "Create it before deploying"
        exit 1
    fi
    log_success ".env.dndchat.production found"
    
    # Check if required source directories exist
    local required_dirs=("src" "scripts")
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$PROJECT_ROOT/$dir" ]; then
            log_error "Required directory '$dir' not found!"
            exit 1
        fi
    done
    log_success "Required directories exist"
    
    # Check if required files exist
    local required_files=("requirements.txt" "pyproject.toml")
    for file in "${required_files[@]}"; do
        if [ ! -f "$PROJECT_ROOT/$file" ]; then
            log_error "Required file '$file' not found!"
            exit 1
        fi
    done
    log_success "Required files exist"
    
    # Check SSH connectivity
    log_info "Testing SSH connection to $SSH_USER@$SSH_HOST..."
    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_USER@$SSH_HOST" exit 2>/dev/null; then
        log_warning "SSH key authentication not configured"
        log_info "You'll be prompted for password multiple times during deployment"
        log_info "Consider setting up SSH keys: ssh-copy-id $SSH_USER@$SSH_HOST"
    else
        log_success "SSH connection successful"
    fi
}

create_remote_directory() {
    log_info "Creating remote directory structure..."
    ssh "$SSH_USER@$SSH_HOST" "mkdir -p $REMOTE_DIR/data/user_requests"
    log_success "Remote directory created: $REMOTE_DIR"
}

upload_application_files() {
    log_info "Uploading application files (query-only, minimal deployment)..."
    
    # Create temporary tar file locally
    local TAR_FILE="$PROJECT_ROOT/deployment.tar.gz"
    log_info "  → Creating deployment archive..."
    
    # Create temporary directory structure for tar
    local TEMP_DIR="$PROJECT_ROOT/.deploy_tmp"
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR/src/query" "$TEMP_DIR/src/utils" "$TEMP_DIR/scripts"
    
    # Copy files to temp directory
    # Flask API
    cp "$PROJECT_ROOT/src/api.py" "$TEMP_DIR/src/"
    touch "$TEMP_DIR/src/__init__.py"
    
    # Query module
    cp "$PROJECT_ROOT/src/query/docling_query.py" "$TEMP_DIR/src/query/"
    cp "$PROJECT_ROOT/src/query/query_must_filter.py" "$TEMP_DIR/src/query/"
    cp "$PROJECT_ROOT/src/query/__init__.py" "$TEMP_DIR/src/query/" 2>/dev/null || touch "$TEMP_DIR/src/query/__init__.py"
    
    # Utils module
    cp "$PROJECT_ROOT/src/utils/chromadb_connector.py" "$TEMP_DIR/src/utils/"
    cp "$PROJECT_ROOT/src/utils/config.py" "$TEMP_DIR/src/utils/"
    cp "$PROJECT_ROOT/src/utils/rag_output.py" "$TEMP_DIR/src/utils/"
    cp "$PROJECT_ROOT/src/utils/token_validator.py" "$TEMP_DIR/src/utils/"
    cp "$PROJECT_ROOT/src/utils/rate_limiter.py" "$TEMP_DIR/src/utils/"
    cp "$PROJECT_ROOT/src/utils/cost_tracker.py" "$TEMP_DIR/src/utils/"
    touch "$TEMP_DIR/src/utils/__init__.py"
    
    # Dependency files
    if [ -f "$PROJECT_ROOT/requirements-production.txt" ]; then
        cp "$PROJECT_ROOT/requirements-production.txt" "$TEMP_DIR/requirements.txt"
    else
        cp "$PROJECT_ROOT/requirements.txt" "$TEMP_DIR/requirements.txt"
    fi
    
    if [ -f "$PROJECT_ROOT/pyproject-production.toml" ]; then
        cp "$PROJECT_ROOT/pyproject-production.toml" "$TEMP_DIR/pyproject.toml"
    else
        cp "$PROJECT_ROOT/pyproject.toml" "$TEMP_DIR/pyproject.toml"
    fi
    
    # Scripts
    cp "$PROJECT_ROOT/scripts/setup_venv.sh" "$TEMP_DIR/scripts/"
    cp "$PROJECT_ROOT/scripts/start_flask.sh" "$TEMP_DIR/scripts/"
    cp "$PROJECT_ROOT/scripts/stop_flask.sh" "$TEMP_DIR/scripts/"
    
    # .env.dndchat.production file (will be renamed to .env.dndchat and placed in parent directory on production server)
    cp "$PROJECT_ROOT/.env.dndchat.production" "$TEMP_DIR/.env.dndchat"
    
    # Apache .htaccess file for PHP proxy
    if [ -f "$PROJECT_ROOT/.htaccess.production" ]; then
        cp "$PROJECT_ROOT/.htaccess.production" "$TEMP_DIR/.htaccess"
        log_success "  ✓ Apache .htaccess configuration included"
    fi
    
    # PHP proxy script
    if [ -f "$PROJECT_ROOT/api_proxy.php" ]; then
        cp "$PROJECT_ROOT/api_proxy.php" "$TEMP_DIR/api_proxy.php"
        log_success "  ✓ PHP proxy script included"
    fi
    
    # Create tar archive
    cd "$TEMP_DIR"
    tar -czf "$TAR_FILE" .
    cd "$PROJECT_ROOT"
    rm -rf "$TEMP_DIR"
    log_success "  ✓ Deployment archive created"
    
    # Upload tar file
    log_info "  → Uploading deployment archive..."
    scp "$TAR_FILE" "$SSH_USER@$SSH_HOST:$REMOTE_DIR/deployment.tar.gz"
    log_success "  ✓ Archive uploaded"
    
    # Extract on remote server
    log_info "  → Extracting files on remote server..."
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && tar -xzf deployment.tar.gz && rm deployment.tar.gz"
    log_success "  ✓ Files extracted and archive cleaned up"
    
    # Move .env.dndchat to parent directory (outside public_html for security)
    log_info "  → Moving .env.dndchat to parent directory for security..."
    ssh "$SSH_USER@$SSH_HOST" "mv $REMOTE_DIR/.env.dndchat ~/.env.dndchat && chmod 600 ~/.env.dndchat"
    log_success "  ✓ .env.dndchat secured in parent directory"
    
    # Set permissions
    log_info "  → Setting file permissions..."
    ssh "$SSH_USER@$SSH_HOST" "chmod +x $REMOTE_DIR/scripts/*.sh"
    log_success "  ✓ Permissions set"
    
    # Clean up local tar file
    rm -f "$TAR_FILE"
    log_success "  ✓ Query-only modules deployed"
    log_info "    Excluded: chunkers, converters, embedders, preprocessors, transformers"
}

setup_virtual_environment() {
    log_info "Setting up Python virtual environment on remote server..."
    
    # Make scripts executable
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && chmod +x scripts/*.sh"
    
    # Run setup_venv.sh
    log_info "  → Running setup_venv.sh (this may take 3-5 minutes)..."
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && ./scripts/setup_venv.sh" || {
        log_error "Virtual environment setup failed!"
        log_error "Check Python version (requires 3.10+) on remote server"
        exit 1
    }
    log_success "  ✓ Virtual environment created"
    
    # Install package in development mode
    log_info "  → Installing package in development mode..."
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && source venv/bin/activate && pip install -e ."
    log_success "  ✓ Package installed"
}

verify_chromacloud_connectivity() {
    log_info "Verifying ChromaCloud connectivity from remote server..."
    
    # Test ChromaDB connection
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && source venv/bin/activate && python3 -c \"
from src.utils.chromadb_connector import ChromaDBConnector
try:
    connector = ChromaDBConnector()
    collections = [col.name for col in connector.list_collections()]
    print('✓ Connected to ChromaCloud')
    print('  Collections:', collections)
    if 'adnd_1e' not in collections:
        print('  WARNING: Expected collection adnd_1e not found')
        exit(1)
except Exception as e:
    print('✗ ChromaCloud connection failed:', str(e))
    exit(1)
\"" || {
        log_error "ChromaCloud connectivity check failed!"
        log_error "Verify credentials in ~/.env.dndchat are correct"
        exit 1
    }
    log_success "  ✓ ChromaCloud connection verified"
}

start_flask_server() {
    log_info "Starting Flask server (HTTP-only, Apache handles SSL)..."
    
    # Stop Flask if already running
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && ./scripts/stop_flask.sh" 2>/dev/null || true
    
    # Start Flask in HTTP mode (Apache will proxy with SSL)
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && ./scripts/start_flask.sh"
    
    # Wait for startup
    log_info "  → Waiting for Flask to start (5 seconds)..."
    sleep 5
    
    # Verify Flask is running on localhost:5000
    log_info "  → Verifying Flask health endpoint..."
    if ssh "$SSH_USER@$SSH_HOST" "curl -s http://localhost:5000/health" > /dev/null 2>&1; then
        log_success "  ✓ Flask server started successfully with HTTPS"
    elif ssh "$SSH_USER@$SSH_HOST" "curl -s http://localhost:5000/health" > /dev/null 2>&1; then
        log_warning "  ⚠ Flask server started with HTTP only (SSL certificates not found)"
        log_warning "  To enable HTTPS, set SSL_CERT_PATH and SSL_KEY_PATH in ~/.env.dndchat"
    else
        log_error "Flask health check failed!"
        log_error "Check Flask logs: ssh $SSH_USER@$SSH_HOST 'tail -50 $REMOTE_DIR/flask.log'"
        exit 1
    fi
}

run_integration_tests() {
    log_info "Running integration tests..."
    
    # Test health endpoint
    log_info "  → Testing /health endpoint..."
    ssh "$SSH_USER@$SSH_HOST" "curl -s http://localhost:5000/health | grep -q 'healthy'" || {
        log_warning "Health endpoint test failed"
        return 1
    }
    log_success "  ✓ Health endpoint OK"
    
    # Test ChromaDB collections via Python (no CLI needed)
    log_info "  → Testing ChromaDB collections..."
    ssh "$SSH_USER@$SSH_HOST" "cd $REMOTE_DIR && source venv/bin/activate && python3 -c \"
from src.utils.chromadb_connector import ChromaDBConnector
connector = ChromaDBConnector()
collections = [col.name for col in connector.list_collections()]
print('Collections found:', len(collections))
for c in collections:
    print(f'  - {c}')
\"" || {
        log_warning "Collections test failed"
        return 1
    }
    log_success "  ✓ Collections accessible"
    
    log_success "Integration tests passed!"
}

print_deployment_summary() {
    echo
    log_success "========================================="
    log_success "  Deployment Complete!"
    log_success "========================================="
    echo
    log_info "Server Details:"
    echo "  • Host: $SSH_HOST"
    echo "  • Directory: $REMOTE_DIR"
    echo "  • Flask Port: 5000"
    echo "  • ChromaDB: ChromaCloud"
    echo
    log_info "Useful Commands:"
    echo "  • View logs: ssh $SSH_USER@$SSH_HOST 'tail -f $REMOTE_DIR/flask.log'"
    echo "  • Restart Flask: ssh $SSH_USER@$SSH_HOST 'cd $REMOTE_DIR && ./scripts/stop_flask.sh && ./scripts/start_flask.sh'"
    echo "  • Check health: curl http://$SSH_HOST:5000/health"
    echo
    log_info "Next Steps:"
    echo "  1. Test from React frontend: https://react.gravitycar.com"
    echo "  2. Verify CORS headers allow frontend requests"
    echo "  3. Test OAuth2 token validation"
    echo "  4. Monitor Flask logs for errors"
    echo "  5. Set up cron job for auto-restart on reboot"
    echo
    log_info "Auto-Restart on Reboot (optional):"
    echo "  ssh $SSH_USER@$SSH_HOST"
    echo "  crontab -e"
    echo "  # Add line: @reboot cd $REMOTE_DIR && ./scripts/start_flask.sh"
    echo
}

################################################################################
# Main Deployment Flow
################################################################################

main() {
    # Parse command-line arguments
    if [ $# -lt 2 ]; then
        log_error "Usage: $0 <SSH_HOST> <SSH_USER>"
        log_error "Example: $0 dndchat.gravitycar.com gravityc"
        exit 1
    fi
    
    SSH_HOST="$1"
    SSH_USER="$2"
    
    # Print banner
    print_banner
    
    # Step 1: Check local prerequisites
    check_local_prerequisites
    
    # Step 3: Create remote directory structure
    create_remote_directory
    
    # Step 4: Upload application files
    upload_application_files
    
    # Step 5: Setup virtual environment
    setup_virtual_environment
    
    # Step 6: Verify ChromaCloud connectivity
    verify_chromacloud_connectivity
    
    # Step 7: Start Flask server
    start_flask_server
    
    # Step 8: Run integration tests
    run_integration_tests
    
    # Step 9: Print deployment summary
    print_deployment_summary
}

# Run main function
main "$@"
