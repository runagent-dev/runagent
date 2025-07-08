//! Init command implementation with embedded templates

use crate::utils::{output::CliOutput, validation};
use anyhow::{Context, Result};
use clap::Args;
use chrono::Utc;
use serde_json::json;
use std::fs;
use std::path::PathBuf;

/// Initialize a new RunAgent project
#[derive(Args)]
pub struct InitArgs {
    /// Project path (defaults to current directory)
    #[arg(default_value = ".")]
    path: PathBuf,

    /// Template variant (basic, advanced, default)
    #[arg(long, default_value = "default")]
    template: String,

    /// Enable interactive prompts
    #[arg(short, long)]
    interactive: bool,

    /// Overwrite existing folder
    #[arg(long)]
    overwrite: bool,

    /// Use LangChain framework
    #[arg(long)]
    langchain: bool,

    /// Use LangGraph framework
    #[arg(long)]
    langgraph: bool,

    /// Use LlamaIndex framework
    #[arg(long)]
    llamaindex: bool,

    /// Use Rust LangChain framework
    #[arg(long, name = "rust-langchain")]
    rust_langchain: bool,

    /// Use Rust framework (generic)
    #[arg(long)]
    rust: bool,

    /// Project name (for interactive mode)
    #[arg(long)]
    name: Option<String>,
}

pub async fn execute(args: InitArgs, output: &CliOutput) -> Result<()> {
    // Choose framework
    let framework = determine_framework(&args)?;

    // Determine path & name
    let (project_path, project_name) = determine_project_path(&args)?;

    // Interactive adjustments
    let (final_framework, final_template) = if args.interactive {
        handle_interactive_mode(&framework, &args.template, output)?
    } else {
        (framework, args.template.clone())
    };

    // Handle existing path
    handle_existing_path(&project_path, args.overwrite, output)?;

    // Create directory
    fs::create_dir_all(&project_path)
        .with_context(|| format!("Failed to create project directory: {}", project_path.display()))?;

    // Show configuration
    display_project_config(&project_name, &project_path, &final_framework, &final_template, output);

    // Generate files
    generate_project_files(&project_path, &project_name, &final_framework, &final_template, output)?;

    // Next steps
    show_next_steps(&project_path, &final_framework, output);

    Ok(())
}

fn determine_framework(args: &InitArgs) -> Result<String> {
    let flags = [
        (args.langchain, "langchain"),
        (args.langgraph, "langgraph"),
        (args.llamaindex, "llamaindex"),
        (args.rust_langchain, "rust-langchain"),
        (args.rust, "rust"),
    ];
    let selected: Vec<&str> = flags
        .iter()
        .filter(|(on, _)| *on)
        .map(|(_, name)| *name)
        .collect();
    match selected.len() {
        0 => Ok("langchain".into()),
        1 => Ok(selected[0].into()),
        _ => Err(anyhow::anyhow!(
            "Only one framework can be specified: {}",
            selected.join(", ")
        )),
    }
}

fn determine_project_path(args: &InitArgs) -> Result<(PathBuf, String)> {
    let cwd = std::env::current_dir().context("Failed to get current directory")?;
    if args.path == PathBuf::from(".") {
        if let Some(ref name) = args.name {
            validation::validate_project_name(name)?;
            let path = cwd.join(name);
            Ok((path, name.clone()))
        } else if args.interactive {
            Ok((cwd.clone(), "runagent-project".into()))
        } else {
            let dir = cwd
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("runagent-project")
                .to_string();
            Ok((cwd, dir))
        }
    } else {
        let project_path = args
            .path
            .canonicalize()
            .unwrap_or_else(|_| args.path.clone());
        let project_name = if let Some(ref name) = args.name {
            validation::validate_project_name(name)?;
            name.clone()
        } else {
            project_path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("runagent-project")
                .to_string()
        };
        validation::validate_project_name(&project_name)?;
        Ok((project_path, project_name))
    }
}

