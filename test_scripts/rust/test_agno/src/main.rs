//sync version non-streaming

// use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
// use serde_json::json;

// fn main() -> runagent::RunAgentResult<()> {
//     // Direct struct construction
//     let client = RunAgentClient::new(RunAgentClientConfig {
//         agent_id: "ae29bd73-b3d3-42c8-a98f-5d7aec7ee919".to_string(),
//         entrypoint_tag: "agno_print_response".to_string(),
//         ..RunAgentClientConfig::default() // Omits None values
//     })?;

//     let response = client.run(&[("prompt", json!("which is better toyota or honda"))])?;
//     println!("Response: {}", response);
//     Ok(())
// }

// ******************************Streaming Part with agno****************************************
//sync version streaming

// use runagent::blocking::{RunAgentClient, RunAgentClientConfig};
// use serde_json::json;

// fn main() -> runagent::RunAgentResult<()> {
//     let client = RunAgentClient::new(RunAgentClientConfig {
//         agent_id: "ae29bd73-b3d3-42c8-a98f-5d7aec7ee919".to_string(),
//         entrypoint_tag: "agno_print_response_stream".to_string(),
//         ..RunAgentClientConfig::default()
//     })?;

//     // Streaming collects all chunks into a vector
//     let chunks = client.run_stream(&[("prompt", json!("tell me a brief story about oracle monopoloy"))])?;
//     for chunk in chunks {
//         println!(">> {}", chunk?);
//     }
//     Ok(())
// }


// async version streaming

// use runagent::{RunAgentClient, RunAgentClientConfig};
// use serde_json::json;
// use futures::StreamExt;

// #[tokio::main]
// async fn main() -> runagent::RunAgentResult<()> {
//     let client = RunAgentClient::new(RunAgentClientConfig {
//         agent_id: "ad29bd73-b3d3-42c8-a98f-5d7aec7ee919".to_string(),
//         entrypoint_tag: "agno_print_response_stream".to_string(),
//         ..RunAgentClientConfig::default()
//     }).await?;

//     // Real streaming - processes chunks as they arrive
//     let mut stream = client.run_stream(&[("prompt", json!("tell me a long story about scotland"))]).await?;
//     while let Some(chunk) = stream.next().await {
//         println!(">> {}", chunk?);
//     }
//     Ok(())
// }


//async version non-streaming

use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    // Direct struct construction
    let client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: "ae29bd73-b3d3-42c8-a98f-5d7aec7ee919".to_string(),
        entrypoint_tag: "agno_print_response".to_string(),
        ..RunAgentClientConfig::default()
    }).await?;

    let response = client.run(&[("prompt", json!("which is better toyota or land rover"))]).await?;
    println!("Response: {}", response);
    Ok(())
}