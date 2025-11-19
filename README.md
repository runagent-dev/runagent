<p align="center">
  <a href="https://run-agent.ai/#gh-dark-mode-only">
    <img src="./docs/logo/logo_dark.svg" width="318px" alt="RunAgent logo" />
  </a>
  <a href="https://run-agent.ai/#gh-light-mode-only">
    <img src="./docs/logo/logo_light.svg" width="318px" alt="RunAgent Logo" />
  </a>
</p>

<h2 align="center">Secured, reliable AI agent deployment at scale</h2>

<h4 align="center">Run your stack. Let us run your agents.</h4>

<p align="center">
  <a href="https://docs.run-agent.ai">
    <img src="https://img.shields.io/badge/Click%20here%20for-RunAgent%20Docs-blue?style=for-the-badge&logo=read-the-docs" alt="Read the Docs">
  </a>
</p>

<div align="center">

<table>
  <thead>
    <tr>
      <th align="center"><a href="https://github.com/runagent-dev/runagent-py">runagent-py</a></th>
      <th align="center"><a href="https://github.com/runagent-dev/runagent-js">runagent-js</a></th>
      <th align="center"><a href="https://github.com/runagent-dev/runagent-rs">runagent-rs</a></th>
      <th align="center"><a href="https://github.com/runagent-dev/runagent-go">runagent-go</a></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center">
        <a href="https://pepy.tech/projects/runagent">
          <img src="https://static.pepy.tech/personalized-badge/runagent?period=total&units=ABBREVIATION&left_color=BLACK&right_color=GREEN&left_text=downloads" alt="PyPI Downloads">
        </a>
      </td>
      <td align="center">
        <a href="https://www.npmjs.com/package/runagent">
          <img src="https://img.shields.io/npm/dt/runagent" alt="npm downloads">
        </a>
      </td>
      <td align="center">
        <a href="https://crates.io/crates/runagent">
          <img src="https://img.shields.io/crates/d/runagent" alt="Crates.io downloads">
        </a>
      </td>
      <td align="center">
        <a href="https://github.com/runagent-dev/runagent-go">
          <img src="https://img.shields.io/github/stars/runagent-dev/runagent-go?style=social" alt="GitHub stars">
        </a>
      </td>
    </tr>
      <tr>
      <td align="center">
        <img src="https://img.shields.io/pypi/v/runagent" alt="PyPI version">
      </td>
      <td align="center">
        <img src="https://img.shields.io/npm/v/runagent" alt="npm version">
      </td>
      <td align="center">
        <img src="https://img.shields.io/crates/v/runagent" alt="Crates.io version">
      </td>
      <td align="center">
        <a href="https://pkg.go.dev/github.com/runagent-dev/runagent-go">
          <img src="https://pkg.go.dev/badge/github.com/runagent-dev/runagent-go.svg" alt="Go Reference">
        </a>
      </td>
    </tr>
  </tbody>
</table>
</div>

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

## Local Development

Deploy and test your agents locally with full debugging capabilities before deploying to RunAgent Cloud.

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

### Deploy to RunAgent Cloud

Once your agent is tested locally, deploy to production:

```bash
# Authenticate (first time only)
runagent setup --api-key <your-api-key>

# Deploy to cloud
runagent deploy --folder .
```

Your agent will be live globally with automatic scaling, monitoring, and enterprise security. View all your agents and execution metrics in the [dashboard](https://app.run-agent.ai/dashboard).


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

<div align="center">

## <b><code>🚀 RunAgent Cloud Deployment</code></b>

**Now Available: Production-Ready Cloud Infrastructure**

Deploy to production in seconds with enterprise-grade infrastructure

<br>

<table>
<tr>
<td align="center" width="200">
<a href="https://app.run-agent.ai/auth/signin"><b>Sign Up</b></a>
</td>
<td align="center" width="200">
<a href="https://app.run-agent.ai/dashboard"><b>Dashboard</b></a>
</td>
<td align="center" width="200">
<a href="https://docs.run-agent.ai/runagent-cloud/overview"><b>Documentation</b></a>
</td>
</tr>
</table>

</div>

Deploy your agents to RunAgent Cloud with enterprise-grade infrastructure and experience the fastest agent deployment. RunAgent Cloud provides serverless auto-scaling, comprehensive security, and real-time monitoring - all managed for you.

### Get Started with RunAgent Cloud

1. **Sign up** at [app.run-agent.ai](https://app.run-agent.ai/auth/signin)
2. **Generate API Key**: After signing in, go to **Settings → API Keys → Generate API Key**
3. **Authenticate CLI**: Configure your CLI with your API key
4. **Deploy**: Deploy your agents with a single command

```bash
# Authenticate with RunAgent Cloud
runagent setup --api-key <your-api-key>

# Deploy your agent
runagent deploy --folder ./my-agent
```

### Fastest Agent Deployment

From zero to production in seconds. RunAgent Cloud automatically selects the optimal VM image based on your agent's requirements, with deployment typically completing in 30-60 seconds for standard images, or up to 2 minutes for specialized configurations.

### Security-First Architecture

Every agent runs in its own **isolated sandbox environment**:
- Complete process isolation
- Network segmentation  
- Resource limits and monitoring
- Zero data leakage between agents

### Dashboard & Monitoring

The RunAgent Cloud dashboard provides comprehensive insights into your agents:

- **Agent Execution Metadata** - Detailed information about each execution
- **Execution Time Tracking** - Monitor performance and optimize accordingly
- **Agent Management** - View and manage all your deployed agents
- **Usage Analytics** - Track usage patterns and resource consumption
- **Real-time Monitoring** - Live status and health checks
- **Execution History** - Complete audit trail of all agent invocations

Access your dashboard at [app.run-agent.ai/dashboard](https://app.run-agent.ai/dashboard) after signing in.

### Enterprise-Grade Features

RunAgent Cloud provides:

- **Auto-scaling** - Automatically scales based on demand
- **Global Edge Distribution** - Low-latency access worldwide
- **Built-in Monitoring** - Comprehensive analytics and observability
- **Production-Grade Security** - Enterprise security and compliance
- **Multiple VM Images** - Automatic image selection optimized for your agent
- **Serverless Infrastructure** - Zero infrastructure management

---

## 📚 Documentation

- **[Getting Started](https://docs.run-agent.ai/get-started/introduction.md)** - Deploy your first agent in 5 minutes
- **[CLI Reference](https://docs.run-agent.ai/cli/overview.md)** - Complete command-line interface guide  
- **[SDK Documentation](https://docs.run-agent.ai/sdk/overview.md)** - Multi-language SDK guides
- **[Framework Guides](https://docs.run-agent.ai/frameworks/overview.md)** - Framework-specific tutorials
- **[API Reference](https://docs.run-agent.ai/api-reference/introduction.md)** - REST API documentation
- **[RunAgent Cloud Guide](https://docs.run-agent.ai/runagent-cloud/overview)** - Complete cloud deployment guide

---

## 🧠 Action Memory System (Coming Soon)

RunAgent is introducing **Action Memory** - a revolutionary approach to agent reliability that focuses on *how to remember* rather than *what to remember*.

### How It Will Work

- **Action-Centric**: Instead of storing raw conversation data, it captures decision patterns and successful action sequences
- **Cross-Language**: Memory persists across all SDK languages seamlessly  
- **Reliability Focus**: Learns from successful outcomes to improve future decisions
- **Ecosystem Integration**: Works with any framework - LangGraph, CrewAI, Letta, and more

This will ensure your agents become more reliable over time, regardless of which programming language or framework you use to interact with them.

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