fn handle_interactive_mode(
    framework: &str,
    template: &str,
    output: &CliOutput,
) -> Result<(String, String)> {
    output.info("🎯 Interactive project setup");

    // Framework choice
    let final_framework = if framework == "langchain" {
        output.info("Available frameworks:");
        output.list_items(&[
            "1. langchain",
            "2. langgraph", 
            "3. llamaindex",
            "4. rust-langchain",
            "5. rust",
        ]);
        output.info("Using default: langchain");
        "langchain".into()
    } else {
        framework.to_string()
    };

    // Template choice
    let final_template = if template == "default" {
        let choices = get_available_templates(&final_framework);
        output.info(&format!("Templates for {}:", final_framework));
        output.list_items(&choices.iter().map(|s| s.as_str()).collect::<Vec<_>>());
        output.info("Using default: basic");
        "basic".into()
    } else {
        template.to_string()
    };

    Ok((final_framework, final_template))
}

fn get_available_templates(framework: &str) -> Vec<String> {
    match framework {
        "langchain" => vec!["basic", "advanced", "streaming"],
        "langgraph" => vec!["basic", "advanced", "graph"],
        "llamaindex" => vec!["basic", "rag", "chat"],
        "rust-langchain" => vec!["basic", "async"],
        "rust" => vec!["basic", "tokio", "axum"],
        _ => vec!["basic"],
    }
    .into_iter()
    .map(String::from)
    .collect()
}

fn handle_existing_path(path: &PathBuf, overwrite: bool, output: &CliOutput) -> Result<()> {
    if path.exists() {
        if path.is_file() {
            return Err(anyhow::anyhow!("Path exists and is a file: {}", path.display()));
        }
        if path.read_dir()?.next().is_some() {
            if !overwrite {
                output.error(&format!("Directory exists and is not empty: {}", path.display()));
                output.info("💡 Use --overwrite to force initialization");
                return Err(anyhow::anyhow!("Directory not empty"));
            } else {
                output.warning(&format!("Overwriting directory: {}", path.display()));
            }
        }
    }
    Ok(())
}

fn display_project_config(
    name: &str,
    path: &PathBuf,
    framework: &str,
    template: &str,
    output: &CliOutput,
) {
    output.info("🚀 Initializing project:");
    output.config_item("Name", name);
    output.config_item("Path", &path.display().to_string());
    output.config_item("Framework", framework);
    output.config_item("Template", template);
}

fn generate_project_files(
    project_path: &PathBuf,
    project_name: &str,
    framework: &str,
    template: &str,
    output: &CliOutput,
) -> Result<()> {
    output.info("📁 Creating project files...");

    match framework {
        "langchain" => generate_langchain_project(project_path, template)?,
        "langgraph" => generate_langgraph_project(project_path, template)?,
        "llamaindex" => generate_llamaindex_project(project_path, template)?,
        "rust-langchain" => generate_rust_langchain_project(project_path, project_name, template)?,
        "rust" => generate_rust_project(project_path, project_name, template)?,
        _ => return Err(anyhow::anyhow!("Unsupported framework: {}", framework)),
    }

    generate_common_files(project_path, project_name, framework)?;
    output.success("✅ Project files created!");
    Ok(())
}

fn generate_langchain_project(project_path: &PathBuf, template: &str) -> Result<()> {
    let main_py = match template {
        "basic" => get_langchain_basic_template(),
        "advanced" => get_langchain_advanced_template(),
        "streaming" => get_langchain_streaming_template(),
        _ => get_langchain_basic_template(),
    };
    fs::write(project_path.join("main.py"), main_py)?;

    let reqs = match template {
        "basic" => "langchain\nlangchain-openai\npython-dotenv",
        "advanced" => "langchain\nlangchain-openai\nlangchain-community\npython-dotenv\nfaiss-cpu",
        "streaming" => "langchain\nlangchain-openai\npython-dotenv\nasyncio",
        _ => "langchain\nlangchain-openai\npython-dotenv",
    };
    fs::write(project_path.join("requirements.txt"), reqs)?;
    fs::write(project_path.join(".env.example"), "OPENAI_API_KEY=your_api_key_here\n")?;
    Ok(())
}

