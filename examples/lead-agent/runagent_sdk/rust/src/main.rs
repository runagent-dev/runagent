use runagent::client::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing Lead Score Agent with Rust SDK");
    
    // Replace with your actual agent ID from `runagent serve`
    let agent_id = "bd87871d-b4c4-4ec1-990b-bef0ea4766f7";
    
    println!("\n🚀 Testing Lead Score Flow");
    println!("============================");
    
    // Connect to lead score agent
    let client = RunAgentClient::new(
        agent_id, 
        "lead_score_flow",  // entrypoint_tag
        false,  // local = true
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

