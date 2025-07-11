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

RunAgent is a production-ready tool/platform for deploying AI agents and accessing those agents with from a wide variety of languages(provided SDKs). With out-of-the-box support for invoking & streaming and outputs, and any pythonic agentic framework, RunAgent gives you the infrastructure and tools to seamlessly deploy your agents, and build applications on top of them.


<div style="width:100%;display:flex;justify-content:center;align-items:center;">
  <a href="https://run-agent.ai/#gh-dark-mode-only" style="flex:1;">
    <img src="./docs/images/runagent_dia_dark.jpg" style="width:100%;max-width:900px;" alt="RunAgent Diagram" />
  </a>
  <a href="https://run-agent.ai/#gh-light-mode-only" style="flex:1;">
    <img src="./docs/images/runagent_dia_light.jpg" style="width:100%;max-width:900px;" alt="RunAgent Diagram" />
  </a>
</div>

### Why RunAgent?

- **🚀 Deploy in Minutes**: From local development to production with a single command
- **🔧 Framework Agnostic**: Works with any AI agent framework
- **🌊 Response Streaming**: Real-time agent responses for interactive applications
- **📦 Serverless Architecture**: Scale automatically, pay only for what you use(Coming Soon)
- **🛡️ Secure by Default**: Sandboxed execution environments(Coming Soon)
- **📊 Built-in Monitoring**: Logs, metrics, and debugging tools included(Coming Soon)

## ✨ Features

### 🖥️ Powerful CLI

- Initialize projects from framework-specific(or blank) templates.
- Local development server with FastAPI(both REST and WebSocket support)
- One-command deployment for configured projects.
- Separate Environment management for project.
- Real-time agent invocation & streaming.

### 📚 Multi-Language SDKs

- **Python SDK** - `pip install runagent`
- **JavaScript SDK** - `npm install runagent`
- **Rust SDK**
- **Go SDK**

### 🏗️ Serverless Deployment

- Sandboxed environment for each deployed agent.
- Automatic scaling and load balancing.
- Webhook support for event-driven architectures.
- Built-in security and compliance features.
- (More features of Feedback)


## 🚀 QuickStart(Deploying an Agent)

RunAgent toolset gives you the power to both: 1. Deploy an agent from any Agentic framework(Using runagent CLI) and 2. Use a CLI-deployed agent in yout application(Any of our language specific SDKs). The SDKs gives you kind of a native experience of using the cutting-edge agentic features, but in your own development environment.

> The python SDK is binded with the RunAgent CLI. For other language SDKs, you need to install from respective package repositories.

### 1. Installation

```bash
pip install runagent
```

### 2. Initialize from a template:

We have created a bunch of predefined [templates](./templates) covering most of our supported frameworks. These will work as examples and starting point for users, and you can initiate those with `runagent init` command.

```bash
# for a framework specific template, use framework tags:
runagent init <project_name> --langgraph

# We will create a minimal project `my_agent`:
runagent init my_agent
```


If we look at the directory structure:

```bash
my-agent/
├── __init__.py
├── email_agent.py
├── main.py
└── runagent.config.json
```
In any runagent project most important file is `runagent.config.json` file, it keeps metadata relevent to that project, as well as the list of `entrypoints`, which are the functions/methods from codebase, that will be exposed through runagent server.