fn generate_langgraph_project(project_path: &PathBuf, template: &str) -> Result<()> {
    let graph_py = match template {
        "basic" => get_langgraph_basic_template(),
        "advanced" => get_langgraph_advanced_template(),
        _ => get_langgraph_basic_template(),
    };
    fs::write(project_path.join("graph.py"), graph_py)?;
    fs::write(
        project_path.join("requirements.txt"),
        "langgraph\nlangchain\nlangchain-openai\npython-dotenv",
    )?;
    fs::write(project_path.join(".env.example"), "OPENAI_API_KEY=your_api_key_here\n")?;
    Ok(())
}

fn generate_llamaindex_project(project_path: &PathBuf, template: &str) -> Result<()> {
    let main_py = match template {
        "basic" => get_llamaindex_basic_template(),
        "rag" => get_llamaindex_rag_template(),
        _ => get_llamaindex_basic_template(),
    };
    fs::write(project_path.join("main.py"), main_py)?;
    fs::write(
        project_path.join("requirements.txt"),
        "llama-index\nllama-index-llms-openai\npython-dotenv",
    )?;
    fs::write(project_path.join(".env.example"), "OPENAI_API_KEY=your_api_key_here\n")?;
    Ok(())
}

fn generate_rust_langchain_project(
    project_path: &PathBuf,
    project_name: &str,
    template: &str,
) -> Result<()> {
    let cargo = format!(
        r#"[package]
name = "{}"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = {{ version = "1.0", features = ["full"] }}
serde = {{ version = "1.0", features = ["derive"] }}
serde_json = "1.0"
reqwest = {{ version = "0.11", features = ["json"] }}
anyhow = "1.0"
tracing = "0.1"
tracing-subscriber = "0.3"

# RunAgent SDK
runagent = {{ path = "../path/to/runagent" }}
"#,
        project_name
    );
    fs::write(project_path.join("Cargo.toml"), cargo)?;
    fs::create_dir_all(project_path.join("src"))?;

    let main_rs = match template {
        "basic" => get_rust_langchain_basic_template(),
        "async" => get_rust_langchain_async_template(),
        _ => get_rust_langchain_basic_template(),
    };
    fs::write(project_path.join("src/main.rs"), main_rs)?;
    fs::write(project_path.join(".env.example"), "OPENAI_API_KEY=your_api_key_here\n")?;
    Ok(())
}

fn generate_rust_project(
    project_path: &PathBuf,
    project_name: &str,
    template: &str,
) -> Result<()> {
    let deps = if template == "axum" {
        "axum = \"0.7\"\ntower = \"0.4\"\n"
    } else {
        ""
    };
    let cargo = format!(
        r#"[package]
name = "{}"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = {{ version = "1.0", features = ["full"] }}
serde = {{ version = "1.0", features = ["derive"] }}
serde_json = "1.0"
anyhow = "1.0"
{}
"#,
        project_name, deps
    );
    fs::write(project_path.join("Cargo.toml"), cargo)?;
    fs::create_dir_all(project_path.join("src"))?;

    let main_rs = match template {
        "basic" => get_rust_basic_template(),
        "tokio" => get_rust_tokio_template(),
        "axum" => get_rust_axum_template(),
        _ => get_rust_basic_template(),
    };
    fs::write(project_path.join("src/main.rs"), main_rs)?;
    Ok(())
}

