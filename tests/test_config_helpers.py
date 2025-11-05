#!/usr/bin/env python3
"""Unit tests for config helper functions."""

import pytest
import os
from src.utils.config import ConfigManager


class TestConfigHelpers:
    """Test type-safe environment variable helpers."""
    
    def test_get_env_string_returns_value(self):
        """Test getting string environment variable."""
        os.environ['TEST_STRING'] = 'hello'
        config = ConfigManager()
        
        result = config.get_env_string('TEST_STRING')
        assert result == 'hello'
        
        del os.environ['TEST_STRING']
    
    def test_get_env_string_returns_default(self):
        """Test string default when not found."""
        config = ConfigManager()
        result = config.get_env_string('NONEXISTENT_VAR', 'default_value')
        assert result == 'default_value'
    
    def test_get_env_int_returns_value(self):
        """Test getting integer environment variable."""
        os.environ['TEST_INT'] = '42'
        config = ConfigManager()
        
        result = config.get_env_int('TEST_INT', 0)
        assert result == 42
        assert isinstance(result, int)
        
        del os.environ['TEST_INT']
    
    def test_get_env_int_invalid_returns_default(self):
        """Test integer default when value is invalid."""
        os.environ['TEST_INT'] = 'not_a_number'
        config = ConfigManager()
        
        result = config.get_env_int('TEST_INT', 99)
        assert result == 99
        
        del os.environ['TEST_INT']
    
    def test_get_env_float_returns_value(self):
        """Test getting float environment variable."""
        os.environ['TEST_FLOAT'] = '3.14'
        config = ConfigManager()
        
        result = config.get_env_float('TEST_FLOAT', 0.0)
        assert abs(result - 3.14) < 0.001
        assert isinstance(result, float)
        
        del os.environ['TEST_FLOAT']
    
    def test_get_env_float_invalid_returns_default(self):
        """Test float default when value is invalid."""
        os.environ['TEST_FLOAT'] = 'not_a_float'
        config = ConfigManager()
        
        result = config.get_env_float('TEST_FLOAT', 1.5)
        assert result == 1.5
        
        del os.environ['TEST_FLOAT']
    
    def test_get_env_bool_true_values(self):
        """Test boolean true values."""
        config = ConfigManager()
        
        for true_val in ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']:
            os.environ['TEST_BOOL'] = true_val
            result = config.get_env_bool('TEST_BOOL', False)
            assert result is True, f"Failed for value: {true_val}"
        
        if 'TEST_BOOL' in os.environ:
            del os.environ['TEST_BOOL']
    
    def test_get_env_bool_false_values(self):
        """Test boolean false values."""
        config = ConfigManager()
        
        for false_val in ['false', 'False', '0', 'no', 'off', 'anything_else']:
            os.environ['TEST_BOOL'] = false_val
            result = config.get_env_bool('TEST_BOOL', True)
            assert result is False, f"Failed for value: {false_val}"
        
        if 'TEST_BOOL' in os.environ:
            del os.environ['TEST_BOOL']
    
    def test_get_env_bool_default(self):
        """Test boolean default when not found."""
        config = ConfigManager()
        result = config.get_env_bool('NONEXISTENT_BOOL', True)
        assert result is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
