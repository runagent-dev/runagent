use runagent::client::RunAgentClient;
use serde_json::json;
use futures::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🧪 Testing StockAgent with Rust SDK");
    println!("====================================");
    
    // Replace with your actual agent ID from `runagent serve`
    let agent_id = "6cf5351f-b228-4648-9a07-20608ef490be";
    
    println!("\n📡 Testing StockAgent Streaming Simulation");
    println!("{}", "=".repeat(50));
    
    // Connect to the streaming entrypoint
    let client = RunAgentClient::new(
        agent_id,
        "simulate_stream",  // The streaming entrypoint tag
        false  // local = true
    ).await?;
    
    println!("✅ Client initialized");
    
    // Run simulation with parameters
    let mut stream = client.run_stream(&[
        ("num_agents", json!(5)),           // Number of trading agents
        ("total_days", json!(3)),           // Simulation duration in days
        ("sessions_per_day", json!(2)),     // Trading sessions per day
        ("model", json!("gpt-4o-mini")),   // LLM model to use
        ("stock_a_price", json!(30.0)),    // Initial stock A price
        ("stock_b_price", json!(40.0)),    // Initial stock B price
        ("enable_events", json!(true))     // Enable market events
    ]).await?;
    
    println!("🚀 Simulation started, streaming updates...\n");
    
    // Process the stream
    let mut update_count = 0;
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                update_count += 1;
                
                // Parse the chunk to see what type of update it is
                if let Some(obj) = chunk.as_object() {
                    match obj.get("type").and_then(|v| v.as_str()) {
                        Some("init") => {
                            println!("🔧 {}", obj.get("message").unwrap());
                        },
                        Some("agents_initialized") => {
                            println!("✅ {}", obj.get("message").unwrap());
                        },
                        Some("day_start") => {
                            let day = obj.get("day").unwrap();
                            println!("\n📅 Day {} started", day);
                            if let Some(data) = obj.get("data") {
                                println!("   Stock A: ${}", data["stock_a_price"]);
                                println!("   Stock B: ${}", data["stock_b_price"]);
                            }
                        },
                        Some("session") => {
                            let session = obj.get("session").unwrap();
                            let message = obj.get("message").unwrap();
                            println!("   ⏰ {}", message);
                        },
                        Some("day_end") => {
                            println!("   ✅ Day complete\n");
                        },
                        Some("log") => {
                            // Print log messages
                            if let Some(msg) = obj.get("message") {
                                println!("   📝 {}", msg);
                            }
                        },
                        Some("complete") => {
                            println!("\n🎉 {}", obj.get("message").unwrap());
                            if let Some(data) = obj.get("data") {
                                println!("\n📊 Simulation Results:");
                                println!("{}", serde_json::to_string_pretty(data)?);
                            }
                        },
                        Some("error") => {
                            println!("❌ Error: {}", obj.get("message").unwrap());
                        },
                        _ => {
                            println!("📦 Update {}: {}", update_count, chunk);
                        }
                    }
                }
            },
            Err(e) => {
                println!("❌ Stream Error: {}", e);
                break;
            }
        }
    }
    
    println!("\n✅ Received {} total updates", update_count);
    println!("✅ StockAgent test completed successfully!");
    
    Ok(())
}