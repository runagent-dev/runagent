from abc import ABC, abstractmethod
from typing import Dict

class BaseTemplate(ABC):
    """Base template for all framework templates"""
    
    @abstractmethod
    def generate_files(self) -> Dict[str, str]:
        """Generate all required files for the framework"""
        pass
    
    @abstractmethod
    def get_runner_template(self) -> str:
        """Get the runner.py template content"""
        pass
    
    @abstractmethod
    def get_requirements(self) -> str:
        """Get the requirements.txt content"""
        pass
    
    @abstractmethod
    def get_env_template(self) -> str:
        """Get the .env template content"""
        pass
