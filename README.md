<p align="center">
  <a href="https://run-agent.ai/#gh-dark-mode-only">
    <img src="./docs/logo/logo_dark.svg" width="318px" alt="RunAgent logo" />
  </a>
  <a href="https://run-agent.ai/#gh-light-mode-only">
    <img src="./docs/logo/logo_light.svg" width="318px" alt="RunAgent Logo" />
  </a>
</p>

<h2 align="center">
  Simple Serverless Deployment for AI Agents
</h2>

<p align="center">
  <a href="https://docs.run-agent.ai">
    <img
      src="https://img.shields.io/badge/Click%20here%20for-RunAgent%20Docs-blue?style=for-the-badge&logo=read-the-docs"
      alt="Read the Docs">
  </a>
</p>


<p align="center">
  <a href="https://pypi.org/project/runagent/">
    <img src="https://img.shields.io/pypi/v/runagent" alt="PyPI" />
  </a>
  <a href="https://pypi.org/project/runagent/">
    <img src="https://img.shields.io/pypi/dm/runagent" alt="PyPI - Downloads" />
  </a>
  <a href="https://pypi.org/project/runagent/">
    <img src="https://img.shields.io/pypi/pyversions/runagent.svg" alt="Python Versions" />
  </a>
  <a href="https://discord.gg/runagent">
    <img src="https://img.shields.io/discord/1389567838825480192?color=7289DA&label=Discord&logo=discord&logoColor=white" alt="Discord" />
  </a>
</p>

<p align="center">
  <strong>Deploy AI agents to production in minutes, not days.</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-cli">CLI</a> •
  <a href="#-sdk">SDK</a> •
  <a href="#-templates">Templates</a>
</p>

---

## 🎯 What is RunAgent?

RunAgent is a production-ready platform for deploying AI agents. Whether you're using LangGraph, LangChain, LlamaIndex, or any other framework, RunAgent provides the infrastructure and tools to take your agents from development to production seamlessly.

### Why RunAgent?

- **🚀 Deploy in Minutes**: From local development to production with a single command
- **🔧 Framework Agnostic**: Works with any AI agent framework
- **📦 Serverless Architecture**: Scale automatically, pay only for what you use
- **🛡️ Secure by Default**: Sandboxed execution environments
- **📊 Built-in Monitoring**: Logs, metrics, and debugging tools included
- **🌊 Response Streaming**: Real-time agent responses for interactive applications

## ✨ Features

### 🖥️ Powerful CLI
- Initialize projects from templates
- Local development server with hot reload
- One-command deployment to production
- Real-time log streaming
- Environment management

### 📚 Multi-Language SDKs
- **Python SDK** - Available now with sync/async support
- **JavaScript SDK** - Coming soon
- **Rust SDK** - Coming soon
- **Go SDK** - Coming soon

### 🏗️ Production Ready
- Firecracker-based sandboxed environments
- Automatic scaling and load balancing
- Webhook support for event-driven architectures
- Built-in security and compliance features

## 🚀 Quick Start

### Installation

```bash
pip install runagent
```

### Create Your First Agent

1. **Initialize from a template**:
```bash
runagent init my-agent --framework langgraph
cd my-agent
```

2. **Configure your agent** (`runagent.config.json`):
```json
{
  "agent_name": "my-agent",
  "description": "My intelligent agent",
  "framework": "langgraph",
  "version": "1.0.0",
  "agent_architecture": {
    "entrypoints": [
      {
        "file": "agents.py",
        "module": "app.invoke",
        "type": "generic"
      },
      {
        "file": "agents.py",
        "module": "app.stream",
        "type": "generic_stream"
      }
    ]
  }
}
```

3. **Test locally**:
```bash
runagent serve .
```

4. **Deploy to production** (coming soon):
```bash
runagent deploy .
```

## 🔧 CLI

The RunAgent CLI is your command center for agent operations:

| Command | Description |
|---------|-------------|
| `runagent init` | Create a new agent project from templates |
| `runagent serve` | Run agent locally for development |
| `runagent deploy` | Deploy agent to production (coming soon) |
| `runagent logs` | Stream logs from running agents |
| `runagent status` | Check agent deployment status |
| `runagent list` | List all deployed agents |
| `runagent delete` | Remove a deployed agent |

### Example: Creating a Problem-Solving Agent

