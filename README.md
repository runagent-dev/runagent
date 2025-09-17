# RunAgent

<p align="center">
  <a href="https://run-agent.ai/#gh-dark-mode-only">
    <img src="./docs/logo/logo_dark.svg" width="318px" alt="RunAgent logo" />
  </a>
  <a href="https://run-agent.ai/#gh-light-mode-only">
    <img src="./docs/logo/logo_light.svg" width="318px" alt="RunAgent Logo" />
  </a>
</p>

<h2 align="center">Secured, reliable AI agent deployment at scale</h2>

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

**Select a Python agent framework and choose your SDK language:**

</div>

---

## 🔷 **LangGraph Problem Solver Agent**

**Perfect for**: Multi-step reasoning, problem decomposition, solution validation

<table>
<tr>
<td width="25%"><b>🐍 Python SDK</b></td>
<td width="25%"><b>🟨 JavaScript SDK</b></td>
<td width="25%"><b>🦀 Rust SDK</b></td>
<td width="25%"><b>🔷 Go SDK</b></td>
</tr>
<tr>
<td valign="top">

```python
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="lg-solver-123",
    entrypoint_tag="solve_problem",
    local=True
)

result = client.run(
    query="My laptop is slow",
    num_solutions=3,
    constraints=[{
        "type": "budget", 
        "value": 100
    }]
)
print(result)
```

</td>
<td valign="top">

```javascript
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({
  agentId: "lg-solver-123",
  entrypointTag: "solve_problem",
  local: true
});

await client.initialize();
const result = await client.run({
  query: "My laptop is slow",
  num_solutions: 3,
  constraints: [{
    type: "budget",
    value: 100
  }]
});
console.log(result);
```

</td>
<td valign="top">

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = RunAgentClient::new(
        "lg-solver-123", 
        "solve_problem", 
        true
    ).await?;
    
    let result = client.run(&[
        ("query", json!("My laptop is slow")),
        ("num_solutions", json!(3)),
        ("constraints", json!([{
            "type": "budget", 
            "value": 100
        }]))
    ]).await?;
    
    println!("Result: {}", result);
    Ok(())
}
```

</td>
<td valign="top">

```go
package main

import (
    "context"
    "fmt"
    "github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
    client, _ := client.New(
        "lg-solver-123", 
        "solve_problem", 
        true
    )
    defer client.Close()

    result, _ := client.Run(
        context.Background(), 
        map[string]interface{}{
            "query": "My laptop is slow",
            "num_solutions": 3,
            "constraints": []map[string]interface{}{
                {"type": "budget", "value": 100},
            },
        }
    )
    fmt.Printf("Result: %v\n", result)
}
```

</td>
</tr>
</table>

---

## 👥 **CrewAI Research Team**

**Perfect for**: Multi-agent collaboration, research tasks, complex analysis

<table>
<tr>
<td width="25%"><b>🐍 Python SDK</b></td>
<td width="25%"><b>🟨 JavaScript SDK</b></td>
<td width="25%"><b>🦀 Rust SDK</b></td>
<td width="25%"><b>🔷 Go SDK</b></td>
</tr>
<tr>
<td valign="top">

```python
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="crew-research-456",
    entrypoint_tag="research_crew",
    local=True
)

result = client.run(
    topic="AI Security Best Practices"
)
print(result["final_report"])

# Stream crew collaboration
for update in client.run(
    topic="Blockchain trends"
):
    print(f"Agent {update['agent']}: "
          f"{update['task_update']}")
```

</td>
<td valign="top">

```javascript
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({
  agentId: "crew-research-456",
  entrypointTag: "research_crew",
  local: true
});

await client.initialize();
const result = await client.run({
  topic: "AI Security Best Practices"
});
console.log(result.final_report);

// Stream crew collaboration
for await (const update of client.run({
  topic: "Blockchain trends"
})) {
  console.log(`Agent ${update.agent}: ${update.task_update}`);
}
```

</td>
<td valign="top">

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = RunAgentClient::new(
        "crew-research-456", 
        "research_crew", 
        true
    ).await?;
    
    let result = client.run(&[
        ("topic", json!("AI Security Best Practices"))
    ]).await?;
    
    println!("Research Result: {}", result);
    Ok(())
}
```

</td>
<td valign="top">

```go
package main

import (
    "context"
    "fmt"
    "github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
    client, _ := client.New(
        "crew-research-456", 
        "research_crew", 
        true
    )
    defer client.Close()

    result, _ := client.Run(
        context.Background(), 
        map[string]interface{}{
            "topic": "AI Security Best Practices",
        }
    )
    fmt.Printf("Research Result: %v\n", result)
}
```

