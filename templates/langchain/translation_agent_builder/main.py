#!/usr/bin/env python3
"""
Simple LangChain Translation Agent
"""
import os
import json
import traceback
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

# Load environment variables
load_dotenv()

def translate_text(text, target_language):
    """
    Translate the given text to the specified target language.
    
    Parameters:
    - text: str - The text to translate
    - target_language: str - The language to translate the text into
    
    Returns:
    - dict: A dictionary containing the success status and the translated text or error message.
    """
    try:
        # Check if we have OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "OpenAI API key not found. Please set OPENAI_API_KEY in .env file",
                "timestamp": datetime.now().isoformat(),
                "framework": "langchain",
                "agent_type": "translation"
            }
        
        # Initialize LLM for translation
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,  # Set temperature to 0 for deterministic output
            api_key=api_key
        )
        
        # Create the prompt for translation
        prompt = f"Translate the following text to {target_language}: {text}"
        response = llm.invoke([HumanMessage(content=prompt)])
        
        return {
            "success": True,
            "translated_text": response.content,
            "input": {
                "text": text,
                "target_language": target_language
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "framework": "langchain",
                "agent_type": "translation",
                "response_length": len(response.content)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "input": {
                "text": text,
                "target_language": target_language
            },
            "timestamp": datetime.now().isoformat(),
            "framework": "langchain",
            "agent_type": "translation"
        }

def translate_text_stream(text, target_language):
    """
    Stream the translation of the given text to the specified target language.
    
    Parameters:
    - text: str - The text to translate
    - target_language: str - The language to translate the text into
    
    Yields:
    - dict: A dictionary containing the streaming translation chunks or error messages.
    """
    try:
        # Check if we have OpenAI API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            yield {
                "type": "error",
                "error": "OpenAI API key not found. Please set OPENAI_API_KEY in .env file",
                "timestamp": datetime.now().isoformat(),
                "framework": "langchain",
                "agent_type": "translation"
            }
            return
        
        # Initialize LLM for streaming translation
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            api_key=api_key,
            streaming=True
        )
        
        # Create the prompt for translation
        prompt = f"Translate the following text to {target_language}: {text}"
        
        chunk_count = 0
        for chunk in llm.stream([HumanMessage(content=prompt)]):
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
        
    except Exception as e:
        yield {
            "type": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }

def translate(text, target_language):
    """
    Entry point for translating text.
    
    Parameters:
    - text: str - The text to translate
    - target_language: str - The language to translate the text into
    
    Returns:
    - dict: The result of the translation.
    """
    return translate_text(text, target_language)

def translate_stream(text, target_language):
    """
    Entry point for streaming translation of text.
    
    Parameters:
    - text: str - The text to translate
    - target_language: str - The language to translate the text into
    
    Yields:
    - dict: Streaming translation results.
    """
    yield from translate_text_stream(text, target_language)

def health_check():
    """Health check function"""
    return {
        "status": "healthy",
        "framework": "langchain",
        "agent_type": "translation",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "openai_api_key_set": bool(os.getenv("OPENAI_API_KEY")),
            "python_version": os.sys.version,
        }
    }

if __name__ == "__main__":
    # Test the translation agent locally
    print("Testing LangChain translation agent locally...")
    
    # Test non-streaming translation
    result = translate("Hello, how are you?", "Spanish")
    print("Non-streaming translation result:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*50 + "\n")
    
    # Test streaming translation
    print("Streaming translation result:")
    for chunk in translate_stream("Tell me a short joke", "French"):
        print(f"Chunk: {json.dumps(chunk, indent=2)}")
    
    print("\n" + "="*50 + "\n")
    
    # Test health check
    health = health_check()
    print("Health check:")
    print(json.dumps(health, indent=2))