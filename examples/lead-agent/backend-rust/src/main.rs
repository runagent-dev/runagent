use axum::{
    extract::Json,
    http::{Method, StatusCode, HeaderValue},
    response::Json as JsonResponse,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tower_http::cors::{CorsLayer, AllowOrigin};
use runagent::{RunAgentClient, RunAgentClientConfig};

// RunAgent configuration
const RUNAGENT_ID: &str = "be87871d-b4c4-4ec1-990b-bef0ea4766f7";

// Request/Response types
#[derive(Deserialize)]
struct ScoreLeadsRequest {
    #[serde(default)]
    agent_id: Option<String>, // Deprecated: kept for backward compatibility but ignored
    candidates: Vec<Value>,
    #[serde(default)]
    top_n: Option<u32>,
    #[serde(default)]
    job_description: Option<String>,
    #[serde(default)]
    generate_emails: Option<bool>,
    #[serde(default)]
    additional_instructions: Option<String>,
}

#[derive(Deserialize)]
struct ScoreSingleRequest {
    #[serde(default)]
    agent_id: Option<String>, // Deprecated: kept for backward compatibility but ignored
    #[serde(default)]
    candidate_id: Option<String>,
    name: String,
    #[serde(default)]
    email: Option<String>,
    bio: String,
    #[serde(default)]
    skills: Option<String>,
    #[serde(default)]
    job_description: Option<String>,
    #[serde(default)]
    additional_instructions: Option<String>,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    traceback: Option<String>,
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    service: String,
    version: String,
}

/// POST /api/score-leads - Score multiple leads using RunAgent
async fn score_leads(
    Json(request): Json<ScoreLeadsRequest>,
) -> Result<JsonResponse<Value>, (StatusCode, JsonResponse<ErrorResponse>)> {
    // Validate required fields
    if request.candidates.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            JsonResponse(ErrorResponse {
                error: "candidates list is required".to_string(),
                traceback: None,
            }),
        ));
    }

    // Normalize candidates: ensure they're all objects, not JSON strings
    let normalized_candidates: Vec<Value> = request
        .candidates
        .into_iter()
        .map(|candidate| {
            match candidate {
                Value::String(s) => {
                    // If it's a JSON string, parse it
                    serde_json::from_str(&s).unwrap_or_else(|_| {
                        json!({
                            "error": format!("Invalid candidate format: expected object or JSON string, got: {}", s)
                        })
                    })
                }
                Value::Object(_) => candidate,
                _ => {
                    json!({
                        "error": format!("Invalid candidate format: expected object or JSON string, got: {}", candidate)
                    })
                }
            }
        })
        .collect();

    // Debug: Log candidate types before sending to SDK
    println!("[DEBUG] Number of candidates: {}", normalized_candidates.len());
    if let Some(first) = normalized_candidates.first() {
        println!("[DEBUG] First candidate type: object");
        println!("[DEBUG] First candidate sample: {}", serde_json::to_string(first).unwrap_or_default());
    }

    // Initialize RunAgent client using configured agent ID
    // API key will be picked up from RUNAGENT_API_KEY environment variable
    let client = match RunAgentClient::new(RunAgentClientConfig {
        agent_id: RUNAGENT_ID.to_string(),
        entrypoint_tag: "lead_score_flow".to_string(),
        local: Some(false), // Set to false when using RunAgent Cloud
        ..RunAgentClientConfig::default()
    })
    .await
    {
        Ok(client) => client,
        Err(e) => {
            return Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                JsonResponse(ErrorResponse {
                    error: format!("Failed to initialize RunAgent client: {}", e),
                    traceback: Some(format!("{:?}", e)),
                }),
            ));
        }
    };

    // Prepare parameters
    let mut params = vec![
        ("top_n", json!(request.top_n.unwrap_or(3))),
        ("generate_emails", json!(request.generate_emails.unwrap_or(true))),
    ];

    if let Some(job_description) = request.job_description {
        params.push(("job_description", json!(job_description)));
    }

    if let Some(additional_instructions) = request.additional_instructions {
        params.push(("additional_instructions", json!(additional_instructions)));
    }

    // Add candidates as JSON array
    params.push(("candidates", json!(normalized_candidates)));

    // Run the lead scoring flow
    match client.run(&params).await {
        Ok(result) => {
            // Debug: Log the result structure
            println!("[DEBUG] Agent result type: {}", result);
            println!("[DEBUG] Agent result keys: {:?}", result.as_object().map(|o| o.keys().collect::<Vec<_>>()));
            
            // Extract payload field if it exists (RunAgent wraps result in {"payload": "...", "type": "object"})
            let final_result = if let Some(obj) = result.as_object() {
                if let Some(payload_value) = obj.get("payload") {
                    if let Some(payload_str) = payload_value.as_str() {
                        // Try to parse the payload JSON string
                        serde_json::from_str::<Value>(payload_str).unwrap_or(result)
                    } else {
                        result
                    }
                } else {
                    // Check if result is a JSON string that needs parsing
                    if let Some(result_str) = result.as_str() {
                        serde_json::from_str::<Value>(result_str).unwrap_or(result)
                    } else {
                        result
                    }
                }
            } else if let Some(result_str) = result.as_str() {
                // Result is a string, try to parse it
                serde_json::from_str::<Value>(result_str).unwrap_or(result)
            } else {
                result
            };
            
            Ok(JsonResponse(final_result))
        }
        Err(e) => {
            eprintln!("Error in score_leads: {:?}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                JsonResponse(ErrorResponse {
                    error: format!("Agent execution failed: {}", e),
                    traceback: Some(format!("{:?}", e)),
                }),
            ))
        }
    }
}

