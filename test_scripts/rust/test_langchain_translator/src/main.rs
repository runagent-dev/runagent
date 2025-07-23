use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let agent_id = "e5054c41-dc0f-4c55-8dee-b23865f005ce";
    
    println!("🌊 Testing LangChain Translator Agent - Streaming");
    
    let stream_client = RunAgentClient::new(agent_id, "text_translation_stream", true).await?;

    let mut stream = stream_client.run_stream(&[
        ("text", json!("আমার মন খারাপ। শরীর টা ভালো লাগছে না।")),
        ("target_language", json!("English"))
    ]).await?;
    
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                println!("{}", chunk);
            }
            Err(e) => {
                println!("❌ Error: {}", e);
                break;
            }
        }
    }
    
    println!("\n✅ Translation streaming test completed!");
    
    Ok(())
}