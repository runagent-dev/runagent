use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing Parlant Agent with Rust SDK");
    println!("=======================================");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "9c39620c-c309-4478-a44e-2a45e254a9fb";
    
    // ============================================
    // NON-STREAMING TESTS
    // ============================================
    
    // Test 1: Simple Chat
    println!("\n1️⃣ Testing Simple Chat");
    
    let simple_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "parlant_simple".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    let simple_response = simple_client.run(&[
        ("message", json!("What's the weather like in Paris?"))
    ]).await?;
    
    println!("✅ Simple Chat Response:");
    println!("{}", serde_json::to_string_pretty(&simple_response)?);
    
    
    Ok(())
}



// ############################streaming##################################

use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing Parlant Agent with Rust SDK");
    println!("=======================================");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "9c39620c-c309-4478-a44e-2a45e254a9fb";
    
    // Test 5: Streaming Chat
    println!("\n5️⃣ Testing Streaming Chat");
    println!("{}", "-".repeat(30));
    
    let stream_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "parlant_stream".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;

    let mut stream = stream_client.run_stream(&[
        ("message", json!("can you tell me the sum of 10 to 20."))
    ]).await?;

    println!("✅ Streaming Response:");
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                print!("{}", chunk);
            },
            Err(e) => {
                println!("❌ Stream Error: {}", e);
                break;
            }
        }
    }
    
    Ok(())
}