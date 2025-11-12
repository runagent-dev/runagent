import json
import typing as t
from pathlib import Path
from datetime import datetime
from runagent.constants import AGENT_CONFIG_FILE_NAME
from runagent.utils.imports import PackageImporter
from runagent.utils.schema import RunAgentConfig
from runagent.utils.enums.framework import Framework


def get_agent_config(folder_path: Path) -> t.Optional[dict]:
    """
    Get agent configuration from runagent.config.json file.

    Args:
        folder_path: Path to agent folder

    Returns:
        Config dict if found, None otherwise
    """
    # Try JSON config first
    config_path_json = folder_path / AGENT_CONFIG_FILE_NAME

    # Try YAML config paths
    config_path_yaml = folder_path / AGENT_CONFIG_FILE_NAME.replace(
        ".json", ".yaml"
    )
    config_path_yml = folder_path / AGENT_CONFIG_FILE_NAME.replace(
        ".json", ".yml"
    )

    config_data = None

    if config_path_json.exists():
        with config_path_json.open() as f:
            try:
                config_data = json.load(f)
                if not config_data:
                    raise ValueError(
                        f"Config file {config_path_json} is empty"
                    )
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON format in {config_path_json}: {str(e)}"
                )
            except Exception as e:
                raise ValueError(
                    f"Error reading JSON config file {config_path_json}: "
                    f"{str(e)}"
                )

    elif config_path_yaml.exists() or config_path_yml.exists():
        try:
            import yaml

            yaml_path = (
                config_path_yaml if config_path_yaml.exists() 
                else config_path_yml
            )
            with yaml_path.open() as f:
                config_data = yaml.safe_load(f)
                if not config_data:
                    raise ValueError(
                        f"Config file {yaml_path} is empty"
                    )
        except yaml.YAMLError as e:
            raise ValueError(
                f"Invalid YAML format in {yaml_path}: {str(e)}"
            )
        except Exception as e:
            raise ValueError(
                f"Error reading YAML config file {yaml_path}: {str(e)}"
            )
    else:
        raise ValueError(
            f"No config file found. Tried: {config_path_json}, "
            f"{config_path_yaml}, {config_path_yml}"
        )

    # Check for .env file and load environment variables
    env_path = folder_path / ".env"
    if env_path.exists():
        try:
            from dotenv import dotenv_values

            env_vars = dotenv_values(env_path)

            # Update env_vars in config data
            if "env_vars" not in config_data:
                config_data["env_vars"] = {}
            config_data["env_vars"].update(env_vars)
        except Exception as e:
            raise ValueError(f"Error loading .env file: {str(e)}")
    
    # Handle missing fields gracefully for backward compatibility
    default_values = {
        'agent_id': None,
    }
    
    # Add missing fields with defaults
    for field, default_value in default_values.items():
        if field not in config_data:
            config_data[field] = default_value
    
    # Convert string timestamps back to datetime objects for database compatibility
    if 'created_at' in config_data and isinstance(config_data['created_at'], str):
        try:
            from datetime import datetime
            config_data['created_at'] = datetime.fromisoformat(config_data['created_at'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # If parsing fails, use current time
            config_data['created_at'] = datetime.now()
    
    return RunAgentConfig(**config_data)


def detect_framework(folder_path: Path) -> Framework:
    """
    Detect framework from agent's runagent.config.json file.

    Args:
    folder_path: Path to agent folder

    Returns:
    Framework name from config
    """
    config = get_agent_config(folder_path)
    framework = config.framework

    return framework


def validate_agent(
    folder: Path, dynamic_loading: bool = False
) -> t.Tuple[bool, t.Dict[str, t.Any]]:
    """
    Validate agent project structure.

    Args:
        folder: Path to agent folder

    Returns:
        Tuple of (is_valid, validation_details)
    """
    folder_path = folder
    if not folder_path.exists():
        return False, {
            "valid": False,
            "error_msgs": [f"Agent Folder not found: {folder}"],
        }

    config = get_agent_config(folder_path)
    # framework = config.framework
    
    # If no agent_architecture or empty entrypoints, validation passes (for existing codebase without entrypoints)
    if config.agent_architecture is None or not config.agent_architecture.entrypoints:
        return True, {
            "valid": True,
            "folder_exists": True,
            "files_found": [],
            "missing_files": [],
            "success_msgs": ["No entrypoints configured (existing codebase mode)"],
            "error_msgs": [],
            "warning_msgs": ["Add entrypoints to runagent.config.json to enable agent execution"],
        }
    
    if config.framework.is_pythonic():
        is_valid, details = validate_pythonic_agent(config, dynamic_loading, folder_path)
    else:
        is_valid, details = validate_webhook_agent(config, dynamic_loading, folder_path)

    return is_valid, details


def validate_webhook_agent(config, dynamic_loading, folder_path):
    return True, dict(
        valid=True,
        folder_exists=True,
        files_found=[],
        missing_files=[],
        success_msgs=[],
        error_msgs=[],
        warning_msgs=[],
    )

def validate_pythonic_agent(config, dynamic_loading, folder_path):

    validation_details = {
        "valid": False,
        "folder_exists": True,
        "files_found": [],
        "missing_files": [],
        "success_msgs": [],
        "error_msgs": [],
        "warning_msgs": [],
    }

    suggested_files = ["requirements.txt"]
    unwanted_files = [".env"]

    # Check for runagent.config.json and validate schema
    # try:

    # Validate each entrypoint dynamically
    for entrypoint in config.agent_architecture.entrypoints:
        entrypoint_file = folder_path / entrypoint.file
        module_name = entrypoint.module

        if not entrypoint_file.exists():
            validation_details["error_msgs"].append(
                f"Entrypoint file not found: {entrypoint_file}"
            )
            validation_details["missing_files"].append(entrypoint.file)
            validation_details["valid"] = False
            continue

        if dynamic_loading:
            try:
                importer = PackageImporter()
                importer.resolve_import(entrypoint_file, module_name)
                validation_details["success_msgs"].append(
                    f"Found {module_name} reference in {entrypoint_file}"
                )
            except Exception as e:
                validation_details["error_msgs"].append(str(e))
                validation_details["valid"] = False
        else:
            try:
                content = entrypoint_file.read_text()
                if module_name in content:
                    validation_details["success_msgs"].append(
                        f"Found {module_name} reference in {entrypoint_file}"
                    )
                else:
                    validation_details["error_msgs"].append(
                        f"Module {module_name} not found in {entrypoint_file}"
                    )
                    validation_details["missing_files"].append(
                        f"{module_name} module reference"
                    )
                    validation_details["valid"] = False
            except Exception as e:
                validation_details["error_msgs"].append(
                    f"Failed to read {entrypoint_file}: {str(e)}"
                )
                validation_details["valid"] = False

    # Check for unwanted files
    for unwanted_file in unwanted_files:
        if (folder_path / unwanted_file).exists():
            validation_details["warning_msgs"].append(
                f"Found unwanted file: {unwanted_file}"
            )
            validation_details.setdefault("unwanted_files", []).append(unwanted_file)

    # Check for suggested files
    for file_name in suggested_files:
        file_path = folder_path / file_name
        if file_path.exists():
            validation_details["files_found"].append(file_name)
            validation_details["success_msgs"].append(
                f"Found suggested file: {file_name}"
            )
        else:
            validation_details["warning_msgs"].append(
                f"Missing suggested file: {file_name}"
            )

    # Detect framework
    try:
        validation_details["framework"] = detect_framework(folder_path).value
    except Exception as e:
        validation_details["error_msgs"].append(f"Failed to detect framework: {str(e)}")
        validation_details["valid"] = False

    # Overall validation
    validation_details["valid"] = (
        len(validation_details["missing_files"]) == 0
        and len(validation_details["error_msgs"]) == 0
    )

    # If validation failed but no error messages, add generic error
    if not validation_details["valid"] and not validation_details["error_msgs"]:
        validation_details["error_msgs"].append(
            "Agent validation failed - missing required components"
        )

    return validation_details["valid"], validation_details


def get_agent_config_with_defaults(agent_path: Path) -> t.Dict[str, t.Any]:
    """
    Load agent config with sensible defaults for new fields.
    This ensures all new database fields have values even for legacy agents.
    
    Args:
        agent_path: Path to the agent directory
        
    Returns:
        Dictionary with config values and defaults for missing fields
    """
    config = get_agent_config(agent_path)
    if not config:
        # No config file - return defaults
        return {
            'agent_name': agent_path.name,
            'description': 'No description provided',
            'template': '',  # Empty string for blank templates
            'version': '1.0.0',
            'created_at': datetime.now(),  # Return datetime object, not string
            'agent_id': None,
        }
    
    # Convert Pydantic object to dict
    if hasattr(config, 'to_dict'):
        config_dict = config.to_dict()
    elif hasattr(config, 'dict'):
        config_dict = config.dict()
    elif hasattr(config, 'model_dump'):
        config_dict = config.model_dump()
    else:
        config_dict = config
    
    # Convert string timestamps back to datetime objects for database compatibility
    if 'created_at' in config_dict and isinstance(config_dict['created_at'], str):
        try:
            config_dict['created_at'] = datetime.fromisoformat(config_dict['created_at'].replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # If parsing fails, use current time
            config_dict['created_at'] = datetime.now()
    
    # Add defaults for missing fields (only for fields not handled by schema)
    defaults = {
        'agent_name': agent_path.name,
        'description': 'No description provided',
        'template': '',  # Empty string for blank templates (will be overridden by actual template if present)
        'version': '1.0.0',
        'created_at': datetime.now(),  # Return datetime object, not string
    }
    
    for key, default_value in defaults.items():
        if key not in config_dict:
            config_dict[key] = default_value
    
    return config_dict
