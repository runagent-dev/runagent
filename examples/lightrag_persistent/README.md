# LightRAG RunAgent Integration

A RunAgent-compatible implementation of LightRAG for document ingestion and intelligent querying.

## Features

- **Document Ingestion**: Ingest text documents into a persistent RAG system
- **Intelligent Querying**: Query documents using multiple search modes (naive, local, global, hybrid)
- **Persistent Storage**: Data persists across VM restarts using RunAgent's persistent folders
- **Dual Entrypoints**: Separate functions for ingesting and querying

## File Structure

```
lightrag_agent/
├── agent.py                 # Main agent implementation
├── requirements.txt         # Python dependencies
├── runagent.config.json    # RunAgent configuration
├── test_sdk.py             # SDK test script
└── README.md               # This file
```

## Setup

1. Deploy the agent using RunAgent CLI:
```bash
runagent deploy
```

2. Note the `agent_id` from the deployment output

3. Update `test_sdk.py` with your `agent_id`:
```python
AGENT_ID = "your-agent-id-here"
```

## Usage

### Ingest Text from File

```python
from runagent import RunAgentClient

ingest_client = RunAgentClient(
    agent_id="your-agent-id",
    entrypoint_tag="ingest_text",
    local=False,
    user_id="your_user_id",
    persistent_memory=True
)

# Ingest from file
with open("document.txt", 'r') as f:
    text = f.read()

result = ingest_client.run(text=text)
print(result)
```

### Query the RAG System

```python
from runagent import RunAgentClient

query_client = RunAgentClient(
    agent_id="your-agent-id",
    entrypoint_tag="query_rag",
    local=False,
    user_id="your_user_id",
    persistent_memory=True
)

# Query with hybrid mode (default)
result = query_client.run(
    query="What are the main themes?",
    mode="hybrid"  # Options: "naive", "local", "global", "hybrid"
)

print(result['result'])
```

## Query Modes

- **naive**: Simple text matching
- **local**: Context-aware local search
- **global**: Broad semantic search
- **hybrid**: Combines local and global for best results (recommended)

## Testing

Run the included test script:

```bash
python test_sdk.py
```

This will:
1. Ingest sample text about LightRAG
2. Run multiple queries with different modes
3. Display results for each query

## Environment Variables

Required environment variables (set in your RunAgent environment):
- `OPENAI_API_KEY`: Your OpenAI API key

## Persistent Storage

The RAG database is stored in `rad/rag_storage/` which persists across VM restarts thanks to RunAgent's persistent folders configuration.

## API Reference

### ingest_text(text, **kwargs)

Ingest text into the RAG system.

**Parameters:**
- `text` (str): Text content to ingest
- `**kwargs`: Additional parameters

**Returns:**
```python
{
    "status": "success",
    "message": "Successfully ingested X characters",
    "working_dir": "rad/rag_storage"
}
```

### query_rag(query, mode="hybrid", **kwargs)

Query the RAG system.

**Parameters:**
- `query` (str): Question or search query
- `mode` (str): Search mode ("naive", "local", "global", "hybrid")
- `**kwargs`: Additional parameters

**Returns:**
```python
{
    "status": "success",
    "query": "Your question",
    "mode": "hybrid",
    "result": "Answer from RAG system",
    "working_dir": "rag_storage"
}
```