# RunAgent Installation and Usage Guide

This guide walks you through installing and using the RunAgent package, including the CLI tool, SDK, and templates.

## Installation

### 1. Install from PyPI

```bash
pip install runagent
```

### 2. Install from GitHub (for latest development version)

```bash
pip install git+https://github.com/yourusername/runagent.git
```

### 3. Install for Development

```bash
git clone https://github.com/yourusername/runagent.git
cd runagent
pip install -e ".[dev]"
```

## Configuration

Before using RunAgent, configure your API key:

```bash
# Set via environment variable
export RUNAGENT_API_KEY=your_api_key_here

# Or configure via CLI
runagent configure --api-key your_api_key_here
```

You can also set a custom API base URL if needed:

```bash
runagent configure --base-url https://your-custom-api.example.com
```

## CLI Usage

### Initialize a New Agent Project

```bash
# Create a new project with the default LangGraph template
runagent init my-agent

# Specify a different framework or template
runagent init my-agent --platform langgraph --template advanced
```

This will create a directory with the template files that you can customize:

```
my-agent/
├── agent.py           # Main agent code
├── requirements.txt   # Dependencies
└── README.md          # Documentation
```

### Deploy an Agent

Once you've customized your agent code, deploy it to the RunAgent platform:

```bash
# Navigate to your agent directory
cd my-agent

# Deploy the agent
runagent deploy .

# Specify the agent framework if needed
runagent deploy . --type langgraph
```

The deployment command will return a deployment ID that you can use to reference your agent.

### Check Deployment Status

```bash
# Check the status of your deployment
runagent status <deployment_id>

# Get detailed JSON output
runagent status <deployment_id> --json
```

### List All Deployments

```bash
# List all your deployed agents
runagent list

# Filter by status
runagent list --status running
```

### Run an Agent

```bash
# Run with a simple text input
runagent run <deployment_id> --json-input '{"query": "Hello, agent!"}'

# Run with input from a JSON file
runagent run <deployment_id> --input input.json

# Run with a webhook for result notification
runagent run <deployment_id> --webhook https://your-webhook.example.com/hook
```

### Stream Logs

```bash
# Stream all logs from a deployment
runagent logs <deployment_id>

# Stream logs for a specific execution
runagent logs <deployment_id> --execution <execution_id>

# Get recent logs without streaming
runagent logs <deployment_id> --no-follow
```

### Test in Sandbox Mode

Test your agent without fully deploying it:

```bash
# Run your agent in sandbox mode
runagent sandbox . --json-input '{"query": "Test query"}'

# Specify input file and agent type
runagent sandbox . --input test-input.json --type langgraph
```

### Delete a Deployment

```bash
# Delete a deployed agent
runagent delete <deployment_id>
```

## SDK Usage

### Basic SDK Operations

```python
from runagent import RunAgentClient

# Initialize the client
client = RunAgentClient()  # API key from env or config
# OR
client = RunAgentClient(api_key="your_api_key_here")

# Deploy an agent
deployment = client.deploy("./my-agent", agent_type="langgraph")
deployment_id = deployment["deployment_id"]
print(f"Deployed agent with ID: {deployment_id}")

# Check deployment status
status = client.get_status(deployment_id)
print(f"Status: {status['status']}")

# Run the agent
execution = client.run_agent(
    deployment_id,
    {"query": "Hello, agent!"},
    webhook_url="https://your-webhook.example.com/hook"
)
execution_id = execution["execution_id"]
print(f"Execution started with ID: {execution_id}")

# Check execution status
exec_status = client.get_execution_status(deployment_id, execution_id)
print(f"Execution status: {exec_status['status']}")
print(f"Output: {exec_status.get('output')}")

# List deployments
deployments = client.list_deployments(status="running")
print(f"Found {len(deployments)} running deployments")

# Delete deployment
client.delete_agent(deployment_id)
```

### Streaming Logs with the SDK

```python
import time

def handle_log(log_data):
    timestamp = log_data.get("timestamp", "")
    message = log_data.get("message", "")
    print(f"[{timestamp}] {message}")

# Stream all logs from a deployment
ws = client.stream_logs(deployment_id, callback=handle_log)

# Stream logs for a specific execution
ws = client.stream_logs(deployment_id, execution_id=execution_id, callback=handle_log)

# Keep the connection open
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    ws.close()
```

### Testing in Sandbox Mode

```python
# Run agent in sandbox
sandbox_result = client.run_sandbox(
    "./my-agent",
    {"query": "Test query"},
    agent_type="langgraph"
)

print(f"Sandbox ID: {sandbox_result.get('sandbox_id')}")
print(f"Output: {sandbox_result.get('output')}")
```

## Template Usage

### Available Templates

RunAgent comes with built-in templates that you can use as starting points for your agents:

1. **LangGraph Default**: A simple agent that processes input and returns a response
   - Path: `langgraph/default`

2. **LangGraph Advanced**: A more complex agent that uses LLMs and maintains conversation history
   - Path: `langgraph/advanced`

### Customizing Templates

After initializing a project with a template, you'll typically want to:

1. Modify the agent logic in `agent.py`
2. Add any additional dependencies to `requirements.txt`
3. Test your agent with `runagent sandbox`
4. Deploy your agent with `runagent deploy`

