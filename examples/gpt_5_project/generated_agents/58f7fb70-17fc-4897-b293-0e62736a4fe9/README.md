# research_writing_agent

A research writing agent that conducts literature discovery, summarizes findings, and drafts structured research sections (e.g., background, methods, results, discussion). It can query specified sources, synthesize evidence, and produce well-cited, publication-ready prose with configurable depth and format.

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
topic, research_question, depth, sources, citation_style, sections, audience, max_words, include_abstract, deadline

## Entrypoints
main, main_stream
