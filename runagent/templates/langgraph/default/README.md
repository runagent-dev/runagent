# runagent/templates/langgraph/default/README.md
# RunAgent - Default LangGraph Template

This is a simple LangGraph agent template that processes input and generates a response.

## Structure

- `agent.py`: Contains the agent implementation
- `requirements.txt`: Contains the required dependencies

## How to Use

1. Modify the `generate_response` function to implement your agent's logic
2. Add any additional dependencies to `requirements.txt`
3. Deploy the agent using the RunAgent CLI:

```bash
runagent deploy .
```

## Agent Function

The agent exposes a `run` function that accepts a dictionary with input data and returns a dictionary with the output.

Input format:
```json
{
  "query": "Your query here"
}
```

Output format:
```json
{
  "input": "Your query here",
  "steps": ["Step 1", "Step 2"],
  "output": "Response to your query"
}
```

## Customization

You can extend this template by:

1. Adding more nodes to the graph
2. Integrating with LLMs
3. Adding tools and external API calls

See the LangGraph documentation for more details: https://langchain-ai.github.io/langgraph/