</td>
</tr>
</table>

---

## 🧠 **Letta Memory Agent**

**Perfect for**: Long-term conversations, personalized interactions, context retention

<table>
<tr>
<td width="25%"><b>🐍 Python SDK</b></td>
<td width="25%"><b>🟨 JavaScript SDK</b></td>
<td width="25%"><b>🦀 Rust SDK</b></td>
<td width="25%"><b>🔷 Go SDK</b></td>
</tr>
<tr>
<td valign="top">

```python
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="letta-memory-789",
    entrypoint_tag="chat_with_memory",
    local=True
)

# Agent remembers context
result = client.run(
    message="Hi, I'm Sarah and I love hiking"
)
print(result)

# Later - agent recalls Sarah's interests
result = client.run(
    message="What outdoor activities "
            "would you recommend?"
)
print(result)
```

</td>
<td valign="top">

```javascript
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({
  agentId: "letta-memory-789",
  entrypointTag: "chat_with_memory",
  local: true
});

await client.initialize();

// Agent remembers context
let result = await client.run({
  message: "Hi, I'm Sarah and I love hiking"
});
console.log(result);

// Later - agent recalls Sarah's interests
result = await client.run({
  message: "What outdoor activities would you recommend?"
});
console.log(result);
```

</td>
<td valign="top">

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = RunAgentClient::new(
        "letta-memory-789", 
        "chat_with_memory", 
        true
    ).await?;
    
    // Agent remembers context
    let result = client.run(&[
        ("message", json!("Hi, I'm Sarah and I love hiking"))
    ]).await?;
    
    println!("Response: {}", result);
    Ok(())
}
```

</td>
<td valign="top">

```go
package main

import (
    "context"
    "fmt"
    "github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
    client, _ := client.New(
        "letta-memory-789", 
        "chat_with_memory", 
        true
    )
    defer client.Close()

    // Agent remembers context
    result, _ := client.Run(
        context.Background(), 
        map[string]interface{}{
            "message": "Hi, I'm Sarah and I love hiking",
        }
    )
    fmt.Printf("Response: %v\n", result)
}
```

</td>
</tr>
</table>

---

## ⚡ **Custom OpenAI Agent**

**Perfect for**: Custom AI assistants, specialized tasks, flexible integrations

<table>
<tr>
<td width="25%"><b>🐍 Python SDK</b></td>
<td width="25%"><b>🟨 JavaScript SDK</b></td>
<td width="25%"><b>🦀 Rust SDK</b></td>
<td width="25%"><b>🔷 Go SDK</b></td>
</tr>
<tr>
<td valign="top">

```python
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="openai-assistant-321",
    entrypoint_tag="smart_assistant",
    local=True
)

result = client.run(
    user_msg="Analyze remote work benefits",
    temperature=0.7,
    model="gpt-4"
)
print(result)

# Streaming response
for chunk in client.run(
    user_msg="Write AI trends report",
    temperature=0.8
):
    print(chunk, end='')
```

</td>
<td valign="top">

```javascript
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({
  agentId: "openai-assistant-321",
  entrypointTag: "smart_assistant",
  local: true
});

await client.initialize();
const result = await client.run({
  user_msg: "Analyze remote work benefits",
  temperature: 0.7,
  model: "gpt-4"
});
console.log(result);

// Streaming response
for await (const chunk of client.run({
  user_msg: "Write AI trends report"
})) {
  process.stdout.write(chunk);
}
```

</td>
<td valign="top">

```rust
use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = RunAgentClient::new(
        "openai-assistant-321", 
        "smart_assistant", 
        true
    ).await?;
    
    let result = client.run(&[
        ("user_msg", json!("Analyze remote work benefits")),
        ("temperature", json!(0.7)),
        ("model", json!("gpt-4"))
    ]).await?;
    
    println!("Response: {}", result);
    Ok(())
}
```

</td>
<td valign="top">

```go
package main

import (
    "context"
    "fmt"
    "github.com/runagent-dev/runagent-go/pkg/client"
)

func main() {
    client, _ := client.New(
        "openai-assistant-321", 
        "smart_assistant", 
        true
    )
    defer client.Close()

    result, _ := client.Run(
        context.Background(), 
        map[string]interface{}{
            "user_msg": "Analyze remote work benefits",
            "temperature": 0.7,
            "model": "gpt-4",
        }
    )
    fmt.Printf("Response: %v\n", result)
}
```

</td>
</tr>
</table>

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