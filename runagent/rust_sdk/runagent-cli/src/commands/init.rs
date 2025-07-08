//! Init command implementation
//!
//! Initializes new RunAgent projects with support for multiple frameworks
//! including Python (LangChain, LangGraph, LlamaIndex) and Rust frameworks.

use crate::utils::{output::CliOutput, validation};
use anyhow::{Context, Result};
use clap::Args;
use chrono::Utc;
use serde_json::json;
use std::collections::HashMap;
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
    let (project_path, project_name) = determine_project_path(&args, output)?;

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

fn determine_project_path(args: &InitArgs, output: &CliOutput) -> Result<(PathBuf, String)> {
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
        "basic" => include_str!("../../../../../templates/langchain/basic/main.py"),
        "advanced" => include_str!("../../../../../templates/langchain/advanced/main.py"),
        "streaming" => include_str!("../../../../../templates/langchain/streaming/main.py"),
        _ => include_str!("../../../../../templates/langchain/basic/main.py"),
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
        "basic" => include_str!("../../../../../templates/langgraph/basic/graph.py"),
        "advanced" => include_str!("../../../../../templates/langgraph/advanced/graph.py"),
        _ => include_str!("../../../../../templates/langgraph/basic/graph.py"),
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
        "basic" => include_str!("../../../../../templates/llamaindex/basic/main.py"),
        "rag" => include_str!("../../../../../templates/llamaindex/rag/main.py"),
        _ => include_str!("../../../../../templates/llamaindex/basic/main.py"),
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
        "[package]\nname = \"{}\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[dependencies]\ntokio = {{ version = \"1.0\", features = [\"full\"] }}\nserde = {{ version = \"1.0\", features = [\"derive\"] }}\nserde_json = \"1.0\"\nreqwest = {{ version = \"0.11\", features = [\"json\"] }}\nanyhow = \"1.0\"\ntracing = \"0.1\"\ntracing-subscriber = \"0.3\"\n\n# RunAgent SDK\nrunagent = {{ path = \"../path/to/runagent\" }}\n",
        project_name
    );
    fs::write(project_path.join("Cargo.toml"), cargo)?;
    fs::create_dir_all(project_path.join("src"))?;

    let main_rs = match template {
        "basic" => include_str!("../../../../../templates/rust-langchain/basic/main.rs"),
        "async" => include_str!("../../../../../templates/rust-langchain/async/main.rs"),
        _ => include_str!("../../../../../templates/rust-langchain/basic/main.rs"),
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
        "[package]\nname = \"{}\"\nversion = \"0.1.0\"\nedition = \"2021\"\n\n[dependencies]\ntokio = {{ version = \"1.0\", features = [\"full\"] }}\nserde = {{ version = \"1.0\", features = [\"derive\"] }}\nserde_json = \"1.0\"\nanyhow = \"1.0\"\n{}",
        project_name, deps
    );
    fs::write(project_path.join("Cargo.toml"), cargo)?;
    fs::create_dir_all(project_path.join("src"))?;

    let main_rs = match template {
        "basic" => include_str!("../../../../../templates/rust/basic/main.rs"),
        "tokio" => include_str!("../../../../../templates/rust/tokio/main.rs"),
        "axum" => include_str!("../../../../../templates/rust/axum/main.rs"),
        _ => include_str!("../../../../../templates/rust/basic/main.rs"),
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
        "# {}\n\nA RunAgent project using the {} framework.\n\n## Setup\n\n{}\n\n## Usage\n\n```bash\nrunagent serve .\nrunagent run --id <agent-id> --message='Hello World'\n```\n\n## Development\n\n{}\n",
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
    let steps = if framework.starts_with("rust") {
        vec![
            &cd,
            "cargo build",
            "cp .env.example .env",
            &format!("runagent serve {}", rel.display()),
            "# in another shell:",
            "runagent run --id <agent-id> --message='Hello from Rust!'",
        ]
    } else {
        vec![
            &cd,
            "pip install -r requirements.txt",
            "cp .env.example .env",
            &format!("runagent serve {}", rel.display()),
            "# in another shell:",
            "runagent run --id <agent-id> --message='Hello World!'",
        ]
    };
    output.next_steps(&steps);
    output.separator();
    output.info("📖 Docs: https://docs.run-agent.ai/");
    output.info("🔗 Examples: https://github.com/runagent-dev/runagent/tree/main/examples");
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_determine_framework() {
        let args = InitArgs {
            path: PathBuf::from("."),
            template: "basic".into(),
            interactive: false,
            overwrite: false,
            langchain: true,
            langgraph: false,
            llamaindex: false,
            rust_langchain: false,
            rust: false,
            name: None,
        };
        assert_eq!(determine_framework(&args).unwrap(), "langchain");
    }

    #[test]
    fn test_multiple_frameworks_error() {
        let args = InitArgs {
            path: PathBuf::from("."),
            template: "basic".into(),
            interactive: false,
            overwrite: false,
            langchain: true,
            langgraph: true,
            llamaindex: false,
            rust_langchain: false,
            rust: false,
            name: None,
        };
        assert!(determine_framework(&args).is_err());
    }

    #[test]
    fn test_validate_project_name() {
        assert!(validation::validate_project_name("valid").is_ok());
        assert!(validation::validate_project_name("").is_err());
    }

    #[tokio::test]
    async fn test_generate_langchain_project() {
        let tmp = TempDir::new().unwrap();
        generate_langchain_project(tmp.path(), "basic").unwrap();
        assert!(tmp.path().join("main.py").exists());
        assert!(tmp.path().join("requirements.txt").exists());
    }

    #[tokio::test]
    async fn test_generate_rust_project() {
        let tmp = TempDir::new().unwrap();
        generate_rust_project(tmp.path(), "proj", "basic").unwrap();
        assert!(tmp.path().join("Cargo.toml").exists());
        assert!(tmp.path().join("src/main.rs").exists());
    }
}
