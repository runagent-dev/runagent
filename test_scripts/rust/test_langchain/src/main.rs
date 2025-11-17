// use runagent::client::RunAgentClient;
// use serde_json::json;

// #[tokio::main]
// async fn main() -> Result<(), Box<dyn std::error::Error>> {
//     println!("🧪 Testing LangChain Agent with Rust SDK");
    
//     // Replace with the actual agent ID from `runagent serve`
//     let agent_id = "578b088a-0476-40e9-8ebc-1068284fd824";
    
//     // Test: Non-streaming execution
//     println!("\n🚀 Testing Non-Streaming Execution");
//     println!("==================================");
    
//     // Connect directly with host and port since we know where the server is running
//     let client = RunAgentClient::new(
//         agent_id, 
//         "generic", 
//         true,  // local = true
//         // Some("127.0.0.1"), 
//         // Some(8452)  // Use the port from your server output
//     ).await?;
    
//     // println!("🔗 Connected to agent at 127.0.0.1:8452");
    
//     // Test with proper arguments that match the `run` function signature
//     let response = client.run_with_args(
//         &[], // No positional args
//         &[
//             ("message", json!("Hello from Rust SDK! Can you tell me about RunAgent?")),
//             ("temperature", json!(0.7)),
//             ("model", json!("gpt-4o-mini"))
//         ]
//     ).await?;
    
//     println!("✅ Response received:");
//     println!("{}", serde_json::to_string_pretty(&response)?);
    
//     println!("\n✅ Test completed successfully!");
    
//     Ok(())
// }

// ******************************Streaming Part with LangChain****************************************


use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "b78cef0b-b57e-455d-a61e-6dc36e6e2ca9";
    
    println!("🌊 LangChain Streaming Test");
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "generic_stream".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    let mut stream = client.run_stream(&[
        ("message", json!("Tell me a paragraph about journey by boat")),
        ("temperature", json!(0.8)),
        ("model", json!("gpt-4o-mini"))
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