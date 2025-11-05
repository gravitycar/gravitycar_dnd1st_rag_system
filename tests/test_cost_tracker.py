#!/usr/bin/env python3
"""Unit tests for CostTracker."""

import pytest
from unittest.mock import Mock, patch
from src.utils.cost_tracker import CostTracker


class TestCostTracker:
    """Test OpenAI cost tracking and budget enforcement."""
    
    def test_cost_calculation_gpt4o_mini(self):
        """Test cost calculation for gpt-4o-mini."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        # 1000 input tokens, 500 output tokens
        info = tracker.record_query('user-123', prompt_tokens=1000, completion_tokens=500)
        
        # Expected: (1000/1M * $0.15) + (500/1M * $0.60) = $0.00015 + $0.0003 = $0.00045
        expected_cost = (1000 / 1_000_000 * 0.15) + (500 / 1_000_000 * 0.60)
        assert abs(info['query_cost'] - expected_cost) < 0.000001
    
    def test_cost_calculation_gpt4o(self):
        """Test cost calculation for gpt-4o (more expensive)."""
        tracker = CostTracker(daily_budget_usd=10.0, alert_email=None, model='gpt-4o')
        
        # 1000 input tokens, 500 output tokens
        info = tracker.record_query('user-123', prompt_tokens=1000, completion_tokens=500)
        
        # Expected: (1000/1M * $2.50) + (500/1M * $10.00) = $0.0025 + $0.005 = $0.0075
        expected_cost = (1000 / 1_000_000 * 2.50) + (500 / 1_000_000 * 10.00)
        assert abs(info['query_cost'] - expected_cost) < 0.000001
    
    def test_unknown_model_fallback(self):
        """Test that unknown models fall back to gpt-4o-mini pricing."""
        # Note: CostTracker raises ValueError for unknown models in __init__
        with pytest.raises(ValueError, match="Unknown model"):
            tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='unknown-model')
    
    def test_daily_cost_accumulation(self):
        """Test that daily costs accumulate correctly."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        # First query
        info1 = tracker.record_query('user-123', prompt_tokens=1000, completion_tokens=500)
        cost1 = info1['query_cost']
        
        # Second query
        info2 = tracker.record_query('user-456', prompt_tokens=2000, completion_tokens=1000)
        cost2 = info2['query_cost']
        
        # Daily total should be sum of both (with floating point tolerance)
        assert abs(info2['daily_cost'] - (cost1 + cost2)) < 0.0001
    
    def test_budget_not_exceeded_initially(self):
        """Test that budget is not exceeded initially."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        exceeded, info = tracker.is_budget_exceeded()
        
        assert exceeded is False
        assert info['daily_cost'] == 0.0
        assert info['remaining'] == 1.0
    
    def test_budget_exceeded_detection(self):
        """Test that budget exceeded is detected."""
        tracker = CostTracker(daily_budget_usd=0.01, alert_email=None, model='gpt-4o-mini')
        
        # Record expensive queries (inflated token counts)
        for i in range(10):
            tracker.record_query(f'user-{i}', prompt_tokens=10000, completion_tokens=50000)
        
        exceeded, info = tracker.is_budget_exceeded()
        
        assert exceeded is True
        assert info['daily_cost'] > 0.01
        assert info['percentage'] > 100
    
    def test_per_user_cost_tracking(self):
        """Test that per-user costs are tracked."""
        tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model='gpt-4o-mini')
        
        # User 1 makes 2 queries
        tracker.record_query('user-1', prompt_tokens=1000, completion_tokens=500)
        tracker.record_query('user-1', prompt_tokens=1000, completion_tokens=500)
        
        # User 2 makes 1 query
        tracker.record_query('user-2', prompt_tokens=1000, completion_tokens=500)
        
        # Check user_costs dict
        assert 'user-1' in tracker.user_costs
        assert 'user-2' in tracker.user_costs
        assert tracker.user_costs['user-1'] > tracker.user_costs['user-2']
    
    def test_80_percent_alert_triggered(self):
        """Test that 80% warning alert is triggered once."""
        mock_send = Mock()
        
        tracker = CostTracker(daily_budget_usd=0.01, alert_email='test@example.com', model='gpt-4o-mini')
        tracker._send_email = mock_send
        
        # Record queries to hit exactly 80% (not exceed 100%)
        # Each query costs: (1500/1M * 0.15) + (3000/1M * 0.60) = 0.000225 + 0.0018 = 0.002025
        # Need 4 queries to get to ~0.0081 (81% of 0.01)
        for i in range(4):
            tracker.record_query(f'user-{i}', prompt_tokens=1500, completion_tokens=3000)
        
        # Should have sent warning email (once) and it should be a warning, not critical
        assert mock_send.call_count == 1
        assert 'Warning' in mock_send.call_args[0][0]
        assert 'CRITICAL' not in mock_send.call_args[0][0]
    
    def test_100_percent_alert_triggered(self):
        """Test that 100% critical alert is triggered."""
        mock_send = Mock()
        
        tracker = CostTracker(daily_budget_usd=0.01, alert_email='test@example.com', model='gpt-4o-mini')
        tracker._send_email = mock_send
        
        # Record queries to exceed budget
        for i in range(10):
            tracker.record_query(f'user-{i}', prompt_tokens=2000, completion_tokens=8000)
        
        # Should have sent critical email
        assert mock_send.call_count >= 1
        assert 'CRITICAL' in str(mock_send.call_args)
    
    def test_model_pricing_validation(self):
        """Test that valid models are accepted."""
        valid_models = ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']
        
        for model in valid_models:
            tracker = CostTracker(daily_budget_usd=1.0, alert_email=None, model=model)
            assert tracker.model == model


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
