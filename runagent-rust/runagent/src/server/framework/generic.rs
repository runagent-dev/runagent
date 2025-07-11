//! Generic executor for any Python framework
//!
//! This executor provides a framework-agnostic way to execute Python functions
//! and can be used as a fallback for any AI agent framework.

use super::FrameworkExecutor;
use crate::types::{RunAgentError, RunAgentResult, EntryPoint};
use crate::utils::imports::ImportResolver;
use futures::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::pin::Pin;

/// Generic executor for any Python framework
pub struct GenericExecutor {
    agent_dir: PathBuf,
    import_resolver: ImportResolver,
    reserved_tags: Vec<String>,
}

impl GenericExecutor {
    /// Create a new generic executor
    pub fn new<P: AsRef<Path>>(agent_dir: P) -> RunAgentResult<Self> {
        let agent_dir = agent_dir.as_ref().to_path_buf();
        let import_resolver = ImportResolver::new(&agent_dir)?;

        Ok(Self {
            agent_dir,
            import_resolver,
            reserved_tags: vec![], // No reserved tags for generic
        })
    }

    /// Create a new generic executor with verbose logging
    pub fn with_verbose<P: AsRef<Path>>(agent_dir: P, verbose: bool) -> RunAgentResult<Self> {
        let agent_dir = agent_dir.as_ref().to_path_buf();
        let import_resolver = ImportResolver::with_verbose(&agent_dir, verbose)?;

        Ok(Self {
            agent_dir,
            import_resolver,
            reserved_tags: vec![],
        })
    }

    /// Resolve an entrypoint to its executable function reference
    fn resolve_entrypoint(&self, entrypoint: &EntryPoint) -> RunAgentResult<String> {
        let entrypoint_filepath = self.agent_dir.join(&entrypoint.file);
        
        if !entrypoint_filepath.exists() {
            return Err(RunAgentError::validation(format!(
                "Entrypoint file not found: {}",
                entrypoint_filepath.display()
            )));
        }

        // Split module into primary and secondary attributes
        let module_parts: Vec<&str> = entrypoint.module.split('.').collect();
        let primary_module = module_parts[0];
        let secondary_attrs = &module_parts[1..];

        // Create the function reference path
        let mut function_ref = primary_module.to_string();
        for attr in secondary_attrs {
            function_ref.push('.');
            function_ref.push_str(attr);
        }

        // In a real implementation, this would validate that the function exists
        // For now, we just return the constructed reference
        tracing::debug!(
            "Resolved entrypoint {} -> {} in file {}",
            entrypoint.tag,
            function_ref,
            entrypoint_filepath.display()
        );

        Ok(function_ref)
    }