fn generate_common_files(
    project_path: &PathBuf,
    project_name: &str,
    framework: &str,
) -> Result<()> {
    let config = json!({
        "agent_name": project_name,
        "description": format!("A RunAgent project using {}", framework),
        "framework": framework,
        "template": "basic",
        "version": "1.0.0",
        "created_at": Utc::now().to_rfc3339(),
        "agent_architecture": {
            "entrypoints": [{
                "file": if framework.starts_with("rust") { "src/main.rs" } else { "main.py" },
                "module": "run",
                "tag": "generic"
            }]
        },
        "env_vars": {}
    });
    fs::write(
        project_path.join("runagent.config.json"),
        serde_json::to_string_pretty(&config)?,
    )?;

    let readme = format!(
        r#"# {}

A RunAgent project using the {} framework.

## Setup

{}

## Usage

```bash
runagent serve .
runagent run --id <agent-id> --message='Hello World'
```

## Development

{}
"#,
        project_name,
        framework,
        if framework.starts_with("rust") {
            "1. Install Rust\n2. cargo build"
        } else {
            "1. pip install -r requirements.txt\n2. cp .env.example .env"
        },
        if framework.starts_with("rust") {
            "- Edit src/main.rs\n- cargo run\n- cargo test"
        } else {
            "- Edit main.py\n- python main.py"
        }
    );
    fs::write(project_path.join("README.md"), readme)?;

    let gitignore = if framework.starts_with("rust") {
        "/target/\nCargo.lock\n.env\n"
    } else {
        "__pycache__/\n*.pyc\n.env\n"
    };
    fs::write(project_path.join(".gitignore"), gitignore)?;
    Ok(())
}

fn show_next_steps(project_path: &PathBuf, framework: &str, output: &CliOutput) {
    let rel = project_path
        .strip_prefix(std::env::current_dir().unwrap_or_default())
        .unwrap_or(project_path);
    let cd = if rel != PathBuf::from(".") {
        format!("cd {}", rel.display())
    } else {
        "# already here".into()
    };
    
    // Fix the temporary value issue by creating owned strings
    let serve_command_rust = format!("runagent serve {}", rel.display());
    let serve_command_python = format!("runagent serve {}", rel.display());
    
    let steps = if framework.starts_with("rust") {
        vec![
            cd.as_str(),
            "cargo build",
            "cp .env.example .env",
            serve_command_rust.as_str(),
            "# in another shell:",
            "runagent run --id <agent-id> --message='Hello from Rust!'",
        ]
    } else {
        vec![
            cd.as_str(),
            "pip install -r requirements.txt",
            "cp .env.example .env",
            serve_command_python.as_str(),
            "# in another shell:",
            "runagent run --id <agent-id> --message='Hello World!'",
        ]
    };
    output.next_steps(&steps);
    output.separator();
    output.info("📖 Docs: https://docs.run-agent.ai/");
    output.info("🔗 Examples: https://github.com/runagent-dev/runagent/tree/main/examples");
}

// Embedded templates
fn get_langchain_basic_template() -> &'static str {
    r#"#!/usr/bin/env python3
"""
Basic LangChain Agent Template
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

load_dotenv()

def run(*args, **kwargs):
    """Main agent function"""
    # Get input message
    message = kwargs.get("message", "Hello from RunAgent!")
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Process message
    response = llm.invoke([HumanMessage(content=message)])
    
    return {
        "response": response.content,
        "input": message,
        "framework": "langchain"
    }

if __name__ == "__main__":
    result = run(message="Test message")
    print(result)
"#
}

fn get_langchain_advanced_template() -> &'static str {
    r#"#!/usr/bin/env python3
"""
Advanced LangChain Agent Template with Memory
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

load_dotenv()

# Global memory instance
memory = ConversationBufferMemory()

def run(*args, **kwargs):
    """Advanced agent with memory"""
    message = kwargs.get("message", "Hello from RunAgent!")
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create conversation chain
    conversation = ConversationChain(
        llm=llm,
        memory=memory,
        verbose=True
    )
    
    # Process message
    response = conversation.predict(input=message)
    
    return {
        "response": response,
        "input": message,
        "framework": "langchain",
        "memory_length": len(memory.chat_memory.messages),
        "template": "advanced"
    }

if __name__ == "__main__":
    result = run(message="What's the weather like?")
    print(result)
"#
}

fn get_langchain_streaming_template() -> &'static str {
    r#"#!/usr/bin/env python3
"""
Streaming LangChain Agent Template
"""
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

load_dotenv()

