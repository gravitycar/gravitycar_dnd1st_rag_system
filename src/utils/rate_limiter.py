#!/usr/bin/env python3
"""
Token bucket rate limiter with per-user file storage.

Uses fcntl for file locking to prevent race conditions.
Each user gets their own JSON file to eliminate cross-user contention.
"""

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Tuple


class TokenBucket:
    """Per-user file-based rate limiter with fcntl locking."""
    
    def __init__(
        self, 
        capacity: int = 15, 
        refill_rate: float = 1/60, 
        daily_limit: int = 30,
        data_dir: str = None
    ):
        """
        Initialize token bucket rate limiter.
        
        Args:
            capacity: Max tokens (burst allowance) - default 15
            refill_rate: Tokens per second - default 1/60 (1 per minute)
            daily_limit: Max requests per user per day - default 30
            data_dir: Directory to store user rate limit files
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.daily_limit = daily_limit
        
        if data_dir is None:
            data_dir = os.getenv('RATE_LIMIT_DIR', 'data/user_requests')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_user_file(self, user_id: str) -> Path:
        """Get path to user's rate limit file."""
        safe_id = user_id.replace('/', '_').replace('\\', '_')
        return self.data_dir / f"{safe_id}.json"
    
    def allow_request(self, user_id: str) -> Tuple[bool, dict]:
        """
        Check if request allowed for user.
        
        Args:
            user_id: User identifier (GUID from api.gravitycar.com)
            
        Returns:
            (allowed: bool, info: dict)
            
        info dict contains:
            - allowed: bool
            - reason: str (if denied)
            - remaining_burst: int (tokens left)
            - daily_remaining: int (requests left today)
            - retry_after: int (seconds until next token, if rate limited)
            - message: str (human-readable explanation)
        """
        user_file = self._get_user_file(user_id)
        
        try:
            # Read current state (create if doesn't exist)
            if user_file.exists():
                with open(user_file, 'r') as f:
                    # Try to acquire exclusive lock (non-blocking)
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except IOError:
                        # File is locked - concurrent request from same user
                        return False, {
                            'allowed': False,
                            'reason': 'concurrent_request',
                            'message': 'Another request is being processed. Please wait and try again.',
                            'retry_after': 1
                        }
                    
                    try:
                        data = json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            else:
                # New user - initialize
                data = {
                    'user_id': user_id,
                    'tokens': self.capacity,
                    'last_refill': time.time(),
                    'daily_count': 0,
                    'daily_reset': time.strftime('%Y-%m-%d')
                }
            
            # Process rate limit logic
            now = time.time()
            today = time.strftime('%Y-%m-%d')
            
            # Reset daily counter if new day
            if data['daily_reset'] != today:
                data['daily_count'] = 0
                data['daily_reset'] = today
                data['tokens'] = self.capacity
                data['last_refill'] = now
            
            # Check daily limit first
            if data['daily_count'] >= self.daily_limit:
                return False, {
                    'allowed': False,
                    'reason': 'daily_limit_exceeded',
                    'daily_remaining': 0,
                    'retry_after': None,
                    'message': f'Daily limit of {self.daily_limit} requests exceeded. Try again tomorrow.'
                }
            
            # Refill tokens based on elapsed time
            elapsed = now - data['last_refill']
            refill_amount = elapsed * self.refill_rate
            data['tokens'] = min(self.capacity, data['tokens'] + refill_amount)
            data['last_refill'] = now
            
            # Check token availability
            if data['tokens'] >= 1.0:
                data['tokens'] -= 1.0
                data['daily_count'] += 1
                
                # Write updated state with exclusive lock
                with open(user_file, 'w') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        json.dump(data, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                return True, {
                    'allowed': True,
                    'remaining_burst': int(data['tokens']),
                    'daily_remaining': self.daily_limit - data['daily_count'],
                    'retry_after': None
                }
            else:
                # Rate limited - calculate wait time
                tokens_needed = 1.0 - data['tokens']
                retry_after = int(tokens_needed / self.refill_rate)
                
                return False, {
                    'allowed': False,
                    'reason': 'rate_limited',
                    'remaining_burst': 0,
                    'daily_remaining': self.daily_limit - data['daily_count'],
                    'retry_after': retry_after,
                    'message': f'Rate limit exceeded. Please wait {retry_after} seconds.'
                }
        
        except Exception as e:
            # Fail closed on any error (deny request)
            return False, {
                'allowed': False,
                'reason': 'system_error',
                'message': f'Rate limiting system error: {str(e)}',
                'retry_after': 5
            }
