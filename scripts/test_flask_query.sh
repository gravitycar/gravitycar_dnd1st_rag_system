#!/usr/bin/bash

# Test script for Flask API query endpoint
# Usage: ./scripts/test_flask_query.sh "Bearer <token>" "Your question here"
# Example: ./scripts/test_flask_query.sh "Bearer eyJ..." "What is a beholder?"

# Check arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 \"Bearer <token>\" \"<question>\" [debug] [k]"
    echo ""
    echo "Arguments:"
    echo "  token    - Full Bearer token (e.g., \"Bearer eyJ...\")"
    echo "  question - Question to ask (e.g., \"What is a beholder?\")"
    echo "  debug    - Optional: true/false (default: false)"
    echo "  k        - Optional: number of chunks to retrieve (default: 15)"
    echo ""
    echo "Example:"
    echo "  $0 \"Bearer eyJhbGc...\" \"What is a beholder?\""
    echo "  $0 \"Bearer eyJhbGc...\" \"How many XP for fighter 9th level?\" true 20"
    exit 1
fi

BEARER_TOKEN="$1"
QUESTION="$2"
DEBUG="${3:-false}"
K="${4:-15}"

# Load environment to get Flask port
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

FLASK_PORT=${FLASK_PORT:-5000}
FLASK_URL="http://localhost:${FLASK_PORT}/api/query"
CORS_ORIGIN="${CORS_ORIGINS%%,*}"  # Use first CORS origin

# Build JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
  "question": "$QUESTION",
  "debug": $DEBUG,
  "k": $K
}
EOF
)

# Display request info
echo "================================================================================"
echo "Testing Flask API Query"
echo "================================================================================"
echo "URL: $FLASK_URL"
echo "Origin: $CORS_ORIGIN"
echo "Question: $QUESTION"
echo "Debug: $DEBUG"
echo "K: $K"
echo "================================================================================"
echo ""

# Make request (save to temp file to separate JSON from HTTP status)
TEMP_OUTPUT=$(mktemp)
HTTP_STATUS=$(curl -X POST "$FLASK_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: $BEARER_TOKEN" \
  -H "Origin: $CORS_ORIGIN" \
  -d "$JSON_PAYLOAD" \
  -w "%{http_code}" \
  -s -o "$TEMP_OUTPUT")

# Display formatted JSON
cat "$TEMP_OUTPUT" | jq '.'

# Display HTTP status
echo ""
echo "HTTP Status: $HTTP_STATUS"

# Cleanup
rm -f "$TEMP_OUTPUT"

echo ""
echo "================================================================================"
