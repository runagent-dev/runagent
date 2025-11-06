# Lead Agent Backend (Rust)

Rust backend for the Lead Score Agent API, using Axum and the RunAgent Rust SDK.

## Features

- ✅ POST `/api/score-leads` - Score multiple leads using RunAgent
- ✅ POST `/api/score-single` - Score a single candidate
- ✅ GET `/api/health` - Health check endpoint
- ✅ CORS support for frontend integration
- ✅ JSON request/response handling
- ✅ Error handling with proper HTTP status codes

## Requirements

- Rust 1.70+
- RunAgent Rust SDK (from `/home/azureuser/runagent/runagent-rust/runagent`)

## Setup

1. Install dependencies:
```bash
cd backend-rust
cargo build --release
```

2. Set environment variables (optional):
```bash
export PORT=8000  # Default is 8000
```

3. Run the server:
```bash
cargo run --release
```

Or run in release mode:
```bash
cargo run --release
```

## API Endpoints

### POST /api/score-leads

Score multiple leads using RunAgent.

**Request Body:**
```json
{
  "agent_id": "your-agent-id",
  "candidates": [
    {
      "id": "1",
      "name": "John Doe",
      "email": "john@example.com",
      "bio": "...",
      "skills": "React, Node.js"
    }
  ],
  "top_n": 3,
  "job_description": "...",
  "generate_emails": true,
  "additional_instructions": ""
}
```

**Response:**
```json
{
  "success": true,
  "total_candidates": 6,
  "top_candidates": [...],
  "all_candidates": [...],
  "emails_generated": [...]
}
```

### POST /api/score-single

Score a single candidate.

**Request Body:**
```json
{
  "agent_id": "your-agent-id",
  "candidate_id": "1",
  "name": "John Doe",
  "email": "john@example.com",
  "bio": "...",
  "skills": "React, Node.js",
  "job_description": "...",
  "additional_instructions": ""
}
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "lead-score-api",
  "version": "1.0.0"
}
```

## CORS

The server is configured to accept requests from:
- `http://localhost:5173`
- `http://127.0.0.1:5173`
- `http://10.1.0.5:5173`
- `http://20.84.81.110:5173`

You can modify the CORS configuration in `src/main.rs` if needed.

## Differences from Python Backend

- Uses Axum web framework instead of Flask
- Uses RunAgent Rust SDK instead of Python SDK
- Type-safe request/response handling with Serde
- Async/await throughout
- Better error handling with Result types

## Development

Run with hot reload (requires cargo-watch):
```bash
cargo install cargo-watch
cargo watch -x run
```

## Build for Production

```bash
cargo build --release
./target/release/lead-agent-backend
```

