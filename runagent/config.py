# runagent/config.py
"""
Configuration handling for RunAgent.
"""

import os
import json
from pathlib import Path
import logging

from .exceptions import InvalidConfigError

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".runagent" / "config.json"
DEFAULT_CONFIG = {
    "base_url": "https://api.runagent.io",
    "api_key": None,
}

def ensure_config_dir():
    """Ensure the config directory exists."""
    config_dir = DEFAULT_CONFIG_PATH.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_config(config_path=None):
    """Get the current configuration."""
    config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    
    if not config_path.exists():
        # Return default config if file doesn't exist
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return {**DEFAULT_CONFIG, **config}  # Merge with defaults
    except json.JSONDecodeError:
        raise InvalidConfigError(f"Invalid JSON in config file: {config_path}")
    except Exception as e:
        logger.warning(f"Failed to read config: {e}")
        return DEFAULT_CONFIG.copy()

def set_config(config_dict, config_path=None):
    """Set the configuration."""
    config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    ensure_config_dir()
    
    # Merge with existing config
    current_config = get_config(config_path)
    updated_config = {**current_config, **config_dict}
    
    try:
        with open(config_path, "w") as f:
            json.dump(updated_config, f, indent=2)
        return updated_config
    except Exception as e:
        raise InvalidConfigError(f"Failed to write config: {e}")

def get_api_key():
    """Get the API key from environment or config."""
    # First check environment variable
    api_key = os.environ.get("RUNAGENT_API_KEY")
    if api_key:
        return api_key
    
    # Then check config file
    config = get_config()
    return config.get("api_key")
