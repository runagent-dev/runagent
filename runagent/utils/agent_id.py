"""
Agent ID generation and management utilities
"""
import hashlib
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
import json
import os


def generate_agent_id() -> str:
    """Generate a new UUID for agent ID"""
    return str(uuid.uuid4())


def generate_agent_fingerprint(folder_path: Path) -> str:
    """
    Generate a fingerprint for an agent folder based on its contents.
    This helps identify if the same agent is being uploaded multiple times.
    """
    fingerprint_data = {
        "files": {},
        "structure": []
    }
    
    # Get all files and their basic info
    for file_path in sorted(folder_path.rglob("*")):
        if file_path.is_file() and not file_path.name.startswith("."):
            # Skip unnecessary files
            if file_path.name in ["__pycache__", ".DS_Store", "Thumbs.db"]:
                continue
            if file_path.suffix in [".pyc", ".pyo", ".log"]:
                continue
                
            relative_path = file_path.relative_to(folder_path)
            fingerprint_data["files"][str(relative_path)] = {
                "size": file_path.stat().st_size,
                "mtime": file_path.stat().st_mtime
            }
            fingerprint_data["structure"].append(str(relative_path))
    
    # Create hash from the fingerprint data
    fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
    return hashlib.sha256(fingerprint_json.encode()).hexdigest()


def get_agent_name_from_folder(folder_path: Path) -> str:
    """Extract a meaningful agent name from the folder path"""
    return folder_path.name


def generate_config_fingerprint(agent_path: Path) -> Optional[str]:
    """
    Generate fingerprint for runagent.config.json file.
    This helps detect when the config file has been modified.
    
    Args:
        agent_path: Path to the agent directory
        
    Returns:
        SHA256 hash of the config file content, or None if file doesn't exist
    """
    config_path = agent_path / "runagent.config.json"
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    except Exception:
        return None


def get_framework_from_folder(folder_path: Path) -> Optional[str]:
    """
    Try to detect framework from folder contents.
    This is a simple heuristic - can be enhanced later.
    """
    folder_path = Path(folder_path)
    
    # Check for common framework files
    if (folder_path / "requirements.txt").exists():
        try:
            with open(folder_path / "requirements.txt", "r") as f:
                content = f.read().lower()
                if "langchain" in content:
                    return "langchain"
                elif "crewai" in content:
                    return "crewai"
                elif "autogen" in content:
                    return "autogen"
                elif "openai" in content:
                    return "openai"
        except:
            pass
    
    # Check for common framework directories/files
    if (folder_path / "langchain").exists():
        return "langchain"
    elif (folder_path / "crewai").exists():
        return "crewai"
    elif (folder_path / "autogen").exists():
        return "autogen"
    
    # Check main.py for imports
    main_py = folder_path / "main.py"
    if main_py.exists():
        try:
            with open(main_py, "r") as f:
                content = f.read().lower()
                if "from langchain" in content or "import langchain" in content:
                    return "langchain"
                elif "from crewai" in content or "import crewai" in content:
                    return "crewai"
                elif "from autogen" in content or "import autogen" in content:
                    return "autogen"
                elif "openai" in content:
                    return "openai"
        except:
            pass
    
    return "unknown"


def get_agent_metadata(folder_path: Path, framework: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract comprehensive metadata from an agent folder
    """
    folder_path = Path(folder_path)
    
    detected_framework = framework or get_framework_from_folder(folder_path)
    
    return {
        "name": get_agent_name_from_folder(folder_path),
        "description": f"Agent uploaded from {folder_path.name}",
        "framework": detected_framework,
        "template": "default",  # Can be enhanced to detect actual template
        "version": "1.0.0",
        "fingerprint": generate_agent_fingerprint(folder_path),
        "source_folder": str(folder_path),
        "entrypoints": _detect_entrypoints(folder_path),
        "env_vars": _detect_env_vars(folder_path)
    }


def _detect_entrypoints(folder_path: Path) -> list:
    """Detect entrypoints in the agent folder"""
    entrypoints = []
    
    # Look for main.py with common patterns
    main_py = folder_path / "main.py"
    if main_py.exists():
        try:
            with open(main_py, "r") as f:
                content = f.read()
                
                # Simple heuristic to find functions that could be entrypoints
                import ast
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if any(keyword in node.name.lower() for keyword in ['main', 'run', 'execute', 'handle', 'process']):
                                entrypoints.append({
                                    "file": "main.py",
                                    "module": node.name,
                                    "tag": node.name.lower()
                                })
                except:
                    # Fallback to default entrypoints
                    entrypoints = [
                        {"file": "main.py", "module": "main", "tag": "main"},
                        {"file": "main.py", "module": "run", "tag": "run"}
                    ]
        except:
            pass
    
    # If no entrypoints found, provide defaults
    if not entrypoints:
        entrypoints = [
            {"file": "main.py", "module": "mock_response_stream", "tag": "minimal_stream"},
            {"file": "main.py", "module": "mock_response", "tag": "minimal"}
        ]
    
    return entrypoints


def _detect_env_vars(folder_path: Path) -> Dict[str, str]:
    """Detect environment variables from .env files or config"""
    env_vars = {}
    
    # Check for .env file
    env_file = folder_path / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip()
        except:
            pass
    
    return env_vars
