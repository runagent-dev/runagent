# runagent/utils/config.py
import os
import json
import typing as t
from pathlib import Path

from runagent.constants import AGENT_CONFIG_FILE_NAME, LOCAL_CACHE_DIRECTORY, USER_DATA_FILE_NAME, ENV_RUNAGENT_API_KEY, ENV_RUNAGENT_BASE_URL, DEFAULT_BASE_URL


class Config:
    """Utility class for handling configuration files"""
    
    @staticmethod
    def create_config(project_dir: str, config_content: t.Dict[str, t.Any]) -> str:
        """
        Create or update runagent.config.json in the project directory
        
        Args:
            project_dir: Project directory
            config_content: Configuration content
            
        Returns:
            Path to created config file
        """
        config_file = Path(project_dir) / AGENT_CONFIG_FILE_NAME
        
        # Update existing config if it exists
        if config_file.exists():
            with config_file.open('r') as f:
                existing_config = json.load(f)
            
            # Merge configs, new values take precedence
            existing_config.update(config_content)
            config_content = existing_config
        
        # Write config file
        with config_file.open('w') as f:
            json.dump(config_content, f, indent=2)
        
        return str(config_file)
    
    @staticmethod
    def get_config(project_dir: str) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Get configuration from runagent.config.json
        
        Args:
            project_dir: Project directory
            
        Returns:
            Configuration content or None if not found
        """
        config_file = Path(project_dir) / AGENT_CONFIG_FILE_NAME
        
        if not config_file.exists():
            return None
        
        with config_file.open('r') as f:
            return json.load(f)

    @staticmethod
    def get_user_config() -> t.Dict[str, t.Any]:
        """
        Get user configuration from {ENV_LOCAL_CACHE_DIRECTORY}/config.json
        
        Returns:
            User configuration content
        """
        config_dir = Path.home() / LOCAL_CACHE_DIRECTORY
        config_file = config_dir / USER_DATA_FILE_NAME

        if not config_file.exists():
            return {}

        try:
            with config_file.open('r') as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def set_user_config(key: str, value: t.Any) -> bool:
        """
        Set a value in the user configuration
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Returns:
            True if successful, False otherwise
        """
        config_dir = Path.home() / LOCAL_CACHE_DIRECTORY
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / USER_DATA_FILE_NAME
        
        # Get existing config or create new
        if config_file.exists():
            try:
                with config_file.open('r') as f:
                    config = json.load(f)
            except Exception:
                config = {}
        else:
            config = {}
        
        # Update config
        config[key] = value
        
        # Write config
        try:
            with config_file.open('w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_base_url() -> str:
        """
        Get API URL from user config or environment variable
        
        Returns:
            API URL
        """
            # * source 1: CLI/SDK direct input
            # * source 1.5: User config file
            # * source 2: Environment Key
            # * source 3: Default Value

        # Check user config
        user_config = Config.get_user_config()
        api_url = user_config.get('base_url')

        # Check environment variable
        if not api_url:
            api_url = os.environ.get(ENV_RUNAGENT_BASE_URL)
        
        if not api_url:
            api_url = DEFAULT_BASE_URL
            
        # if not api_url.startswith(('http://', 'https://')):
        #     api_url = f"http://{base_url}"

        return api_url
        
    @staticmethod
    def set_base_url(base_url: str) -> bool:
        """
        Set the API URL in the user configuration
        
        Args:
            url: API URL
            
        Returns:
            True if successful, False otherwise
        """
        return Config.set_user_config('base_url', base_url)
    
    @staticmethod
    def get_api_key() -> t.Optional[str]:
        """
        Get API token from user config or environment variable
        
        Returns:
            API token or None if not found
        """
        # Check user config
        user_config = Config.get_user_config()
        api_key = user_config.get('api_key')

        # Check environment variable
        if not api_key:
            api_key = os.environ.get(ENV_RUNAGENT_API_KEY)
        
        return api_key

    @staticmethod
    def set_api_key(api_key: str) -> bool:
        """
        Set the API token in the user configuration
        
        Args:
            token: API token
            
        Returns:
            True if successful, False otherwise
        """
        return Config.set_user_config('api_key', api_key)
    
    @staticmethod
    def save_deployment_info(agent_id: str, info: t.Dict[str, t.Any]) -> str:
        """
        Save deployment information
        
        Args:
            agent_id: Agent ID
            info: Deployment information
            
        Returns:
            Path to saved file
        """
        deployments_dir = Path.cwd() / ".deployments"
        deployments_dir.mkdir(exist_ok=True)
        
        info_file = deployments_dir / f"{agent_id}.json"
        with info_file.open('w') as f:
            json.dump(info, f, indent=2)
        
        return str(info_file)
    
    @staticmethod
    def get_deployment_info(agent_id: str) -> t.Optional[t.Dict[str, t.Any]]:
        """
        Get deployment information
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Deployment information or None if not found
        """
        deployments_dir = Path.cwd() / ".deployments"
        info_file = deployments_dir / f"{agent_id}.json"
        
        if not info_file.exists():
            return None
        
        with info_file.open('r') as f:
            return json.load(f)

    # Add these methods to your Config class

    @staticmethod
    def clear_user_config() -> bool:
        """
        Clear all user configuration
        
        Returns:
            True if successful, False otherwise
        """
        config_dir = Path.home() / LOCAL_CACHE_DIRECTORY
        config_file = config_dir / USER_DATA_FILE_NAME
        
        try:
            if config_file.exists():
                config_file.unlink()
            return True
        except Exception:
            return False

    @staticmethod
    def is_configured() -> bool:
        """
        Check if RunAgent is properly configured
        
        Returns:
            True if both API key and base URL are set
        """
        config = Config.get_user_config()
        return bool(config.get('api_key') and config.get('base_url'))

    @staticmethod
    def get_config_status() -> t.Dict[str, t.Any]:
        """
        Get detailed configuration status
        
        Returns:
            Dictionary with configuration details
        """
        config = Config.get_user_config()
        return {
            'configured': Config.is_configured(),
            'api_key_set': bool(Config.get_api_key()),
            'base_url': Config.get_base_url(),
            'user_email': config.get('email'),
            'user_name': config.get('name'),
            'config_file_exists': (Path.home() / LOCAL_CACHE_DIRECTORY / USER_DATA_FILE_NAME).exists()
        }

    @staticmethod
    def backup_config() -> t.Optional[str]:
        """
        Create a backup of current configuration (without API key for security)
        
        Returns:
            Path to backup file or None if failed
        """
        config = Config.get_user_config()
        if not config:
            return None
        
        # Remove sensitive data from backup
        backup_config = {k: v for k, v in config.items() if k != 'api_key'}
        
        backup_dir = Path.home() / LOCAL_CACHE_DIRECTORY / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        import time
        timestamp = int(time.time())
        backup_file = backup_dir / f"config_backup_{timestamp}.json"
        
        try:
            with backup_file.open('w') as f:
                json.dump(backup_config, f, indent=2)
            return str(backup_file)
        except Exception:
            return None