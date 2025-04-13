# README.md
# RunAgent

Deploy and manage AI agents with ease.

## About

RunAgent is a command-line tool and SDK that allows you to easily deploy, manage, and interact with AI agents built with frameworks like LangGraph. It takes care of the infrastructure, so you can focus on your agent logic.

## Features

- **Simple CLI**: Deploy agents with a single command
- **SDK**: Integrate RunAgent into your Python applications
- **Templates**: Get started quickly with pre-built agent templates
- **Sandbox Mode**: Test your agents before deployment
- **Real-time Logs**: Stream logs from your running agents
- **Webhooks**: Get notified when your agent completes a task

## Installation

```bash
pip install runagent
```

## Quick Start

1. Initialize a new agent project:
```bash
runagent init my-agent
cd my-agent
```

2. Modify the agent code to suit your needs:
```bash
# Edit agent.py to add your logic
```

3. Deploy your agent:
```bash
runagent deploy .
```

4. Run your agent:
```bash
runagent run <deployment_id> --input '{"query": "Hello, agent!"}'
```

## CLI Reference

- `runagent init [PATH]`: Initialize a new agent project
- `runagent deploy [PATH]`: Deploy an agent
- `runagent status <DEPLOYMENT_ID>`: Check agent status
- `runagent logs <DEPLOYMENT_ID>`: Stream agent logs
- `runagent run <DEPLOYMENT_ID>`: Run an agent
- `runagent sandbox [PATH]`: Run an agent in sandbox mode
- `runagent list`: List all deployed agents
- `runagent delete <DEPLOYMENT_ID>`: Delete a deployed agent
- `runagent configure`: Configure RunAgent settings

## SDK Usage

```python
from runagent import RunAgentClient

# Initialize client
client = RunAgentClient(api_key="your_api_key")

# Deploy an agent
deployment = client.deploy("./my-agent")
deployment_id = deployment["deployment_id"]

# Run the agent
execution = client.run_agent(
    deployment_id, 
    {"query": "Hello, agent!"}
)

# Check execution status
status = client.get_execution_status(
    deployment_id, 
    execution["execution_id"]
)

print(f"Status: {status['status']}")
print(f"Output: {status['output']}")
```

## Development

To set up the development environment:

```bash
git clone https://github.com/runagent-dev/runagent.git
cd runagent
pip install -e ".[dev]"
```

## License

MIT