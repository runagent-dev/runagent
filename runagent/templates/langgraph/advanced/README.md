# runagent/templates/langgraph/advanced/README.md
# RunAgent - Advanced LangGraph Template

This is an advanced LangGraph agent template that uses an LLM to generate responses and maintains conversation history.

## Structure

- `agent.py`: Contains the agent implementation with LLM integration
- `requirements.txt`: Contains the required dependencies

## Setup

1. Set the OpenAI API key in your environment:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

2. Deploy the agent using the RunAgent CLI:
   ```bash
   runagent deploy .
   ```

## Agent Function

The agent exposes a `run` function that accepts a dictionary with input data and returns a dictionary with the output.

Input format:
```json
{
  "query": "Your query here",
  "messages": [
    {"role": "human", "content": "Previous message"},
    {"role": "ai", "content": "Previous response"}
  ]
}
```

Output format:
```json
{
  "input": "Your query here",
  "messages": [
    {"role": "human", "content": "Previous message"},
    {"role": "ai", "content": "Previous response"},
    {"role": "human", "content": "Your query here"},
    {"role": "ai", "content": "New response"}
  ],
  "output": "New response"
}
```

## Customization

You can extend this template by:

1. Changing the LLM model or provider
2. Adding more complex conversation flows
3. Integrating tools and external API calls

See the LangChain and LangGraph documentation for more details.