def run(*args, **kwargs):
    """Non-streaming version"""
    message = kwargs.get("message", "Hello from RunAgent!")
    
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    response = llm.invoke([HumanMessage(content=message)])
    
    return {
        "response": response.content,
        "input": message,
        "framework": "langchain",
        "streaming": False
    }

def run_stream(*args, **kwargs):
    """Streaming version"""
    message = kwargs.get("message", "Hello from RunAgent!")
    
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY"),
        streaming=True
    )
    
    # Stream response
    for chunk in llm.stream([HumanMessage(content=message)]):
        yield {
            "chunk": chunk.content,
            "type": "content",
            "framework": "langchain"
        }

if __name__ == "__main__":
    result = run(message="Tell me a joke")
    print(result)
"#
}

fn get_langgraph_basic_template() -> &'static str {
    r#"#!/usr/bin/env python3
"""
Basic LangGraph Agent Template
"""
import os
from dotenv import load_dotenv
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

load_dotenv()

def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Main agent reasoning node"""
    message = state.get("input", "Hello from RunAgent!")
    
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    response = llm.invoke([HumanMessage(content=message)])
    
    return {
        "output": response.content,
        "framework": "langgraph",
        "node": "agent"
    }

def create_graph():
    """Create the LangGraph workflow"""
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add edge to end
    workflow.add_edge("agent", END)
    
    return workflow.compile()

# Global graph instance
graph = create_graph()

def run(*args, **kwargs):
    """Main agent function using LangGraph"""
    input_data = kwargs.get("message", "Hello from RunAgent!")
    
    # Run the graph
    result = graph.invoke({"input": input_data})
    
    return {
        "response": result.get("output"),
        "input": input_data,
        "framework": "langgraph",
        "graph_result": result
    }

if __name__ == "__main__":
    result = run(message="Explain LangGraph")
    print(result)
"#
}

fn get_langgraph_advanced_template() -> &'static str {
    r#"#!/usr/bin/env python3
"""
Advanced LangGraph Agent with Tools
"""
import os
from dotenv import load_dotenv
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

load_dotenv()

def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Agent reasoning node"""
    message = state.get("input", "")
    
    llm = ChatOpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    response = llm.invoke([HumanMessage(content=message)]).content
    
    return {
        "output": response,
        "next": "end"
    }

def create_graph():
    """Create advanced LangGraph"""
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("agent", agent_node)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    workflow.add_edge("agent", END)
    
    return workflow.compile()

# Global graph instance
graph = create_graph()

def run(*args, **kwargs):
    """Advanced agent"""
    input_data = kwargs.get("message", "Hello from RunAgent!")
    
    result = graph.invoke({
        "input": input_data,
    })
    
    return {
        "response": result.get("output"),
        "input": input_data,
        "framework": "langgraph",
        "graph_result": result
    }

if __name__ == "__main__":
    result = run(message="search for python tutorials")
    print(result)
"#
}

fn get_llamaindex_basic_template() -> &'static str {
    r#"#!/usr/bin/env python3
"""
Basic LlamaIndex Agent Template
"""
import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Document
from llama_index.llms.openai import OpenAI

load_dotenv()

def run(*args, **kwargs):
    """Main agent function using LlamaIndex"""
    message = kwargs.get("message", "Hello from RunAgent!")
    
    # Initialize LLM
    llm = OpenAI(
        model="gpt-3.5-turbo",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create some sample documents
    documents = [
        Document(text="RunAgent is a platform for deploying AI agents."),
        Document(text="LlamaIndex is a framework for building LLM applications."),
    ]
    
    # Create index
    index = VectorStoreIndex.from_documents(documents)
    
    # Create query engine
    query_engine = index.as_query_engine(llm=llm)
    
    # Query the index
    response = query_engine.query(message)
    
    return {
        "response": str(response),
        "input": message,
        "framework": "llamaindex",
        "documents_count": len(documents)
    }

if __name__ == "__main__":
    result = run(message="What is RunAgent?")
    print(result)
"#
}

fn get_llamaindex_rag_template() -> &'static str {
    r#"#!/usr/bin/env python3
