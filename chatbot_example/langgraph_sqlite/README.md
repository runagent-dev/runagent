# LangGraph SQLite Chatbot

A production-ready chatbot example built with LangGraph and SQLite persistence, demonstrating multi-user, multi-thread conversation management with streaming support.

## Overview

This example implements a persistent chatbot using:
- **LangGraph** for agent orchestration
- **SQLite** for conversation persistence
- **LangChain OpenAI** for LLM integration
- **RunAgent** for deployment and management

The chatbot supports multiple users, conversation threads, and real-time streaming responses.

## Features

### ✅ Core Capabilities

- **Persistent Memory**: Conversations are stored in SQLite databases and persist across sessions
- **Multi-User Support**: Each user gets isolated conversation storage
- **Multi-Thread Conversations**: Users can maintain multiple independent conversation threads
- **Streaming Responses**: Real-time token-by-token streaming using LangGraph's native `stream_mode="messages"`
- **Conversation History**: Retrieve full conversation history for any thread
- **Thread Management**: List all conversation threads for a user

### 🎯 Entrypoints

The agent exposes 4 entrypoints:

1. **`chat`** - Non-streaming chat with persistent memory
2. **`chat_stream`** - Streaming chat with real-time token output
3. **`get_history`** - Retrieve conversation history for a thread
4. **`list_threads`** - List all conversation threads for a user

## Architecture

### State Management

```python
class ChatState(TypedDict):
    """State schema for the chat agent."""
    messages: Annotated[list, add_messages]
```

The graph uses LangGraph's `add_messages` reducer to automatically manage message history.

### Persistence

- **Storage Location**: `chat_storage/` directory (mapped to `/persistent/chat_storage` by RunAgent)
- **Database**: SQLite database (`conversations.db`)
- **Checkpointing**: Uses LangGraph's `SqliteSaver` for state persistence
- **Thread Isolation**: Each `thread_id` maintains separate conversation state

### Graph Structure

```
START → chat_node → END
```

The graph is simple but powerful:
- Receives user message
- Adds system message if needed
- Invokes LLM with full conversation history
- Returns AI response
- Automatically persists state via checkpointer

## Setup

### Prerequisites

- Python 3.8+
- OpenAI API key
- RunAgent CLI installed

### Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

3. **Deploy with RunAgent**:
   ```bash
   runagent deploy
   ```

## Usage

### Python SDK

```python
from runagent import RunAgentClient

# Initialize client
client = RunAgentClient(
    agent_id="your-agent-id",
    entrypoint_tag="chat",
    local=False,
    user_id="user123",
    persistent_memory=True
)

# Non-streaming chat
result = client.run(
    message="Hello, how are you?",
    user_id="user123",
    thread_id="conversation_001"
)
print(result['response'])

# Streaming chat
stream_client = RunAgentClient(
    agent_id="your-agent-id",
    entrypoint_tag="chat_stream",
    local=False,
    user_id="user123",
    persistent_memory=True
)

for chunk in stream_client.run(
    message="Tell me a story",
    user_id="user123",
    thread_id="conversation_001"
):
    if chunk.get('type') == 'content':
        print(chunk['content'], end='', flush=True)
```

### Rust SDK

```rust
use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

let client = RunAgentClient::new(RunAgentClientConfig {
    agent_id: "your-agent-id".to_string(),
    entrypoint_tag: "chat".to_string(),
    local: Some(false),
    user_id: Some("user123".to_string()),
    persistent_memory: Some(true),
    ..RunAgentClientConfig::default()
}).await?;

let result = client.run(&[
    ("message", json!("Hello, how are you?")),
    ("user_id", json!("user123")),
    ("thread_id", json!("conversation_001")),
]).await?;
```

## Entrypoint Details

### 1. `chat` - Non-Streaming Chat

**Function**: `chat_response()`

**Parameters**:
- `message` (str): User's input message
- `user_id` (str): Unique user identifier
- `thread_id` (str): Conversation thread ID

**Returns**:
```json
{
    "status": "success",
    "response": "AI response text",
    "user_id": "user123",
    "thread_id": "conversation_001",
    "message_count": 5
}
```

### 2. `chat_stream` - Streaming Chat

**Function**: `chat_response_stream()`

**Parameters**: Same as `chat`

