use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing agno Agent with Rust SDK");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "aacf274a-32b8-497d-85a4-aa8597686c40";
    
    // Test: Non-streaming execution
    println!("\n🚀 Testing Non-Streaming Execution");
    println!("==================================");
    
    // Connect directly with host and port since we know where the server is running
    let client = RunAgentClient::new(
        agent_id, 
        "agno_print_response", 
        true,  // local = true
        // Some("127.0.0.1"), 
        // Some(8452)  // Use the port from your server output
    ).await?;
    
    // println!("🔗 Connected to agent at 127.0.0.1:8452");
    
    let response = client.run_with_args(
            &[json!("Write a report on NVDA")], // positional args
            &[] // no keyword args
        ).await?;
    
    println!("✅ Response received:");
    println!("{}", serde_json::to_string_pretty(&response)?);
    
    println!("\n✅ Test completed successfully!");
    
    Ok(())
}

// ******************************Streaming Part with agno****************************************



use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "d31336a7-7c02-43cb-a906-6019b06a1249";
    
    println!("🌊 ag2 Streaming Test");
    let client = RunAgentClient::new(agent_id, "agno_print_response_stream", true).await?;
    
    let mut stream = client.run_stream(&[
        ("prompt", json!("Tell me about solar system"))
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