### Example: Customizing the LangGraph Template

Let's modify the default LangGraph template to add a custom tool:

```python
# agent.py
from typing import Dict, TypedDict, List
from langgraph.graph import StateGraph, END
import requests

class AgentState(TypedDict):
    """Represents the state of the agent."""
    input: str
    steps: List[str]
    output: str
    weather_data: Dict

def process_input(state: AgentState) -> AgentState:
    """First step: process the input."""
    user_input = state["input"]
    steps = state.get("steps", [])
    steps.append(f"Received input: {user_input}")
    
    return {"input": user_input, "steps": steps}

def get_weather(state: AgentState) -> AgentState:
    """Get weather data for the location in the input."""
    user_input = state["input"]
    steps = state.get("steps", [])
    
    # Extract location from input (simplified example)
    location = user_input
    
    try:
        # Call weather API (example)
        response = requests.get(f"https://api.example.com/weather?location={location}")
        weather_data = response.json()
        
        steps.append(f"Retrieved weather data for {location}")
        
        return {
            "input": user_input,
            "steps": steps,
            "weather_data": weather_data
        }
    except Exception as e:
        steps.append(f"Error getting weather: {str(e)}")
        return {
            "input": user_input,
            "steps": steps,
            "weather_data": {"error": str(e)}
        }

def generate_response(state: AgentState) -> AgentState:
    """Generate a response using the weather data."""
    user_input = state["input"]
    steps = state.get("steps", [])
    weather_data = state.get("weather_data", {})
    
    if "error" in weather_data:
        response = f"Sorry, I couldn't get the weather: {weather_data['error']}"
    else:
        temp = weather_data.get("temperature", "unknown")
        conditions = weather_data.get("conditions", "unknown")
        response = f"The weather in {user_input} is {conditions} with a temperature of {temp}°C."
    
    steps.append(f"Generated response: {response}")
    
    return {
        "input": user_input,
        "steps": steps,
        "weather_data": weather_data,
        "output": response
    }

def create_agent_graph() -> StateGraph:
    """Create and return the agent workflow graph."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("process_input", process_input)
    workflow.add_node("get_weather", get_weather)
    workflow.add_node("generate_response", generate_response)
    
    # Add edges
    workflow.add_edge("process_input", "get_weather")
    workflow.add_edge("get_weather", "generate_response")
    workflow.add_edge("generate_response", END)
    
    # Set entry point
    workflow.set_entry_point("process_input")
    
    return workflow

# Create the compiled graph
agent_graph = create_agent_graph().compile()

def run(input_data: Dict) -> Dict:
    """Run the agent with the given input."""
    # Extract input text
    input_text = input_data.get("query", "")
    if not input_text and "input" in input_data:
        input_text = input_data["input"]
    
    # Initialize state
    state = {"input": input_text, "steps": []}
    
    # Run the agent
    result = agent_graph.invoke(state)
    return result
```

Don't forget to update your `requirements.txt`:

```
langgraph>=0.0.15
langchain>=0.0.191
requests>=2.25.0
```

## Common Workflows

### 1. Creating and Deploying a Simple Agent

```bash
# Initialize a new project
runagent init my-first-agent

# Customize the agent.py file
# (Edit the code as needed)

# Test in sandbox
runagent sandbox my-first-agent --json-input '{"query": "Hello!"}'

# Deploy
runagent deploy my-first-agent

# Run the deployed agent
runagent run <deployment_id> --json-input '{"query": "Hello!"}'
```

### 2. Working with Advanced LangGraph Agents

```bash
# Initialize with advanced template
runagent init llm-agent --template advanced

# Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here

# Test in sandbox
runagent sandbox llm-agent --json-input '{"query": "What can you tell me about LangGraph?"}'

# Deploy
runagent deploy llm-agent

# Run with conversation history
runagent run <deployment_id> --json-input '{
  "query": "Follow up on our previous conversation",
  "messages": [
    {"role": "human", "content": "What can you tell me about LangGraph?"},
    {"role": "ai", "content": "LangGraph is a library for..."}
  ]
}'
```

### 3. Monitoring Agents in Production

```bash
# List all deployments
runagent list

# Check specific deployment status
runagent status <deployment_id>

# Stream logs in real-time
runagent logs <deployment_id>

# Check execution status
runagent status <deployment_id> --execution <execution_id>
```

## Troubleshooting

### Common Issues and Solutions

1. **Authentication Errors**
   - Ensure your API key is correctly set (environment variable or configuration)
   - Try running `runagent configure --api-key your_key_here`

2. **Deployment Failures**
   - Check your `agent.py` file implements the required `run()` function
   - Verify all dependencies are listed in `requirements.txt`
   - Check logs with `runagent logs <deployment_id>`

3. **Execution Failures**
   - Ensure your input format matches what the agent expects
   - Check execution logs for detailed error information

4. **WebSocket Connection Issues**
   - Check network connectivity and firewall settings
   - Verify you're using the correct deployment and execution IDs

### Getting Help

If you encounter issues not covered here, you can:

- Check the full documentation at https://docs.runagent.live
- Open an issue on GitHub: https://github.com/runagent-dev/runagent/issues
- Contact support: support@runagent.live