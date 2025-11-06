use axum::{
    http::Method,
    response::{Html, Json, Sse},
    routing::{get, post},
    Router,
};
use futures::StreamExt;
use runagent::client::RunAgentClient;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use tokio_stream::wrappers::ReceiverStream;
use tower_http::cors::{Any, CorsLayer};

#[derive(Deserialize)]
struct ReviewRequest {
    code: String,
    language: Option<String>,
    focus_area: Option<String>,
}

#[derive(Serialize)]
struct ReviewResponse {
    success: bool,
    result: Option<serde_json::Value>,
    error: Option<String>,
}

#[derive(Serialize)]
struct StreamChunk {
    content: String,
    finished: bool,
}

// Serve the HTML page
async fn serve_html() -> Html<&'static str> {
    Html(include_str!("../static/index.html"))
}

// Removed non-streaming review function - only streaming supported

// Handle streaming code review
async fn review_code_stream(Json(request): Json<ReviewRequest>) -> Sse<ReceiverStream<Result<axum::response::sse::Event, std::convert::Infallible>>> {
    let (tx, rx) = tokio::sync::mpsc::channel(100);
    
    // Spawn background task for streaming
    tokio::spawn(async move {
        println!("🌊 Starting streaming review for {} code", request.language.as_deref().unwrap_or("unknown"));
        
        // Connect to RunAgent - REPLACE "YOUR_AGENT_ID_HERE" with your actual agent ID
        let client = match RunAgentClient::new("355a44e4-c7a0-483b-85c8-80d9b676e293", "code_review_stream", true).await {
            Ok(client) => client,
            Err(e) => {
                let _ = tx.send(Ok(axum::response::sse::Event::default()
                    .data(serde_json::to_string(&StreamChunk {
                        content: format!("Error connecting to agent: {}", e),
                        finished: true,
                    }).unwrap()))).await;
                return;
            }
        };

        // Prepare parameters
        let mut params = vec![("code", json!(request.code))];
        
        if let Some(language) = request.language {
            params.push(("language", json!(language)));
        }
        
        if let Some(focus_area) = request.focus_area {
            params.push(("focus_area", json!(focus_area)));
        }

        // Start streaming
        match client.run_stream(&params).await {
            Ok(mut stream) => {
                while let Some(chunk_result) = futures::StreamExt::next(&mut stream).await {
                    match chunk_result {
                        Ok(chunk) => {
                            let content = if let Some(text) = chunk.get("content") {
                                text.as_str().unwrap_or("").to_string()
                            } else {
                                chunk.to_string()
                            };
                            
                            let event = axum::response::sse::Event::default()
                                .data(serde_json::to_string(&StreamChunk {
                                    content,
                                    finished: false,
                                }).unwrap());
                            
                            if tx.send(Ok(event)).await.is_err() {
                                break; // Client disconnected
                            }
                        }
                        Err(e) => {
                            let event = axum::response::sse::Event::default()
                                .data(serde_json::to_string(&StreamChunk {
                                    content: format!("Stream error: {}", e),
                                    finished: true,
                                }).unwrap());
                            let _ = tx.send(Ok(event)).await;
                            break;
                        }
                    }
                }
                
                // Send completion event
                let event = axum::response::sse::Event::default()
                    .data(serde_json::to_string(&StreamChunk {
                        content: "\n✅ Review completed!".to_string(),
                        finished: true,
                    }).unwrap());
                let _ = tx.send(Ok(event)).await;
            }
            Err(e) => {
                let event = axum::response::sse::Event::default()
                    .data(serde_json::to_string(&StreamChunk {
                        content: format!("Failed to start stream: {}", e),
                        finished: true,
                    }).unwrap());
                let _ = tx.send(Ok(event)).await;
            }
        }
    });

    Sse::new(ReceiverStream::new(rx))
}

// Health check endpoint
async fn health_check() -> Json<HashMap<&'static str, &'static str>> {
    Json([("status", "healthy"), ("service", "code-reviewer-backend")].iter().cloned().collect())
}

// Get example code snippets
async fn get_examples() -> Json<HashMap<&'static str, Vec<(&'static str, &'static str)>>> {
    let examples = [
        ("rust", vec![
            ("Simple Function", r#"fn add(a: i32, b: i32) -> i32 {
    a + b
}"#),
            ("Unsafe Code", r#"unsafe fn dangerous_operation() {
    let mut x = 42;
    let ptr = &mut x as *mut i32;
    *ptr = 100;
    println!("Value: {}", x);
}"#),
            ("Security Issue", r#"use std::process::Command;

fn execute_command(user_input: &str) -> String {
    let password = "hardcoded_secret_123";
    
    let output = Command::new("sh")
        .arg("-c")
        .arg(user_input)  // Command injection risk!
        .output()
        .unwrap();
    
    String::from_utf8(output.stdout).unwrap()
}"#),
        ]),
        ("python", vec![
            ("Basic Function", r#"def calculate_average(numbers):
    return sum(numbers) / len(numbers)"#),
            ("Performance Issue", r#"def process_data(items):
    result = ""
    for item in items:
        result = result + str(item) + " "  # Inefficient concatenation
    return result"#),
            ("Security Risk", r#"import os
import pickle

API_KEY = "sk-1234567890abcdef"  # Hardcoded secret

def load_user_data(data):
    return pickle.loads(data)  # Unsafe deserialization

def run_command(cmd):
    os.system(cmd)  # Command injection risk"#),
        ]),
    ].iter().cloned().collect();
    
    Json(examples)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 Starting Code Reviewer Web Backend...");
    
    // Setup CORS
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([Method::GET, Method::POST])
        .allow_headers(Any);

    // Build the router - ONLY STREAMING SUPPORT
    let app = Router::new()
        .route("/", get(serve_html))
        .route("/health", get(health_check))
        .route("/api/review/stream", post(review_code_stream))  // Only streaming endpoint
        .route("/api/examples", get(get_examples))
        .layer(cors);

    // Start the server
    let listener = tokio::net::TcpListener::bind("127.0.0.1:3001").await?;
    println!("🌐 Server running at http://127.0.0.1:3001");
    
    axum::serve(listener, app).await?;
    
    Ok(())
}