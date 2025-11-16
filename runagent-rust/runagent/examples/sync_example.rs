//! Sync example using blocking RunAgentClient
//!
//! This is useful for simple scripts or when you can't use async/await.
//! Note: For better performance, prefer the async version.

use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

fn main() -> runagent::RunAgentResult<()> {
    // dotenvy::from_filename("local.env").ok(); // optional

    let agent_id = "a6977384-6c88-40dc-a629-e6bf077786ae";
    let entrypoint_tag = "minimal";

    let client = RunAgentClient::new(
        RunAgentClientConfig::new(agent_id, entrypoint_tag)
            .with_local(true)
            .with_address("127.0.0.1", 8452)
            .with_enable_registry(false) // Skip DB lookup since we have explicit address
    )?;

    let response = client.run(&[("message", json!("Hello!"))])?;

    println!("Response: {}", response);
    Ok(())
}

