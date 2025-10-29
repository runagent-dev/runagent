# Lead Score SaaS - Complete Deployment Guide

## 🚀 Quick Start

This is a complete SaaS solution for AI-powered lead scoring using RunAgent and CrewAI. Users can upload their candidates' CSV, provide a job description, and get AI-scored results with automated email generation.

## 📋 Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- npm or yarn
- OpenAI API key
- Serper API key (for web search)

## 🏗️ Architecture

```
┌─────────────────┐
│   React Frontend │
│   (Port 5173)   │
└────────┬────────┘
         │ HTTP REST API
         ↓
┌─────────────────┐
│  Flask Backend  │
│   (Port 8000)   │
└────────┬────────┘
         │ RunAgent Python SDK
         ↓
┌─────────────────┐
│  RunAgent Agent │
│  (CrewAI Flow)  │
└─────────────────┘
```

## 📦 Part 1: Deploy RunAgent Agent

### Step 1: Setup Environment

```bash
cd examples/lead-score-flow

# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here
EOF
```

### Step 2: Install Dependencies

```bash
# Install RunAgent
pip install runagent

# Install project dependencies
crewai install
```

### Step 3: Deploy Locally

```bash
# Start the RunAgent server
runagent serve .

# You'll see output like:
# ✓ Agent deployed successfully!
# Agent ID: dbf63fb6-a11c-40a9-aae0-84e57b16ad01
# Entrypoints:
#   - lead_score_flow
#   - score_candidate
```

**🔑 IMPORTANT: Copy the Agent ID - you'll need it for the frontend!**

### Step 4: Test the Agent (Optional)

```bash
# Test in a new terminal
python test_agent.py
```

```python
# test_agent.py
from runagent import RunAgentClient

client = RunAgentClient(
    agent_id="YOUR_AGENT_ID_HERE",
    entrypoint_tag="lead_score_flow",
    local=True
)

result = client.run(top_n=3, generate_emails=True)
print(result)
```

## 🔧 Part 2: Deploy Backend API

### Step 1: Setup Backend

```bash
cd ../../backend  # Go to backend folder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Start Backend Server

```bash
python app.py

# Server will start on http://localhost:8000
```

### Step 3: Test Backend (Optional)

```bash
curl http://localhost:8000/api/health
```

## 🎨 Part 3: Deploy Frontend

### Step 1: Setup Frontend

```bash
cd ../frontend  # Go to frontend folder

# Install dependencies
npm install

# Or with yarn
yarn install
```

### Step 2: Start Development Server

```bash
npm run dev

# Or with yarn
yarn dev

# Frontend will start on http://localhost:5173
```

### Step 3: Build for Production

```bash
npm run build

# Serve the built files
npm run preview
```

## 🎯 Usage Guide

### For End Users

1. **Open the Application**
   - Navigate to `http://localhost:5173`

2. **Configure Settings**
   - Enter your RunAgent Agent ID (from Step 3 of Part 1)
   - Paste the job description
   - Set the number of top candidates (default: 3)

3. **Upload Candidates**
   - Prepare a CSV file with columns: `id,name,email,bio,skills`
   - Drag and drop or click to upload

4. **View Results**
   - See scored candidates ranked by AI
   - Download all scores as CSV
   - Download personalized emails for all candidates

### Sample CSV Format

```csv
id,name,email,bio,skills
1,John Doe,john@example.com,"Experienced React developer with 5 years","React, Node.js, TypeScript"
2,Jane Smith,jane@example.com,"Full-stack developer specializing in AI","Python, React, TensorFlow"
```

## 🌐 Deployment to Production

### Option 1: Deploy with RunAgent Cloud

```bash
# Deploy agent to RunAgent Cloud
runagent deploy .

# This will give you a cloud agent ID
# Update the backend to use this ID
```

### Option 2: Deploy with Docker

**Create docker-compose.yml:**

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - AGENT_ID=${AGENT_ID}
    depends_on:
      - agent

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  agent:
    build: ./examples/lead-score-flow
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SERPER_API_KEY=${SERPER_API_KEY}
```

**Deploy:**

```bash
docker-compose up -d
```

### Option 3: Deploy to Cloud Platforms

#### Backend (Flask API)
- **Heroku**: `git push heroku main`
- **Railway**: Connect GitHub repo
- **AWS EB**: `eb deploy`
- **Google Cloud Run**: `gcloud run deploy`

#### Frontend (React)
- **Vercel**: `vercel --prod`
- **Netlify**: `netlify deploy --prod`
- **AWS S3 + CloudFront**: Build and upload to S3
- **GitHub Pages**: `npm run build` and push to gh-pages

## 🔒 Security Best Practices

1. **API Keys**
   - Never commit `.env` files
   - Use environment variables
   - Rotate keys regularly

2. **CORS**
   - Configure proper CORS origins in production
   - Don't use `*` for allowed origins

3. **Rate Limiting**
   - Implement rate limiting on API endpoints
   - Use tools like `flask-limiter`

4. **Authentication**
   - Add user authentication (JWT, OAuth)
   - Implement API key authentication for backend

## 🐛 Troubleshooting

### Agent Not Found Error
```bash
# Ensure agent is running
runagent serve .

# Check agent status
runagent list
```

### Connection Refused Error
```bash
# Check if backend is running
curl http://localhost:8000/api/health

# Check if all services are running
ps aux | grep -E '(runagent|flask|node)'
```

### CSV Upload Error
- Ensure CSV has required columns: id, name, email, bio, skills
- Check CSV encoding (should be UTF-8)
- Verify no special characters in CSV

## 📊 Monitoring and Logs

### View Agent Logs
```bash
# In the terminal where runagent serve is running
# Logs will show agent activity
```

### View Backend Logs
```bash
# Backend logs show in terminal
# For production, use logging services like:
# - Datadog
# - New Relic
# - CloudWatch
```

## 🎓 Customization

### Adding More Features

1. **Custom Scoring Criteria**
   - Edit `src/lead_score_flow/constants.py`
   - Modify agent prompts in `config/tasks.yaml`

2. **Different Email Templates**
   - Update `lead_response_crew` configuration
   - Modify email generation logic

3. **Additional Data Points**
   - Add columns to CSV
   - Update Candidate model in `types.py`
   - Update frontend to handle new fields

### Scaling for High Volume

1. **Use Background Jobs**
   ```python
   # Use Celery or RQ for async processing
   from celery import Celery
   
   @celery.task
   def score_leads_async(data):
       # Process in background
   ```

2. **Cache Results**
   ```python
   # Use Redis for caching
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'redis'})
   ```

## 💡 Tips for Best Results

1. **Job Descriptions**
   - Be specific and detailed
   - Include must-have vs nice-to-have skills
   - Mention company culture and values

2. **Candidate Bios**
   - Encourage detailed bios
   - Include years of experience
   - Mention specific projects or achievements

3. **Scoring**
   - Use `additional_instructions` for specific criteria
   - Adjust `top_n` based on your hiring needs
   - Review and refine based on results

## 📞 Support

- **Documentation**: https://docs.run-agent.ai
- **Discord**: https://discord.gg/Q9P9AdHVHz
- **GitHub Issues**: https://github.com/runagent-dev/runagent

## 📄 License

This project is licensed under the MIT License.

---

**Made with ❤️ using RunAgent, CrewAI, React, and Flask**