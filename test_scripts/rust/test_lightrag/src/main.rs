use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

// Configuration (mirrors test_scripts/python/client_test_lightrag.py)
const AGENT_ID: &str = "63751c14-0ed5-426c-ab44-aa94e5505bed";
const LOCAL_MODE: bool = false;
const USER_ID: &str = "rad123";

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    // Ingest client (persistent memory enabled)
    let ingest_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: AGENT_ID.to_string(),
        entrypoint_tag: "ingest_text".to_string(),
        local: Some(LOCAL_MODE),
        host: None,
        port: None,
        api_key: None,
        base_url: None,
        extra_params: None,
        enable_registry: None,
        user_id: Some(USER_ID.to_string()),
        persistent_memory: Some(true),
    })
    .await?;

    // Query client (same user_id + persistent_memory)
    let query_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: AGENT_ID.to_string(),
        entrypoint_tag: "query_rag".to_string(),
        local: Some(LOCAL_MODE),
        host: None,
        port: None,
        api_key: None,
        base_url: None,
        extra_params: None,
        enable_registry: None,
        user_id: Some(USER_ID.to_string()),
        persistent_memory: Some(true),
    })
    .await?;

    // Example query (same as Python test)
    let question = "population prediction";
    println!("============================================================");
    println!("STEP: Query RAG");
    println!("============================================================");

    let result = query_client
        .run(&[
            ("query", json!(question)),
            // mode is optional; default is handled server-side but we match Python example
            ("mode", json!("hybrid")),
        ])
        .await?;

    println!("Result: {}", result);
    Ok(())
}
