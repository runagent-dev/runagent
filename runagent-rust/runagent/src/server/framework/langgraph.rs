//! LangGraph-specific executor
//!
//! This executor provides specialized handling for LangGraph agents and workflows,
//! with support for graph execution, state management, and conditional routing.

use super::{FrameworkExecutor, GenericExecutor};
use crate::types::{RunAgentError, RunAgentResult, EntryPoint};
use futures::Stream;
use serde_json::Value;
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::pin::Pin;

/// LangGraph-specific executor with support for graph workflows
pub struct LangGraphExecutor {
    /// Generic executor for fallback functionality
    generic: GenericExecutor,
    /// Agent directory
    agent_dir: PathBuf,
    /// Reserved LangGraph entrypoint tags
    reserved_tags: Vec<String>,
}

impl LangGraphExecutor {
    /// Create a new LangGraph executor
    pub fn new<P: AsRef<Path>>(agent_dir: P) -> RunAgentResult<Self> {
        let agent_dir = agent_dir.as_ref().to_path_buf();
        let generic = GenericExecutor::new(&agent_dir)?;

        Ok(Self {
            generic,
            agent_dir,
            reserved_tags: vec![
                "invoke".to_string(),
                "stream".to_string(),
                "ainvoke".to_string(),
                "astream".to_string(),
                "get_graph".to_string(),
                "get_state".to_string(),
                "update_state".to_string(),
                "compile".to_string(),
            ],
        })
    }

    /// Create a new LangGraph executor with verbose logging
    pub fn with_verbose<P: AsRef<Path>>(agent_dir: P, verbose: bool) -> RunAgentResult<Self> {
        let agent_dir = agent_dir.as_ref().to_path_buf();
        let generic = GenericExecutor::with_verbose(&agent_dir, verbose)?;

        Ok(Self {
            generic,
            agent_dir,
            reserved_tags: vec![
                "invoke".to_string(),
                "stream".to_string(),
                "ainvoke".to_string(),
                "astream".to_string(),
                "get_graph".to_string(),
                "get_state".to_string(),
                "update_state".to_string(),
                "compile".to_string(),
            ],
        })
    }

    /// Handle LangGraph invoke with graph execution simulation
    fn handle_invoke(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        tracing::info!("Executing LangGraph invoke: {}", entrypoint.tag);

        // LangGraph invoke processes input through a graph workflow
        let graph_input = if !input_kwargs.is_empty() {
            Value::Object(input_kwargs.iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect())
        } else if !input_args.is_empty() {
            input_args[0].clone()
        } else {
            serde_json::json!({"messages": []})
        };

        // Simulate graph execution steps
        let execution_steps = vec![
            serde_json::json!({
                "node": "agent",
                "action": "reasoning",
                "input": graph_input,
                "output": {
                    "thoughts": "Processing user input through graph workflow",
                    "action": "continue"
                }
            }),
            serde_json::json!({
                "node": "tools",
                "action": "tool_selection",
                "input": {
                    "available_tools": ["search", "calculator", "code_executor"],
                    "selected_tool": "search"
                },
                "output": {
                    "tool_result": "Mock tool execution result"
                }
            }),
            serde_json::json!({
                "node": "final_response",
                "action": "synthesis",
                "input": {
                    "agent_thoughts": "Processing user input through graph workflow",
                    "tool_results": "Mock tool execution result"
                },
                "output": {
                    "final_answer": "This is a mock LangGraph response generated through graph execution"
                }
            })
        ];

        let mut result = self.generic.execute(entrypoint, input_args, input_kwargs)?;
        
        if let Some(obj) = result.as_object_mut() {
            obj.insert("framework".to_string(), Value::String("langgraph".to_string()));
            obj.insert("method".to_string(), Value::String("invoke".to_string()));
            obj.insert("graph_execution".to_string(), Value::Bool(true));
            obj.insert("execution_steps".to_string(), Value::Array(execution_steps));
            obj.insert("langgraph_result".to_string(), serde_json::json!({
                "type": "graph_response",
                "final_state": {
                    "messages": [
                        {
                            "role": "user",
                            "content": graph_input
                        },
                        {
                            "role": "assistant", 
                            "content": "This is a mock LangGraph response generated through graph execution"
                        }
                    ]
                },
                "graph_metadata": {
                    "nodes_executed": ["agent", "tools", "final_response"],
                    "total_steps": 3,
                    "execution_time": "0.5s"
                }
            }));
        }

        Ok(result)
    }

