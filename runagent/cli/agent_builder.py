# File: runagent/cli/agent_builder.py

import os
import json
import click
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from runagent.agent_builder.llm_client import UniversalLLMClient
from runagent.agent_builder.intent_parser import IntentParser
from runagent.agent_builder.template_manager import TemplateManager
from runagent.agent_builder.agent_generator import AgentGenerator
from runagent.agent_builder.conversation_memory import ConversationMemory

console = Console()


class AgentBuilderSession:
    """Manages the agent building session with conversation memory"""
    
    def __init__(self):
        self.memory = ConversationMemory()
        self.llm_client = None
        self.intent_parser = None
        self.template_manager = TemplateManager()
        self.agent_generator = None
        
    def initialize_llm(self):
        """Initialize LLM client from environment variables"""
        try:
            self.llm_client = UniversalLLMClient()
            self.intent_parser = IntentParser(self.llm_client)
            self.agent_generator = AgentGenerator(self.llm_client, self.template_manager)
            return True
        except Exception as e:
            console.print(f"❌ [red]Failed to initialize LLM: {e}[/red]")
            console.print("\n💡 Make sure you have set one of these environment variables:")
            console.print("   • OPENAI_API_KEY")
            console.print("   • ANTHROPIC_API_KEY")  
            console.print("   • GROQ_API_KEY")
            console.print("   • GOOGLE_API_KEY")
            return False
    
    def collect_requirements(self) -> Dict[str, Any]:
        """Collect agent requirements through conversation"""
        console.print(Panel("🤖 RunAgent Agent Builder", style="bold blue"))
        console.print("Let's build your AI agent! I'll help you create it step by step.\n")
        
        # Get user description
        user_input = Prompt.ask(
            "[bold]Describe the agent you want to build[/bold]",
            default="A helpful assistant"
        )
        
        self.memory.add_message("user", user_input)
        
        # Parse intent and extract requirements
        requirements = self._parse_requirements_with_retries(user_input)
        
        # Fill in missing information
        requirements = self._complete_requirements(requirements)
        
        return requirements
    
    def _parse_requirements_with_retries(self, user_input: str, max_retries: int = 3) -> Dict[str, Any]:
        """Parse requirements with retry logic"""
        for attempt in range(max_retries):
            try:
                console.print(f"🔍 Analyzing your requirements... (attempt {attempt + 1})")
                
                # Get conversation context
                context = self.memory.get_conversation_summary()
                
                requirements = self.intent_parser.parse_agent_requirements(
                    user_input, 
                    context=context
                )
                
                if self._validate_requirements(requirements):
                    return requirements
                    
            except Exception as e:
                console.print(f"⚠️ [yellow]Parse attempt {attempt + 1} failed: {e}[/yellow]")
                
        # If all attempts fail, ask for clarification
        return self._ask_for_clarification()
    
    def _validate_requirements(self, requirements: Dict[str, Any]) -> bool:
        """Validate if requirements are complete enough"""
        required_fields = ['agent_type', 'framework']
        return all(field in requirements for field in required_fields)
    
    def _ask_for_clarification(self) -> Dict[str, Any]:
        """Ask user for clarification when parsing fails"""
        console.print("\n🤔 I need some clarification to build your agent properly.")
        
        # Ask for framework
        framework = self._ask_for_framework()
        
        # Ask for agent type/purpose  
        agent_type = Prompt.ask(
            "What type of agent do you want? (e.g., chatbot, research, email, code)",
            default="chatbot"
        )
        
        return {
            'framework': framework,
            'agent_type': agent_type,
            'description': "User specified agent",
            'capabilities': []
        }
    
    def _ask_for_framework(self) -> str:
        """Ask user to select framework"""
        available_frameworks = self.template_manager.get_available_frameworks()
        
        console.print("\n📚 Available frameworks:")
        table = Table()
        table.add_column("Option", style="cyan")
        table.add_column("Framework", style="green") 
        table.add_column("Description", style="dim")
        
        framework_descriptions = {
            'langchain': 'General purpose LLM applications',
            'langgraph': 'Multi-agent workflows and graphs',
            'crewai': 'Collaborative multi-agent systems',
            'autogen': 'Conversational multi-agent framework',
            'ag2': 'Advanced multi-agent conversations',
            'agno': 'Simple and efficient agents',
            'llamaindex': 'Data-aware applications with RAG',
            'letta': 'Memory-enabled persistent agents',
            'openai': 'Direct OpenAI API integration',
            'default': 'Simple mock agents for testing'
        }
        
        for i, fw in enumerate(available_frameworks, 1):
            desc = framework_descriptions.get(fw, "Agent framework")
            table.add_row(str(i), fw, desc)
            
        console.print(table)
        
        while True:
            try:
                choice = Prompt.ask(
                    f"Select framework (1-{len(available_frameworks)})",
                    default="1"
                )
                index = int(choice) - 1
                if 0 <= index < len(available_frameworks):
                    return available_frameworks[index]
                else:
                    console.print("❌ Invalid choice. Please try again.")
            except ValueError:
                console.print("❌ Please enter a number.")
    
    def _complete_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Complete missing requirements through user interaction"""
        
        # Ask for folder name if not specified
        if 'folder_name' not in requirements:
            default_name = f"{requirements.get('agent_type', 'agent')}_{requirements.get('framework', 'agent')}"
            requirements['folder_name'] = Prompt.ask(
                "Enter folder name for your agent",
                default=default_name
            )
        
        # Ask for API keys
        requirements['api_keys'] = self._collect_api_keys(requirements.get('framework'))
        
        return requirements
    
    def _collect_api_keys(self, framework: str) -> Dict[str, str]:
        """Collect necessary API keys"""
        api_keys = {}
        
        console.print(f"\n🔑 Setting up API keys for {framework}...")
        
        # Ask what LLM provider they want to use
        console.print("Which LLM provider do you want to use?")
        providers = [
            ("OpenAI", "OPENAI_API_KEY"),
            ("Anthropic (Claude)", "ANTHROPIC_API_KEY"), 
            ("Groq", "GROQ_API_KEY"),
            ("Google (Gemini)", "GOOGLE_API_KEY"),
            ("Skip for now", None)
        ]
        
        table = Table()
        table.add_column("Option", style="cyan")
        table.add_column("Provider", style="green")
        
        for i, (name, _) in enumerate(providers, 1):
            table.add_row(str(i), name)
            
        console.print(table)
        
        while True:
            try:
                choice = Prompt.ask(f"Select provider (1-{len(providers)})", default="1")
                index = int(choice) - 1
                if 0 <= index < len(providers):
                    provider_name, key_name = providers[index]
                    if key_name:
                        api_key = Prompt.ask(
                            f"Enter your {provider_name} API key",
                            password=True
                        )
                        if api_key.strip():
                            api_keys[key_name] = api_key.strip()
                    break
                else:
                    console.print("❌ Invalid choice. Please try again.")
            except ValueError:
                console.print("❌ Please enter a number.")
        
        # Framework-specific API keys
        if framework == 'letta':
            letta_url = Prompt.ask(
                "Enter Letta server URL",
                default="http://localhost:8283"
            )
            api_keys['LETTA_SERVER_URL'] = letta_url
            
        return api_keys
    
    def create_agent(self, requirements: Dict[str, Any]) -> bool:
        """Create the agent based on requirements"""
        try:
            console.print(f"\n🏗️ Creating {requirements['framework']} agent...")
            
            # Load framework template
            framework = requirements['framework']
            self.template_manager.load_framework_templates(framework)
            
            # Generate agent
            success = self.agent_generator.generate_agent(requirements)
            
            if success:
                folder_path = Path.cwd() / requirements['folder_name']
                console.print(f"\n✅ [green]Agent created successfully![/green]")
                console.print(f"📁 Location: [cyan]{folder_path}[/cyan]")
                console.print(f"\n📝 [bold]Next steps:[/bold]")
                console.print(f"  1. [cyan]cd {requirements['folder_name']}[/cyan]")
                console.print(f"  2. [cyan]runagent serve .[/cyan]")
                console.print(f"  3. Test your agent!")
                return True
            else:
                console.print("❌ [red]Failed to create agent[/red]")
                return False
                
        except Exception as e:
            console.print(f"❌ [red]Error creating agent: {e}[/red]")
            return False


@click.command()
@click.option("--interactive", "-i", is_flag=True, help="Force interactive mode")
@click.option("--framework", help="Specify framework directly")
@click.option("--type", "agent_type", help="Specify agent type")
@click.option("--folder", help="Specify folder name")
def agent_builder(interactive, framework, agent_type, folder):
    """🤖 Build AI agents with natural language"""
    
    session = AgentBuilderSession()
    
    # Initialize LLM client
    if not session.initialize_llm():
        console.print("\n💡 [yellow]You can export an API key and try again:[/yellow]")
        console.print("   export OPENAI_API_KEY='your-key-here'")
        console.print("   export ANTHROPIC_API_KEY='your-key-here'")
        raise click.ClickException("LLM initialization failed")
    
    try:
        # Collect requirements
        if interactive or not all([framework, agent_type, folder]):
            requirements = session.collect_requirements()
        else:
            # Use provided arguments
            requirements = {
                'framework': framework,
                'agent_type': agent_type,
                'folder_name': folder,
                'description': f"{agent_type} agent using {framework}",
                'capabilities': [],
                'api_keys': session._collect_api_keys(framework)
            }
        
        # Create the agent
        success = session.create_agent(requirements)
        
        if not success:
            raise click.ClickException("Agent creation failed")
            
    except KeyboardInterrupt:
        console.print("\n\n🛑 [yellow]Agent building cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n❌ [red]Unexpected error: {e}[/red]")
        raise click.ClickException("Agent building failed")


if __name__ == "__main__":
    agent_builder()