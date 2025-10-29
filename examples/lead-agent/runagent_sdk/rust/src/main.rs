use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing Lead Score Agent with Rust SDK");
    
    // Replace with your actual agent ID from `runagent serve`
    let agent_id = "dd520db6-5ff6-4b2b-9eea-e3c50453b4d9";
    
    println!("\n🚀 Testing Lead Score Flow");
    println!("============================");
    
    // Connect to lead score agent
    let client = RunAgentClient::new(
        agent_id, 
        "lead_score_flow",  // entrypoint_tag
        true,  // local = true
    ).await?;
    
    // Call the lead score flow with parameters
    let response = client.run_with_args(
        &[], // no positional args
        &[
            ("top_n", json!(1)),
            ("generate_emails", json!(true))
        ]
    ).await?;
    
    println!("✅ Lead Score Response received:");
    println!("{}", serde_json::to_string_pretty(&response)?);
    
    println!("\n✅ Lead Score test completed successfully!");
    
    Ok(())
}

