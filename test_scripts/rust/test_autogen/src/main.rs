use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing AutoGen Agent with Rust SDK");
    
    // Replace with the actual agent ID from `runagent serve`
    let agent_id = "5cc3e314-cad0-42ec-9115-e1d9225ebb54";
    
    // Test: Non-streaming execution
    println!("\n🚀 Testing Non-Streaming Execution");
    println!("==================================");
    
    // Connect to AutoGen agent with invoke entrypoint
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "autogen_invoke".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    // AutoGen expects a 'task' parameter
    let response = client.run(&[
        ("task", json!("What is AutoGen?"))
    ]).await?;
    
    println!("✅ AutoGen Response received:");
    println!("{}", serde_json::to_string_pretty(&response)?);
    
    println!("\n✅ AutoGen test completed successfully!");
    
    Ok(())
}


// ******************************Streaming Part with autogent****************************************



use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing AutoGen Agent (Parsing Existing Response)");
    
    // Replace with your actual AutoGen agent ID
    let agent_id = "5cc3e314-cad0-42ec-9115-e1d9225ebb54";
    
    println!("\n🚀 Testing AutoGen with Response Parsing");
    println!("========================================");
    
    let token_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "autogen_token_stream".to_string(),
        local: Some(true),
        ..RunAgentClientConfig::default()
    }).await?;
    
    let mut token_stream = token_client.run_stream(&[
        ("task", json!("Write a brief summary of machine learning"))
    ]).await?;
    
    println!("📝 Raw token streaming output:");
    while let Some(chunk_result) = token_stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                println!("{}", chunk);
            },
            Err(e) => {
                println!("❌ Token Stream Error: {}", e);
                break;
            }
        }
    }
    
    println!("\n✅ All AutoGen tests completed successfully!");
    
    Ok(())
}