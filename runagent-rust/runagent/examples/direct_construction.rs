//! Example showing direct struct construction
//!
//! This shows how to pass a config object directly to the client constructor.

use runagent::RunAgentClient;
use serde_json::json;

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    // Direct struct construction
    let client = RunAgentClient::new(runagent::RunAgentClientConfig {
        agent_id: "a6977384-6c88-40dc-a629-e6bf077786ae".to_string(),
        entrypoint_tag: "minimal".to_string(),
        api_key: Some("rau_b4dcebdef6386726b08971a1cc968d8a2b77c5834d30f3f5a43bddf065cd95cb".to_string()),
        base_url: Some("http://localhost:8333/".to_string()),
        local: None,
        host: None,
        port: None,
        extra_params: None,
        enable_registry: None,
    }).await?;

    let response = client.run(&[("message", json!("Hello!"))]).await?;

    println!("Response: {}", response);
    Ok(())
}

