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

RunAgent is an agentic ecosystem that enables developers to build AI agents once in Python using any python agentic frameworks like LangGraph, CrewAI, Letta, LlamaIndex, then access them natively from any programming language. The platform features stateful self-learning capabilities with RunAgent Memory (coming soon), allowing agents to retain context and improve it's action memory over time.

![Animated SVG](./docs/images/runagent_update.svg)


RunAgent has multi-language SDK support for seamless integration across TypeScript, JavaScript, Go, and other languages, eliminating the need to rewrite agents for different tech stacks. RunAgent Cloud provides automated deployment with serverless auto-scaling, comprehensive agent security, and real-time monitoring capabilities.


## Quick Start

### Installation

```bash
pip install runagent
```

### Initialize Your First Agent

```bash
# The basic
runagent init my-agent                # Basic template


# Also you can choose from various frameworks
runagent init my-agent --langgraph    # LangGraph template
runagent init my-agent --crewai       # CrewAI template  
runagent init my-agent --letta        # Letta template
```

## Agent Configuration

Every RunAgent project requires a `runagent.config.json` file that defines your agent's structure and capabilities. 

This configuration file specifies basic metadata (name, framework, version), defines entrypoints for either Python functions or external webhooks, and sets environment variables like API keys. The entrypoints array is the core component, allowing you to expose functions from any Python framework (LangGraph, CrewAI, OpenAI) or integrate external services (N8N, Zapier) through a unified interface accessible from any programming language.
### Example Configuration

```json
{
  "agent_name": "LangGraph Problem Solver",
  "description": "Multi-step problem analysis and solution validation agent",
  "framework": "langgraph",
  "version": "1.0.0",
  "agent_architecture": {
    "entrypoints": [
      {
        "file": "agent.py",
        "module": "solve_problem",
        "tag": "solve_problem"
      },
      {
        "file": "agent.py",
        "module": "solve_problem_stream",
        "tag": "solve_problem_stream"
      }
    ]
  },
  "env_vars": {
    "OPENAI_API_KEY": "your-api-key"
  }
}
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


##  **LangGraph Problem Solver Agent (An Example)**

```python
# agent.py
from langgraph.graph import StateGraph
from typing import TypedDict, List

class ProblemState(TypedDict):
    query: str
    num_solutions: int
    constraints: List[dict]
    solutions: List[str]
    validated: bool

def analyze_problem(state):
    # Problem analysis logic
    return {"solutions": [...]}

def validate_solutions(state):
    # Validation logic
    return {"validated": True}

# Build the graph
workflow = StateGraph(ProblemState)
workflow.add_node("analyze", analyze_problem)
workflow.add_node("validate", validate_solutions)
workflow.add_edge("analyze", "validate")
workflow.set_entry_point("analyze")

app = workflow.compile()

def solve_problem(query, num_solutions, constraints):
    result = app.invoke({
        "query": query,
        "num_solutions": num_solutions,
        "constraints": constraints
    })
    return result

async def solve_problem_stream(query, num_solutions, constraints):
    async for event in app.astream({
        "query": query,
        "num_solutions": num_solutions,
        "constraints": constraints
    }):
        yield event
```

**🌐 Access from any language:**

RunAgent offers multi-language SDKs : Rust, TypeScript, JavaScript, Go, and beyond—so you can integrate seamlessly without ever rewriting your agents for different stacks.

<table>
<tr>
<td width="25%"><b>Python SDK</b></td>
<td width="25%"><b>JavaScript SDK</b></td>
<td width="25%"><b>Rust SDK</b></td>
<td width="25%"><b>Go SDK</b></td>
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

# Streaming
for chunk in client.run(
    query="Fix my phone", 
    num_solutions=4
):
    print(chunk)
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

// Streaming
for await (const chunk of client.run({
  query: "Fix my phone",
  num_solutions: 4
})) {
  process.stdout.write(chunk);
}
```

</td>
<td valign="top">

```rust
use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

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
    
    // Streaming
    let mut stream = client.run_stream(&[
        ("query", json!("Fix my phone")),
        ("num_solutions", json!(4))
    ]).await?;
    
    while let Some(chunk) = stream.next().await {
        print!("{}", chunk?);
    }
    
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

    // Streaming
    stream, _ := client.RunStream(
        context.Background(),
        map[string]interface{}{
            "query": "Fix my phone",
            "num_solutions": 4,
        }
    )
    defer stream.Close()

    for {
        chunk, hasMore, _ := stream.Next(context.Background())
        if !hasMore { break }
        fmt.Print(chunk)
    }
}
```

</td>
</tr>
</table>

---

## Action Memory System (Coming Soon)

RunAgent is introducing **Action Memory** - a revolutionary approach to agent reliability that focuses on *how to remember* rather than *what to remember*.

### How It Will Work

- **Action-Centric**: Instead of storing raw conversation data, it captures decision patterns and successful action sequences
- **Cross-Language**: Memory persists across all SDK languages seamlessly  
- **Reliability Focus**: Learns from successful outcomes to improve future decisions
- **Ecosystem Integration**: Works with any framework - LangGraph, CrewAI, Letta, and more

This will ensure your agents become more reliable over time, regardless of which programming language or framework you use to interact with them.

---

## Remote Deployment (Coming very soon)

Deploy your agents with enterprise-grade infrastructure and experience the fastest agent deployment.

### ⚡Fastest agent deployment

From zero to production in the time it takes to draw a breath, making **RunAgent** one of the fastest agent deployment platforms available on planet earth 🌍 .

### Security-First Architecture

Every agent runs in its own **isolated sandbox environment**:
- Complete process isolation
- Network segmentation  
- Resource limits and monitoring
- Zero data leakage between agents

### ✨ The +++999 Aura of Agent Deployment

Our remote deployment will provide:

- Auto-scaling based on demand
- Global edge distribution
- Built-in monitoring and analytics  
- Production-grade security and compliance



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