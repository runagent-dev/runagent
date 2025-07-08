use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing LangChain Agent with Rust SDK");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "7d8bf036-199d-4ced-8d9d-aad39d8c96a9";
    
    // Test 1: Non-streaming execution
    println!("\n1️⃣ Testing Non-Streaming Execution");
    println!("=====================================");
    
    let client = RunAgentClient::new(agent_id, "generic", true).await?;
    
    let response = client.run(&[
        ("message", json!("Hello from Rust SDK! Can you tell me about RunAgent?")),
        ("temperature", json!(0.7)),
        ("model", json!("gpt-3.5-turbo"))
    ]).await?;
    
    println!("✅ Response received:");
    println!("{}", serde_json::to_string_pretty(&response)?);