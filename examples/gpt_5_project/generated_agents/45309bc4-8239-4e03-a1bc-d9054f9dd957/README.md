# report_writer_agno

A report-writing assistant built with agno that generates structured reports from user inputs and provided data. It can create executive summaries, detailed sections, and recommendations based on the user's topic, scope, and source material.

## Framework
agno

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
title, topic, audience, scope, sources, format_style, length, deadline, include_summary, include_recommendations

## Entrypoints
main
