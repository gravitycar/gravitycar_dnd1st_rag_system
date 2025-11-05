#!/usr/bin/env python3
"""Unit tests for TokenBucket rate limiter."""

import pytest
import time
import json
import tempfile
from pathlib import Path
from src.utils.rate_limiter import TokenBucket


class TestTokenBucket:
    """Test token bucket rate limiting."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for rate limit files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_first_request_allowed(self, temp_dir):
        """Test that first request is allowed."""
        limiter = TokenBucket(capacity=15, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        allowed, info = limiter.allow_request('user-123')
        
        assert allowed is True
        assert info['allowed'] is True
        assert info['remaining_burst'] == 14  # Started with 15, used 1
        assert info['daily_remaining'] == 29  # Started with 30, used 1
    
    def test_burst_capacity_exhaustion(self, temp_dir):
        """Test that burst capacity is enforced."""
        limiter = TokenBucket(capacity=3, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        
        # Use all 3 tokens
        for i in range(3):
            allowed, info = limiter.allow_request('user-123')
            assert allowed is True
        
        # 4th request should fail
        allowed, info = limiter.allow_request('user-123')
        assert allowed is False
        assert info['reason'] == 'rate_limited'
        assert 'retry_after' in info
    
    def test_token_refill(self, temp_dir):
        """Test that tokens refill over time."""
        limiter = TokenBucket(capacity=5, refill_rate=2, daily_limit=30, data_dir=temp_dir)  # 2 tokens/sec
        
        # Use all 5 tokens
        for i in range(5):
            limiter.allow_request('user-123')
        
        # Wait for 1 token to refill (0.5 seconds)
        time.sleep(0.6)
        
        # Should succeed now
        allowed, info = limiter.allow_request('user-123')
        assert allowed is True
    
    def test_daily_limit_enforcement(self, temp_dir):
        """Test that daily limit is enforced."""
        limiter = TokenBucket(capacity=5, refill_rate=10, daily_limit=3, data_dir=temp_dir)
        
        # Use 3 requests (daily limit)
        for i in range(3):
            allowed, info = limiter.allow_request('user-123')
            assert allowed is True
        
        # 4th request should fail with daily_limit_exceeded
        allowed, info = limiter.allow_request('user-123')
        assert allowed is False
        assert info['reason'] == 'daily_limit_exceeded'
        assert info['daily_remaining'] == 0
    
    def test_daily_reset(self, temp_dir):
        """Test that daily counter resets on new day."""
        limiter = TokenBucket(capacity=5, refill_rate=1, daily_limit=3, data_dir=temp_dir)
        
        # Use all daily requests
        for i in range(3):
            limiter.allow_request('user-123')
        
        # Manually update the file to previous day
        user_file = Path(temp_dir) / 'user-123.json'
        with open(user_file, 'r') as f:
            data = json.load(f)
        
        data['daily_reset'] = '2020-01-01'  # Old date
        
        with open(user_file, 'w') as f:
            json.dump(data, f)
        
        # Next request should succeed (new day)
        allowed, info = limiter.allow_request('user-123')
        assert allowed is True
        assert info['daily_remaining'] == 2  # Reset to daily limit - 1
    
    def test_per_user_isolation(self, temp_dir):
        """Test that users have independent rate limits."""
        limiter = TokenBucket(capacity=2, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        
        # User 1 exhausts their tokens
        limiter.allow_request('user-1')
        limiter.allow_request('user-1')
        allowed, _ = limiter.allow_request('user-1')
        assert allowed is False
        
        # User 2 should still have tokens
        allowed, info = limiter.allow_request('user-2')
        assert allowed is True
        assert info['remaining_burst'] == 1
    
    def test_file_creation(self, temp_dir):
        """Test that user rate limit files are created."""
        limiter = TokenBucket(capacity=15, refill_rate=1/60, daily_limit=30, data_dir=temp_dir)
        limiter.allow_request('user-abc')
        
        user_file = Path(temp_dir) / 'user-abc.json'
        assert user_file.exists()
        
        with open(user_file, 'r') as f:
            data = json.load(f)
        
        assert data['user_id'] == 'user-abc'
        assert 'tokens' in data
        assert 'daily_count' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
