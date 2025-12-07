import os
import sqlite3
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver

# Persistent storage directory - RunAgent maps this to /persistent/{folder_name}
STORAGE_DIR = "chat_storage"


class ChatState(TypedDict):
    """State schema for the chat agent."""
    messages: Annotated[list, add_messages]


def get_sqlite_checkpointer(user_id: str) -> SqliteSaver:
    """
    Create a SQLite checkpointer for the given user.
    Each user gets their own database file for conversation persistence.
    
    Args:
        user_id: Unique user identifier
    
    Returns:
        SqliteSaver instance connected to user's database
    """
    # Ensure storage directory exists
    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    # Create user-specific database file
    # db_path = os.path.join(STORAGE_DIR, f"{user_id}_conversations.db")
    db_path = os.path.join(STORAGE_DIR, "conversations.db")
    
    # Create connection with thread safety disabled (required for LangGraph)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    # Create and return checkpointer
    return SqliteSaver(conn)


def create_chat_graph(user_id: str) -> StateGraph:
    """
    Create a compiled chat graph with persistent memory for a user.
    
    Args:
        user_id: Unique user identifier
    
    Returns:
        Compiled StateGraph with SQLite persistence
    """
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    # Define the chat node
    def chat_node(state: ChatState) -> ChatState:
        """Process user message and generate AI response."""
        # Add system message if this is the first message
        messages = state["messages"]
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            system_msg = SystemMessage(
                content=(
                    "You are a helpful AI assistant. "
                    "You have access to conversation history and should use it to provide contextual responses. "
                    "Be friendly, concise, and helpful."
                )
            )
            messages = [system_msg] + messages
        
        # Get AI response
        response = llm.invoke(messages)
        
        # Return updated state with AI message
        return {"messages": [response]}
    
    # Build the graph
    graph_builder = StateGraph(ChatState)
    graph_builder.add_node("chat", chat_node)
    graph_builder.add_edge(START, "chat")
    graph_builder.add_edge("chat", END)
    
    # Compile with SQLite persistence
    checkpointer = get_sqlite_checkpointer(user_id)
    graph = graph_builder.compile(checkpointer=checkpointer)
    
    return graph


def chat_response(
    message: str = None,
    user_id: str = "default_user",
    thread_id: str = "default_thread",
    **kwargs
) -> dict:
    """
    Non-streaming chat response with persistent memory.
    
    Args:
        message: User's input message
        user_id: Unique user identifier (used for separate DB per user)
        thread_id: Conversation thread ID (allows multiple conversations per user)
        **kwargs: Additional parameters
    
    Returns:
        Dictionary with response content and metadata
    """
    # Handle message from kwargs if not provided
    if message is None:
        message = kwargs.get('prompt', kwargs.get('query', ''))
    
    if not message:
        return {
            "status": "error",
            "message": "No input message provided",
            "user_id": user_id,
            "thread_id": thread_id
        }
    
    try:
        # Create graph with user-specific persistence
        graph = create_chat_graph(user_id)
        
        # Configuration for this conversation thread
        config = {"configurable": {"thread_id": thread_id}}
        
        # Prepare input state
        input_state = {"messages": [HumanMessage(content=message)]}
        
        # Invoke the graph
        result = graph.invoke(input_state, config=config)
        
        # Extract AI response
        ai_message = result["messages"][-1]
        response_content = ai_message.content if hasattr(ai_message, 'content') else str(ai_message)
        
        return {
            "status": "success",
            "response": response_content,
            "user_id": user_id,
            "thread_id": thread_id,
            "message_count": len(result["messages"])
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id,
            "thread_id": thread_id
        }


