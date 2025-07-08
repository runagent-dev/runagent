use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing LangChain Agent with Rust SDK");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "e547af1e-25cf-43fc-a345-e2027dae06db";
    
    // Test: Non-streaming execution
    println!("\n🚀 Testing Non-Streaming Execution");
    println!("==================================");
    
    // Connect directly with host and port since we know where the server is running
    let client = RunAgentClient::with_address(
        agent_id, 
        "generic", 
        true,  // local = true
        Some("127.0.0.1"), 
        Some(8452)  // Use the port from your server output
    ).await?;
    
    println!("🔗 Connected to agent at 127.0.0.1:8452");
    
    // Test with proper arguments that match the `run` function signature
    let response = client.run_with_args(
        &[], // No positional args
        &[
            ("message", json!("Hello from Rust SDK! Can you tell me about RunAgent?")),
            ("temperature", json!(0.7)),
            ("model", json!("gpt-3.5-turbo"))
        ]
    ).await?;
    
    println!("✅ Response received:");
    println!("{}", serde_json::to_string_pretty(&response)?);
    
    println!("\n✅ Test completed successfully!");
    
    Ok(())
}