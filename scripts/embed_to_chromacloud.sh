#!/bin/bash
################################################################################
# ChromaCloud Embedding Script
# Embeds all 3 D&D books to ChromaCloud from local machine
#
# PREREQUISITE: Uncomment ChromaCloud credentials in .env:
#   chroma_cloud_api_key=YOUR_CHROMACLOUD_API_KEY
#   chroma_cloud_tenant_id=YOUR_TENANT_ID
#   chroma_cloud_database=adnd_1e
#
# USAGE:
#   ./scripts/embed_to_chromacloud.sh
#
# This script must be run BEFORE deploying to production!
################################################################################

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
    echo -e "${BLUE}  ChromaCloud Embedding Script${NC}"
    echo -e "${BLUE}  D&D 1st Edition (3 Books)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if venv is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        log_error "Virtual environment not activated!"
        log_error "Run: source venv/bin/activate"
        exit 1
    fi
    log_success "Virtual environment active: $VIRTUAL_ENV"
    
    # Check if chunk files exist
    if [ ! -f "data/chunks/chunks_Monster_Manual_(1e).json" ]; then
        log_error "Monster Manual chunks not found!"
        exit 1
    fi
    if [ ! -f "data/chunks/chunks_Players_Handbook_(1e)_organized.json" ]; then
        log_error "Player's Handbook chunks not found!"
        exit 1
    fi
    if [ ! -f "data/chunks/chunks_DMG_with_query_must.json" ]; then
        log_error "Dungeon Master's Guide chunks not found!"
        exit 1
    fi
    log_success "All chunk files found"
    
    # Check if ChromaCloud credentials are uncommented in .env
    if ! grep -q "^chroma_cloud_api_key=" .env; then
        log_error "ChromaCloud credentials not enabled in .env!"
        echo
        log_info "Please uncomment these lines in .env:"
        echo "  chroma_cloud_api_key=YOUR_CHROMACLOUD_API_KEY"
        echo "  chroma_cloud_tenant_id=YOUR_TENANT_ID"
        echo "  chroma_cloud_database=adnd_1e"
        exit 1
    fi
    log_success "ChromaCloud credentials enabled"
}

verify_chromacloud_connection() {
    log_info "Verifying ChromaCloud connection..."
    python3 -c "
from src.utils.chromadb_connector import ChromaDBConnector
try:
    connector = ChromaDBConnector()
    collections = [col.name for col in connector.list_collections()]
    print('✓ Connected to ChromaCloud')
    print('  Existing collections:', collections if collections else 'None')
except Exception as e:
    print('✗ ChromaCloud connection failed:', str(e))
    exit(1)
" || {
        log_error "ChromaCloud connection failed!"
        exit 1
    }
    log_success "ChromaCloud connection verified"
}

embed_book() {
    local chunk_file=$1
    local collection_name=$2
    local book_name=$3
    
    log_info "Embedding $book_name..."
    log_info "  File: $chunk_file"
    log_info "  Collection: $collection_name"
    
    dnd-embed "$chunk_file" "$collection_name" || {
        log_error "Failed to embed $book_name!"
        exit 1
    }
    
    log_success "$book_name embedded successfully!"
    echo
}

verify_all_collections() {
    log_info "Verifying all collections in ChromaCloud..."
    
    dnd-rag collections || {
        log_error "Failed to list collections!"
        exit 1
    }
    
    # Check that we have exactly 3 collections
    local collection_count=$(python3 -c "
from src.utils.chromadb_connector import ChromaDBConnector
connector = ChromaDBConnector()
print(len(connector.list_collections()))
")
    
    if [ "$collection_count" != "3" ]; then
        log_warning "Expected 3 collections, found $collection_count"
    else
        log_success "All 3 collections verified!"
    fi
}

test_sample_query() {
    log_info "Testing sample query..."
    
    dnd-query dnd_monster_manual "What is a beholder?" || {
        log_warning "Sample query failed (this may be OK if just starting)"
    }
    
    log_success "Sample query test complete"
}

print_summary() {
    echo
    log_success "========================================="
    log_success "  Embedding Complete!"
    log_success "========================================="
    echo
    log_info "Collections Created:"
    echo "  • dnd_monster_manual (Monster Manual)"
    echo "  • dnd_players_handbook (Player's Handbook)"
    echo "  • dnd_dmg (Dungeon Master's Guide)"
    echo
    log_info "Next Steps:"
    echo "  1. Verify collections: dnd-rag collections"
    echo "  2. Test queries: dnd-query dnd_monster_manual \"What is a beholder?\""
    echo "  3. Deploy to production: ./scripts/deploy_to_production.sh dndchat.gravitycar.com your_user"
    echo
    log_warning "IMPORTANT: Re-comment ChromaCloud credentials in .env if you want to use local ChromaDB again"
    echo
}

main() {
    print_banner
    
    # Step 1: Check prerequisites
    check_prerequisites
    
    # Step 2: Verify ChromaCloud connection
    verify_chromacloud_connection
    
    # Step 3: Embed Monster Manual
    embed_book \
        "data/chunks/chunks_Monster_Manual_(1e).json" \
        "dnd_monster_manual" \
        "Monster Manual"
    
    # Step 4: Embed Player's Handbook
    embed_book \
        "data/chunks/chunks_Players_Handbook_(1e)_organized.json" \
        "dnd_players_handbook" \
        "Player's Handbook"
    
    # Step 5: Embed Dungeon Master's Guide
    embed_book \
        "data/chunks/chunks_DMG_with_query_must.json" \
        "dnd_dmg" \
        "Dungeon Master's Guide"
    
    # Step 6: Verify all collections
    verify_all_collections
    
    # Step 7: Test sample query
    test_sample_query
    
    # Step 8: Print summary
    print_summary
}

# Run main function
main