```bash
# Initialize from template
runagent init problem-solver --framework langgraph

# Navigate to project
cd problem-solver

# Install dependencies
pip install -r requirements.txt

# Run locally
runagent serve .

# Your agent is now running at http://localhost:8000
```

## 📦 SDK

### Python SDK

The Python SDK provides intuitive interfaces for interacting with deployed agents:

#### Synchronous Usage

```python
from runagent import RunAgentClient

# Initialize client
client = RunAgentClient(agent_id="your-agent-id")

# Simple invocation
result = client.run_generic({
    "query": "How do I fix my broken phone?",
    "num_solutions": 3
})
print(result)
```

#### Streaming Responses

```python
# Stream responses for real-time interaction
for chunk in client.run_generic_stream({
    "query": "Explain quantum computing",
    "detail_level": "beginner"
}):
    print(chunk, end="", flush=True)
```

#### Asynchronous Support

```python
import asyncio
from runagent import AsyncRunAgentClient

async def main():
    client = AsyncRunAgentClient(agent_id="your-agent-id")
    
    # Async invocation
    result = await client.run_generic({
        "query": "What's the weather like?",
        "location": "San Francisco"
    })
    print(result)
    
    # Async streaming
    async for chunk in client.run_generic_stream({
        "query": "Write a story about AI",
        "length": "short"
    }):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

### JavaScript SDK (Coming Soon)

```javascript
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({ agentId: 'your-agent-id' });

// Simple invocation
const result = await client.runGeneric({
  query: 'Help me plan a trip to Japan',
  duration: '7 days'
});

// Streaming
for await (const chunk of client.runGenericStream({ query: 'Tell me a joke' })) {
  process.stdout.write(chunk);
}
```

## 📋 Templates

Get started quickly with our pre-built templates:

- **problem-solver** - Multi-step problem-solving agent
- **chatbot** - Conversational AI assistant
- **data-analyst** - Data processing and analysis agent
- **web-researcher** - Internet research and summarization
- **code-assistant** - Programming help and code generation

```bash
# List available templates
runagent templates list

# Initialize from a specific template
runagent init my-chatbot --template chatbot
```

## 🏢 Enterprise Features (Coming Soon)

- **Private Cloud Deployment**: Run RunAgent in your own infrastructure
- **Advanced Security**: SOC2 compliance, encryption at rest
- **Team Collaboration**: Shared agents, role-based access control
- **Custom Domains**: Deploy agents to your own domains
- **SLA Support**: 99.9% uptime guarantee

## 📚 Documentation

For detailed documentation, visit [docs.run-agent.ai](https://docs.run-agent.ai)

- [Getting Started Guide](https://docs.run-agent.ai/getting-started)
- [CLI Reference](https://docs.run-agent.ai/cli)
- [SDK Documentation](https://docs.run-agent.ai/sdk)
- [Deployment Guide](https://docs.run-agent.ai/deployment)
- [Best Practices](https://docs.run-agent.ai/best-practices)

## 🗺️ Roadmap

### ✅ Available Now
- CLI with local deployment
- Python SDK with sync/async support
- Pre-built templates
- Response streaming
- Basic monitoring and logging

### 🚧 Coming Soon
- Serverless cloud deployment
- JavaScript, Rust, and Go SDKs
- Web dashboard for agent management
- Advanced monitoring and analytics
- Multi-region deployment
- Webhook integrations
- Team collaboration features

### 🔮 Future
- Private cloud deployment options
- Advanced security features
- Custom runtime environments
- Agent marketplace

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

```bash
# Clone the repository
git clone https://github.com/runagent-dev/runagent.git
cd runagent

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black runagent tests
```

## 💬 Community & Support

- [Discord Community](https://discord.gg/runagent) - Chat with other developers
- [GitHub Discussions](https://github.com/runagent-dev/runagent/discussions) - Ask questions and share ideas
- [Twitter](https://twitter.com/runagent_ai) - Follow for updates
- [Blog](https://run-agent.ai/blog) - Tutorials and best practices

## 📄 License

RunAgent is MIT licensed. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

RunAgent is built on the shoulders of giants. Special thanks to the teams behind LangChain, LangGraph, LlamaIndex, and the broader AI community.

---

<p align="center">
  <strong>Ready to deploy your AI agents?</strong>
</p>

<p align="center">
  <a href="https://run-agent.ai">Get Started →</a>
</p>

<p align="center">
  Made with ❤️ by the RunAgent Team
</p>
