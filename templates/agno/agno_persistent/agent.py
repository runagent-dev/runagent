from textwrap import dedent
from typing import List, Optional
from agno.agent import Agent
from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from agno.session import AgentSession

# Single SQLite DB for all agents/sessions
# Note: The backend automatically maps "rad" folder to /persistent/rad
# So we can use relative path "rad/agents.db" and it will persist across VM restarts
db = SqliteDb(db_file="simi/agents.db")


def get_chat_agent(
    user: str = "user",
    new_session: bool = True,
    session_id: Optional[str] = None,
) -> Agent:
    """
    Create and return a simple persistent chatbot Agent.
    
    Args:
        user: User ID to associate with the agent.
        new_session: If False, will try to resume the latest existing session
                     for this user (unless session_id is provided).
        session_id: If provided and new_session=False, use this specific session.
    
    Returns:
        An initialized Agent instance.
    """
    resolved_session_id: Optional[str] = None
    
    if not new_session:
        # If caller gave a specific session_id, use it
        if session_id is not None:
            resolved_session_id = session_id
        else:
            # Otherwise, try to resume the latest existing session for this user
            existing_sessions: List[AgentSession] = db.get_sessions(  # type: ignore
                user_id=user,
                session_type=SessionType.AGENT,
            )
            if len(existing_sessions) > 0:
                resolved_session_id = existing_sessions[0].session_id
    
    agent = Agent(
        user_id=user,
        session_id=resolved_session_id,
        model=OpenAIChat(id="gpt-4o-mini"),
        instructions=dedent(
            """\
            You are a helpful, general-purpose AI assistant.
            
            Goals:
            - Answer questions clearly and concisely.
            - Ask for clarification when needed.
            - Use a friendly, professional tone.
            
            You have access to the conversation history via the session.
            Use that context to keep multi-turn conversations coherent.
            """
        ),
        db=db,
        # Persist and reuse chat history across runs for this session
        read_chat_history=True,
        markdown=True,
    )
    
    return agent


def agent_print_response(prompt: str = None, user: str = "user", session_id: Optional[str] = None, new_session: bool = False, **kwargs):
    """
    Non-streaming response with session management.
    
    Args:
        prompt: User's message/prompt (can also be passed as 'message' in kwargs)
        user: User ID for session management (default: "user")
        session_id: Optional specific session ID to resume (default: None, will auto-resume latest)
        new_session: If True, creates a new session. If False, resumes existing session (default: False)
        **kwargs: Additional parameters (supports 'message' as alias for 'prompt')
    
    Returns:
        Serializable response content with session metadata
    """
    # Handle prompt from kwargs if not provided directly
    if prompt is None:
        prompt = kwargs.get('message', '')
    
    agent = get_chat_agent(user=user, new_session=new_session, session_id=session_id)
    
    # Get the response object
    response = agent.run(prompt)
    
    # Extract the actual content from the response object
    if hasattr(response, 'content'):
        return {
            "content": response.content,
            "session_id": agent.session_id,
            "user_id": agent.user_id
        }
    elif hasattr(response, 'messages') and response.messages:
        # Get the last message content
        content = response.messages[-1].content if hasattr(response.messages[-1], 'content') else str(response.messages[-1])
        return {
            "content": content,
            "session_id": agent.session_id,
            "user_id": agent.user_id
        }
    elif hasattr(response, 'text'):
        return {
            "content": response.text,
            "session_id": agent.session_id,
            "user_id": agent.user_id
        }
    else:
        # Fallback: convert to string
        return {
            "content": str(response),
            "session_id": agent.session_id,
            "user_id": agent.user_id
        }


def agent_print_response_stream(prompt: str = None, user: str = "user", session_id: Optional[str] = None, new_session: bool = False, **kwargs):
    """
    Streaming response with session management.
    
    Args:
        prompt: User's message/prompt (can also be passed as 'message' in kwargs)
        user: User ID for session management (default: "user")
        session_id: Optional specific session ID to resume (default: None, will auto-resume latest)
        new_session: If True, creates a new session. If False, resumes existing session (default: False)
        **kwargs: Additional parameters (supports 'message' as alias for 'prompt')
    
    Yields:
        Serializable chunks with content and session metadata
    """
    # Handle prompt from kwargs if not provided directly
    if prompt is None:
        prompt = kwargs.get('message', '')
    
    agent = get_chat_agent(user=user, new_session=new_session, session_id=session_id)
    
    # Yield session info first
    yield {
        "type": "session_info",
        "session_id": agent.session_id,
        "user_id": agent.user_id
    }
    
    # Stream the response
    for chunk in agent.run(prompt, stream=True):
        yield {
            "type": "content",
            "content": chunk.content if hasattr(chunk, 'content') else str(chunk)
        }
    
    # Yield final session confirmation
    yield {
        "type": "session_end",
        "session_id": agent.session_id
    }


