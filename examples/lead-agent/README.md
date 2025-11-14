# Lead Score SaaS

AI-powered lead scoring SaaS solution using RunAgent and CrewAI. The RunAgent agent uses CrewAI to analyze candidates, score them against job descriptions, and generate personalized follow-up emails.

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- npm or yarn
- OpenAI API key
- Serper API key (for web search)

## What the Agent Does

The RunAgent agent provides two main entry points:

1. **`lead_score_flow`**: Complete workflow that:
   - Scores all candidates against a job description using AI analysis
   - Ranks candidates by their match score
   - Generates personalized follow-up emails for all candidates
   - Returns top N candidates with detailed scoring rationale

2. **`score_candidate`**: Score a single candidate:
   - Analyzes candidate bio, skills, and experience
   - Compares against job requirements
   - Returns score (0-100) with detailed reasoning

The agent uses CrewAI with specialized crews:
- **LeadScoreCrew**: Analyzes and scores candidates based on job fit
- **LeadResponseCrew**: Generates personalized email responses

## Architecture

```
React Frontend (Port 5173)
    ↓ HTTP REST API
Flask Backend (Port 8000)
    ↓ RunAgent Python SDK
RunAgent Agent (CrewAI Flow)
    ├── LeadScoreCrew (scoring)
    └── LeadResponseCrew (email generation)
```

## Quick Start

### 1. Initialize and Configure RunAgent Agent

```bash
cd lead-score-flow

# Initialize the agent (creates runagent.config.json)
runagent init . --framework crewai

# This generates a unique agent_id and creates runagent.config.json
```

The `runagent init` command creates `runagent.config.json` with:
- Generated `agent_id` (unique identifier)
- Framework configuration (crewai)
- Empty `entrypoints` array

**Configure Entrypoints:**

The agent already has entrypoints configured in `runagent.config.json`:
```json
{
  "agent_architecture": {
    "entrypoints": [
      {
        "file": "main.py",
        "module": "run_flow",
        "tag": "lead_score_flow"
      },
      {
        "file": "main.py",
        "module": "score_single_candidate",
        "tag": "score_candidate"
      }
    ]
  }
}
```

**Important:** If you manually edit the `agent_id` in `runagent.config.json`, you must register it:
```bash
runagent register .
```

### 2. Setup Environment and Dependencies

```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here
EOF

# Install dependencies
pip install runagent
crewai install
```

### 3. Deploy RunAgent Agent Locally

```bash
# Start the RunAgent server
runagent serve .

# Copy the Agent ID from the output
```

### 4. Deploy Backend API

```bash
cd ../backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
python app.py
```

### 5. Deploy Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173`.

## Usage

1. **Configure Settings**
   - Enter your RunAgent Agent ID
   - Paste the job description
   - Set the number of top candidates (default: 3)

2. **Upload Candidates**
   - Prepare a CSV file with columns: `id,name,email,bio,skills`
   - Upload via the interface

3. **View Results**
   - See scored candidates ranked by AI
   - Download scores as CSV
   - Download personalized emails

### Sample CSV Format

```csv
id,name,email,bio,skills
1,John Doe,john@example.com,"Experienced React developer with 5 years","React, Node.js, TypeScript"
2,Jane Smith,jane@example.com,"Full-stack developer specializing in AI","Python, React, TensorFlow"
```

## Production Deployment with RunAgent Cloud

For production, deploy the agent to RunAgent Cloud for better scalability and reliability.

### Prerequisites

1. **RunAgent Account** - Sign up at [run-agent.ai](https://run-agent.ai)
2. **API Key** - Get your API key from the dashboard
3. **Authenticate CLI** - Configure your CLI with your API key

### Authentication Setup

```bash
# Setup authentication
runagent setup --api-key <your-api-key>

# Verify configuration
runagent setup --api-key <your-api-key>
```

### Deploy to Cloud

```bash
cd lead-score-flow

# Deploy to RunAgent Cloud (combines upload + start)
runagent deploy .

# You'll receive output like:
# ✅ Full deployment successful!
# 🆔 Agent ID: abc-123-def-456
# 🌐 Endpoint: https://api.run-agent.ai/api/v1/agents/abc-123-def-456
```

**Alternative: Two-Step Deploy**

For more control, upload and start separately:

```bash
# Step 1: Upload agent
runagent upload .

# Step 2: Start agent
runagent start --id <agent-id>
```

**Benefits of RunAgent Cloud:**
- Managed infrastructure with automatic scaling
- No need to run `runagent serve` locally
- Better performance and reliability
- Access from anywhere without local setup
- 24/7 uptime
- Full monitoring dashboard

After deployment, update your backend to use the cloud agent ID instead of the local one. The backend will connect to the cloud agent automatically when using `local=False` in the RunAgent client configuration.

## Security

- Never commit `.env` files
- Use environment variables for API keys
- Configure proper CORS origins in production
- Implement rate limiting and authentication

## Troubleshooting

### Agent Not Found
```bash
runagent serve .
runagent list
```

### Connection Refused
```bash
curl http://localhost:8000/api/health
```

### CSV Upload Error
- Ensure CSV has required columns: id, name, email, bio, skills
- Check CSV encoding (should be UTF-8)

## Customization

- **Scoring Criteria**: Edit `lead-score-flow/src/lead_score_flow/constants.py`
- **Email Templates**: Update `lead_response_crew` configuration
- **Additional Data**: Add columns to CSV and update models

## Support

- Documentation: https://docs.run-agent.ai
- Discord: https://discord.gg/Q9P9AdHVHz
- GitHub Issues: https://github.com/runagent-dev/runagent

## License

MIT License

---

For detailed deployment instructions, see [deployment_guide.md](./deployment_guide.md).

