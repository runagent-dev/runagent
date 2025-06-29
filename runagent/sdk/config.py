"""
SDK Configuration management.
"""

import json
import os
import typing as t
from pathlib import Path

from ..constants import (
    DEFAULT_BASE_URL,
    ENV_RUNAGENT_API_KEY,
    ENV_RUNAGENT_BASE_URL,
    LOCAL_CACHE_DIRECTORY,
    USER_DATA_FILE_NAME,
)
from .exceptions import AuthenticationError, ValidationError


class SDKConfig:
    """Manage SDK configuration and authentication"""

    def __init__(
        self,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        config_file: t.Optional[str] = None,
    ):
        """
        Initialize configuration.

        Args:
            api_key: API key (overrides env var and config file)
            base_url: Base URL (overrides env var and config file)
            config_file: Path to custom config file
        """
        self.config_file = (
            Path(config_file) if config_file else self._get_default_config_path()
        )

        # Load configuration from various sources
        self._config = self._load_config()

        # Override with provided values
        if api_key:
            self._config["api_key"] = api_key
        if base_url:
            self._config["base_url"] = base_url

    def _get_default_config_path(self) -> Path:
        """Get default config file path"""
        config_dir = Path(LOCAL_CACHE_DIRECTORY)
        config_dir.mkdir(exist_ok=True)
        return config_dir / USER_DATA_FILE_NAME

    def _load_config(self) -> t.Dict[str, t.Any]:
        """Load configuration from all sources"""
        config = {}

        # 1. Load from config file
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config.update(json.load(f))
            except (json.JSONDecodeError, IOError):
                pass

        # 2. Override with environment variables
        if os.getenv(ENV_RUNAGENT_API_KEY):
            config["api_key"] = os.getenv(ENV_RUNAGENT_API_KEY)

        if os.getenv(ENV_RUNAGENT_BASE_URL):
            config["base_url"] = os.getenv(ENV_RUNAGENT_BASE_URL)
        elif "base_url" not in config:
            config["base_url"] = DEFAULT_BASE_URL

        return config

    def save_config(self) -> bool:
        """Save current configuration to file"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self._config, f, indent=2)
            return True
        except (IOError, OSError):
            return False

    def setup(
        self,
        api_key: t.Optional[str] = None,
        base_url: t.Optional[str] = None,
        save: bool = True,
    ) -> bool:
        """
        Setup and validate configuration.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the service
            save: Whether to save to config file

        Returns:
            True if setup is successful

        Raises:
            AuthenticationError: If authentication fails
            ValidationError: If configuration is invalid
        """
        # Update configuration
        if api_key:
            self._config["api_key"] = api_key
        if base_url:
            if not base_url.startswith(("http://", "https://")):
                base_url = f"https://{base_url}"
            self._config["base_url"] = base_url

        # Validate configuration
        if not self._config.get("api_key"):
            raise ValidationError("API key is required")

        # Test authentication
        if not self._test_authentication():
            raise AuthenticationError("Authentication failed with provided credentials")

        # Save if requested
        if save:
            self.save_config()

        return True

    def _test_authentication(self) -> bool:
        """Test authentication with current configuration"""
        try:
            from .http import EndpointHandler

            handler = EndpointHandler(
                api_key=self._config.get("api_key"),
                base_url=self._config.get("base_url"),
            )
            response = handler.validate_api_key()
            return response.get("status") == "success"
        except Exception:
            return False

    def is_configured(self) -> bool:
        """Check if SDK is properly configured"""
        return bool(self._config.get("api_key") and self._config.get("base_url"))

    def is_authenticated(self) -> bool:
        """Check if current configuration is authenticated"""
        return self.is_configured() and self._test_authentication()

    def get_status(self) -> t.Dict[str, t.Any]:
        """Get detailed configuration status"""
        return {
            "configured": self.is_configured(),
            "authenticated": self.is_authenticated() if self.is_configured() else False,
            "api_key_set": bool(self._config.get("api_key")),
            "base_url": self._config.get("base_url"),
            "user_info": {
                k: v
                for k, v in self._config.items()
                if k not in ["api_key", "base_url"]
            },
            "config_file": str(self.config_file),
            "config_file_exists": self.config_file.exists(),
        }

    def clear(self) -> bool:
        """Clear all configuration"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            self._config.clear()
            return True
        except (IOError, OSError):
            return False

    # Property accessors
    @property
    def api_key(self) -> t.Optional[str]:
        """Get API key"""
        return self._config.get("api_key")

    @property
    def base_url(self) -> str:
        """Get base URL"""
        return self._config.get("base_url", DEFAULT_BASE_URL)

    @property
    def user_info(self) -> t.Dict[str, t.Any]:
        """Get user information"""
        return {
            k: v for k, v in self._config.items() if k not in ["api_key", "base_url"]
        }