def chat_response_stream(
    message: str = None,
    user_id: str = "default_user",
    thread_id: str = "default_thread",
    **kwargs
):
    """
    Streaming chat response with persistent memory.
    Uses LangGraph's native stream_mode="messages" to stream LLM tokens.
    
    Args:
        message: User's input message
        user_id: Unique user identifier (used for separate DB per user)
        thread_id: Conversation thread ID (allows multiple conversations per user)
        **kwargs: Additional parameters
    
    Yields:
        Dictionary chunks with streaming content and metadata
    """
    # Handle message from kwargs if not provided
    if message is None:
        message = kwargs.get('prompt', kwargs.get('query', ''))
    
    if not message:
        yield {
            "type": "error",
            "message": "No input message provided",
            "user_id": user_id,
            "thread_id": thread_id
        }
        return
    
    try:
        # Create graph with user-specific persistence
        graph = create_chat_graph(user_id)
        
        # Configuration for this conversation thread
        config = {"configurable": {"thread_id": thread_id}}
        
        # Prepare input state
        input_state = {"messages": [HumanMessage(content=message)]}
        
        # Yield session info first
        yield {
            "type": "session_info",
            "user_id": user_id,
            "thread_id": thread_id
        }
        
        # Use LangGraph's native streaming with stream_mode="messages"
        # This streams LLM tokens directly from the graph execution
        # The stream returns tuples of (message_chunk, metadata)
        for message_chunk, metadata in graph.stream(
            input_state,
            config=config,
            stream_mode="messages"  # Stream LLM tokens token-by-token
        ):
            # message_chunk is the token streamed by the LLM
            # Only yield AI message chunks (not system or human messages)
            if hasattr(message_chunk, 'content') and message_chunk.content:
                # Filter to only stream from the chat node
                if metadata.get("langgraph_node") == "chat":
                    yield {
                        "type": "content",
                        "content": message_chunk.content
                    }
        
        # Yield completion info
        yield {
            "type": "complete",
            "user_id": user_id,
            "thread_id": thread_id
        }
    
    except Exception as e:
        yield {
            "type": "error",
            "message": str(e),
            "user_id": user_id,
            "thread_id": thread_id
        }


def get_conversation_history(
    user_id: str = "default_user",
    thread_id: str = "default_thread",
    **kwargs
) -> dict:
    """
    Retrieve conversation history for a specific thread.
    
    Args:
        user_id: Unique user identifier
        thread_id: Conversation thread ID
        **kwargs: Additional parameters
    
    Returns:
        Dictionary with conversation history
    """
    try:
        # Create graph to access checkpointer
        graph = create_chat_graph(user_id)
        
        # Configuration for this conversation thread
        config = {"configurable": {"thread_id": thread_id}}
        
        # Get state snapshot
        state = graph.get_state(config)
        
        if state and state.values and "messages" in state.values:
            messages = state.values["messages"]
            
            # Format messages for response
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    formatted_messages.append({
                        "role": "user",
                        "content": msg.content
                    })
                elif isinstance(msg, AIMessage):
                    formatted_messages.append({
                        "role": "assistant",
                        "content": msg.content
                    })
                elif isinstance(msg, SystemMessage):
                    formatted_messages.append({
                        "role": "system",
                        "content": msg.content
                    })
            
            return {
                "status": "success",
                "user_id": user_id,
                "thread_id": thread_id,
                "messages": formatted_messages,
                "message_count": len(formatted_messages)
            }
        else:
            return {
                "status": "success",
                "user_id": user_id,
                "thread_id": thread_id,
                "messages": [],
                "message_count": 0,
                "info": "No conversation history found for this thread"
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id,
            "thread_id": thread_id
        }


def list_user_threads(
    user_id: str = "default_user",
    **kwargs
) -> dict:
    """
    List all conversation threads for a user.
    
    Args:
        user_id: Unique user identifier
        **kwargs: Additional parameters
    
    Returns:
        Dictionary with list of thread IDs
    """
    try:
        # db_path = os.path.join(STORAGE_DIR, f"{user_id}_conversations.db")
        db_path = os.path.join(STORAGE_DIR, "conversations.db")
        
        if not os.path.exists(db_path):
            return {
                "status": "success",
                "user_id": user_id,
                "threads": [],
                "thread_count": 0,
                "info": "No conversations found for this user"
            }
        
        # Connect to user's database
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        # Query distinct thread IDs
        cursor.execute("""
            SELECT DISTINCT json_extract(config, '$.configurable.thread_id') as thread_id
            FROM checkpoints
            WHERE thread_id IS NOT NULL
            ORDER BY checkpoint_id DESC
        """)
        
        threads = [row[0] for row in cursor.fetchall() if row[0]]
        conn.close()
        
        return {
            "status": "success",
            "user_id": user_id,
            "threads": threads,
            "thread_count": len(threads)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id
        }