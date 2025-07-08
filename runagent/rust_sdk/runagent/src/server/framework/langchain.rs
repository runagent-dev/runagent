//! LangChain-specific executor
//!
//! This executor provides specialized handling for LangChain agents and chains,
//! with support for common LangChain patterns like invoke, stream, and batch operations.

use super::{FrameworkExecutor, GenericExecutor};
use crate::types::{RunAgentError, RunAgentResult, EntryPoint};
use futures::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::pin::Pin;

/// LangChain-specific executor with support for LangChain patterns
pub struct LangChainExecutor {
    /// Generic executor for fallback functionality
    generic: GenericExecutor,
    /// Agent directory
    agent_dir: PathBuf,
    /// Reserved LangChain entrypoint tags
    reserved_tags: Vec<String>,
}

impl LangChainExecutor {
    /// Create a new LangChain executor
    pub fn new<P: AsRef<Path>>(agent_dir: P) -> RunAgentResult<Self> {
        let agent_dir = agent_dir.as_ref().to_path_buf();
        let generic = GenericExecutor::new(&agent_dir)?;

        Ok(Self {
            generic,
            agent_dir,
            reserved_tags: vec![
                "invoke".to_string(),
                "stream".to_string(),
                "stream_token".to_string(),
                "batch".to_string(),
                "ainvoke".to_string(),
                "astream".to_string(),
                "abatch".to_string(),
            ],
        })
    }

    /// Create a new LangChain executor with verbose logging
    pub fn with_verbose<P: AsRef<Path>>(agent_dir: P, verbose: bool) -> RunAgentResult<Self> {
        let agent_dir = agent_dir.as_ref().to_path_buf();
        let generic = GenericExecutor::with_verbose(&agent_dir, verbose)?;

        Ok(Self {
            generic,
            agent_dir,
            reserved_tags: vec![
                "invoke".to_string(),
                "stream".to_string(),
                "stream_token".to_string(),
                "batch".to_string(),
                "ainvoke".to_string(),
                "astream".to_string(),
                "abatch".to_string(),
            ],
        })
    }

    /// Handle LangChain-specific invoke pattern
    fn handle_invoke(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        tracing::info!("Executing LangChain invoke: {}", entrypoint.tag);

        // LangChain invoke typically takes a single input or a dict
        let langchain_input = if !input_kwargs.is_empty() {
            // Use kwargs as the input dict
            Value::Object(input_kwargs.iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect())
        } else if !input_args.is_empty() {
            // Use first arg as input
            input_args[0].clone()
        } else {
            Value::Object(serde_json::Map::new())
        };

        // Execute with generic executor but add LangChain-specific metadata
        let mut result = self.generic.execute(entrypoint, input_args, input_kwargs)?;
        
        if let Some(obj) = result.as_object_mut() {
            obj.insert("framework".to_string(), Value::String("langchain".to_string()));
            obj.insert("method".to_string(), Value::String("invoke".to_string()));
            obj.insert("langchain_input".to_string(), langchain_input);
            
            // Add LangChain-specific result structure
            obj.insert("langchain_result".to_string(), serde_json::json!({
                "type": "invoke_response",
                "content": "Mock LangChain invoke response",
                "usage_metadata": {
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "total_tokens": 30
                },
                "response_metadata": {
                    "model_name": "mock-model",
                    "system_fingerprint": "mock-fingerprint"
                }
            }));
        }

        Ok(result)
    }

    /// Handle LangChain-specific streaming patterns
    fn handle_stream(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        use futures::stream;
        
        tracing::info!("Executing LangChain stream: {}", entrypoint.tag);

        let langchain_input = if !input_kwargs.is_empty() {
            Value::Object(input_kwargs.iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect())
        } else if !input_args.is_empty() {
            input_args[0].clone()
        } else {
            Value::Object(serde_json::Map::new())
        };

        // Create LangChain-specific streaming response
        let chunks = vec![
            Ok(serde_json::json!({
                "type": "langchain_stream_start",
                "data": {
                    "input": langchain_input,
                    "entrypoint": entrypoint.tag
                },
                "metadata": {
                    "framework": "langchain",
                    "stream_type": "content"
                }
            })),
            Ok(serde_json::json!({
                "type": "langchain_content",
                "data": {
                    "content": "Hello",
                    "additional_kwargs": {},
                    "response_metadata": {}
                },
                "metadata": {
                    "chunk_index": 0
                }
            })),
            Ok(serde_json::json!({
                "type": "langchain_content", 
                "data": {
                    "content": " from",
                    "additional_kwargs": {},
                    "response_metadata": {}
                },
                "metadata": {
                    "chunk_index": 1
                }
            })),
            Ok(serde_json::json!({
                "type": "langchain_content",
                "data": {
                    "content": " LangChain!",
                    "additional_kwargs": {},
                    "response_metadata": {}
                },
                "metadata": {
                    "chunk_index": 2
                }
            })),
            Ok(serde_json::json!({
                "type": "langchain_stream_end",
                "data": {
                    "finish_reason": "stop",
                    "usage_metadata": {
                        "input_tokens": 10,
                        "output_tokens": 15,
                        "total_tokens": 25
                    }
                },
                "metadata": {
                    "framework": "langchain",
                    "final": true
                }
            })),
        ];

        Ok(Box::pin(stream::iter(chunks)))
    }

