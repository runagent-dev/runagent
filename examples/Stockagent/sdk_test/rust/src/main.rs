use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing StockAgent with Rust SDK");
    println!("====================================");
    
    // Initialize the client
    let client = RunAgentClient::new(
        "6cf5351f-b228-4648-9a07-20608ef490be",  // Agent ID
        "simulate_stream",                        // Entrypoint
        false                                     // Remote connection
    ).await?;
    
    println!("✅ Client initialized");
    
    println!("🔄 Starting simulation...");
    // Run simulation with parameters (matching Python SDK exactly)
    let mut stream = client.run_stream(&[
        ("num_agents", json!("5")),           // String values like Python
        ("total_days", json!("2")),           // String values like Python
        ("sessions_per_day", json!("2")),     // String values like Python
        ("model", json!("gpt-4o-mini"))      // String values like Python
    ]).await?;
    
    println!("🚀 Simulation started, streaming updates...\n");
    
    // Process the stream - simple output like Python SDK
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                // Just print the raw data like Python SDK
                println!("{}", chunk);
            },
            Err(e) => {
                println!("❌ Stream Error: {}", e);
                break;
            }
        }
    }
    
    println!("✅ StockAgent test completed successfully!");  
    Ok(())
}