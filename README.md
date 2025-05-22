# RunAgent

[![PyPI version](https://badge.fury.io/py/runagent.svg)](https://badge.fury.io/py/runagent)
[![Python Versions](https://img.shields.io/pypi/pyversions/runagent.svg)](https://pypi.org/project/runagent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://docs.runagent.dev)
[![Discord](https://img.shields.io/discord/1234567890?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/runagent)

RunAgent is a powerful command-line tool and SDK for deploying, managing, and interacting with AI agents. Built with modern Python practices, it provides a seamless experience for both developers and AI practitioners.

## 🌟 Features

- **Framework Agnostic**: Support for LangGraph, LangChain, LlamaIndex, and more
- **Simple CLI**: Deploy and manage agents with intuitive commands
- **Python SDK**: Integrate RunAgent into your applications
- **Templates**: Pre-built agent templates for quick starts
- **Sandbox Mode**: Test agents locally before deployment
- **Real-time Logging**: Stream logs from running agents
- **Webhook Support**: Get notified of agent task completions
- **Environment Management**: Handle API keys and configurations securely

## 📦 Installation

```bash
# Install from PyPI
pip install runagent

# Install with development dependencies
pip install "runagent[dev]"
```

## 🚀 Quick Start

1. **Initialize a new agent project**:
```bash
runagent init my-agent
cd my-agent
```

2. **Customize your agent**:
```python
# Edit agent.py to implement your logic
```

3. **Deploy your agent**:
```bash
runagent deploy .
```

4. **Run your agent**:
```bash
runagent run <deployment_id> --input '{"query": "Hello, agent!"}'
```

## 📚 Documentation

For detailed documentation, visit [docs.runagent.dev](https://docs.runagent.dev)

## 🛠️ CLI Reference

| Command | Description |
|---------|-------------|
| `runagent init [PATH]` | Initialize a new agent project |
| `runagent deploy [PATH]` | Deploy an agent |
| `runagent status <ID>` | Check agent status |
| `runagent logs <ID>` | Stream agent logs |
| `runagent run <ID>` | Run an agent |
| `runagent sandbox [PATH]` | Run in sandbox mode |
| `runagent list` | List deployed agents |
| `runagent delete <ID>` | Delete a deployment |
| `runagent configure` | Configure settings |

## 💻 SDK Usage

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

## 🏗️ Development

### Prerequisites

- Python 3.8+
- Git
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/runagent-dev/runagent.git
cd runagent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=runagent
```

### Code Style

We use:
- Black for code formatting
- isort for import sorting
- flake8 for linting
- mypy for type checking

```bash
# Format code
black runagent tests

# Sort imports
isort runagent tests

# Run linters
flake8 runagent tests
mypy runagent tests
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all our contributors
- Inspired by the AI agent community
- Built with modern Python best practices

## 📞 Support

- [Documentation](https://docs.runagent.dev)
- [Discord Community](https://discord.gg/runagent)
- [GitHub Issues](https://github.com/runagent-dev/runagent/issues)
- [Email Support](mailto:support@runagent.dev)

---

<p align="center">
Made with ❤️ by the RunAgent Team
</p>