# File: runagent/agent_builder/agent_generator.py

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from rich.console import Console

from runagent.agent_builder.llm_client import UniversalLLMClient
from runagent.agent_builder.template_manager import TemplateManager

console = Console()


class AgentGenerator:
    """Generate agents based on requirements and templates"""
    
    def __init__(self, llm_client: UniversalLLMClient, template_manager: TemplateManager):
        self.llm_client = llm_client
        self.template_manager = template_manager
        
    def generate_agent(self, requirements: Dict[str, Any]) -> bool:
        """Generate agent based on requirements"""
        try:
            framework = requirements['framework']
            agent_type = requirements['agent_type']
            folder_name = requirements['folder_name']
            
            console.print(f"🎯 Framework: {framework}")
            console.print(f"🤖 Agent Type: {agent_type}")
            console.print(f"📁 Folder: {folder_name}")
            
            # Load framework templates
            self.template_manager.load_framework_templates(framework)
            
            # Select best template
            template_name = self.template_manager.get_best_template(
                framework, agent_type, requirements
            )
            console.print(f"📋 Using template: {template_name}")
            
            # Create target folder
            target_folder = Path.cwd() / folder_name
            if target_folder.exists():
                console.print(f"⚠️ Folder {folder_name} already exists")
                return False
            
            # Copy template files
            success = self.template_manager.copy_template_to_folder(
                framework, template_name, target_folder
            )
            
            if not success:
                return False
            
            # Customize the agent
            self._customize_agent(target_folder, requirements, framework, template_name)
            
            # Create .env file
            self._create_env_file(target_folder, requirements.get('api_keys', {}))
            
            console.print(f"✅ Agent generated successfully!")
            return True
            
        except Exception as e:
            console.print(f"❌ Error generating agent: {e}")
            return False
    
    def _customize_agent(self, target_folder: Path, requirements: Dict[str, Any], framework: str, template_name: str):
        """Customize agent based on requirements"""
        
        # Update config file
        self._update_config_file(target_folder, requirements)
        
        # Generate custom code if needed
        if requirements.get('capabilities') or requirements['description'] != "User specified agent":
            self._generate_custom_code(target_folder, requirements, framework)
    
    def _update_config_file(self, target_folder: Path, requirements: Dict[str, Any]):
        """Update runagent.config.json with custom details"""
        config_file = target_folder / "runagent.config.json"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update with requirements
            config['agent_name'] = requirements.get('folder_name', 'custom_agent')
            config['description'] = requirements['description']
            config['version'] = '1.0.0'
            config['created_at'] = datetime.now().isoformat()
            
            # Update template source
            if 'template_source' in config:
                config['template_source']['author'] = 'runagent-builder'
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
    
    def _generate_custom_code(self, target_folder: Path, requirements: Dict[str, Any], framework: str):
        """Generate custom code based on requirements using LLM"""
        
        try:
            # Find main code files to customize
            main_files = self._find_main_files(target_folder, framework)
            
            for file_path in main_files:
                if file_path.suffix == '.py':
                    self._customize_python_file(file_path, requirements, framework)
                    
        except Exception as e:
            console.print(f"⚠️ Warning: Could not generate custom code: {e}")
    
    def _find_main_files(self, target_folder: Path, framework: str) -> List[Path]:
        """Find main files that should be customized"""
        main_files = []
        
        # Common main file patterns
        patterns = [
            'main.py',
            'agent.py', 
            'agents.py',
            '*agent*.py',
            'run.py'
        ]
        
        for pattern in patterns:
            files = list(target_folder.glob(pattern))
            main_files.extend(files)
        
        return main_files
    
    def _customize_python_file(self, file_path: Path, requirements: Dict[str, Any], framework: str):
        """Customize a Python file based on requirements"""
        
        try:
            with open(file_path, 'r') as f:
                original_content = f.read()
            
            # Generate customized code
            custom_code = self._generate_code_with_llm(
                original_content, requirements, framework, file_path.name
            )
            
            if custom_code and custom_code.strip() != original_content.strip():
                # Backup original
                backup_path = file_path.with_suffix('.py.original')
                with open(backup_path, 'w') as f:
                    f.write(original_content)
                
                # Write customized code
                with open(file_path, 'w') as f:
                    f.write(custom_code)
                
                console.print(f"🎨 Customized {file_path.name}")
                
        except Exception as e:
            console.print(f"⚠️ Warning: Could not customize {file_path.name}: {e}")
    
    def _generate_code_with_llm(self, original_code: str, requirements: Dict[str, Any], framework: str, filename: str) -> str:
        """Generate customized code using LLM"""
        
        system_prompt = f"""You are an expert {framework} developer. Your task is to customize the provided agent code based on user requirements.

Guidelines:
1. Keep the existing structure and imports
2. Maintain compatibility with the {framework} framework
3. Only modify the core logic to match the requirements
4. Don't break existing function signatures that are used by runagent
5. Add helpful comments explaining changes
6. Ensure the code is production-ready

Requirements to implement:
- Agent Type: {requirements['agent_type']}
- Description: {requirements['description']}
- Capabilities: {', '.join(requirements.get('capabilities', []))}
- Tools needed: {', '.join(requirements.get('tools_needed', []))}

Return only the complete Python code, no explanations."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Customize this {filename} file:\n\n```python\n{original_code}\n```"}
        ]
        
        try:
            response = self.llm_client.chat_completion(messages, temperature=0.1)
            
            # Extract code from response
            if "```python" in response:
                code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
                if code_match:
                    return code_match.group(1)
            elif "```" in response:
                code_match = re.search(r'```\n(.*?)\n```', response, re.DOTALL)
                if code_match:
                    return code_match.group(1)
            else:
                # Assume the entire response is code
                return response
                
        except Exception as e:
            console.print(f"⚠️ LLM customization failed: {e}")
            return original_code
        
        return original_code
    
    def _create_env_file(self, target_folder: Path, api_keys: Dict[str, str]):
        """Create .env file with API keys"""
        env_file = target_folder / ".env"
        
        env_content = []
        env_content.append("# API Keys - Add your actual keys here")
        env_content.append("")
        
        # Add provided API keys
        for key_name, key_value in api_keys.items():
            env_content.append(f"{key_name}={key_value}")
        
        # Add placeholder for common keys not provided
        common_keys = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY", 
            "GROQ_API_KEY",
            "GOOGLE_API_KEY"
        ]
        
        for key_name in common_keys:
            if key_name not in api_keys:
                env_content.append(f"# {key_name}=your-key-here")
        
        env_content.append("")
        env_content.append("# Other configuration")
        env_content.append("# DEBUG=true")
        
        with open(env_file, 'w') as f:
            f.write('\n'.join(env_content))
        
        console.print(f"🔑 Created .env file with API keys")