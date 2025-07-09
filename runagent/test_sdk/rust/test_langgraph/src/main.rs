use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing LangGraph Complex Input Types");
    
    // Replace with your actual agent ID from `runagent serve`
    let agent_id = "758f3ed9-4867-469a-bbdd-6e83eddb5a4d";
    
    // Complex input structures to test
    let constraints = json!([
        {"type": "budget", "value": 100, "priority": "high"},
        {"type": "time", "value": "2 hours", "priority": "medium"}
    ]);
    
    let user_context = json!({
        "experience_level": "beginner",
        "available_tools": ["screwdriver", "hammer"],
        "budget": 50,
        "preferences": {
            "solution_type": "DIY",
            "avoid": ["expensive tools"]
        }
    });
    
    let metadata = json!({
        "request_id": "rust-test-123",
        "user_id": "test-user",
        "nested": {"deep": {"value": 42}}
    });
    
    // Test 1: Non-streaming with complex inputs
    println!("\n🚀 Test 1: Non-Streaming");
    let client = RunAgentClient::new(agent_id, "generic", true).await?;
    
    let response = client.run(&[
        ("query", json!("My laptop is running slowly")),
        ("num_solutions", json!(3)),
        ("constraints", constraints.clone()),
        ("user_context", user_context.clone()),
        ("metadata", metadata.clone())
    ]).await?;
    
    println!("✅ Non-streaming response received");
    println!("📄 Response keys: {:?}", 
        response);

    Ok(())
}

// ******************************Streaming Part with LangChain****************************************


use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "758f3ed9-4867-469a-bbdd-6e83eddb5a4d";
    
    let constraints = json!([{"type": "budget", "value": 100, "priority": "high"}]);
    let user_context = json!({"experience_level": "beginner"});
    let metadata = json!({"request_id": "rust-test-123"});
    
    // Test streaming with complex inputs
    println!("🌊 Streaming test:");
    let stream_client = RunAgentClient::new(agent_id, "generic_stream", true).await?;
    
    let mut stream = stream_client.run_stream(&[
        ("query", json!("Fix my slow computer")),
        ("num_solutions", json!(2)),
        ("constraints", constraints),
        ("user_context", user_context),
        ("metadata", metadata)
    ]).await?;
    
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                println!("{}", chunk);
            }
            Err(e) => {
                println!("Error: {}", e);
                break;
            }
        }
    }
    
    Ok(())
}