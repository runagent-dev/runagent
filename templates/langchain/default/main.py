#!/usr/bin/env python3
"""
Simple LangChain Test Agent for RunAgent Development
"""
import os
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run(*args, **kwargs):
    """
    Main agent function for non-streaming execution
    
    Expected input format:
    - message: string - The message to process
    - temperature: float (optional) - LLM temperature (default: 0.7)
    - model: string (optional) - Model to use (default: gpt-3.5-turbo)
    """
    try:
        # Extract parameters
        message = kwargs.get("message", "Hello from RunAgent!")
        temperature = kwargs.get("temperature", 0.7)
        model = kwargs.get("model", "gpt-3.5-turbo")
        
        # Check if we have OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "OpenAI API key not found. Please set OPENAI_API_KEY in .env file",
                "mock_response": f"Mock response to: {message}",
                "timestamp": datetime.now().isoformat(),
                "framework": "langchain",
                "agent_type": "test"
            }
        
        # Try to import and use LangChain
        try:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage
            
            # Initialize LLM
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=api_key
            )
            
            # Process message
            response = llm.invoke([HumanMessage(content=message)])
            
            return {
                "success": True,
                "response": response.content,
                "input": {
                    "message": message,
                    "temperature": temperature,
                    "model": model
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "framework": "langchain",
                    "agent_type": "test",
                    "model_used": model,
                    "response_length": len(response.content)
                }
            }
            
        except ImportError as e:
            # LangChain not installed, return mock response
            return {
                "success": True,
                "response": f"Mock LangChain response to: {message}",
                "input": {
                    "message": message,
                    "temperature": temperature,
                    "model": model
                },
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "framework": "langchain",
                    "agent_type": "test_mock",
                    "note": f"LangChain not available: {str(e)}",
                    "mock": True
                }
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "input": kwargs,
            "timestamp": datetime.now().isoformat(),
            "framework": "langchain",
            "agent_type": "test"
        }

def run_stream(*args, **kwargs):
    """
    Streaming version of the agent
    """
    try:
        message = kwargs.get("message", "Hello from RunAgent!")
        temperature = kwargs.get("temperature", 0.7)
        model = kwargs.get("model", "gpt-3.5-turbo")
        
        # Check API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Mock streaming response
            mock_chunks = [
                "Mock", " streaming", " response", " to:", f" {message}"
            ]
            for i, chunk in enumerate(mock_chunks):
                yield {
                    "chunk_id": i + 1,
                    "content": chunk,
                    "type": "content",
                    "framework": "langchain",
                    "mock": True,
                    "timestamp": datetime.now().isoformat()
                }
            
            yield {
                "type": "complete",
                "total_chunks": len(mock_chunks),
                "framework": "langchain",
                "mock": True,
                "timestamp": datetime.now().isoformat()
            }
            return
        
        # Try real streaming
        try:
            from langchain_openai import ChatOpenAI
            from langchain.schema import HumanMessage
            
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=api_key,
                streaming=True
            )
            
            chunk_count = 0
            for chunk in llm.stream([HumanMessage(content=message)]):
                chunk_count += 1
                yield {
                    "chunk_id": chunk_count,
                    "content": chunk.content,
                    "type": "content",
                    "framework": "langchain",
                    "timestamp": datetime.now().isoformat()
                }
            
            yield {
                "type": "complete",
                "total_chunks": chunk_count,
                "framework": "langchain",
                "timestamp": datetime.now().isoformat()
            }
            
        except ImportError:
            # Mock streaming fallback
            mock_response = f"Mock streaming response to: {message}"
            words = mock_response.split()
            
            for i, word in enumerate(words):
                yield {
                    "chunk_id": i + 1,
                    "content": word + " ",
                    "type": "content",
                    "framework": "langchain",
                    "mock": True,
                    "timestamp": datetime.now().isoformat()
                }
            
            yield {
                "type": "complete",
                "total_chunks": len(words),
                "framework": "langchain",
                "mock": True,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        yield {
            "type": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }

def health_check():
    """Health check function"""
    return {
        "status": "healthy",
        "framework": "langchain",
        "agent_type": "test",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
            "python_version": os.sys.version,
        }
    }

if __name__ == "__main__":
    # Test the agent locally
    print("Testing LangChain agent locally...")
    
    # Test non-streaming
    result = run(message="Hello, this is a test message!")
    print("Non-streaming result:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*50 + "\n")
    
    # Test streaming
    print("Streaming result:")
    for chunk in run_stream(message="Tell me a short joke"):
        print(f"Chunk: {json.dumps(chunk, indent=2)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test health check
    health = health_check()
    print("Health check:")
    print(json.dumps(health, indent=2))