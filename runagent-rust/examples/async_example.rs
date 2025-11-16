//! Async example using RunAgentClient
//!
//! This is the recommended approach for most use cases.

use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    // dotenvy::from_filename("local.env").ok(); // optional

    let agent_id = "a6977384-6c88-40dc-a629-e6bf077786ae";
    let entrypoint_tag = "minimal";

    let client = RunAgentClient::new(
        RunAgentClientConfig::new(agent_id, entrypoint_tag)
            .with_local(true)
            .with_address("127.0.0.1", 8452)
            .with_enable_registry(false) // Skip DB lookup since we have explicit address
    ).await?;

    let response = client.run(&[("message", json!("Hello!"))]).await?;

    println!("Response: {}", response);
    Ok(())
}

