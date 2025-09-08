# Parlant Agent Template

This template demonstrates how to build AI agents using [Parlant](https://parlant.io), a conversation modeling framework that ensures reliable, guideline-driven agent behavior.

## Overview

Parlant is designed for building production-ready conversational AI agents that follow your specific business rules and guidelines. Unlike traditional prompt engineering, Parlant uses structured guidelines, tools, and journeys to ensure consistent agent behavior.

## Key Features

- **🎯 Guideline-driven behavior**: Define clear rules for how your agent should respond
- **🔧 Tool integration**: Connect external APIs and services seamlessly
- **🧭 Conversational journeys**: Guide users through multi-step interactions
- **🌊 Streaming support**: Real-time response streaming

## Prerequisites

Before running this agent, make sure you have:

1. **OpenAI API Key**: Parlant uses OpenAI as the default LLM provider
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

2. **Python 3.10+**: Parlant requires Python 3.10 or later

## Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up your environment variables:
   ```bash
   # Required
   export OPENAI_API_KEY="your-openai-api-key"
   
   # Optional
   export PARLANT_LOG_LEVEL="INFO"
   ```

## Agent Architecture

This template includes several entrypoints that demonstrate different Parlant capabilities:

### Available Entrypoints

1. **`parlant_simple`** - Basic chat interaction
   - Input: `message` (string)
   - Output: Structured response with content and metadata

2. **`parlant_stream`** - Streaming responses
   - Input: `message` (string)
   - Output: Stream of response chunks


### Built-in Tools

The agent comes with several pre-configured tools:

- **`get_current_time`**: Returns the current date and time
- **`weather_info`**: Provides weather information for cities (mock implementation)

### Guidelines

The agent is configured with behavioral guidelines:

- **Weather queries**: Uses weather tool and provides helpful suggestions
- **Time queries**: Returns current time in a friendly manner  
- **Greetings**: Responds warmly and asks how to help
- **Help requests**: Provides suggestions of available capabilities
- **Farewells**: Polite responses and invitation for future questions

## Usage Examples

### Basic Chat
```python
# Using RunAgent CLI
runagent run your-agent-id parlant_simple message="What's the weather like in Paris?"
```

### Streaming Chat
```python
# The parlant_stream entrypoint will stream responses in real-time
runagent run your-agent-id parlant_stream message="Tell me a story about AI"
```

### Custom Guidelines
```python
# Define custom behavior
guidelines = [
    {
        "condition": "User asks about pricing",
        "action": "Politely explain that pricing information is available on our website"
    }
]
runagent run your-agent-id parlant_custom message="How much does this cost?" guidelines=guidelines
```

## Customization

### Adding New Tools

1. Define your tool using the `@p.tool` decorator:
   ```python
   @p.tool
   async def your_custom_tool(context: p.ToolContext, param: str) -> p.ToolResult:
       # Your tool logic here
       return p.ToolResult("Tool response")
   ```

2. Add the tool to your agent's guidelines:
   ```python
   await agent.create_guideline(
       condition="When user needs custom functionality",
       action="Use the custom tool to help them",
       tools=[your_custom_tool]
   )
   ```

### Adding New Guidelines

Guidelines define how your agent should behave in specific situations:

```python
await agent.create_guideline(
    condition="User asks about company policies",
    action="Provide accurate policy information and direct them to HR if needed",
    tools=[policy_lookup_tool]  # Optional
)
```

### Environment Variables

- `OPENAI_API_KEY`: Required for LLM functionality
- `PARLANT_LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `ANTHROPIC_API_KEY`: Alternative LLM provider (if using Anthropic)

## Production Considerations

### Guidelines Best Practices

1. **Be specific**: Clear conditions lead to reliable behavior
2. **Test thoroughly**: Use Parlant's built-in testing tools
3. **Monitor guidelines**: Track which guidelines are applied
4. **Iterative improvement**: Refine based on real conversations





## Learn More

- **Parlant Documentation**: https://parlant.io/docs
- **Parlant GitHub**: https://github.com/emcie-co/parlant
- **RunAgent Documentation**: https://docs.run-agent.ai
- **Examples**: Check the `examples/` directory for more complex use cases

## Support

For issues specific to this template:
- RunAgent GitHub Issues: https://github.com/runagent-dev/runagent/issues

For Parlant-specific questions:
- Parlant Discord: https://discord.gg/parlant  
- Parlant GitHub Issues: https://github.com/emcie-co/parlant/issues