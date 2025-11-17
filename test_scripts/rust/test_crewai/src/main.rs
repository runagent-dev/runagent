use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing CrewAI Agent with Rust SDK");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "07f24366-2762-4b25-9595-e7c9d7f6e3d1";
    
    // Test: Non-streaming execution
    println!("\n🚀 Testing Non-Streaming Execution");
    println!("==================================");
    
    // Connect to CrewAI agent
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "research_crew".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    // CrewAI expects a 'topic' parameter
    let response = client.run(&[
        ("topic", json!("AI Agent Deployment"))
    ]).await?;
    
    println!("✅ CrewAI Response received:");
    println!("{}", serde_json::to_string_pretty(&response)?);
    
    println!("\n✅ CrewAI test completed successfully!");
    
    Ok(())
}

// ******************************Streaming Part with crewai****************************************

// crewai streaming bug

use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "07f24366-2762-4b25-9595-e7c9d7f6e3d1";
    
    println!("🌊 CrewAI Streaming Test");
    
    // Test 1: Regular CrewAI streaming
    println!("\n📡 Testing research_crew (Full Object Stream)");
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "research_crew".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    let mut stream = client.run_stream(&[
        ("topic", json!("AI Agent Deployment"))
    ]).await?;
    
    println!("Streaming full CrewAI objects:");
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                println!("📦 Chunk: {}", chunk);
            },
            Err(e) => {
                println!("❌ Error: {}", e);
                break;
            }
        }
    }
    Ok(())
}