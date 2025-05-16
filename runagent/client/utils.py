# runagent/utils.py
"""
Utility functions for RunAgent.
"""

import os
import tempfile
import zipfile
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)

def package_agent(agent_path):
    """
    Package an agent directory into a zip file.
    
    Args:
        agent_path: Path to the agent directory
        
    Returns:
        Path to the temporary zip file
    """
    agent_path = Path(agent_path).resolve()
    if not agent_path.is_dir():
        raise ValueError(f"Agent path must be a directory: {agent_path}")
    
    # Create a temporary file
    temp_zip = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    temp_zip.close()
    
    # Create a zip file
    with zipfile.ZipFile(temp_zip.name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(agent_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, agent_path)
                zipf.write(file_path, arcname)
    
    logger.debug(f"Packaged agent at {agent_path} to {temp_zip.name}")
    return temp_zip.name

def validate_agent_directory(agent_path):
    """
    Validate that the agent directory has the required files.
    
    Args:
        agent_path: Path to the agent directory
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    agent_path = Path(agent_path)
    
    # Check if agent.py exists
    if not (agent_path / "agent.py").exists():
        raise ValueError(f"Missing agent.py in {agent_path}")
    
    # Check if requirements.txt exists
    if not (agent_path / "requirements.txt").exists():
        logger.warning(f"Missing requirements.txt in {agent_path}")
    
    return True

def parse_agent_metadata(agent_path):
    """
    Parse metadata from the agent directory.
    
    Args:
        agent_path: Path to the agent directory
        
    Returns:
        Dict with agent metadata
    """
    agent_path = Path(agent_path)
    
    # Check for metadata.json
    metadata_path = agent_path / "metadata.json"
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {metadata_path}")
    
    # Default metadata
    return {
        "name": agent_path.name,
        "framework": "langgraph",
        "version": "0.1.0",
    }