    /// Handle LangChain token streaming
    fn handle_stream_token(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        use futures::stream;
        
        tracing::info!("Executing LangChain token stream: {}", entrypoint.tag);

        // Token-level streaming with individual tokens
        let tokens = vec!["Hello", " ", "from", " ", "Lang", "Chain", "!", " ", "This", " ", "is", " ", "token", " ", "streaming", "."];
        
        let mut chunks = vec![
            Ok(serde_json::json!({
                "type": "langchain_token_stream_start",
                "data": {
                    "input": input_kwargs,
                    "entrypoint": entrypoint.tag
                },
                "metadata": {
                    "framework": "langchain",
                    "stream_type": "token"
                }
            }))
        ];

        for (i, token) in tokens.iter().enumerate() {
            chunks.push(Ok(serde_json::json!({
                "type": "langchain_token",
                "data": {
                    "token": token,
                    "token_index": i,
                    "is_final": false
                },
                "metadata": {
                    "chunk_index": i
                }
            })));
        }

        chunks.push(Ok(serde_json::json!({
            "type": "langchain_token_stream_end",
            "data": {
                "total_tokens": tokens.len(),
                "finish_reason": "stop"
            },
            "metadata": {
                "framework": "langchain",
                "final": true
            }
        })));

        Ok(Box::pin(stream::iter(chunks)))
    }

    /// Handle LangChain batch operations
    fn handle_batch(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        tracing::info!("Executing LangChain batch: {}", entrypoint.tag);

        // Batch operations process multiple inputs
        let batch_inputs = if let Some(inputs) = input_kwargs.get("inputs") {
            inputs.as_array().unwrap_or(&vec![]).clone()
        } else if !input_args.is_empty() && input_args[0].is_array() {
            input_args[0].as_array().unwrap_or(&vec![]).clone()
        } else {
            vec![serde_json::json!({"default": "input"})]
        };

        let batch_results: Vec<Value> = batch_inputs.iter().enumerate().map(|(i, input)| {
            serde_json::json!({
                "index": i,
                "input": input,
                "output": {
                    "content": format!("Mock batch response for input {}", i),
                    "metadata": {
                        "batch_index": i,
                        "processed_at": chrono::Utc::now().to_rfc3339()
                    }
                }
            })
        }).collect();

        let mut result = self.generic.execute(entrypoint, input_args, input_kwargs)?;
        
        if let Some(obj) = result.as_object_mut() {
            obj.insert("framework".to_string(), Value::String("langchain".to_string()));
            obj.insert("method".to_string(), Value::String("batch".to_string()));
            obj.insert("batch_size".to_string(), Value::Number(batch_inputs.len().into()));
            obj.insert("batch_results".to_string(), Value::Array(batch_results));
        }

        Ok(result)
    }
}

impl FrameworkExecutor for LangChainExecutor {
    fn execute(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        match entrypoint.tag.as_str() {
            "invoke" | "ainvoke" => self.handle_invoke(entrypoint, input_args, input_kwargs),
            "batch" | "abatch" => self.handle_batch(entrypoint, input_args, input_kwargs),
            _ => {
                // Fall back to generic execution with LangChain metadata
                let mut result = self.generic.execute(entrypoint, input_args, input_kwargs)?;
                
                if let Some(obj) = result.as_object_mut() {
                    obj.insert("framework".to_string(), Value::String("langchain".to_string()));
                    obj.insert("executor".to_string(), Value::String("LangChainExecutor".to_string()));
                }
                
                Ok(result)
            }
        }
    }

    fn execute_stream(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        match entrypoint.tag.as_str() {
            "stream" | "astream" => self.handle_stream(entrypoint, input_args, input_kwargs),
            "stream_token" => self.handle_stream_token(entrypoint, input_args, input_kwargs),
            _ => {
                // Fall back to generic streaming with LangChain metadata
                self.generic.execute_stream(entrypoint, input_args, input_kwargs)
            }
        }
    }

