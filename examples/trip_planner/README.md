# TripGenius - AI Trip Planner SaaS

A complete SaaS application for AI-powered trip planning using RunAgent, AG2, and FalkorDB GraphRAG.

## Architecture

```
travel-planner-saas/
├── agent/              # RunAgent-compatible trip planner agent
│   ├── trip_agent.py
│   ├── requirements.txt
│   └── runagent.config.json
├── backend/            # Flask REST API
│   ├── app.py
│   └── requirements.txt
└── frontend/           # Web UI
    ├── index.html
    ├── style.css
    ├── app.js
    └── package.json
```

## Prerequisites

1. **Python 3.8+**
2. **Node.js 14+** (for frontend dev server)
3. **OpenAI API Key** - Get from https://platform.openai.com/api-keys
4. **Google Maps API Key** - Get from https://console.cloud.google.com/ (enable Directions API)
5. **RunAgent CLI** installed (`pip install runagent`)

## Setup Instructions

### Step 1: Setup and Deploy the Agent

```bash
cd agent

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="your-openai-api-key"
export GOOGLE_MAP_API_KEY="your-google-maps-api-key"

# Deploy the agent locally with RunAgent
runagent serve .
```

**Important**: Copy the Agent ID from the output. It will look like:
```
Agent ID: abc12345-6789-0def-1234-567890abcdef
```

### Step 2: Setup Backend

Open a new terminal:

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Set environment variables with your Agent ID from Step 2
export AGENT_ID="abc12345-6789-0def-1234-567890abcdef"  # Replace with your actual Agent ID
export LOCAL_MODE="true"
export OPENAI_API_KEY="your-openai-api-key"

# Start the Flask server
python app.py
```

The backend will run on `http://localhost:5000`

### Step 4: Setup Frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will open automatically at `http://localhost:3000`

## Usage

1. Open `http://localhost:3000` in your browser
2. Browse example trips or create your own
3. Fill in:
   - **Destination**: City name (e.g., "Rome")
   - **Number of Days**: 1-14 days
   - **Preferences**: What you're interested in (food, culture, history, etc.)
4. Click "Create Itinerary" or "Stream Itinerary"
5. View your AI-generated trip plan!

## Features

- ✅ AI-powered trip planning with AG2 multi-agent system
- ✅ **Works for ANY city worldwide** (powered by GPT-4o knowledge)
- ✅ **Google Maps integration for real travel times and distances**
- ✅ Structured itinerary output with daily events
- ✅ Beautiful, responsive web interface
- ✅ Streaming and non-streaming modes
- ✅ Example trip templates
- ✅ RunAgent deployment compatible
- ✅ No database required - fully dynamic!

## API Endpoints

### Backend API

- `GET /health` - Health check
- `POST /api/trip` - Create trip itinerary (non-streaming)
- `POST /api/trip/stream` - Create trip itinerary (streaming)
- `GET /api/examples` - Get example trip queries
- `GET /api/destinations` - Get popular destinations

### Request Format

```json
{
  "destination": "Rome",
  "num_days": 3,
  "preferences": "historical sites, Italian cuisine"
}
```

### Response Format

```json
{
  "success": true,
  "itinerary": {
    "days": [
      {
        "events": [
          {
            "type": "Attraction",
            "location": "Colosseum",
            "city": "Rome",
            "description": "Ancient amphitheater..."
          },
          {
            "type": "Restaurant",
            "location": "Trattoria da Enzo",
            "city": "Rome",
            "description": "Traditional Roman dishes..."
          }
        ]
      }
    ]
  }
}
```

## Configuration

### Agent Configuration (runagent.config.json)

The agent exposes two entrypoints:
- `trip_create` - Non-streaming trip planning
- `trip_stream` - Streaming trip planning

### Environment Variables

**Agent:**
- `OPENAI_API_KEY` - OpenAI API key (required)
- `GOOGLE_MAP_API_KEY` - Google Maps API key (required for travel times)

**Backend:**
- `AGENT_ID` - RunAgent agent ID (required)
- `LOCAL_MODE` - "true" for local, "false" for remote (default: "true")

## Troubleshooting

### Agent not found
- Ensure `runagent serve .` is running in the agent directory
- Copy the correct Agent ID to the backend

### FalkorDB connection error
- Ensure Docker container is running on port 6379
- Check `FALKORDB_HOST` and `FALKORDB_PORT` environment variables

### Backend not connecting to agent
- Verify `AGENT_ID` in backend matches the agent ID from `runagent serve`
- Ensure `LOCAL_MODE=true` when running locally

### Frontend not loading
- Check that backend is running on port 5000
- Check browser console for CORS errors

## Production Deployment

For production deployment with RunAgent Cloud:

1. Deploy agent to RunAgent Cloud:
   ```bash
   runagent deploy .
   ```

2. Update backend environment:
   ```bash
   export AGENT_ID="your-cloud-agent-id"
   export LOCAL_MODE="false"
   ```

3. Deploy backend and frontend to your hosting platform

## License

Apache License 2.0

## Support

For issues or questions, please refer to:
- RunAgent Documentation: https://docs.run-agent.ai
- AG2 Documentation: https://docs.ag2.ai