    /// Create a mock execution result
    fn create_execution_result(
        &self,
        entrypoint: &EntryPoint,
        function_ref: &str,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> Value {
        serde_json::json!({
            "success": true,
            "framework": "generic",
            "executor": "GenericExecutor",
            "entrypoint": {
                "tag": entrypoint.tag,
                "file": entrypoint.file,
                "module": entrypoint.module,
                "function_ref": function_ref
            },
            "input": {
                "args": input_args,
                "kwargs": input_kwargs
            },
            "result": {
                "type": "mock_response",
                "content": "This is a mock response from the Generic executor. In a real implementation, this would execute the Python function using PyO3 or subprocess.",
                "timestamp": chrono::Utc::now().to_rfc3339(),
                "agent_dir": self.agent_dir.to_string_lossy()
            },
            "metadata": {
                "note": "Python integration via PyO3 needed for actual execution",
                "execution_method": "mock",
                "rust_version": env!("CARGO_PKG_VERSION")
            }
        })
    }

    /// Get the runner function for a specific entrypoint
    pub fn get_runner(&self, entrypoint: &EntryPoint) -> RunAgentResult<impl Fn(&[Value], &HashMap<String, Value>) -> RunAgentResult<Value>> {
        let function_ref = self.resolve_entrypoint(entrypoint)?;
        let entrypoint_clone = entrypoint.clone();
        
        Ok(move |input_args: &[Value], input_kwargs: &HashMap<String, Value>| -> RunAgentResult<Value> {
            tracing::debug!("Executing non-streaming entrypoint: {}", entrypoint_clone.tag);
            
            // In a real implementation, this would:
            // 1. Set up Python environment
            // 2. Import the module
            // 3. Call the function with input_args and input_kwargs
            // 4. Return the result
            
            // For now, return a mock result
            Ok(serde_json::json!({
                "success": true,
                "result": format!("Mock execution of {} with {} args and {} kwargs", 
                    function_ref, input_args.len(), input_kwargs.len()),
                "function": function_ref,
                "entrypoint": entrypoint_clone.tag
            }))
        })
    }

    /// Get the streaming runner function for a specific entrypoint
    pub fn get_stream_runner(&self, entrypoint: &EntryPoint) -> RunAgentResult<impl Fn(&[Value], &HashMap<String, Value>) -> Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        let function_ref = self.resolve_entrypoint(entrypoint)?;
        let entrypoint_clone = entrypoint.clone();
        
        Ok(move |input_args: &[Value], input_kwargs: &HashMap<String, Value>| -> Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>> {
            use futures::stream;
            
            tracing::debug!("Executing streaming entrypoint: {}", entrypoint_clone.tag);
            
            // Create a mock stream that yields several chunks
            let chunks = vec![
                Ok(serde_json::json!({
                    "chunk_id": 1,
                    "type": "start",
                    "data": "Starting execution...",
                    "function": function_ref,
                    "entrypoint": entrypoint_clone.tag
                })),
                Ok(serde_json::json!({
                    "chunk_id": 2,
                    "type": "processing", 
                    "data": "Processing input...",
                    "input_summary": {
                        "args_count": input_args.len(),
                        "kwargs_count": input_kwargs.len()
                    }
                })),
                Ok(serde_json::json!({
                    "chunk_id": 3,
                    "type": "progress",
                    "data": "Mock streaming progress...",
                    "progress": 50
                })),
                Ok(serde_json::json!({
                    "chunk_id": 4,
                    "type": "result",
                    "data": format!("Mock streaming result from {}", function_ref),
                    "progress": 100
                })),
                Ok(serde_json::json!({
                    "chunk_id": 5,
                    "type": "complete",
                    "data": "Stream completed",
                    "final": true
                })),
            ];

            Box::pin(stream::iter(chunks))
        })
    }
}

impl FrameworkExecutor for GenericExecutor {
    fn execute(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        let function_ref = self.resolve_entrypoint(entrypoint)?;
        
        tracing::info!("Executing generic entrypoint: {} -> {}", entrypoint.tag, function_ref);
        
        // Create execution result
        Ok(self.create_execution_result(entrypoint, &function_ref, input_args, input_kwargs))
    }

    fn execute_stream(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        use futures::stream;
        
        let function_ref = self.resolve_entrypoint(entrypoint)?;
        
        tracing::info!("Executing generic streaming entrypoint: {} -> {}", entrypoint.tag, function_ref);
        
        // Create a mock stream
        let entrypoint_clone = entrypoint.clone();
        let function_ref_clone = function_ref.clone();
        let input_args_clone = input_args.to_vec();
        let input_kwargs_clone = input_kwargs.clone();
        
        let stream = stream::iter(vec![
            Ok(serde_json::json!({
                "chunk": 1,
                "type": "initialization",
                "data": "Initializing streaming execution...",
                "entrypoint": entrypoint_clone.tag,
                "function": function_ref_clone
            })),
            Ok(serde_json::json!({
                "chunk": 2,
                "type": "input_processing",
                "data": "Processing input arguments...",
                "input_summary": {
                    "args": input_args_clone.len(),
                    "kwargs": input_kwargs_clone.len()
                }
            })),
            Ok(serde_json::json!({
                "chunk": 3,
                "type": "execution",
                "data": "Mock streaming execution in progress...",
                "progress": 33
            })),
            Ok(serde_json::json!({
                "chunk": 4,
                "type": "execution",
                "data": "Continuing mock execution...",
                "progress": 66
            })),
            Ok(serde_json::json!({
                "chunk": 5,
                "type": "result",
                "data": format!("Mock streaming result from {}", function_ref),
                "progress": 100
            })),
            Ok(serde_json::json!({
                "chunk": 6,
                "type": "completion",
                "data": "Streaming execution completed",
                "final": true,
                "metadata": {
                    "total_chunks": 6,
                    "execution_method": "mock"
                }
            })),
        ]);

        Ok(Box::pin(stream))
    }

