# Parlant RunAgent - Quick Start

A simple guide to run Parlant agents with RunAgent in under 2 minutes.

## Prerequisites

- Python 3.10+
- OpenAI API Key

## Setup & Run

### 1. Install Dependencies
```bash
pip install parlant runagent
```

### 2. Set OpenAI API Key
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### 3. Start Parlant Server (Terminal 1)
```bash
parlant-server run
```
*Keep this terminal running. Server will start at http://localhost:8800*

### 4. Start RunAgent (Terminal 2)
```bash
runagent serve /path/to/parlant/template
```
*This will create the agent with tools (calculator, time, weather) and start the RunAgent server*

### 5. Use with Any SDK

Go to the runagent templates https://github.com/runagent-dev/runagent/tree/main/templates to try

## Agent Capabilities

- **Current Time** - "What time is it?"
- **Calculator** - "Calculate 25 * 4 + 10"
- **Weather** - "What's the weather in Tokyo?"
- **General Chat** - Ask anything!

## Available Entrypoints

- `parlant_simple` - Non-streaming responses
- `parlant_stream` - Streaming responses

That's it! Your Parlant agent is now running and accessible from any RunAgent SDK.
## Support

For issues specific to this template:
- RunAgent GitHub Issues: https://github.com/runagent-dev/runagent/issues

For Parlant-specific questions:
- Parlant Discord: https://discord.gg/parlant  
- Parlant GitHub Issues: https://github.com/emcie-co/parlant/issues