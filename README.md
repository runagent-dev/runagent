# RunAgent

<p align="center">
  <a href="https://run-agent.ai/#gh-dark-mode-only">
    <img src="./docs/logo/logo_dark.svg" width="318px" alt="RunAgent logo" />
  </a>
  <a href="https://run-agent.ai/#gh-light-mode-only">
    <img src="./docs/logo/logo_light.svg" width="318px" alt="RunAgent Logo" />
  </a>
</p>

<h2 align="center">Universal AI Agent Platform</h2>

<p align="center">
  <strong>Secured, reliable AI agent deployment at scale</strong>
</p>

<h3 align="center">Write agent once, use everywhere</h3>

<p align="center">
  <a href="https://docs.run-agent.ai">
    <img src="https://img.shields.io/badge/Click%20here%20for-RunAgent%20Docs-blue?style=for-the-badge&logo=read-the-docs" alt="Read the Docs">
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
  <a href="https://discord.gg/Q9P9AdHVHz">
    <img src="https://img.shields.io/discord/1389567838825480192?color=7289DA&label=Discord&logo=discord&logoColor=white" alt="Discord" />
  </a>
</p>

---

## What is RunAgent?

RunAgent is a universal AI agent deployment platform that allows you to **write agents once in Python and access them natively from any programming language**. Whether you're building with LangGraph, CrewAI, Letta, or any Python framework, RunAgent provides seamless deployment and cross-language access.

<div align="center">
  <img src="./docs/images/runagent_dia_light.jpg" style="width:100%;max-width:900px;" alt="RunAgent Architecture" />
</div>

## Quick Start

### Installation

```bash
pip install runagent
```

### Initialize Your First Agent

```bash
# Choose from various frameworks
runagent init my-agent --langgraph    # LangGraph template
runagent init my-agent --crewai       # CrewAI template  
runagent init my-agent --letta        # Letta template
runagent init my-agent                # Basic template
```

## Local Deployment

Deploy and test your agents locally with full debugging capabilities.

### Deploy Agent Locally

```bash
cd my-agent
runagent serve .
```

This starts a local FastAPI server with:
- Auto-allocated ports to avoid conflicts
- Real-time debugging and logging  
- WebSocket support for streaming
- Built-in API documentation at `/docs`

### Use Your Agent

<div align="center">

**Click on any SDK below to see the implementation:**

</div>

<details>
<summary><strong>🐍 Python SDK</strong></summary>

```python
from runagent import RunAgentClient

# Non-streaming
client = RunAgentClient(
    agent_id="your-agent-id",
    entrypoint_tag="your-tag",
    local=True
)

result = client.run(
    message="Hello from Python!"
)
print(result)

# Streaming
for chunk in client.run(message="Stream this response"):
    print(chunk, end='')
```

</details>

<details>
<summary><strong>🟨 JavaScript/TypeScript SDK</strong></summary>

```javascript
import { RunAgentClient } from 'runagent';

// Non-streaming
const client = new RunAgentClient({
  agentId: "your-agent-id",
  entrypointTag: "your-tag", 
  local: true
});

await client.initialize();
const result = await client.run({
  message: "Hello from JavaScript!"
});
console.log(result);

// Streaming
for await (const chunk of client.run({message: "Stream this"})) {
  process.stdout.write(chunk);
}
```

</details>

<details>
<summary><strong>🦀 Rust SDK</strong></summary>

```rust
use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Non-streaming
    let client = RunAgentClient::new("your-agent-id", "your-tag", true).await?;
    
    let result = client.run(&[
        ("message", json!("Hello from Rust!"))
    ]).await?;
    
    println!("Result: {}", result);
    
    // Streaming
    let mut stream = client.run_stream(&[
        ("message", json!("Stream this response"))
    ]).await?;
    
    while let Some(chunk) = stream.next().await {
        print!("{}", chunk?);
    }
    
    Ok(())
}
```

</details>

<details>
<summary><strong>🔷 Go SDK</strong></summary>

```go
package main

import (
    "context"
    "fmt"
    "github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
    // Non-streaming
    client, _ := client.New("your-agent-id", "your-tag", true)
    defer client.Close()

    result, _ := client.Run(context.Background(), map[string]interface{}{
        "message": "Hello from Go!",
    })
    fmt.Printf("Result: %v\n", result)

    // Streaming  
    stream, _ := client.RunStream(context.Background(), map[string]interface{}{
        "message": "Stream this response",
    })
    defer stream.Close()

    for {
        chunk, hasMore, _ := stream.Next(context.Background())
        if !hasMore { break }
        fmt.Print(chunk)
    }
}
```

