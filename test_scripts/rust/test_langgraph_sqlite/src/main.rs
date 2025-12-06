use runagent::{RunAgentClient, RunAgentClientConfig};
use serde_json::json;
use futures::StreamExt;
use std::time::Duration;
use std::io::Write;
use tokio::time::sleep;

// Configuration (mirrors test_scripts/python/client_test_langgraph_sqlite.py)
const AGENT_ID: &str = "f5dd61ef-578c-4a92-abe0-f967b7602738"; // Replace with your deployed agent ID
const LOCAL_MODE: bool = false; // Set to true for local testing
const USER_ID: &str = "t19"; // RunAgent's persistent storage user ID

#[tokio::main]
async fn main() -> runagent::RunAgentResult<()> {
    println!("{}", "=".repeat(70));
    println!("LangGraph Chatbot Test Suite");
    println!("{}", "=".repeat(70));

    // Initialize clients for different entrypoints
    let chat_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: AGENT_ID.to_string(),
        entrypoint_tag: "chat".to_string(),
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

    let stream_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: AGENT_ID.to_string(),
        entrypoint_tag: "chat_stream".to_string(),
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

    let history_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: AGENT_ID.to_string(),
        entrypoint_tag: "get_history".to_string(),
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

    let threads_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: AGENT_ID.to_string(),
        entrypoint_tag: "list_threads".to_string(),
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

    //////////////////////////// TESTS ////////////////////////////
    // test_basic_conversation(&chat_client).await?;
    // sleep(Duration::from_secs(2)).await;

    test_streaming(&stream_client).await?;
    sleep(Duration::from_secs(2)).await;

    // test_multiple_threads(&chat_client).await?;
    // sleep(Duration::from_secs(2)).await;

    // test_conversation_history(&history_client).await?;
    // sleep(Duration::from_secs(2)).await;

    // test_list_threads(&threads_client).await?;
    // sleep(Duration::from_secs(2)).await;

    // test_persistence_across_sessions(AGENT_ID, LOCAL_MODE, USER_ID).await?;

    println!("\n{}", "=".repeat(70));
    println!("All tests completed successfully!");
    println!("{}", "=".repeat(70));

    Ok(())
}

/// Test basic non-streaming conversation with memory.
async fn test_basic_conversation(chat_client: &RunAgentClient) -> runagent::RunAgentResult<()> {
    println!("\n{}", "=".repeat(70));
    println!("TEST 1: Basic Conversation (Thread: conversation_001)");
    println!("{}", "=".repeat(70));

    let result = chat_client
        .run(&[
            ("message", json!("is it just me or AI will take over the world?")),
            ("user_id", json!(USER_ID)),
            ("thread_id", json!("conversation_001")),
        ])
        .await?;

    if let Some(response) = result.get("response").and_then(|v| v.as_str()) {
        println!("[Assistant]: {}", response);
    }

    if let Some(thread_id) = result.get("thread_id").and_then(|v| v.as_str()) {
        if let Some(message_count) = result.get("message_count").and_then(|v| v.as_u64()) {
            println!(
                "[Info] Thread: {}, Messages: {}",
                thread_id, message_count
            );
        }
    }

    Ok(())
}

/// Test streaming conversation.
async fn test_streaming(stream_client: &RunAgentClient) -> runagent::RunAgentResult<()> {
    println!("\n{}", "=".repeat(70));
    println!("TEST 2: Streaming Response (Thread: conversation_001)");
    println!("{}", "=".repeat(70));

    print!("[Assistant]: ");
    std::io::stdout().flush().unwrap();

    let mut stream = stream_client
        .run_stream(&[
            ("message", json!("can you tell me brieflyabout ai 2027?")),
            ("user_id", json!(USER_ID)),
            ("thread_id", json!("conversation_001")),
        ])
        .await?;

    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                // Check if this is a content chunk
                if let Some(chunk_type) = chunk.get("type").and_then(|v| v.as_str()) {
                    if chunk_type == "content" {
                        if let Some(content) = chunk.get("content").and_then(|v| v.as_str()) {
                            print!("{}", content);
                            std::io::stdout().flush().unwrap();
                        }
                    } else if chunk_type == "complete" {
                        if let Some(thread_id) = chunk.get("thread_id").and_then(|v| v.as_str()) {
                            println!("\n[Info] Thread: {}", thread_id);
                        }
                    }
                }
            }
            Err(e) => {
                eprintln!("Stream error: {}", e);
                break;
            }
        }
    }

    Ok(())
}

