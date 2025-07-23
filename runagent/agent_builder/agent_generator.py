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
        
        # STEP 1: Create/update config file FIRST (so code generation can use the entrypoints)
        self._create_config_file(target_folder, requirements, framework, template_name)
        
        # STEP 2: Generate custom code that implements the specific functionality
        if requirements.get('capabilities') or requirements['description'] != "User specified agent":
            self._generate_custom_code(target_folder, requirements, framework)
    
    def _create_config_file(self, target_folder: Path, requirements: Dict[str, Any], framework: str, template_name: str):
        """Create runagent.config.json file"""
        config_file = target_folder / "runagent.config.json"
        
        # Check if config already exists (from template)
        if config_file.exists():
            # Update existing config
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            # Create new config from scratch
            config = {}
        
        # Update with custom details
        config.update({
            "agent_name": requirements.get('folder_name', 'custom_agent'),
            "description": requirements['description'],
            "framework": framework,
            "template": template_name,
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "template_source": {
                "repo_url": "https://github.com/runagent-dev/runagent.git",
                "path": f"templates/{framework}/{template_name}",
                "author": "runagent-builder"
            }
        })
        
        # Ensure agent_architecture exists
        if "agent_architecture" not in config:
            config["agent_architecture"] = {
                "entrypoints": []
            }
        
        # Generate entrypoints based on framework and agent type
        entrypoints = self._generate_entrypoints(requirements, framework, template_name)
        config["agent_architecture"]["entrypoints"] = entrypoints
        
        # Write config file
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        console.print(f"📋 Created runagent.config.json with {len(entrypoints)} entrypoints")

    def _generate_entrypoints(self, requirements: Dict[str, Any], framework: str, template_name: str) -> List[Dict[str, Any]]:
        """Generate appropriate entrypoints based on framework and requirements using LLM"""
        
        # Use LLM to generate custom entrypoints based on the specific agent requirements
        try:
            entrypoints = self._generate_entrypoints_with_llm(requirements, framework, template_name)
            if entrypoints:
                return entrypoints
        except Exception as e:
            console.print(f"⚠️ LLM entrypoint generation failed: {e}")
        
        # Fallback to basic framework-specific entrypoints
        return self._get_default_entrypoints(framework)

    def _generate_entrypoints_with_llm(self, requirements: Dict[str, Any], framework: str, template_name: str) -> List[Dict[str, Any]]:
        """Use LLM to generate custom entrypoints for the specific agent"""
        
        # Define function for structured entrypoint generation
        generate_entrypoints_function = {
            "name": "generate_agent_entrypoints",
            "description": "Generate appropriate entrypoints for an AI agent based on its specific functionality",
            "parameters": {
                "type": "object",
                "properties": {
                    "entrypoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file": {
                                    "type": "string",
                                    "description": "Python file containing the function (e.g., 'agent.py', 'main.py')"
                                },
                                "module": {
                                    "type": "string", 
                                    "description": "Function name to call (e.g., 'extract_keywords', 'run', 'process_document')"
                                },
                                "tag": {
                                    "type": "string",
                                    "description": "Descriptive tag for the entrypoint (e.g., 'extract_keywords', 'keyword_extraction')"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What this entrypoint does"
                                }
                            },
                            "required": ["file", "module", "tag"]
                        }
                    }
                },
                "required": ["entrypoints"]
            }
        }
        
        system_prompt = f"""You are an expert at designing AI agent architectures. Generate appropriate entrypoints for an agent based on its specific functionality.

Guidelines for entrypoint generation:
1. Create specific, meaningful function names and tags that match the agent's purpose
2. For {framework} framework, typically use 'agent.py' or 'main.py' as the file
3. Include both regular and streaming versions when appropriate
4. Make tags descriptive and specific to the agent's functionality
5. Consider the agent's input parameters and use cases

Agent Requirements:
- Description: {requirements['description']}
- Agent Type: {requirements.get('agent_type', 'assistant')}
- Framework: {framework}
- Capabilities: {', '.join(requirements.get('capabilities', []))}

Examples of good entrypoints:
- Keyword extraction agent: extract_keywords, extract_keywords_stream
- PDF summarizer: summarize_pdf, summarize_document_stream  
- Email writer: compose_email, generate_email_stream
- Code generator: generate_code, generate_code_stream
- Data analyzer: analyze_data, analyze_data_stream

Generate 2-4 entrypoints that specifically match this agent's functionality."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate entrypoints for: {requirements['description']}"}
        ]
        
        try:
            result = self.llm_client.function_call(
                messages=messages,
                functions=[generate_entrypoints_function],
                temperature=0.1
            )
            
            if 'function_call' in result:
                entrypoints_data = result['function_call']['arguments']
                entrypoints = entrypoints_data.get('entrypoints', [])
                
                # Clean up entrypoints and ensure they have required fields
                cleaned_entrypoints = []
                for ep in entrypoints:
                    if all(field in ep for field in ['file', 'module', 'tag']):
                        # Remove description field as it's not needed in config
                        cleaned_ep = {
                            'file': ep['file'],
                            'module': ep['module'], 
                            'tag': ep['tag']
                        }
                        cleaned_entrypoints.append(cleaned_ep)
                
                if cleaned_entrypoints:
                    console.print(f"🎯 Generated {len(cleaned_entrypoints)} custom entrypoints")
                    return cleaned_entrypoints
            
        except Exception as e:
            console.print(f"⚠️ LLM entrypoint generation error: {e}")
        
        return []

    def _get_default_entrypoints(self, framework: str) -> List[Dict[str, Any]]:
        """Get basic default entrypoints for a framework"""
        
        framework_defaults = {
            'langgraph': [
                {"file": "agent.py", "module": "run", "tag": "generic"},
                {"file": "agent.py", "module": "run_stream", "tag": "generic_stream"}
            ],
            'langchain': [
                {"file": "main.py", "module": "run", "tag": "generic"},
                {"file": "main.py", "module": "run_stream", "tag": "generic_stream"}
            ],
            'crewai': [
                {"file": "main.py", "module": "run_crew", "tag": "research_crew"}
            ],
            'openai': [
                {"file": "main.py", "module": "get_response", "tag": "simple_assistant"},
                {"file": "main.py", "module": "get_response_stream", "tag": "simple_assistant_stream"}
            ],
            'autogen': [
                {"file": "agent.py", "module": "agent.run", "tag": "autogen_invoke"},
                {"file": "agent.py", "module": "agent.run_stream", "tag": "autogen_stream"}
            ],
            'ag2': [
                {"file": "agent.py", "module": "invoke", "tag": "ag2_invoke"},
                {"file": "agent.py", "module": "stream", "tag": "ag2_stream"}
            ],
            'agno': [
                {"file": "agent.py", "module": "agent.run", "tag": "agno_assistant"},
                {"file": "agent.py", "module": "agent_run_stream", "tag": "agno_stream"}
            ],
            'llamaindex': [
                {"file": "agent.py", "module": "do_task", "tag": "llamaindex_run"},
                {"file": "agent.py", "module": "stream_task", "tag": "llamaindex_stream"}
            ],
            'letta': [
                {"file": "agent.py", "module": "letta_run", "tag": "basic"},
                {"file": "agent.py", "module": "letta_run_stream", "tag": "basic_stream"}
            ]
        }
        
        return framework_defaults.get(framework, [
            {"file": "main.py", "module": "mock_response", "tag": "minimal"},
            {"file": "main.py", "module": "mock_response_stream", "tag": "minimal_stream"}
        ])
    
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
                original_content, requirements, framework, str(file_path)
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
    
    def _generate_code_with_llm(self, original_code: str, requirements: Dict[str, Any], framework: str, file_path_str: str) -> str:
        """Generate customized code using LLM"""
        
        # Get the entrypoints that were generated for this agent
        file_path = Path(file_path_str)
        config_file = file_path.parent / "runagent.config.json"
        entrypoints = []
        
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    entrypoints = config.get('agent_architecture', {}).get('entrypoints', [])
        except:
            pass
        
        entrypoint_info = ""
        if entrypoints:
            entrypoint_info = "\nRequired entrypoint functions to implement:\n"
            for ep in entrypoints:
                entrypoint_info += f"- {ep['module']} (tag: {ep['tag']})\n"
        
        filename = file_path.name
        system_prompt = f"""You are an expert {framework} developer. Your task is to customize the provided agent code based on user requirements.

Guidelines:
1. Keep the existing structure and imports that work
2. Maintain compatibility with the {framework} framework
3. Implement the SPECIFIC functionality described in the requirements
4. Make sure the code actually implements the described agent behavior
5. Add helpful comments explaining the logic
6. Ensure the code is production-ready and handles errors gracefully
7. IMPORTANT: Implement the exact entrypoint functions specified below

Agent Requirements:
- Agent Type: {requirements['agent_type']}
- Description: {requirements['description']}
- Capabilities: {', '.join(requirements.get('capabilities', []))}
- Tools needed: {', '.join(requirements.get('tools_needed', []))}

{entrypoint_info}

The agent should specifically implement: {requirements['description']}

For example, if this is a keyword extraction agent:
- Implement a function that takes text and num_keywords as parameters
- Extract meaningful keywords from the text
- Return the specified number of keywords
- Handle edge cases like empty text or invalid numbers

Return only the complete Python code that actually implements the described functionality."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Customize this {filename} file to implement the agent functionality:\n\n```python\n{original_code}\n```\n\nMake sure it actually implements: {requirements['description']}"}
        ]
        
        try:
            response = self.llm_client.chat_completion(messages, temperature=0.1, max_tokens=3000)
            
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