    fn get_entrypoints(&self) -> Vec<String> {
        // Generic executor supports any entrypoint
        vec![
            "generic".to_string(),
            "generic_stream".to_string(),
            "run".to_string(),
            "run_stream".to_string(),
            "main".to_string(),
            "execute".to_string(),
            "process".to_string(),
        ]
    }

    fn framework_name(&self) -> &'static str {
        "generic"
    }

    fn supports_entrypoint(&self, _entrypoint: &EntryPoint) -> bool {
        // Generic executor supports any entrypoint
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    fn create_test_agent() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        // Create a simple main.py file
        fs::write(
            agent_path.join("main.py"),
            r#"
def run(*args, **kwargs):
    return {"result": "Hello from Python!", "args": args, "kwargs": kwargs}

def run_stream(*args, **kwargs):
    for i in range(3):
        yield {"chunk": i, "data": f"Streaming chunk {i}"}
"#,
        ).unwrap();

        temp_dir
    }

    #[test]
    fn test_generic_executor_creation() {
        let temp_dir = TempDir::new().unwrap();
        let executor = GenericExecutor::new(temp_dir.path());
        assert!(executor.is_ok());
    }

    #[test]
    fn test_entrypoint_resolution() {
        let temp_dir = create_test_agent();
        let executor = GenericExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "main.py".to_string(),
            module: "run".to_string(),
            tag: "generic".to_string(),
        };
        
        let result = executor.resolve_entrypoint(&entrypoint);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), "run");
    }

    #[test]
    fn test_execution() {
        let temp_dir = create_test_agent();
        let executor = GenericExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "main.py".to_string(),
            module: "run".to_string(),
            tag: "generic".to_string(),
        };
        
        let input_args = vec![serde_json::json!("test")];
        let mut input_kwargs = HashMap::new();
        input_kwargs.insert("key".to_string(), serde_json::json!("value"));
        
        let result = executor.execute(&entrypoint, &input_args, &input_kwargs);
        assert!(result.is_ok());
        
        let response = result.unwrap();
        assert!(response.get("success").and_then(|v| v.as_bool()).unwrap_or(false));
    }

    #[test]
    fn test_streaming_execution() {
        let temp_dir = create_test_agent();
        let executor = GenericExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "main.py".to_string(),
            module: "run_stream".to_string(),
            tag: "generic_stream".to_string(),
        };
        
        let input_args = vec![];
        let input_kwargs = HashMap::new();
        
        let result = executor.execute_stream(&entrypoint, &input_args, &input_kwargs);
        assert!(result.is_ok());
        
        // In a real test, we would consume the stream and verify chunks
        // For now, just verify that we get a stream back
    }

    #[test]
    fn test_framework_name() {
        let temp_dir = TempDir::new().unwrap();
        let executor = GenericExecutor::new(temp_dir.path()).unwrap();
        assert_eq!(executor.framework_name(), "generic");
    }

    #[test]
    fn test_supports_any_entrypoint() {
        let temp_dir = TempDir::new().unwrap();
        let executor = GenericExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "main.py".to_string(),
            module: "any_function".to_string(),
            tag: "custom_tag".to_string(),
        };
        
        assert!(executor.supports_entrypoint(&entrypoint));
    }

    #[test]
    fn test_verbose_mode() {
        let temp_dir = TempDir::new().unwrap();
        let executor = GenericExecutor::with_verbose(temp_dir.path(), true);
        assert!(executor.is_ok());
    }
}