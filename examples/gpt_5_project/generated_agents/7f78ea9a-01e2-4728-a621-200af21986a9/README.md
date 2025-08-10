# research_write_assistant

A research writing agent that takes key research parameters and produces structured, citation-aware drafts and summaries. It supports outlining, literature sourcing, drafting sections, and generating reference lists based on provided depth and source constraints.

## Framework
langgraph

## Usage

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run with RunAgent
```bash
runagent serve .
```

### Test the agent
```bash
python3 agent_test.py <agent_id> localhost <port> "your test message"
```

## Input Fields
topic, depth, target_audience, sections, preferred_sources, citation_style, max_length, deadline

## Entrypoints
main, main_stream
