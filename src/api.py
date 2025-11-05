#!/usr/bin/env python3
"""
Flask REST API for D&D 1st Edition RAG system.

Provides OAuth2-authenticated query endpoint with rate limiting
and cost tracking.
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import sys
import logging
import traceback
from datetime import datetime

# Import RAG system and utilities
from src.query.docling_query import DnDRAG
from src.utils.rag_output import RAGOutput
from src.utils.token_validator import TokenValidator
from src.utils.rate_limiter import TokenBucket
from src.utils.cost_tracker import CostTracker
from src.utils.config import get_env_float, get_env_int, get_env_string

# Note: These helpers will be added to existing src/utils/config.py

# Create Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('flask.log')
    ]
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("=" * 80)
logger.info("Flask API Starting...")
logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
logger.info(f"Auth API: {os.getenv('AUTH_API_URL')}")
logger.info(f"CORS Origins: {os.getenv('CORS_ORIGINS')}")
logger.info("=" * 80)

# Configure CORS from environment variable
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000')
cors_origins_list = [origin.strip() for origin in cors_origins.split(',')]

CORS(app, 
     origins=cors_origins_list,
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)

# Initialize global components
token_validator = TokenValidator(
    api_base_url=os.getenv('AUTH_API_URL'),
    cache_ttl=int(os.getenv('TOKEN_CACHE_TTL', '300'))
)

rate_limiter = TokenBucket(
    capacity=get_env_int('TOKEN_BUCKET_CAPACITY', 15),
    refill_rate=get_env_float('TOKEN_REFILL_RATE', 1/60),
    daily_limit=get_env_int('DAILY_USER_REQUEST_LIMIT', 30),
    data_dir=get_env_string('RATE_LIMIT_DIR', 'data/user_requests')
)

cost_tracker = CostTracker(
    daily_budget_usd=get_env_float('DAILY_BUDGET_USD', 1.0),
    alert_email=get_env_string('ALERT_EMAIL'),
    model=get_env_string('OPENAI_MODEL', 'gpt-4o-mini')  # Get model from config
)

# Initialize RAG system (lazy initialization on first query)
rag = None

def get_rag():
    """Get or initialize RAG system."""
    global rag
    if rag is None:
        try:
            logger.info("Initializing D&D RAG system...")
            rag = DnDRAG()
            logger.info("✅ D&D RAG system initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG system: {e}")
            logger.error(traceback.format_exc())
            raise
    return rag


def extract_token() -> str:
    """Extract JWT token from Authorization header."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    return auth_header.split(' ', 1)[1]


