import os
from typing import Any, Dict
from dotenv import load_dotenv
from letta_client import CreateBlock, Letta
from code_review_tools import analyze_code_quality, detect_security_issues, suggest_improvements

# Load environment variables
load_dotenv()


def _extract_message_from_input(*input_args, **input_kwargs) -> str:
    """Extract message text from various input formats"""
    # Try direct message parameter
    if input_kwargs.get("message"):
        return str(input_kwargs["message"])
    
    # Try code parameter for code review
    if input_kwargs.get("code"):
        return str(input_kwargs["code"])
    
    # Try messages list format
    if input_kwargs.get("messages"):
        messages = input_kwargs["messages"]
        if isinstance(messages, list) and messages:
            last_message = messages[-1]
            if isinstance(last_message, dict) and "content" in last_message:
                return last_message["content"]
    
    # Try first positional argument as string
    if input_args and isinstance(input_args[0], str):
        return input_args[0]
    
    # Fallback
    return "No code provided for review"


def _register_tools(client: Letta) -> Dict[str, str]:
    """Register code review tools with Letta client"""
    tool_fns = [
        analyze_code_quality,
        detect_security_issues,
        suggest_improvements,
    ]

    tool_map: Dict[str, str] = {}
    registration_success = True

    for fn in tool_fns:
        try:
            print(f"  📝 Registering {fn.__name__}...")
            tool = client.tools.upsert_from_function(func=fn)
            tool_map[tool.name] = tool.id
            print(f"  ✅ Successfully registered: {tool.name} -> {tool.id}")
        except Exception as e:
            print(f"  ❌ Failed to register tool {fn.__name__}: {e}")
            registration_success = False

    if not registration_success:
        print("❌ Tool registration failed. Check the errors above.")
        
    return tool_map


def letta_run(*input_args, **input_kwargs):
    """Smart Code Reviewer Agent using Letta with specialized tools"""
    try:
        # Initialize Letta client
        letta_url = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
        client = Letta(base_url=letta_url)
        
        # Register code review tools
        print("🔧 Registering code review tools...")
        tool_map = _register_tools(client)
        
        # Create memory blocks specialized for code review
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are reviewing code for a developer using RunAgent framework. Be thorough but constructive.",
            ),
            CreateBlock(
                label="persona",
                value="You are a senior software engineer and code reviewer with expertise in multiple programming languages, security best practices, and performance optimization. You provide detailed, actionable feedback.",
            ),
        ]

        # Create agent with code review specialization
        agent = client.agents.create(
            name=f"runagent-code-reviewer-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="""You are an expert code reviewer with access to powerful analysis tools:

1. **analyze_code_quality** - Analyzes code for readability, maintainability, and best practices
2. **detect_security_issues** - Scans code for potential security vulnerabilities  
3. **suggest_improvements** - Provides specific improvement recommendations

When reviewing code:
- Always use the appropriate tools to analyze the provided code
- Provide specific, actionable feedback
- Highlight both strengths and areas for improvement
- Consider security, performance, and maintainability
- Be constructive and educational in your feedback

If no code is provided, ask the user to share the code they'd like reviewed.""",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            tool_ids=list(tool_map.values()),
            include_base_tools=True
        )

        print(f"✅ Code Reviewer agent created with ID: {agent.id}")
        print(f"🛠️ Agent has {len(tool_map)} specialized code review tools")
        
        # Extract code/message from input
        message = _extract_message_from_input(*input_args, **input_kwargs)
        
        # Send message to Letta agent
        response = client.agents.messages.create(
            agent_id=agent.id,
            messages=[{
                "role": "user",
                "content": message
            }]
        )
        
        return response
        
    except Exception as e:
        return f"Code review error: {str(e)}"


def letta_run_stream(*input_args, **input_kwargs):
    """Streaming version of the code reviewer agent"""
    try:
        # Initialize Letta client
        letta_url = os.getenv("LETTA_SERVER_URL", "http://localhost:8283")
        client = Letta(base_url=letta_url)
        
        # Register tools
        print("🔧 Registering tools for streaming code review...")
        tool_map = _register_tools(client)
        
        # Create memory blocks
        memory_blocks = [
            CreateBlock(
                label="human",
                value="You are reviewing code for a developer using RunAgent framework. Provide streaming feedback.",
            ),
            CreateBlock(
                label="persona",
                value="You are a senior software engineer providing real-time code review feedback with expertise in security, performance, and best practices.",
            ),
        ]

        # Create streaming agent
        agent = client.agents.create(
            name=f"runagent-code-reviewer-stream-{os.getpid()}",
            memory_blocks=memory_blocks,
            system="""You are an expert code reviewer with streaming capabilities. Use your analysis tools and provide real-time feedback on code quality, security, and improvements. Be thorough but concise in your streaming responses.""",
            model="openai/gpt-4o-mini",
            embedding="openai/text-embedding-ada-002",
            tool_ids=list(tool_map.values()),
            include_base_tools=True
        )

        print(f"✅ Streaming code reviewer created with ID: {agent.id}")
        
        # Extract message from input
        message = _extract_message_from_input(*input_args, **input_kwargs)
        
        # Create streaming response
        stream = client.agents.messages.create_stream(
            agent_id=agent.id,
            messages=[{
                "role": "user",
                "content": message
            }],
            # stream_tokens=True,
        )
        
        # Yield chunks
        for chunk in stream:
            print(chunk)
            yield chunk
            
    except Exception as e:
        yield f"Streaming code review error: {str(e)}"