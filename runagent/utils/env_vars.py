"""
Environment variables utility for merging config and .env files.
"""
import os
from pathlib import Path
from typing import Dict, Any


def load_env_file(env_path: Path) -> Dict[str, str]:
    """
    Load environment variables from .env file
    
    Args:
        env_path: Path to .env file
        
    Returns:
        Dictionary of key-value pairs
    """
    env_vars = {}
    
    if not env_path.exists():
        return env_vars
    
    try:
        with env_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value pairs
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    env_vars[key] = value
    except Exception:
        # If we can't read .env file, continue without it
        pass
    
    return env_vars


def merge_env_vars(config_env_vars: Dict[str, Any], agent_path: Path) -> Dict[str, str]:
    """
    Merge environment variables from config and .env file
    
    Priority: config values override .env values
    
    Args:
        config_env_vars: Environment variables from runagent config
        agent_path: Path to agent directory
        
    Returns:
        Merged dictionary of environment variables
    """
    # Start with .env file variables
    env_file_path = agent_path / '.env'
    merged_vars = load_env_file(env_file_path)
    
    # Override with config variables (config takes priority)
    if config_env_vars:
        for key, value in config_env_vars.items():
            if value is not None:  # Only add non-None values
                merged_vars[key] = str(value)
    
    return merged_vars

