"""
Agent management utilities.
"""

import typing as t
from pathlib import Path

from .exceptions import ValidationError


class AgentManager:
    """Utilities for agent validation and management"""
    
    def __init__(self, config):
        """
        Initialize agent manager.
        
        Args:
            config: SDK configuration object
        """
        self.config = config
    
    def validate_agent(self, folder: str) -> t.Tuple[bool, t.Dict[str, t.Any]]:
        """
        Validate agent project structure.
        
        Args:
            folder: Path to agent folder
            
        Returns:
            Tuple of (is_valid, validation_details)
        """
        folder_path = Path(folder)
        if not folder_path.exists():
            return False, {"error": f"Folder not found: {folder}"}
        
        validation_details = {
            "folder_exists": True,
            "files_found": [],
            "missing_files": [],
            "framework": "unknown",
            "valid": False
        }
        
        # Check for required files
        required_files = ["main.py"]
        optional_files = ["agent.py", "requirements.txt", ".env"]
        
        for file_name in required_files + optional_files:
            file_path = folder_path / file_name
            if file_path.exists():
                validation_details["files_found"].append(file_name)
            elif file_name in required_files:
                validation_details["missing_files"].append(file_name)
        
        # Check if main.py has run function
        main_file = folder_path / "main.py"
        if main_file.exists():
            try:
                content = main_file.read_text()
                if "def run(" in content:
                    validation_details["has_run_function"] = True
                else:
                    validation_details["has_run_function"] = False
                    validation_details["missing_files"].append("run function in main.py")
            except Exception as e:
                validation_details["main_py_error"] = str(e)
        
        # Detect framework
        validation_details["framework"] = self.detect_framework(folder)
        
        # Overall validation
        validation_details["valid"] = (
            len(validation_details["missing_files"]) == 0 and
            validation_details.get("has_run_function", False)
        )
        
        return validation_details["valid"], validation_details
    
    def detect_framework(self, folder: str) -> str:
        """
        Auto-detect framework used in agent project.
        
        Args:
            folder: Path to agent folder
            
        Returns:
            Detected framework name
        """
        folder_path = Path(folder)
        if not folder_path.exists():
            return "unknown"
        
        framework_keywords = {
            'langgraph': ['langgraph', 'StateGraph', 'Graph'],
            'langchain': ['langchain', 'ConversationChain', 'AgentExecutor'],
            'llamaindex': ['llama_index', 'VectorStoreIndex', 'QueryEngine']
        }
        
        # Check main.py and agent.py for imports
        for file_to_check in ['main.py', 'agent.py']:
            file_path = folder_path / file_to_check
            if file_path.exists():
                try:
                    content = file_path.read_text().lower()
                    for framework, keywords in framework_keywords.items():
                        if any(keyword.lower() in content for keyword in keywords):
                            return framework
                except:
                    continue
        
        # Check requirements.txt
        req_file = folder_path / 'requirements.txt'
        if req_file.exists():
            try:
                content = req_file.read_text().lower()
                for framework, keywords in framework_keywords.items():
                    if any(keyword.lower() in content for keyword in keywords):
                        return framework
            except:
                pass
        
        return 'unknown'
    
    def get_project_info(self, folder: str) -> t.Dict[str, t.Any]:
        """
        Get comprehensive information about an agent project.
        
        Args:
            folder: Path to agent folder
            
        Returns:
            Project information dictionary
        """
        folder_path = Path(folder)
        
        info = {
            "folder_path": str(folder_path.absolute()),
            "folder_exists": folder_path.exists(),
            "framework": "unknown",
            "valid": False,
            "files": [],
            "size_mb": 0
        }
        
        if not folder_path.exists():
            return info
        
        # Get file list and size
        total_size = 0
        for file_path in folder_path.rglob("*"):
            if file_path.is_file():
                info["files"].append({
                    "name": str(file_path.relative_to(folder_path)),
                    "size": file_path.stat().st_size
                })
                total_size += file_path.stat().st_size
        
        info["size_mb"] = round(total_size / 1024 / 1024, 2)
        
        # Get validation info
        is_valid, validation_details = self.validate_agent(folder)
        info.update(validation_details)
        
        return info