</details>

---

## Action Memory System (Coming Soon)

RunAgent is introducing **Action Memory** - a revolutionary approach to agent reliability that focuses on *how to remember* rather than *what to remember*.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Request  │───▶│ Decision Engine  │───▶│  Action Store   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        │
                       ┌──────────────────┐              │
                       │  Context Layer   │              │
                       └──────────────────┘              │
                                │                        │
                                ▼                        │
                       ┌──────────────────┐              │
                       │  Pattern Matcher │◀─────────────┘
                       └──────────────────┘              
                                │                        
                                ▼                        
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Response Gen.   │◀───│  Success Cache  │
                       └──────────────────┘    └─────────────────┘
```

### How It Will Work

- **Action-Centric**: Instead of storing raw conversation data, it captures decision patterns and successful action sequences
- **Cross-Language**: Memory persists across all SDK languages seamlessly  
- **Reliability Focus**: Learns from successful outcomes to improve future decisions
- **Ecosystem Integration**: Works with any framework - LangGraph, CrewAI, Letta, and more

This will ensure your agents become more reliable over time, regardless of which programming language or framework you use to interact with them.

---

## Remote Deployment

Deploy your agents to production with enterprise-grade infrastructure.

### Lightning-Fast Deployment

Our remote platform delivers **3-second agent spin-up times** - from cold start to ready state in under 3 seconds, making it one of the fastest agent deployment platforms available.

### Security-First Architecture

Every agent runs in its own **isolated sandbox environment**:
- Complete process isolation
- Network segmentation  
- Resource limits and monitoring
- Zero data leakage between agents
- Encrypted communication channels

### Coming Soon

```bash
# One-command deployment (in development)
runagent deploy --remote
```

The remote deployment will provide:
- Auto-scaling based on demand
- Global edge distribution
- Built-in monitoring and analytics  
- Production-grade security and compliance

---

## Supported Frameworks

RunAgent works with any Python AI framework:

- **LangGraph** - Deploy graph-based agents with full state management
- **CrewAI** - Deploy multi-agent systems with role-based collaboration  
- **Letta** - Deploy memory-enabled conversational agents
- **LangChain** - Deploy chain-based agents with tool integration
- **Custom** - Deploy agents built with any Python framework

---

## Why Choose RunAgent?

**Universal Access**: Write in Python, use from any language - no API complexity

**Framework Agnostic**: Works with your existing agent code, regardless of framework

**Local + Remote**: Start local, scale to production seamlessly  

**Action Memory**: Built-in reliability system that learns from successful patterns

**Developer Experience**: Intuitive CLI, comprehensive SDKs, extensive documentation

**Production Ready**: Enterprise-grade security, monitoring, and performance

---

## Documentation

- **[Getting Started](https://docs.run-agent.ai/get-started/introduction.md)** - Deploy your first agent in 5 minutes
- **[CLI Reference](https://docs.run-agent.ai/cli/overview.md)** - Complete command-line interface guide  
- **[SDK Documentation](https://docs.run-agent.ai/sdk/overview.md)** - Multi-language SDK guides
- **[Framework Guides](https://docs.run-agent.ai/frameworks/overview.md)** - Framework-specific tutorials
- **[API Reference](https://docs.run-agent.ai/api-reference/introduction.md)** - REST API documentation

---

## Community & Support

<div align="center">

**[Discord Community](https://discord.gg/Q9P9AdHVHz)** • **[Documentation](https://docs.run-agent.ai)** • **[GitHub](https://github.com/runagent-dev/runagent)**

</div>

---

<div align="center">

**Ready to build universal AI agents?**

[**Get Started with Local Development →**](https://docs.run-agent.ai/get-started/quickstart.md)

</div>

<p align="center">
  <a href="https://github.com/runagent-dev/runagent">🌟 Star us on GitHub</a> •
  <a href="https://discord.gg/Q9P9AdHVHz">💬 Join Discord</a> •
  <a href="https://docs.run-agent.ai">📚 Read the Docs</a>
</p>

![Visitor Badge](https://visitor-badge.laobi.icu/badge?page_id=runagent-dev.runagent)

<p align="center">
  <sub>Made with ❤️ by the RunAgent Team</sub>
</p>
