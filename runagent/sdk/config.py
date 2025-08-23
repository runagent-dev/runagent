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
        validate_auth: bool = True,
    ) -> bool:
        """
        Setup and validate configuration.

        Args:
            api_key: API key for authentication
            base_url: Base URL for the service
            save: Whether to save to config file
            validate_auth: Whether to validate authentication

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

        # Test authentication if requested
        if validate_auth:
            auth_result = self._test_authentication()
            if not auth_result.get("success"):
                error_msg = auth_result.get("error", "Authentication failed with provided credentials")
                raise AuthenticationError(error_msg)

        # Save if requested
        if save:
            self.save_config()

        return True

    def _test_authentication(self) -> t.Dict[str, t.Any]:
        """Test authentication with current configuration - SIMPLIFIED"""
        try:
            from .rest_client import RestClient

            client = RestClient(
                api_key=self._config.get("api_key"),
                base_url=self._config.get("base_url"),
            )
            
            # Test connection using the profile endpoint
            response = client.http.get("/users/profile", timeout=10)
            
            if response.status_code == 200:
                profile_data = response.json()
                
                # Extract user info from the middleware response structure
                auth_data = profile_data.get("auth_data", {})
                profile_data_inner = profile_data.get("profile_data", {})
                
                user_info = {
                    "email": auth_data.get("email") or profile_data_inner.get("email"),
                    "user_id": auth_data.get("id") or profile_data_inner.get("id"),
                    "tier": profile_data_inner.get("tier", "free")
                }
                
                # Store user info for later display
                self._config.update({
                    "user_email": user_info["email"],
                    "user_id": user_info["user_id"],
                    "user_tier": user_info["tier"],
                    "auth_validated": True
                })
                
                return {
                    "success": True,
                    "user_info": user_info
                }
            
            elif response.status_code == 401:
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "Invalid API key")
                except:
                    error_detail = "API key authentication failed"
                
                return {
                    "success": False,
                    "error": error_detail
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Authentication test failed with status {response.status_code}"
                }
                
        except Exception as e:
            # Handle connection errors gracefully
            error_msg = str(e)
            if "Connection" in error_msg or "timeout" in error_msg.lower():
                return {
                    "success": False,
                    "error": "Cannot connect to middleware server"
                }
            else:
                return {
                    "success": False,
                    "error": f"Authentication test failed: {error_msg}"
                }

    def is_configured(self) -> bool:
        """Check if SDK is configured"""
        return bool(self._config.get("api_key") and self._config.get("base_url"))

    def is_authenticated(self) -> bool:
        """Check if current configuration is authenticated - USE CACHED RESULT"""
        if not self.is_configured():
            return False
        
        # Use cached validation result to avoid repeated API calls
        return self._config.get("auth_validated", False)

    def get_status(self) -> t.Dict[str, t.Any]:
        """Get detailed configuration status - NO REDUNDANT VALIDATION"""
        status = {
            "configured": self.is_configured(),
            "api_key_set": bool(self._config.get("api_key")),
            "base_url": self._config.get("base_url"),
            "config_file": str(self.config_file),
            "config_file_exists": self.config_file.exists(),
            "authenticated": self.is_authenticated(),  # Uses cached result
        }
        
        # Add user info if available (no additional API calls)
        user_info = {
            "email": self._config.get("user_email"),
            "user_id": self._config.get("user_id"),
            "tier": self._config.get("user_tier")
        }
        status["user_info"] = user_info
        
        return status

    def clear(self) -> bool:
        """Clear all configuration"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            self._config.clear()
            return True
        except (IOError, OSError):
            return False

    def validate_authentication(self) -> t.Dict[str, t.Any]:
        """Public method to validate authentication - ONLY WHEN EXPLICITLY CALLED"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "No API key configured",
                "configured": False
            }
        
        # Only validate if explicitly requested
        auth_result = self._test_authentication()
        
        if auth_result.get("success"):
            return {
                "success": True,
                "authenticated": True,
                "user_info": auth_result.get("user_info", {}),
                "base_url": self.base_url
            }
        else:
            return {
                "success": False,
                "authenticated": False,
                "error": auth_result.get("error", "Authentication failed"),
                "base_url": self.base_url
            }

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
            "email": self._config.get("user_email"),
            "user_id": self._config.get("user_id"),
            "tier": self._config.get("user_tier")
        }