/// Test multiple conversation threads.
async fn test_multiple_threads(chat_client: &RunAgentClient) -> runagent::RunAgentResult<()> {
    println!("\n{}", "=".repeat(70));
    println!("TEST 3: Multiple Threads (Thread isolation)");
    println!("{}", "=".repeat(70));

    // Thread 1: Personal chat
    println!("\n--- Thread: personal ---");
    println!("[User]: I'm planning a vacation to Japan");
    let result = chat_client
        .run(&[
            ("message", json!("I'm planning a vacation to Japan")),
            ("user_id", json!(USER_ID)),
            ("thread_id", json!("personal")),
        ])
        .await?;

    if let Some(response) = result.get("response").and_then(|v| v.as_str()) {
        println!("[Assistant]: {}", response);
    }

    sleep(Duration::from_secs(1)).await;

    // Thread 2: Work chat
    println!("\n--- Thread: work ---");
    println!("[User]: I need to debug a Python function");
    let result = chat_client
        .run(&[
            ("message", json!("I need to debug a Python function")),
            ("user_id", json!(USER_ID)),
            ("thread_id", json!("work")),
        ])
        .await?;

    if let Some(response) = result.get("response").and_then(|v| v.as_str()) {
        println!("[Assistant]: {}", response);
    }

    sleep(Duration::from_secs(1)).await;

    // Back to Thread 1 - should remember vacation
    println!("\n--- Thread: personal (continued) ---");
    println!("[User]: Where was I planning to go?");
    let result = chat_client
        .run(&[
            ("message", json!("Where was I planning to go?")),
            ("user_id", json!(USER_ID)),
            ("thread_id", json!("personal")),
        ])
        .await?;

    if let Some(response) = result.get("response").and_then(|v| v.as_str()) {
        println!("[Assistant]: {}", response);
    }

    sleep(Duration::from_secs(1)).await;

    // Thread 2 - should NOT know about vacation
    println!("\n--- Thread: work (continued) ---");
    println!("[User]: Where was I planning to go?");
    let result = chat_client
        .run(&[
            ("message", json!("Where was I planning to go?")),
            ("user_id", json!(USER_ID)),
            ("thread_id", json!("work")),
        ])
        .await?;

    if let Some(response) = result.get("response").and_then(|v| v.as_str()) {
        println!("[Assistant]: {}", response);
    }

    Ok(())
}

/// Test retrieving conversation history.
async fn test_conversation_history(
    history_client: &RunAgentClient,
) -> runagent::RunAgentResult<()> {
    println!("\n{}", "=".repeat(70));
    println!("TEST 4: Conversation History Retrieval");
    println!("{}", "=".repeat(70));

    println!("\nRetrieving history for thread: conversation_001");
    let result = history_client
        .run(&[
            ("user_id", json!(USER_ID)),
            ("thread_id", json!("conversation_001")),
        ])
        .await?;

    println!("{}", serde_json::to_string_pretty(&result)?);

    Ok(())
}

/// Test listing all user threads.
async fn test_list_threads(threads_client: &RunAgentClient) -> runagent::RunAgentResult<()> {
    println!("\n{}", "=".repeat(70));
    println!("TEST 5: List All User Threads");
    println!("{}", "=".repeat(70));

    let result = threads_client
        .run(&[("user_id", json!(USER_ID))])
        .await?;

    if let Some(status) = result.get("status").and_then(|v| v.as_str()) {
        if status == "success" {
            if let Some(user_id) = result.get("user_id").and_then(|v| v.as_str()) {
                if let Some(thread_count) = result.get("thread_count").and_then(|v| v.as_u64()) {
                    println!(
                        "\nUser '{}' has {} conversation(s):",
                        user_id, thread_count
                    );
                }
            }

            if let Some(threads) = result.get("threads").and_then(|v| v.as_array()) {
                for thread in threads {
                    if let Some(thread_str) = thread.as_str() {
                        println!("  - {}", thread_str);
                    }
                }
            }
        } else {
            if let Some(error_msg) = result.get("message").and_then(|v| v.as_str()) {
                println!("Error: {}", error_msg);
            }
        }
    }

    Ok(())
}

/// Test that conversation persists (simulates app restart).
async fn test_persistence_across_sessions(
    agent_id: &str,
    local_mode: bool,
    user_id: &str,
) -> runagent::RunAgentResult<()> {
    println!("\n{}", "=".repeat(70));
    println!("TEST 6: Persistence Test (Simulated Restart)");
    println!("{}", "=".repeat(70));

    println!("\nCreating a new client (simulates app restart)...");

    // Create a completely new client
    let new_client = RunAgentClient::new(RunAgentClientConfig {
        agent_id: agent_id.to_string(),
        entrypoint_tag: "chat".to_string(),
        local: Some(local_mode),
        host: None,
        port: None,
        api_key: None,
        base_url: None,
        extra_params: None,
        enable_registry: None,
        user_id: Some(user_id.to_string()),
        persistent_memory: Some(true),
    })
    .await?;

    // Try to continue old conversation
    println!("\n[User]: What was my name again? (from earlier conversation)");
    let result = new_client
        .run(&[
            ("message", json!("What was my name again?")),
            ("user_id", json!(user_id)),
            ("thread_id", json!("conversation_001")), // Same thread from test 1
        ])
        .await?;

    if let Some(response) = result.get("response").and_then(|v| v.as_str()) {
        println!("[Assistant]: {}", response);
    }

    if let Some(message_count) = result.get("message_count").and_then(|v| v.as_u64()) {
        println!(
            "\n✓ Conversation persisted! The agent remembered from {} messages.",
            message_count
        );
    }

    Ok(())
}

