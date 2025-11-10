#!/bin/bash
################################################################################
# Test PHP Proxy Setup
# 
# This script tests the PHP proxy configuration for the Flask API.
# Run after deployment to verify everything is working.
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

echo "========================================="
echo "  Testing PHP Proxy Setup"
echo "========================================="
echo

# Test 1: Flask backend is running
log_info "Test 1: Checking if Flask is running on localhost:5000..."
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    log_success "Flask is running"
else
    log_error "Flask is not running on localhost:5000"
    echo "  Run: ssh gravityc@dog.he.net 'cd /home/gravityc/public_html/dndchat.gravitycar.com && ./scripts/start_flask.sh'"
    exit 1
fi

# Test 2: Apache serves the site with SSL
log_info "Test 2: Checking if Apache serves HTTPS..."
if curl -I https://dndchat.gravitycar.com 2>&1 | grep -q "200 OK"; then
    log_success "Apache HTTPS is working"
else
    log_error "Apache HTTPS failed"
    exit 1
fi

# Test 3: Health endpoint through PHP proxy
log_info "Test 3: Testing /health through PHP proxy..."
HEALTH_RESPONSE=$(curl -s https://dndchat.gravitycar.com/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    log_success "Health endpoint works through PHP proxy"
    echo "  Response: $HEALTH_RESPONSE"
else
    log_error "Health endpoint failed"
    echo "  Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test 4: CORS headers
log_info "Test 4: Checking CORS headers..."
CORS_HEADERS=$(curl -I -H "Origin: https://react.gravitycar.com" https://dndchat.gravitycar.com/health 2>&1)
if echo "$CORS_HEADERS" | grep -qi "access-control-allow-origin"; then
    log_success "CORS headers present"
else
    log_error "CORS headers missing"
    echo "$CORS_HEADERS"
fi

# Test 5: SSL certificate validity
log_info "Test 5: Checking SSL certificate..."
SSL_INFO=$(curl -vI https://dndchat.gravitycar.com 2>&1 | grep -i "subject:")
if echo "$SSL_INFO" | grep -q "gravitycar.com"; then
    log_success "SSL certificate is valid"
    echo "  $SSL_INFO"
else
    log_error "SSL certificate issue"
    echo "$SSL_INFO"
fi

echo
log_success "========================================="
log_success "  All Tests Passed!"
log_success "========================================="
echo
log_info "Your API is ready at: https://dndchat.gravitycar.com/api/query"
log_info "Update your React frontend to use this URL (no port needed)"
