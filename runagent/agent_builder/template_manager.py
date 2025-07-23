# File: runagent/agent_builder/template_manager.py

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console

console = Console()


class TemplateManager:
    """Manages agent templates from the templates directory"""
    
    def __init__(self):
        self.templates_dir = self._find_templates_dir()
        self.loaded_templates = {}
        
    def _find_templates_dir(self) -> Path:
        """Find the templates directory"""
        # Try to find templates directory relative to current file
        current_file = Path(__file__)
        
        # Look for templates directory in the project
        possible_paths = [
            current_file.parent.parent.parent / "templates",  # From runagent/agent_builder/
            Path.cwd() / "templates",
            Path.cwd() / "runagent" / "templates",
            Path(__file__).parent.parent.parent / "templates"
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
                
        raise FileNotFoundError("Templates directory not found")
    
    def get_available_frameworks(self) -> List[str]:
        """Get list of available frameworks"""
        frameworks = []
        for item in self.templates_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                frameworks.append(item.name)
        return sorted(frameworks)
    
    def load_framework_templates(self, framework: str) -> Dict[str, Any]:
        """Load all templates for a specific framework"""
        framework_dir = self.templates_dir / framework
        
        if not framework_dir.exists():
            raise ValueError(f"Framework '{framework}' not found in templates")
        
        templates = {}
        
        # Load all template variants for this framework
        for template_dir in framework_dir.iterdir():
            if template_dir.is_dir():
                template_name = template_dir.name
                try:
                    template_data = self._load_template(template_dir)
                    templates[template_name] = template_data
                except Exception as e:
                    console.print(f"⚠️ Warning: Failed to load template {framework}/{template_name}: {e}")
        
        self.loaded_templates[framework] = templates
        return templates
    
    def _load_template(self, template_dir: Path) -> Dict[str, Any]:
        """Load a single template"""
        template_data = {
            'path': template_dir,
            'files': [],
            'config': None,
            'requirements': None
        }
        
        # Load all files in template
        for file_path in template_dir.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(template_dir)
                template_data['files'].append({
                    'path': rel_path,
                    'full_path': file_path,
                    'name': file_path.name
                })
        
        # Load config file if exists
        config_file = template_dir / "runagent.config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                template_data['config'] = json.load(f)
        
        # Load requirements if exists
        req_file = template_dir / "requirements.txt"
        if req_file.exists():
            with open(req_file, 'r') as f:
                template_data['requirements'] = f.read().strip().split('\n')
        
        return template_data
    
    def get_best_template(self, framework: str, agent_type: str, requirements: Dict[str, Any]) -> str:
        """Select the best template variant for given requirements"""
        if framework not in self.loaded_templates:
            self.load_framework_templates(framework)
        
        templates = self.loaded_templates[framework]
        
        if not templates:
            raise ValueError(f"No templates found for framework '{framework}'")
        
        # Template selection logic
        template_priorities = {
            'chatbot': ['chatbot', 'basic', 'default'],
            'research': ['advanced', 'rag', 'default'], 
            'email': ['email_agent', 'default'],
            'code': ['advanced', 'default'],
            'math': ['math_genius', 'default'],
            'weather': ['default'],
            'analysis': ['advanced', 'rag', 'default'],
            'writing': ['default'],
            'qa': ['rag', 'advanced', 'default'],
            'assistant': ['default', 'basic']
        }
        
        preferred_templates = template_priorities.get(agent_type, ['default'])
        
        # Find the first available template
        for template_name in preferred_templates:
            if template_name in templates:
                return template_name
        
        # Fallback to first available template
        return list(templates.keys())[0]
    
    def get_template_files(self, framework: str, template_name: str) -> List[Dict[str, Any]]:
        """Get all files in a template"""
        if framework not in self.loaded_templates:
            self.load_framework_templates(framework)
        
        template = self.loaded_templates[framework][template_name]
        return template['files']
    
    def get_template_config(self, framework: str, template_name: str) -> Dict[str, Any]:
        """Get template configuration"""
        if framework not in self.loaded_templates:
            self.load_framework_templates(framework)
        
        template = self.loaded_templates[framework][template_name]
        return template.get('config', {})
    
    def get_template_requirements(self, framework: str, template_name: str) -> List[str]:
        """Get template requirements"""
        if framework not in self.loaded_templates:
            self.load_framework_templates(framework)
        
        template = self.loaded_templates[framework][template_name]
        return template.get('requirements', [])
    
    def copy_template_to_folder(self, framework: str, template_name: str, target_folder: Path) -> bool:
        """Copy template files to target folder"""
        try:
            if framework not in self.loaded_templates:
                self.load_framework_templates(framework)
            
            template = self.loaded_templates[framework][template_name]
            template_path = template['path']
            
            # Create target folder
            target_folder.mkdir(parents=True, exist_ok=True)
            
            # Copy all files
            for file_info in template['files']:
                src_path = file_info['full_path']
                rel_path = file_info['path']
                dest_path = target_folder / rel_path
                
                # Create parent directories if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(src_path, dest_path)
            
            return True
            
        except Exception as e:
            console.print(f"❌ Error copying template: {e}")
            return False