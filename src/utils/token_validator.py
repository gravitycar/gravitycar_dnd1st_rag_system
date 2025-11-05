#!/usr/bin/env python3
"""
OAuth2 JWT token validator with caching.

Validates JWT tokens with api.gravitycar.com and caches results
for 5 minutes to reduce API calls by 80%.
"""

import time
import requests
from threading import Lock
from typing import Optional, Dict
import os


class TokenValidator:
    """Validate JWT tokens with api.gravitycar.com with caching."""
    
    def __init__(self, api_base_url: str, cache_ttl: int = 300):
        """
        Initialize token validator.
        
        Args:
            api_base_url: Base URL for api.gravitycar.com
            cache_ttl: Cache TTL in seconds (default 300 = 5 minutes)
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.cache_ttl = cache_ttl
        self.cache: Dict[str, dict] = {}  # token -> {user_info, expires_at}
        self.lock = Lock()
    
    def validate(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token and return user info.
        
        Args:
            token: JWT token (without "Bearer " prefix)
            
        Returns:
            User info dict: {"id": "guid-string", "email": "...", ...}
            None if invalid
        """
        with self.lock:
            # Check cache first
            now = time.time()
            if token in self.cache:
                cached = self.cache[token]
                if cached['expires_at'] > now:
                    return cached['user_info']
                else:
                    # Expired - remove from cache
                    del self.cache[token]
            
            # Cache miss - validate with API
            try:
                response = requests.get(
                    f"{self.api_base_url}/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=5
                )
                
                if response.status_code == 200:
                    data = response.json()
                    user_info = data.get('data')
                    
                    if user_info:
                        # Cache the result
                        self.cache[token] = {
                            'user_info': user_info,
                            'expires_at': now + self.cache_ttl
                        }
                        return user_info
                
                return None
                
            except requests.exceptions.RequestException as e:
                print(f"Error validating token: {e}")
                return None
    
    def cleanup_expired_cache(self):
        """Remove expired cache entries."""
        with self.lock:
            now = time.time()
            expired_tokens = [
                token for token, data in self.cache.items()
                if data['expires_at'] <= now
            ]
            for token in expired_tokens:
                del self.cache[token]
