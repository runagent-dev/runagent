# File: runagent/agent_builder/intent_parser.py

import json
from typing import Dict, Any, List, Optional
from runagent.agent_builder.llm_client import UniversalLLMClient


class IntentParser:
    """Parse user intent and extract agent requirements using LLM"""
    
    def __init__(self, llm_client: UniversalLLMClient):
        self.llm_client = llm_client
        
    def parse_agent_requirements(self, user_input: str, context: str = "") -> Dict[str, Any]:
        """Parse user input to extract agent requirements"""
        
        # Define function schema for structured extraction
        extract_function = {
            "name": "extract_agent_requirements",
            "description": "Extract structured requirements for building an AI agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "description": "Type of agent (e.g., chatbot, research, email, code, math, weather, etc.)",
                        "enum": ["chatbot", "research", "email", "code", "math", "weather", "analysis", "writing", "qa", "assistant", "other"]
                    },
                    "framework": {
                        "type": "string", 
                        "description": "Preferred AI framework",
                        "enum": ["langchain", "langgraph", "crewai", "autogen", "ag2", "agno", "llamaindex", "letta", "openai", "default"]
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear description of what the agent should do"
                    },
                    "capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of specific capabilities or features needed"
                    },
                    "data_sources": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "description": "Data sources the agent needs to access (web, files, apis, etc.)"
                    },
                    "tools_needed": {
                        "type": "array",
                        "items": {"type": "string"}, 
                        "description": "Specific tools or integrations needed"
                    },
                    "complexity": {
                        "type": "string",
                        "enum": ["simple", "moderate", "complex"],
                        "description": "Estimated complexity level"
                    },
                    "folder_name": {
                        "type": "string",
                        "description": "Suggested folder name for the agent project"
                    }
                },
                "required": ["agent_type", "framework", "description"]
            }
        }
        
        # Create context-aware prompt
        messages = []
        
        if context:
            messages.append({
                "role": "system", 
                "content": f"Previous conversation context: {context}"
            })
        
        messages.extend([
            {
                "role": "system",
                "content": """You are an expert AI agent architect. Your job is to understand user requirements and extract structured information for building AI agents.

Framework Selection Guidelines:
- langchain: General purpose LLM applications, simple workflows
- langgraph: Multi-step workflows, conditional logic, agent graphs  
- crewai: Multiple agents working together collaboratively
- autogen: Conversational multi-agent systems
- ag2: Advanced multi-agent conversations
- agno: Simple, efficient single agents
- llamaindex: Data-heavy applications, RAG, document processing
- letta: Agents that need persistent memory and context
- openai: Direct OpenAI API usage, simple completions
- default: Testing or simple mock agents

Agent Type Guidelines:
- chatbot: Conversational interface
- research: Information gathering and analysis
- email: Email generation and management
- code: Code generation and assistance
- math: Mathematical computations and problem solving
- weather: Weather information and forecasting
- analysis: Data analysis and insights
- writing: Content creation and editing
- qa: Question answering systems
- assistant: General purpose helper

Be smart about framework selection based on the use case."""
            },
            {
                "role": "user", 
                "content": f"I want to build: {user_input}"
            }
        ])
        
        # Get structured response
        try:
            result = self.llm_client.function_call(
                messages=messages,
                functions=[extract_function],
                temperature=0.1
            )
            
            if 'function_call' in result:
                requirements = result['function_call']['arguments']
                
                # Post-process and validate
                requirements = self._post_process_requirements(requirements, user_input)
                return requirements
            else:
                # Fallback to text parsing
                return self._fallback_parse(user_input, result.get('content', ''))
                
        except Exception as e:
            print(f"Function call failed: {e}")
            return self._fallback_parse(user_input, "")
    
    def _post_process_requirements(self, requirements: Dict[str, Any], original_input: str) -> Dict[str, Any]:
        """Post-process and validate extracted requirements"""
        
        # Ensure required fields
        if 'agent_type' not in requirements:
            requirements['agent_type'] = 'assistant'
            
        if 'framework' not in requirements:
            requirements['framework'] = self._suggest_framework(requirements.get('agent_type', 'assistant'))
            
        if 'description' not in requirements:
            requirements['description'] = original_input
            
        # Generate folder name if not provided
        if 'folder_name' not in requirements or not requirements['folder_name']:
            agent_type = requirements['agent_type'].replace(' ', '_')
            framework = requirements['framework']
            requirements['folder_name'] = f"{agent_type}_{framework}_agent"
        
        # Ensure lists are lists
        for list_field in ['capabilities', 'data_sources', 'tools_needed']:
            if list_field not in requirements:
                requirements[list_field] = []
            elif not isinstance(requirements[list_field], list):
                requirements[list_field] = []
        
        # Set default complexity
        if 'complexity' not in requirements:
            requirements['complexity'] = 'simple'
            
        return requirements
    
    def _suggest_framework(self, agent_type: str) -> str:
        """Suggest framework based on agent type"""
        framework_mapping = {
            'chatbot': 'langchain',
            'research': 'crewai', 
            'email': 'openai',
            'code': 'langchain',
            'math': 'llamaindex',
            'weather': 'langchain',
            'analysis': 'langgraph',
            'writing': 'openai',
            'qa': 'llamaindex',
            'assistant': 'langchain'
        }
        return framework_mapping.get(agent_type, 'langchain')
    
    def _fallback_parse(self, user_input: str, llm_response: str) -> Dict[str, Any]:
        """Fallback parsing when function calling fails"""
        
        # Simple keyword-based parsing
        input_lower = user_input.lower()
        
        # Detect framework
        framework = 'langchain'  # default
        framework_keywords = {
            'langgraph': ['langgraph', 'workflow', 'graph', 'multi-step'],
            'crewai': ['crew', 'team', 'multiple agents', 'collaboration'],
            'autogen': ['autogen', 'conversation', 'multi-agent chat'],
            'llamaindex': ['rag', 'document', 'data', 'index', 'retrieval'],
            'letta': ['memory', 'persistent', 'context', 'letta'],
            'openai': ['openai', 'simple', 'completion', 'gpt']
        }
        
        for fw, keywords in framework_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                framework = fw
                break
        
        # Detect agent type
        agent_type = 'assistant'  # default
        type_keywords = {
            'chatbot': ['chat', 'bot', 'conversation', 'talk'],
            'research': ['research', 'analyze', 'investigate', 'study'],
            'email': ['email', 'mail', 'message'],
            'code': ['code', 'programming', 'develop', 'script'],
            'math': ['math', 'calculate', 'compute', 'equation'],
            'weather': ['weather', 'forecast', 'climate'],
            'writing': ['write', 'content', 'blog', 'article']
        }
        
        for atype, keywords in type_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                agent_type = atype
                break
        
        return {
            'agent_type': agent_type,
            'framework': framework,
            'description': user_input,
            'capabilities': [],
            'data_sources': [],
            'tools_needed': [],
            'complexity': 'simple',
            'folder_name': f"{agent_type}_{framework}_agent"
        }