def validate_user() -> dict:
    """
    Validate JWT token and return user info.
    
    Returns:
        User info dict with 'id' key
        
    Aborts with HTTP 401 if invalid token
    """
    token = extract_token()
    if not token:
        return jsonify({'error': 'Missing Authorization header'}), 401
    
    user_info = token_validator.validate(token)
    if not user_info:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    return user_info


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint (no auth required)."""
    logger.debug("Health check requested")
    
    # Check if RAG system can initialize
    try:
        rag_instance = get_rag()
        rag_status = 'ok'
    except Exception as e:
        logger.error(f"RAG system not healthy: {e}")
        rag_status = 'error'
    
    response = {
        'status': 'ok' if rag_status == 'ok' else 'degraded',
        'service': 'dnd_rag',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'components': {
            'rag_system': rag_status
        }
    }
    
    return jsonify(response), 200


@app.route('/api/query', methods=['POST'])
def query():
    """
    Query the D&D RAG system.
    
    Requires:
        - Authorization: Bearer <jwt_token> header
        - JSON body: {"question": str, "debug": bool (optional), "k": int (optional)}
        
    Returns:
        JSON: {answer, diagnostics, errors, meta}
        HTTP 200: Success
        HTTP 400: Bad request (missing question)
        HTTP 401: Unauthorized (invalid token)
        HTTP 429: Rate limit exceeded
        HTTP 503: Budget exceeded
        HTTP 500: Internal error
    """
    request_start = datetime.utcnow()
    logger.info(f"Query request received from {request.remote_addr}")
    
    # 1. Validate token
    user_info = validate_user()
    if isinstance(user_info, tuple):  # Error response
        logger.warning(f"Authentication failed from {request.remote_addr}")
        return user_info
    
    user_id = user_info['id']
    user_email = user_info.get('email', 'unknown')
    logger.info(f"User authenticated: {user_id} ({user_email})")
    
    # 2. Check budget
    budget_exceeded, budget_info = cost_tracker.is_budget_exceeded()
    if budget_exceeded:
        logger.warning(f"Budget exceeded for system (${budget_info.get('daily_cost', 0):.4f} / ${budget_info.get('daily_budget', 0):.2f})")
        return jsonify({
            'error': 'budget_exceeded',
            'message': 'Daily budget exceeded. Service will resume at midnight UTC.',
            'budget_info': budget_info,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 503
    
    # 3. Check rate limit
    allowed, rate_info = rate_limiter.allow_request(user_id)
    if not allowed:
        logger.warning(f"Rate limit exceeded for user {user_id}: {rate_info['reason']}")
        response = jsonify({
            'error': rate_info['reason'],
            'message': rate_info['message'],
            'rate_info': {
                'daily_remaining': rate_info.get('daily_remaining'),
                'retry_after': rate_info.get('retry_after')
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
        response.status_code = 429
        
        if rate_info.get('retry_after'):
            response.headers['Retry-After'] = str(rate_info['retry_after'])
        
        return response
    
    # 4. Parse request
    try:
        data = request.get_json()
        if not data:
            logger.warning(f"Missing JSON body from user {user_id}")
            return jsonify({
                'error': 'Missing JSON body',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 400
        
        question = data.get('question')
        if not question:
            logger.warning(f"Missing question field from user {user_id}")
            return jsonify({
                'error': 'Missing required field: question',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 400
        
        debug = data.get('debug', False)
        k = data.get('k', 15)
        
        logger.info(f"Query from {user_id}: '{question[:100]}...' (debug={debug}, k={k})")
        
    except Exception as e:
        logger.error(f"Invalid JSON from user {user_id}: {e}")
        return jsonify({
            'error': 'Invalid JSON',
            'details': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 400
    
    # 5. Execute query
    try:
        # Get or initialize RAG system
        logger.debug("Getting RAG instance...")
        rag_instance = get_rag()
        
        # Create fresh output buffer
        rag_instance.output = RAGOutput()
        
        logger.info(f"Executing query for user {user_id}...")
        query_start = datetime.utcnow()
        result = rag_instance.query(question, k=k, debug=debug)
        query_duration = (datetime.utcnow() - query_start).total_seconds()
        
        # Extract token counts from OpenAI response
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        logger.info(f"Query completed in {query_duration:.2f}s - Tokens: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens})")
        
        # 6. Record costs
        cost_info = cost_tracker.record_query(user_id, prompt_tokens, completion_tokens)
        logger.info(f"Cost: ${cost_info['query_cost']:.6f} (daily total: ${cost_info['daily_cost']:.4f} / ${cost_info['daily_budget']:.2f})")
        
        # 7. Add metadata to response
        request_duration = (datetime.utcnow() - request_start).total_seconds()
        result['meta'] = {
            'user_id': user_id,
            'rate_limit': {
                'remaining_burst': rate_info['remaining_burst'],
                'daily_remaining': rate_info['daily_remaining']
            },
            'cost': {
                'query_cost': cost_info['query_cost'],
                'daily_total': cost_info['daily_cost'],
                'daily_budget': cost_info['daily_budget']
            },
            'performance': {
                'total_duration_seconds': round(request_duration, 3),
                'query_duration_seconds': round(query_duration, 3)
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        logger.info(f"Request completed successfully for user {user_id} in {request_duration:.2f}s")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Query processing failed for user {user_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Determine error type for better client feedback
        error_type = type(e).__name__
        error_details = str(e)
        
        # Check for common error patterns
        if 'ChromaDB' in error_details or 'chroma' in error_details.lower():
            error_category = 'database_error'
            user_message = 'Database connection failed. Please try again in a moment.'
        elif 'OpenAI' in error_details or 'API' in error_details:
            error_category = 'ai_service_error'
            user_message = 'AI service temporarily unavailable. Please try again.'
        elif 'timeout' in error_details.lower():
            error_category = 'timeout_error'
            user_message = 'Request timed out. Please try a simpler query.'
        else:
            error_category = 'internal_error'
            user_message = 'An unexpected error occurred. Please try again.'
        
        return jsonify({
            'error': 'Query processing failed',
            'error_type': error_type,
            'error_category': error_category,
            'message': user_message,
            'details': error_details,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'request_id': f"{user_id}_{int(request_start.timestamp())}"
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 Not Found: {request.path} from {request.remote_addr}")
    return jsonify({
        'error': 'Endpoint not found',
        'path': request.path,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"500 Internal Server Error: {error}")
    logger.error(traceback.format_exc())
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 500


# Log all requests (middleware)
@app.before_request
def log_request():
    """Log incoming requests."""
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")


@app.after_request
def log_response(response):
    """Log response status."""
    logger.debug(f"Response: {response.status_code}")
    return response


if __name__ == '__main__':
    # For local development only
    app.run(debug=True, host='0.0.0.0', port=5000)