    fn get_entrypoints(&self) -> Vec<String> {
        vec![
            "invoke".to_string(),
            "stream".to_string(),
            "stream_token".to_string(),
            "batch".to_string(),
            "ainvoke".to_string(),
            "astream".to_string(),
            "abatch".to_string(),
            // Include generic entrypoints as fallback
            "run".to_string(),
            "process".to_string(),
        ]
    }

    fn framework_name(&self) -> &'static str {
        "langchain"
    }

    fn supports_entrypoint(&self, entrypoint: &EntryPoint) -> bool {
        self.reserved_tags.contains(&entrypoint.tag) || self.generic.supports_entrypoint(entrypoint)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::fs;

    fn create_test_langchain_agent() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        // Create a LangChain-style agent file
        fs::write(
            agent_path.join("agent.py"),
            r#"
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI

def invoke(input_data):
    # Mock LangChain invoke
    return {"output": f"LangChain response to: {input_data}"}

def stream(input_data):
    # Mock LangChain streaming
    for chunk in ["Hello", " from", " LangChain!"]:
        yield {"content": chunk}

def batch(inputs):
    # Mock LangChain batch
    return [{"output": f"Response to {inp}"} for inp in inputs]
"#,
        ).unwrap();

        temp_dir
    }

    #[test]
    fn test_langchain_executor_creation() {
        let temp_dir = TempDir::new().unwrap();
        let executor = LangChainExecutor::new(temp_dir.path());
        assert!(executor.is_ok());
    }

    #[test]
    fn test_invoke_execution() {
        let temp_dir = create_test_langchain_agent();
        let executor = LangChainExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "agent.py".to_string(),
            module: "invoke".to_string(),
            tag: "invoke".to_string(),
        };
        
        let input_args = vec![];
        let mut input_kwargs = HashMap::new();
        input_kwargs.insert("input".to_string(), serde_json::json!("test message"));
        
        let result = executor.execute(&entrypoint, &input_args, &input_kwargs);
        assert!(result.is_ok());
        
        let response = result.unwrap();
        assert_eq!(response.get("framework").and_then(|v| v.as_str()), Some("langchain"));
        assert_eq!(response.get("method").and_then(|v| v.as_str()), Some("batch"));
        assert!(response.get("batch_results").is_some());
    }

    #[test]
    fn test_framework_name() {
        let temp_dir = TempDir::new().unwrap();
        let executor = LangChainExecutor::new(temp_dir.path()).unwrap();
        assert_eq!(executor.framework_name(), "langchain");
    }

    #[test]
    fn test_supported_entrypoints() {
        let temp_dir = TempDir::new().unwrap();
        let executor = LangChainExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoints = executor.get_entrypoints();
        assert!(entrypoints.contains(&"invoke".to_string()));
        assert!(entrypoints.contains(&"stream".to_string()));
        assert!(entrypoints.contains(&"batch".to_string()));
    }

    #[test]
    fn test_fallback_to_generic() {
        let temp_dir = create_test_langchain_agent();
        let executor = LangChainExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "agent.py".to_string(),
            module: "custom_function".to_string(),
            tag: "custom".to_string(),
        };
        
        let input_args = vec![];
        let input_kwargs = HashMap::new();
        
        let result = executor.execute(&entrypoint, &input_args, &input_kwargs);
        assert!(result.is_ok());
        
        let response = result.unwrap();
        assert_eq!(response.get("framework").and_then(|v| v.as_str()), Some("langchain"));
        assert_eq!(response.get("executor").and_then(|v| v.as_str()), Some("LangChainExecutor"));
    }
}_eq!(response.get("method").and_then(|v| v.as_str()), Some("invoke"));
    }

    #[test]
    fn test_stream_execution() {
        let temp_dir = create_test_langchain_agent();
        let executor = LangChainExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "agent.py".to_string(),
            module: "stream".to_string(),
            tag: "stream".to_string(),
        };
        
        let input_args = vec![];
        let mut input_kwargs = HashMap::new();
        input_kwargs.insert("input".to_string(), serde_json::json!("test message"));
        
        let result = executor.execute_stream(&entrypoint, &input_args, &input_kwargs);
        assert!(result.is_ok());
    }

    #[test]
    fn test_batch_execution() {
        let temp_dir = create_test_langchain_agent();
        let executor = LangChainExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "agent.py".to_string(),
            module: "batch".to_string(),
            tag: "batch".to_string(),
        };
        
        let input_args = vec![];
        let mut input_kwargs = HashMap::new();
        input_kwargs.insert("inputs".to_string(), serde_json::json!(["input1", "input2"]));
        
        let result = executor.execute(&entrypoint, &input_args, &input_kwargs);
        assert!(result.is_ok());
        
        let response = result.unwrap();
        assert_eq!(response.get("framework").and_then(|v| v.as_str()), Some("langchain"));
        assert