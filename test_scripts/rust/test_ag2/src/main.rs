use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing ag2 Agent with Rust SDK");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "145dcae4-4c14-4c8b-bd11-cd6f40fb20ae";
    
    // Test: Non-streaming execution
    println!("\n🚀 Testing Non-Streaming Execution");
    println!("==================================");
    
    // Connect directly with host and port since we know where the server is running
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "ag2_invoke".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    // println!("🔗 Connected to agent at 127.0.0.1:8452");
    
    // Test with proper arguments that match the `run` function signature
    let response = client.run(&[
        ("message", json!("The solar system has 2 planets.")),
        ("max_turns", json!(3))
    ]).await?;
    
    println!("✅ Response received:");
    println!("{}", serde_json::to_string_pretty(&response)?);
    
    println!("\n✅ Test completed successfully!");
    
    Ok(())
}

// ******************************Streaming Part with ag2****************************************



use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "145dcae4-4c14-4c8b-bd11-cd6f40fb20ae";
    
    println!("🌊 ag2 Streaming Test");
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "ag2_stream".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    let mut stream = client.run_stream(&[
        ("message", json!("The solar system has 2 planets.")),
        ("max_turns", json!(3)),
    ]).await?;
    
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => println!("{}", chunk),
            Err(e) => {
                println!("Error: {}", e);
                break;
            }
        }
    }
    
    Ok(())
}