/// POST /api/score-single - Score a single candidate
async fn score_single(
    Json(request): Json<ScoreSingleRequest>,
) -> Result<JsonResponse<Value>, (StatusCode, JsonResponse<ErrorResponse>)> {
    // Validate required fields
    if request.name.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            JsonResponse(ErrorResponse {
                error: "name is required".to_string(),
                traceback: None,
            }),
        ));
    }

    if request.bio.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            JsonResponse(ErrorResponse {
                error: "bio is required".to_string(),
                traceback: None,
            }),
        ));
    }

    // Initialize RunAgent client using configured agent ID
    // For local agents, API key is optional
    let client = match RunAgentClient::new(RunAgentClientConfig {
        agent_id: RUNAGENT_ID.to_string(),
        entrypoint_tag: "score_candidate".to_string(),
        local: Some(true), // local = true for single candidate scoring
        ..RunAgentClientConfig::default()
    })
    .await
    {
        Ok(client) => client,
        Err(e) => {
            return Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                JsonResponse(ErrorResponse {
                    error: format!("Failed to initialize RunAgent client: {}", e),
                    traceback: Some(format!("{:?}", e)),
                }),
            ));
        }
    };

    // Prepare parameters
    let mut params = vec![
        ("candidate_id", json!(request.candidate_id.unwrap_or_else(|| "temp-id".to_string()))),
        ("name", json!(request.name)),
        ("email", json!(request.email.unwrap_or_default())),
        ("bio", json!(request.bio)),
        ("skills", json!(request.skills.unwrap_or_default())),
    ];

    if let Some(job_description) = request.job_description {
        params.push(("job_description", json!(job_description)));
    }

    if let Some(additional_instructions) = request.additional_instructions {
        params.push(("additional_instructions", json!(additional_instructions)));
    }

    // Score single candidate
    match client.run(&params).await {
        Ok(result) => Ok(JsonResponse(result)),
        Err(e) => {
            eprintln!("Error in score_single_candidate: {:?}", e);
            Err((
                StatusCode::INTERNAL_SERVER_ERROR,
                JsonResponse(ErrorResponse {
                    error: format!("Agent execution failed: {}", e),
                    traceback: Some(format!("{:?}", e)),
                }),
            ))
        }
    }
}

/// GET /api/health - Health check endpoint
async fn health_check() -> JsonResponse<HealthResponse> {
    JsonResponse(HealthResponse {
        status: "healthy".to_string(),
        service: "lead-score-api".to_string(),
        version: "1.0.0".to_string(),
    })
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("🚀 Starting Lead Score API Backend (Rust)...");

    // Setup CORS - matching Flask backend origins
    let allowed_origins = vec![
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://10.1.0.5:5173",
        "http://10.1.0.5:5174",
        "http://20.84.81.110:5173",
        "http://20.84.81.110:5174",
    ]
    .into_iter()
    .map(|s| HeaderValue::from_static(s))
    .collect::<Vec<_>>();

    let cors = CorsLayer::new()
        .allow_origin(AllowOrigin::list(allowed_origins))
        .allow_methods([Method::GET, Method::POST, Method::OPTIONS])
        .allow_headers(tower_http::cors::Any);

    // Build the router
    let app = Router::new()
        .route("/api/score-leads", post(score_leads))
        .route("/api/score-single", post(score_single))
        .route("/api/health", get(health_check))
        .layer(cors);

    // Get port from environment or use default
    let port = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(8000);

    let addr = format!("0.0.0.0:{}", port);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    println!("🌐 Server running at http://{}", addr);
    println!("📋 Endpoints:");
    println!("   POST /api/score-leads");
    println!("   POST /api/score-single");
    println!("   GET  /api/health");

    axum::serve(listener, app).await?;

    Ok(())
}