> `entrypoints` can be referred as single most important concept in runagent ecosystem. See more details in [Core Concepts](https://docs.run-agent.ai/get-started/core-concepts).


### 2. Configure your agent (`runagent.config.json`):

If we look at the `main.py` content(partial):

```python
from .email_agent import MockOpenAIClient
from typing import Iterator


def mock_response(message, role="user"):
    """Test the mock agent with non-streaming responses"""
    client = MockOpenAIClient()

    prompt = [
        {
            "role": role,
            "content": message
        }
    ]
    response = client.create(model="gpt-4", messages=prompt)

    print(response.content)
    print(f"\nTokens used: {response.usage_tokens}")
    print(f"Response time: {response.response_time:.2f}s")

    return response.content


def mock_response_stream(message, role="user") -> Iterator[str]:
    """Test the mock agent with streaming responses"""
    client = MockOpenAIClient()
    prompt = [
        {
            "role": role,
            "content": message
        }
    ]
    for chunk in client.create(
        model="gpt-4",
        messages=prompt,
        stream=True
    ):
        if not chunk.finished:
            yield chunk.delta
        else:
            yield "\n[STREAM COMPLETE]"
```

There are `mock_response` and `mock_response_stream` functions, that will be used as agent entrypoints. So we will mention those in `runagent.config.json` file, which is central file for any agent in runagent ecosystem.

Lets take a look at the `runagent.config.json` file:

```json
{
  "agent_name": "my-agent",
  "description": "A simple placeholder agent",
  "framework": "default",
  "template": "default",
  "version": "1.0.0",
  "created_at": "2025-07-11 15:08:18",
  "template_source": {
    "repo_url": "https://github.com/runagent-dev/runagent.git",
    "author": "sawradip",
    "path": "templates/default"
  },
  "agent_architecture": {
    "entrypoints": [
      {
        "file": "main.py",
        "module": "mock_response",
        "tag": "minimal"
      },
      {
        "file": "main.py",
        "module": "mock_response_stream",
        "tag": "minimal_stream"
      }
    ]
  },
  "env_vars": {}
}
```

You can see, in the `entrypoints` list, each record has a relative(or may be absolute) path of the file containing the entrypoint function. As well as a tag, (unique for each project) must be specified. 

In case of streaming entrypoints, (i.e. `mock_response_stream`), the tag must be prefixed with a `_stream` suffix.

### 3. Serve your agent (built-in runagent server):

```bash
# project_dir - Project root directory
runagent serve <project_dir>

# If you are inside teh project directory
runagent serve .

# In our case, <project_name> also works.
runagent serve my_agent
```

You will get an `agent_id`, as well as an url `host:port`, you can use either of them with `RunAgentClient` form any RunAgent SDK.

### 4. Deploy agent on RunAgent Cloud - Serverless (coming soon):

```bash
# Same argument used with `serve`
runagent deploy <project_dir>
```



## 🚀 QuickStart(use a deployed agent)

We provide RunAgent SDK for multiple languages, and are adding new language supports as fast as we can. If you have a preferred language to use, or want to contribute for a specific language, reach out to Discord, or raise an issue.

Remember the `agent_id` and url(`host:port`) we got during deploying, now we will use those, as well as the `tag` specified in `runagent.config.json`. As you have installed the CLI, the `python-sdk` is already installed in your environment. For otehr language installation, follow the previous section in readme, or docs for details.

With our SDKs, you can access the `entrypoints` (the ones we mentioned in `runagent.config.json`) like native functions(yeah! even for streaming). We take care all the complex communication in background.

### Python SDK

We can initiate the client with the `agent_id` and the entrypoint `tag`. First we will try with `minimal` tag, which corresponds to the function `def mock_response(message, role="user"):`. S

```python
from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id=<agent_id>,
    entrypoint_tag=<tag>,
    local=True  # You are running local server
    )
```

Now, if you remember, the function signature of the `mock_response` function is `def mock_response(message, role="user"):`. And the magic teh runagent-sdk provides is, you can invoke the `RunAgentClient.run` method, as teh target entry point method. So you can use:

```
agent_results = ra.run(
    role="user",
    message="Analyze the benefits of remote work for software teams"
)
```

So, to see the total codeblock,
```
from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id=<agent_id>>,
    entrypoint_tag=<tag>,
    local=True
    )


agent_results = ra.run(
    role="user",
    message="Analyze the benefits of remote work for software teams"
)

print(agent_results)
```

Just replace, `agent_id` and `tag` from the deployment, and you have access to the target funtion (almost)natively. if you want to access with `host:port`, that is all supported.
```
ra = RunAgentClient(host=<host>, port=<port>, entrypoint_tag=<tag>, local=True)
```

You must be thinking, that is fine, but what about the streaming?? 
You can use the streaming function's returned interable as a native iterable object. So, 
```
from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id=<agent_id>,
    entrypoint_tag=<tag>,
    local=True
    )

for chunk in ra.run([
        {"role": "user", "content": "Analyze the benefits of remote work "
         "for software teams"}
]):
    print(chunk)
```

No need for the complicated implementation of rest api, web socket, grpc and what not. RunAgent is here to run your agent.


### Rust SDK

Non-streaming Example:

```rust 
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Connect to agent
    let client = RunAgentClient::new(<agent_id>, <tag>, true).await?;
    
    // Simple invocation
    let result = client.run(&[
        ("query", json!("Help me plan a trip to Japan")),
        ("duration", json!("7 days"))
    ]).await?;
    
    println!("Result: {}", result);
    Ok(())
}
```

Streaming Example:

```rust
use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Stream responses for real-time interaction
    let client = RunAgentClient::new(<agent_id>, <tag>, true).await?;
    let mut stream = client.run_stream(&[
        ("query", json!("Explain quantum computing")),
        ("detail_level", json!("beginner"))
    ]).await?;
    
    while let Some(chunk) = stream.next().await {
        print!("{}", chunk?);
    }
    
    Ok(())
}
```

### JavaScript/ TypeScript SDK

Create an `.mjs` file or ad `type: "module"` to your `package.json`.

Non-streaming Example:

```mjs
import { RunAgentClient } from 'runagent';

const ra = new RunAgentClient({
  agentId: <agent_id>,
  host: <host>,
  port: <port>,
  entrypointTag: "minimal",
  local: true
});

await ra.initialize();

const solutionResult = await ra.run({
  role: 'user',
  message: 'Analyze the benefits of remote work for software teams',
});

console.log(solutionResult);
```

Streaming Example:

```mjs
import { RunAgentClient } from 'runagent';

const ra = new RunAgentClient({
  agentId: <agent_id>,
  host: <host>,
  port: <port>,
  entrypointTag: "minimal_stream",
  local: true
});

// Initialize
await ra.initialize();

const stream = await ra.run({
  role: 'user',
  message: 'Analyze the benefits of remote work for software teams',
});

for await (const out of stream) {
  console.log('=====??');
  console.log(out);
  console.log('??====');
}
```

## 🔧 CLI

The RunAgent CLI is your command center for agent operations:

| Command | Description |
|---------|-------------|
| `runagent init` | Create a new agent project from templates |
| `runagent serve` | Run agent locally for development |


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