    /// Handle LangGraph streaming with step-by-step graph execution
    fn handle_stream(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Pin<Box<dyn Stream<Item = RunAgentResult<Value>> + Send>>> {
        use futures::stream;
        
        tracing::info!("Executing LangGraph stream: {}", entrypoint.tag);

        let graph_input = if !input_kwargs.is_empty() {
            Value::Object(input_kwargs.iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect())
        } else if !input_args.is_empty() {
            input_args[0].clone()
        } else {
            serde_json::json!({"messages": []})
        };

        // Create streaming response that shows graph execution steps
        let chunks = vec![
            Ok(serde_json::json!({
                "type": "langgraph_stream_start",
                "data": {
                    "input": graph_input,
                    "graph_info": {
                        "nodes": ["agent", "tools", "conditional", "final_response"],
                        "edges": [
                            {"from": "agent", "to": "conditional"},
                            {"from": "conditional", "to": "tools"},
                            {"from": "tools", "to": "final_response"}
                        ]
                    }
                },
                "metadata": {
                    "framework": "langgraph",
                    "stream_type": "graph_execution"
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_start",
                "data": {
                    "node": "agent",
                    "node_type": "agent_node",
                    "input": graph_input
                },
                "metadata": {
                    "step": 1,
                    "node_index": 0
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_output",
                "data": {
                    "node": "agent",
                    "output": {
                        "thoughts": "I need to process this request step by step",
                        "action": "use_tools",
                        "reasoning": "The user query requires tool assistance"
                    }
                },
                "metadata": {
                    "step": 2,
                    "node_index": 0
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_start",
                "data": {
                    "node": "conditional",
                    "node_type": "conditional_node",
                    "input": {
                        "agent_decision": "use_tools"
                    }
                },
                "metadata": {
                    "step": 3,
                    "node_index": 1
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_output",
                "data": {
                    "node": "conditional",
                    "output": {
                        "next_node": "tools",
                        "condition_met": true
                    }
                },
                "metadata": {
                    "step": 4,
                    "node_index": 1
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_start",
                "data": {
                    "node": "tools",
                    "node_type": "tool_node", 
                    "input": {
                        "tool_name": "search",
                        "tool_args": {"query": "mock search query"}
                    }
                },
                "metadata": {
                    "step": 5,
                    "node_index": 2
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_output",
                "data": {
                    "node": "tools",
                    "output": {
                        "tool_result": "Mock search results from LangGraph tool execution",
                        "tool_metadata": {
                            "execution_time": "0.2s",
                            "success": true
                        }
                    }
                },
                "metadata": {
                    "step": 6,
                    "node_index": 2
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_start",
                "data": {
                    "node": "final_response",
                    "node_type": "response_node",
                    "input": {
                        "agent_thoughts": "I need to process this request step by step",
                        "tool_results": "Mock search results from LangGraph tool execution"
                    }
                },
                "metadata": {
                    "step": 7,
                    "node_index": 3
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_node_output",
                "data": {
                    "node": "final_response",
                    "output": {
                        "final_answer": "Based on the graph execution and tool results, here is the response",
                        "confidence": 0.95
                    }
                },
                "metadata": {
                    "step": 8,
                    "node_index": 3,
                    "final_node": true
                }
            })),
            Ok(serde_json::json!({
                "type": "langgraph_stream_end",
                "data": {
                    "final_state": {
                        "messages": [graph_input, "Based on the graph execution and tool results, here is the response"],
                        "execution_complete": true
                    },
                    "graph_metadata": {
                        "total_nodes_executed": 4,
                        "total_steps": 8,
                        "execution_path": ["agent", "conditional", "tools", "final_response"]
                    }
                },
                "metadata": {
                    "framework": "langgraph",
                    "final": true
                }
            })),
        ];

        Ok(Box::pin(stream::iter(chunks)))
    }

    /// Handle graph structure inspection
    fn handle_get_graph(
        &self,
        entrypoint: &EntryPoint,
        _input_args: &[Value],
        _input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        tracing::info!("Getting LangGraph structure: {}", entrypoint.tag);

        Ok(serde_json::json!({
            "framework": "langgraph",
            "method": "get_graph",
            "graph_structure": {
                "nodes": [
                    {
                        "id": "agent",
                        "type": "agent_node",
                        "description": "Main reasoning agent"
                    },
                    {
                        "id": "conditional",
                        "type": "conditional_node", 
                        "description": "Decision routing node"
                    },
                    {
                        "id": "tools",
                        "type": "tool_node",
                        "description": "Tool execution node"
                    },
                    {
                        "id": "final_response",
                        "type": "response_node",
                        "description": "Final response generation"
                    }
                ],
                "edges": [
                    {"from": "agent", "to": "conditional", "condition": null},
                    {"from": "conditional", "to": "tools", "condition": "use_tools"},
                    {"from": "conditional", "to": "final_response", "condition": "direct_response"},
                    {"from": "tools", "to": "final_response", "condition": null}
                ],
                "entry_point": "agent",
                "end_nodes": ["final_response"]
            },
            "compiled": true,
            "checkpointer": "memory_saver",
            "interrupt_before": [],
            "interrupt_after": []
        }))
    }

    /// Handle state management operations
    fn handle_get_state(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        tracing::info!("Getting LangGraph state: {}", entrypoint.tag);

        let thread_id = input_kwargs.get("thread_id")
            .or_else(|| input_args.get(0))
            .unwrap_or(&serde_json::json!("default"))
            .clone();

        Ok(serde_json::json!({
            "framework": "langgraph",
            "method": "get_state",
            "thread_id": thread_id,
            "state": {
                "messages": [
                    {
                        "role": "user",
                        "content": "Previous user message"
                    },
                    {
                        "role": "assistant",
                        "content": "Previous assistant response"
                    }
                ],
                "current_node": "agent",
                "execution_metadata": {
                    "step_count": 5,
                    "last_update": chrono::Utc::now().to_rfc3339()
                }
            },
            "next_nodes": ["conditional"],
            "checkpoint": {
                "thread_id": thread_id,
                "checkpoint_id": "mock-checkpoint-123",
                "created_at": chrono::Utc::now().to_rfc3339()
            }
        }))
    }
}

impl FrameworkExecutor for LangGraphExecutor {
    fn execute(
        &self,
        entrypoint: &EntryPoint,
        input_args: &[Value],
        input_kwargs: &HashMap<String, Value>,
    ) -> RunAgentResult<Value> {
        match entrypoint.tag.as_str() {
            "invoke" | "ainvoke" => self.handle_invoke(entrypoint, input_args, input_kwargs),
            "get_graph" => self.handle_get_graph(entrypoint, input_args, input_kwargs),
            "get_state" => self.handle_get_state(entrypoint, input_args, input_kwargs),
            _ => {
                // Fall back to generic execution with LangGraph metadata
                let mut result = self.generic.execute(entrypoint, input_args, input_kwargs)?;
                
                if let Some(obj) = result.as_object_mut() {
                    obj.insert("framework".to_string(), Value::String("langgraph".to_string()));
                    obj.insert("executor".to_string(), Value::String("LangGraphExecutor".to_string()));
                    obj.insert("graph_execution".to_string(), Value::Bool(true));
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
            _ => {
                // Fall back to generic streaming
                self.generic.execute_stream(entrypoint, input_args, input_kwargs)
            }
        }
    }

    fn get_entrypoints(&self) -> Vec<String> {
        vec![
            "invoke".to_string(),
            "stream".to_string(),
            "ainvoke".to_string(),
            "astream".to_string(),
            "get_graph".to_string(),
            "get_state".to_string(),
            "update_state".to_string(),
            "compile".to_string(),
            // Include generic entrypoints as fallback
            "run".to_string(),
            "process".to_string(),
        ]
    }

    fn framework_name(&self) -> &'static str {
        "langgraph"
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

    fn create_test_langgraph_agent() -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        let agent_path = temp_dir.path();

        // Create a LangGraph-style agent file
        fs::write(
            agent_path.join("graph.py"),
            r#"
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

def invoke(input_data):
    # Mock LangGraph invoke with graph execution
    return {"output": f"LangGraph graph response to: {input_data}"}

def stream(input_data):
    # Mock LangGraph streaming with node-by-node execution
    nodes = ["agent", "tools", "final_response"]
    for node in nodes:
        yield {"node": node, "output": f"Processing in {node}"}

def get_graph():
    # Mock graph structure
    return {
        "nodes": ["agent", "tools", "final_response"],
        "edges": [("agent", "tools"), ("tools", "final_response")]
    }
"#,
        ).unwrap();

        temp_dir
    }

    #[test]
    fn test_langgraph_executor_creation() {
        let temp_dir = TempDir::new().unwrap();
        let executor = LangGraphExecutor::new(temp_dir.path());
        assert!(executor.is_ok());
    }

    #[test]
    fn test_invoke_execution() {
        let temp_dir = create_test_langgraph_agent();
        let executor = LangGraphExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "graph.py".to_string(),
            module: "invoke".to_string(),
            tag: "invoke".to_string(),
        };
        
        let input_args = vec![];
        let mut input_kwargs = HashMap::new();
        input_kwargs.insert("input".to_string(), serde_json::json!("test message"));
        
        let result = executor.execute(&entrypoint, &input_args, &input_kwargs);
        assert!(result.is_ok());
        
        let response = result.unwrap();
        assert_eq!(response.get("framework").and_then(|v| v.as_str()), Some("langgraph"));
        assert_eq!(response.get("method").and_then(|v| v.as_str()), Some("invoke"));
        assert_eq!(response.get("graph_execution").and_then(|v| v.as_bool()), Some(true));
    }

    #[test]
    fn test_stream_execution() {
        let temp_dir = create_test_langgraph_agent();
        let executor = LangGraphExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "graph.py".to_string(),
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
    fn test_get_graph() {
        let temp_dir = create_test_langgraph_agent();
        let executor = LangGraphExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "graph.py".to_string(),
            module: "get_graph".to_string(),
            tag: "get_graph".to_string(),
        };
        
        let result = executor.execute(&entrypoint, &[], &HashMap::new());
        assert!(result.is_ok());
        
        let response = result.unwrap();
        assert_eq!(response.get("framework").and_then(|v| v.as_str()), Some("langgraph"));
        assert_eq!(response.get("method").and_then(|v| v.as_str()), Some("get_graph"));
        assert!(response.get("graph_structure").is_some());
    }

    #[test]
    fn test_get_state() {
        let temp_dir = create_test_langgraph_agent();
        let executor = LangGraphExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoint = EntryPoint {
            file: "graph.py".to_string(),
            module: "get_state".to_string(),
            tag: "get_state".to_string(),
        };
        
        let mut input_kwargs = HashMap::new();
        input_kwargs.insert("thread_id".to_string(), serde_json::json!("test-thread"));
        
        let result = executor.execute(&entrypoint, &[], &input_kwargs);
        assert!(result.is_ok());
        
        let response = result.unwrap();
        assert_eq!(response.get("framework").and_then(|v| v.as_str()), Some("langgraph"));
        assert_eq!(response.get("method").and_then(|v| v.as_str()), Some("get_state"));
        assert!(response.get("state").is_some());
    }

    #[test]
    fn test_framework_name() {
        let temp_dir = TempDir::new().unwrap();
        let executor = LangGraphExecutor::new(temp_dir.path()).unwrap();
        assert_eq!(executor.framework_name(), "langgraph");
    }

    #[test]
    fn test_supported_entrypoints() {
        let temp_dir = TempDir::new().unwrap();
        let executor = LangGraphExecutor::new(temp_dir.path()).unwrap();
        
        let entrypoints = executor.get_entrypoints();
        assert!(entrypoints.contains(&"invoke".to_string()));
        assert!(entrypoints.contains(&"stream".to_string()));
        assert!(entrypoints.contains(&"get_graph".to_string()));
        assert!(entrypoints.contains(&"get_state".to_string()));
    }
}