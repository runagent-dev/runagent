# How RunAgent Rust SDK Handles API Authentication

## Overview

The Rust SDK is **independent** and doesn't validate tokens itself. Instead, it sends your API token to the RunAgent server, which validates it. Here's how it works:

## 1. API Token Loading (Priority Order)

The SDK loads your API token from these sources in order of priority:

1. **Environment Variable** (Highest Priority)
   ```bash
   export RUNAGENT_API_KEY="your-new-api-key-here"
   ```

2. **Config File** (`~/.runagent/user_data.json`)
   ```json
   {
     "api_key": "your-api-key",
     "base_url": "http://20.84.81.110:8335/"
   }
   ```

3. **Default** (None - will fail on protected endpoints)

## 2. How Tokens Are Sent to Server

When the SDK makes requests, it sends your API token in **TWO ways** for maximum compatibility:

### Method 1: Authorization Header
```rust
Authorization: Bearer <your-api-key>
```

### Method 2: Query Parameter (for WebSocket compatibility)
```
?token=<your-api-key>
```

See `src/client/rest_client.rs` lines 127-149:
- Line 128-130: Adds token as query parameter
- Line 148-149: Adds Authorization header with Bearer token

## 3. Server-Side Validation

The SDK **does NOT validate** tokens locally. When you make a request:

1. SDK sends your API token to the server
2. Server validates the token
3. Server checks if token has permission for requested resource
4. Server returns:
   - ✅ Success (200) if token is valid and authorized
   - ❌ 401 Unauthorized if token is invalid
   - ❌ 403 Forbidden if token is valid but lacks permission

## 4. Updating Your API Key

If you created a new API key, update it using one of these methods:

### Option A: Update Config File
```bash
cat > ~/.runagent/user_data.json << EOF
{
  "api_key": "your-new-api-key-here",
  "base_url": "http://20.84.81.110:8335/"
}
EOF
```

### Option B: Set Environment Variable
```bash
export RUNAGENT_API_KEY="your-new-api-key-here"
export RUNAGENT_BASE_URL="http://20.84.81.110:8335/"
```

### Option C: Use Config API (if implemented)
```rust
use runagent::utils::Config;

let mut config = Config::load()?;
config.api_key = Some("your-new-api-key".to_string());
config.save()?;
```

## 5. Current Status

Your current config file (`~/.runagent/user_data.json`) has:
- **Old API Key**: `rau_af476c074eb5045bfb5dee677140f8a4d3da6215056c26497da48e85390e4b43`
- **Base URL**: `http://20.84.81.110:8335/` ✅ (correct)

To use your new API key, update the config file with the new token!

