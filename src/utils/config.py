#!/usr/bin/env python3
"""
Shared configuration utility for D&D RAG system.

Provides flexible .env file discovery and ChromaDB configuration management
for both local development and remote deployment scenarios.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Tuple


class ConfigManager:
    """
    Centralized configuration management for D&D RAG system.
    
    Features:
    - Flexible .env file discovery (current dir + up to 2 parent dirs)
    - ChromaDB connection configuration with sensible defaults
    - Security-aware for remote deployment scenarios
    """
    
    def __init__(self):
        self._env_loaded = False
        self._env_path: Optional[Path] = None
        self.load_environment()
    
    def load_environment(self) -> bool:
        """
        Search for and load .env file with flexible path discovery.
        
        Search order:
        1. Current working directory
        2. One level up (parent directory)  
        3. Two levels up (grandparent directory)
        
        This supports the security pattern where .env is stored outside
        the web server root directory in remote deployments.
        
        Returns:
            bool: True if .env file was found and loaded, False otherwise
        """
        if self._env_loaded:
            return True
            
        # Search paths: current, parent, grandparent
        search_paths = [
            Path.cwd(),
            Path.cwd().parent,
            Path.cwd().parent.parent
        ]
        
        for search_path in search_paths:
            env_file = search_path / ".env.dndchat"
            if env_file.exists() and env_file.is_file():
                print(f"Loading .env.dndchat from: {env_file}")
                load_dotenv(env_file, override=True)
                self._env_path = env_file
                self._env_loaded = True
                return True
        
        print("Warning: No .env file found in current directory or up to 2 parent directories")
        return False
    
    def get_openai_api_key(self) -> str:
        """
        Get OpenAI API key from environment.
        
        Returns:
            str: The API key
            
        Raises:
            ValueError: If API key is not found
        """
        api_key = os.getenv("gravitycar_openai_api_key")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Please set 'gravitycar_openai_api_key' in .env file"
            )
        return api_key
    
    def get_chroma_config(self) -> Tuple[str, int]:
        """
        Get ChromaDB connection configuration from environment.
        
        Uses .env values with sensible fallbacks:
        - chroma_host_url -> extract host (default: "localhost")
        - chroma_host_port -> port (default: 8060)
        
        Returns:
            Tuple[str, int]: (host, port) for ChromaDB connection
        """
        # Get host from chroma_host_url (e.g., "http://localhost" -> "localhost")
        chroma_host_url = os.getenv("chroma_host_url", "http://localhost")
        if chroma_host_url.startswith("http://"):
            host = chroma_host_url[7:]  # Remove "http://"
        elif chroma_host_url.startswith("https://"):
            host = chroma_host_url[8:]  # Remove "https://"
        else:
            host = chroma_host_url
            
        # Get port
        try:
            port = int(os.getenv("chroma_host_port", "8060"))
        except ValueError:
            print("Warning: Invalid chroma_host_port in .env, using default 8060")
            port = 8060
            
        return host, port
    
    def get_chroma_data_path(self) -> str:
        """
        Get ChromaDB data path from environment.
        
        Returns:
            str: Path to ChromaDB data directory
        """
        return os.getenv("chroma_data_path", "/tmp/chroma")
    
    def get_default_collection_name(self) -> str:
        """
        Get default ChromaDB collection name.
        
        Returns:
            str: Default collection name for AD&D 1st Edition content
        """
        return os.getenv("default_collection_name", "adnd_1e")
    
    def print_config_summary(self) -> None:
        """Print a summary of current configuration for debugging."""
        print("\n=== Configuration Summary ===")
        print(f"Environment file: {self._env_path or 'Not found'}")
        print(f"Environment loaded: {self._env_loaded}")
        
        if self._env_loaded:
            host, port = self.get_chroma_config()
            print(f"ChromaDB host: {host}")
            print(f"ChromaDB port: {port}")
            print(f"ChromaDB data path: {self.get_chroma_data_path()}")
            print(f"Default collection: {self.get_default_collection_name()}")
            
            # Don't print the actual API key for security
            api_key = os.getenv("gravitycar_openai_api_key", "")
            if api_key:
                print(f"OpenAI API key: {'*' * (len(api_key) - 8)}{api_key[-8:]}")
            else:
                print("OpenAI API key: Not set")
        print("==============================\n")
    
    def get_env_string(self, key: str, default: str = None) -> str:
        """
        Get string environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            str: Environment variable value or default
        """
        return os.getenv(key, default)
    
    def get_env_int(self, key: str, default: int) -> int:
        """
        Get integer environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            int: Environment variable value or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            print(f"Warning: Invalid integer value for {key}, using default {default}")
            return default
    
    def get_env_float(self, key: str, default: float) -> float:
        """
        Get float environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found or invalid
            
        Returns:
            float: Environment variable value or default
        """
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            print(f"Warning: Invalid float value for {key}, using default {default}")
            return default
    
    def get_env_bool(self, key: str, default: bool) -> bool:
        """
        Get boolean environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            bool: True if value is 'true', '1', 'yes', 'on' (case-insensitive)
        """
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')


# Global singleton instance for easy import
config = ConfigManager()


def get_chroma_connection_params() -> Tuple[str, int]:
    """
    Convenience function to get ChromaDB connection parameters.
    
    Returns:
        Tuple[str, int]: (host, port) for ChromaDB connection
    """
    return config.get_chroma_config()


def get_openai_api_key() -> str:
    """
    Convenience function to get OpenAI API key.
    
    Returns:
        str: The API key
    """
    return config.get_openai_api_key()


def get_default_collection_name() -> str:
    """
    Convenience function to get default ChromaDB collection name.
    
    Returns:
        str: Default collection name for AD&D 1st Edition content
    """
    return config.get_default_collection_name()


def get_env_string(key: str, default: str = None) -> str:
    """Convenience function for getting string environment variable."""
    return config.get_env_string(key, default)


def get_env_int(key: str, default: int) -> int:
    """Convenience function for getting integer environment variable."""
    return config.get_env_int(key, default)


def get_env_float(key: str, default: float) -> float:
    """Convenience function for getting float environment variable."""
    return config.get_env_float(key, default)


def get_env_bool(key: str, default: bool) -> bool:
    """Convenience function for getting boolean environment variable."""
    return config.get_env_bool(key, default)


if __name__ == "__main__":
    # Test the configuration when run directly
    config.print_config_summary()
    
    try:
        host, port = get_chroma_connection_params()
        print(f"ChromaDB connection test: {host}:{port}")
        
        api_key = get_openai_api_key()
        print(f"OpenAI API key test: {'✅ Found' if api_key else '❌ Missing'}")
        
    except Exception as e:
        print(f"Configuration error: {e}")