# File: runagent/agent_builder/llm_client.py

import os
import json
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Base class for LLM clients"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI client"""
    
    def __init__(self, api_key: str):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=kwargs.get('model', 'gpt-4o-mini'),
            messages=messages,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 2000)
        )
        return response.choices[0].message.content


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client"""
    
    def __init__(self, api_key: str):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # Convert messages format for Claude
        system_message = ""
        user_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_message = msg['content']
            else:
                user_messages.append(msg)
        
        response = self.client.messages.create(
            model=kwargs.get('model', 'claude-3-haiku-20240307'),
            max_tokens=kwargs.get('max_tokens', 2000),
            temperature=kwargs.get('temperature', 0.7),
            system=system_message,
            messages=user_messages
        )
        return response.content[0].text


class GroqClient(BaseLLMClient):
    """Groq client"""
    
    def __init__(self, api_key: str):
        try:
            import groq
            self.client = groq.Groq(api_key=api_key)
        except ImportError:
            raise ImportError("groq package not installed. Run: pip install groq")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=kwargs.get('model', 'mixtral-8x7b-32768'),
            messages=messages,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 2000)
        )
        return response.choices[0].message.content


class GoogleClient(BaseLLMClient):
    """Google Gemini client"""
    
    def __init__(self, api_key: str):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(
                model_name=kwargs.get('model', 'gemini-pro')
            )
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # Convert messages to Gemini format
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])
        
        response = self.client.generate_content(conversation_text)
        return response.text


class UniversalLLMClient:
    """Universal LLM client that works with multiple providers"""
    
    def __init__(self):
        self.client = None
        self.provider = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize client based on available API keys"""
        
        # Try OpenAI first
        if os.getenv('OPENAI_API_KEY'):
            try:
                self.client = OpenAIClient(os.getenv('OPENAI_API_KEY'))
                self.provider = 'openai'
                return
            except Exception as e:
                print(f"Failed to initialize OpenAI: {e}")
        
        # Try Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            try:
                self.client = AnthropicClient(os.getenv('ANTHROPIC_API_KEY'))
                self.provider = 'anthropic'
                return
            except Exception as e:
                print(f"Failed to initialize Anthropic: {e}")
        
        # Try Groq
        if os.getenv('GROQ_API_KEY'):
            try:
                self.client = GroqClient(os.getenv('GROQ_API_KEY'))
                self.provider = 'groq'
                return
            except Exception as e:
                print(f"Failed to initialize Groq: {e}")
        
        # Try Google
        if os.getenv('GOOGLE_API_KEY'):
            try:
                self.client = GoogleClient(os.getenv('GOOGLE_API_KEY'))
                self.provider = 'google'
                return
            except Exception as e:
                print(f"Failed to initialize Google: {e}")
        
        raise Exception("No valid API key found. Please set one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, GOOGLE_API_KEY")
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make a chat completion request"""
        if not self.client:
            raise Exception("LLM client not initialized")
        
        return self.client.chat_completion(messages, **kwargs)
    
    def function_call(self, messages: List[Dict[str, str]], functions: List[Dict], **kwargs) -> Dict[str, Any]:
        """Make a function call (only supported by some providers)"""
        if self.provider == 'openai':
            import openai
            response = self.client.client.chat.completions.create(
                model=kwargs.get('model', 'gpt-4o-mini'),
                messages=messages,
                functions=functions,
                function_call="auto",
                temperature=kwargs.get('temperature', 0.1)
            )
            
            choice = response.choices[0]
            if choice.message.function_call:
                return {
                    'function_call': {
                        'name': choice.message.function_call.name,
                        'arguments': json.loads(choice.message.function_call.arguments)
                    }
                }
            else:
                return {'content': choice.message.content}
        
        else:
            # For non-OpenAI providers, simulate function calling with structured prompts
            function_descriptions = []
            for func in functions:
                func_desc = f"Function: {func['name']}\n"
                func_desc += f"Description: {func['description']}\n"
                func_desc += f"Parameters: {json.dumps(func['parameters'])}\n"
                function_descriptions.append(func_desc)
            
            system_prompt = """You are a function calling assistant. Based on the user's request, determine if you need to call a function or provide a direct response.

Available functions:
""" + "\n".join(function_descriptions) + """

If you need to call a function, respond with this EXACT format:
FUNCTION_CALL: {"name": "function_name", "arguments": {"param1": "value1"}}

If you don't need to call a function, respond normally."""

            messages_with_system = [{"role": "system", "content": system_prompt}] + messages
            
            response = self.chat_completion(messages_with_system, **kwargs)
            
            if response.startswith("FUNCTION_CALL:"):
                try:
                    function_data = json.loads(response.replace("FUNCTION_CALL:", "").strip())
                    return {'function_call': function_data}
                except json.JSONDecodeError:
                    return {'content': response}
            else:
                return {'content': response}
    
    def get_provider(self) -> str:
        """Get current provider name"""
        return self.provider