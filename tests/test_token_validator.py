#!/usr/bin/env python3
"""Unit tests for TokenValidator."""

import pytest
import time
from unittest.mock import Mock, patch
from src.utils.token_validator import TokenValidator


class TestTokenValidator:
    """Test OAuth2 token validation with caching."""
    
    def test_valid_token_success(self):
        """Test validation with valid token."""
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'id': 'user-123',
                'email': 'test@example.com'
            }
        }
        
        with patch('requests.get', return_value=mock_response):
            user_info = validator.validate('fake-token')
        
        assert user_info is not None
        assert user_info['id'] == 'user-123'
        assert user_info['email'] == 'test@example.com'
    
    def test_invalid_token_returns_none(self):
        """Test validation with invalid token."""
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('requests.get', return_value=mock_response):
            user_info = validator.validate('invalid-token')
        
        assert user_info is None
    
    def test_cache_hit_no_api_call(self):
        """Test that cached tokens don't make API calls."""
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        # First call - cache miss
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'id': 'user-123', 'email': 'test@example.com'}
        }
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            validator.validate('token-abc')
            assert mock_get.call_count == 1
            
            # Second call - cache hit (no API call)
            validator.validate('token-abc')
            assert mock_get.call_count == 1  # Still 1, not 2
    
    def test_cache_expiration(self):
        """Test that expired cache entries are removed."""
        validator = TokenValidator('https://api.example.com', cache_ttl=1)  # 1 second TTL
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'id': 'user-123'}
        }
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            # First call
            validator.validate('token-abc')
            assert mock_get.call_count == 1
            
            # Wait for cache to expire
            time.sleep(1.5)
            
            # Second call - cache expired, should make API call
            validator.validate('token-abc')
            assert mock_get.call_count == 2
    
    def test_api_timeout_returns_none(self):
        """Test that API timeouts fail gracefully."""
        import requests
        validator = TokenValidator('https://api.example.com', cache_ttl=60)
        
        with patch('requests.get', side_effect=requests.exceptions.RequestException('Connection timeout')):
            user_info = validator.validate('token-abc')
        
        assert user_info is None
    
    def test_cleanup_expired_cache(self):
        """Test manual cache cleanup."""
        validator = TokenValidator('https://api.example.com', cache_ttl=1)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': {'id': 'user-123'}}
        
        with patch('requests.get', return_value=mock_response):
            validator.validate('token-abc')
        
        # Cache should have 1 entry
        assert len(validator.cache) == 1
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Cleanup
        validator.cleanup_expired_cache()
        
        # Cache should be empty
        assert len(validator.cache) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
