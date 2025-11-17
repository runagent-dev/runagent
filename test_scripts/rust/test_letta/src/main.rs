// use runagent::client::RunAgentClient;
// use serde_json::json;

// #[tokio::main]
// async fn main() -> Result<(), Box<dyn std::error::Error>> {
//     println!("🧪 Testing Letta Advanced Agent with Rust SDK");
    
//     // Replace with the actual agent ID from `runagent serve`
//     let agent_id = "5e9535e5-0345-451c-84dc-163c89697941";
    
//     // Test: Non-streaming execution with RAG
//     println!("\n🚀 Testing Non-Streaming Execution");
//     println!("==================================");
    
//     let client = RunAgentClient::new(
//         agent_id, 
//         "basic", 
//         true,  // local = true
//     ).await?;
    
//     // Test with RAG tool usage
//     let response = client.run_with_args(
//         &[], // no positional args
//         &[
//             ("message", json!("Tell me about love and horoscope"))
//         ]
//     ).await?;
    
//     println!("✅ Letta Advanced Response received:");
//     println!("{}", serde_json::to_string_pretty(&response)?);
    
//     println!("\n✅ Letta Advanced test completed successfully!");
    
//     Ok(())
// }



use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "5e9535e5-0345-451c-84dc-163c89697941";
    
    println!("🌊 Letta Advanced Streaming Test");
    println!("================================");
    
    // Test streaming with RAG tool usage
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "basic_stream".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    let mut stream = client.run_stream(&[
        ("message", json!("Tell me about Mercury retrograde and its effects on relationships."))
    ]).await?;
    
    println!("📡 Streaming Letta Advanced with RAG:");
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                println!("{}", chunk);
            },
            Err(e) => {
                println!("❌ Error: {}", e);
                break;
            }
        }
    }
    
    println!("\n✅ Letta Advanced streaming test completed!");
    
    Ok(())
}