"""
LlamaIndex RAG Template
"""
import os
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, Document

load_dotenv()

def run(*args, **kwargs):
    """RAG-powered agent function"""
    message = kwargs.get("message", "What can you tell me about RunAgent?")
    
    documents = [
        Document(text="RunAgent is a platform for deploying AI agents."),
        Document(text="LlamaIndex specializes in RAG applications."),
    ]
    
    # Create index
    index = VectorStoreIndex.from_documents(documents)
    
    # Create query engine
    query_engine = index.as_query_engine(similarity_top_k=2)
    
    # Query with retrieval
    response = query_engine.query(message)
    
    return {
        "response": str(response),
        "input": message,
        "framework": "llamaindex",
        "template": "rag"
    }

if __name__ == "__main__":
    result = run(message="Tell me about RunAgent")
    print(result)
"#
}

fn get_rust_langchain_basic_template() -> &'static str {
    r#"use anyhow::Result;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<()> {
    println!("RunAgent Rust LangChain Basic Template");
    
    let result = run().await?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    
    Ok(())
}

async fn run() -> Result<serde_json::Value> {
    Ok(json!({
        "response": "Hello from Rust LangChain basic template!",
        "framework": "rust-langchain",
        "template": "basic"
    }))
}
"#
}

fn get_rust_langchain_async_template() -> &'static str {
    r#"use anyhow::Result;
use serde_json::json;
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() -> Result<()> {
    println!("RunAgent Rust LangChain Async Template");
    
    let result = run().await?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    
    Ok(())
}

async fn run() -> Result<serde_json::Value> {
    // Simulate async operation
    sleep(Duration::from_millis(100)).await;
    
    Ok(json!({
        "response": "Hello from Rust LangChain async template!",
        "framework": "rust-langchain",
        "template": "async",
        "async": true
    }))
}
"#
}

fn get_rust_basic_template() -> &'static str {
    r#"use anyhow::Result;
use serde_json::json;

fn main() -> Result<()> {
    println!("RunAgent Rust Basic Template");
    
    let result = run()?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    
    Ok(())
}

fn run() -> Result<serde_json::Value> {
    Ok(json!({
        "response": "Hello from Rust basic template!",
        "framework": "rust",
        "template": "basic"
    }))
}
"#
}

fn get_rust_tokio_template() -> &'static str {
    r#"use anyhow::Result;
use serde_json::json;
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() -> Result<()> {
    println!("RunAgent Rust Tokio Template");
    
    let result = run().await?;
    println!("{}", serde_json::to_string_pretty(&result)?);
    
    Ok(())
}

async fn run() -> Result<serde_json::Value> {
    sleep(Duration::from_millis(100)).await;
    
    Ok(json!({
        "response": "Hello from Rust tokio template!",
        "framework": "rust",
        "template": "tokio"
    }))
}
"#
}

fn get_rust_axum_template() -> &'static str {
    r#"use anyhow::Result;
use axum::{routing::get, Router, Json};
use serde_json::json;
use tokio::net::TcpListener;

#[tokio::main]
async fn main() -> Result<()> {
    println!("RunAgent Rust Axum Template");
    
    let app = Router::new()
        .route("/", get(hello))
        .route("/run", get(run_handler));
    
    let listener = TcpListener::bind("0.0.0.0:3000").await?;
    println!("Server running on http://0.0.0.0:3000");
    
    axum::serve(listener, app).await?;
    
    Ok(())
}

async fn hello() -> Json<serde_json::Value> {
    Json(json!({
        "message": "Hello from RunAgent Rust Axum template!",
        "framework": "rust",
        "template": "axum"
    }))
}

async fn run_handler() -> Json<serde_json::Value> {
    Json(run().await.unwrap_or_else(|_| json!({"error": "Failed to run"})))
}

async fn run() -> Result<serde_json::Value> {
    Ok(json!({
        "response": "Hello from Rust axum template!",
        "framework": "rust",
        "template": "axum"
    }))
}
"#
}