**Yields**: Dictionary chunks with:
- `type: "session_info"` - Initial session metadata
- `type: "content"` - Token chunks from LLM
- `type: "complete"` - Completion metadata
- `type: "error"` - Error information

**Example**:
```python
for chunk in stream_client.run(...):
    if chunk.get('type') == 'content':
        print(chunk['content'], end='', flush=True)
```

### 3. `get_history` - Conversation History

**Function**: `get_conversation_history()`

**Parameters**:
- `user_id` (str): User identifier
- `thread_id` (str): Thread identifier

**Returns**:
```json
{
    "status": "success",
    "user_id": "user123",
    "thread_id": "conversation_001",
    "messages": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ],
    "message_count": 2
}
```

### 4. `list_threads` - List Threads

**Function**: `list_user_threads()`

**Parameters**:
- `user_id` (str): User identifier

**Returns**:
```json
{
    "status": "success",
    "user_id": "user123",
    "threads": ["conversation_001", "conversation_002"],
    "thread_count": 2
}
```

## Testing

### Python Tests

Run the Python test suite:
```bash
cd test_scripts/python
python client_test_langgraph_sqlite.py
```

### Rust Tests

Run the Rust test suite:
```bash
cd test_scripts/rust/test_langgraph_sqlite
cargo run
```

## Configuration

### `runagent.config.json`

Key configuration options:

- **`persistent_folders`**: `["chat_storage"]` - Folders to persist across deployments
- **`entrypoints`**: Defines the 4 entrypoints (chat, chat_stream, get_history, list_threads)
- **`agent_id`**: Unique identifier for the deployed agent

### Environment Variables

- `OPENAI_API_KEY`: Required for LLM access
- `RUNAGENT_API_KEY`: Required for remote deployment (optional for local)

## Streaming Implementation

The streaming implementation uses LangGraph's native `stream_mode="messages"`:

```python
for message_chunk, metadata in graph.stream(
    input_state,
    config=config,
    stream_mode="messages"  # Stream LLM tokens token-by-token
):
    if metadata.get("langgraph_node") == "chat":
        yield {"type": "content", "content": message_chunk.content}
```

This provides true token-by-token streaming directly from the LLM, even when using `.invoke()` in the graph node.

## Multi-User & Multi-Thread Support

### User Isolation

Each `user_id` maintains separate conversation storage. Users cannot access each other's conversations.

### Thread Isolation

Within a user, different `thread_id` values create separate conversation contexts:

```python
# Thread 1: Personal
client.run(message="I'm planning a vacation", thread_id="personal")

# Thread 2: Work
client.run(message="I need to debug code", thread_id="work")

# Back to Thread 1 - remembers vacation
client.run(message="Where was I going?", thread_id="personal")
```

## Persistence Details

- **Storage**: SQLite database in `chat_storage/conversations.db`
- **Checkpointing**: LangGraph's `SqliteSaver` handles state persistence
- **Thread Safety**: Database connection uses `check_same_thread=False` for LangGraph compatibility
- **Persistence**: Data persists across:
  - Agent restarts
  - Client reconnections
  - Server deployments (when using persistent storage)

## Example Use Cases

1. **Customer Support Chatbot**: Multi-user support with conversation history
2. **Personal Assistant**: Multiple conversation threads (work, personal, etc.)
3. **Educational Tutor**: Persistent learning sessions per student
4. **Multi-Tenant SaaS**: Isolated conversations per tenant/user

## Troubleshooting

### Streaming Not Working

- Ensure entrypoint tag ends with `_stream` for streaming entrypoints
- Check that `stream_mode="messages"` is used in the graph
- Verify WebSocket connection is established

### Persistence Issues

- Check `chat_storage/` directory exists and is writable
- Verify `persistent_folders` in `runagent.config.json`
- Ensure `user_id` and `thread_id` are consistent across calls

### Memory Issues

- SQLite databases grow with conversation history
- Consider implementing conversation pruning for old threads
- Monitor database size in `chat_storage/`

## Dependencies

- `langchain`: Core LangChain framework
- `langchain-openai`: OpenAI integration
- `langgraph`: Graph-based agent orchestration
- `langgraph-checkpoint-sqlite`: SQLite persistence
- `openai`: OpenAI API client

## License

Part of the RunAgent examples collection.

## Contributing

This is an example implementation. For improvements or issues, please refer to the main RunAgent repository.

