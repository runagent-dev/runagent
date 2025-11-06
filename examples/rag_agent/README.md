# RAG Agent SaaS Application

A full-stack SaaS application for intelligent document querying using RAG (Retrieval-Augmented Generation) with intelligent database routing.

## Features

- **PDF Upload**: Upload PDF documents to vector databases (products, support, finance)
- **Query Interface**: Ask questions about uploaded documents
- **Streaming & Non-Streaming**: Support for both streaming and non-streaming query responses
- **Database Statistics**: View statistics about uploaded documents
- **Intelligent Routing**: Automatically routes queries to the appropriate database

## Architecture

```
rag_agent/
├── agent/              # RunAgent agent implementation
├── backend/            # Flask backend API
│   ├── app.py         # Main Flask application
│   └── requirements.txt
├── frontend/          # Frontend web application
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── package.json
├── manage_documents.py # Document management utilities
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 14+ (for frontend)
- Environment variables configured (see below)

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the `rag_agent` directory (or set environment variables):
```bash
OPENAI_API_KEY=your-openai-api-key
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-qdrant-api-key
RAG_AGENT_ID=your-agent-id  # Optional, for local mode
```

4. Update the agent ID in `backend/app.py`:
   - You can either set the `RAG_AGENT_ID` environment variable
   - Or update the default value in `app.py` (line 29)

5. Start the backend server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the frontend server:
```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

## Usage

### Upload Documents

1. Open the application in your browser
2. Click on the "📤 Upload Documents" tab
3. Select a PDF file
4. Choose a database type (products, support, or finance)
5. Click "Upload & Process"

### Query Documents

1. Click on the "💬 Query Documents" tab
2. Enter your question in the text area
3. Click "Query" for non-streaming response or "Stream Query" for streaming response
4. View the answer and metadata

### View Statistics

1. Click on the "📊 Statistics" tab
2. View document counts for each database
3. Click "Refresh" to update statistics

## API Endpoints

### Backend API

- `GET /health` - Health check
- `POST /api/upload` - Upload PDF document
- `POST /api/query` - Query documents (non-streaming)
- `POST /api/query/stream` - Query documents (streaming)
- `GET /api/stats` - Get database statistics
- `GET /api/databases` - Get available database types
- `GET /api/examples` - Get example queries

## Database Types

- **products**: Product information, specifications, features
- **support**: Customer support, FAQs, troubleshooting guides
- **finance**: Financial data, revenue, costs, reports

## Troubleshooting

### Backend not starting
- Check that all environment variables are set
- Verify that the agent ID is correct
- Ensure all Python dependencies are installed

### Frontend can't connect to backend
- Verify backend is running on `http://localhost:5000`
- Check browser console for CORS errors
- Update `API_BASE_URL` in `frontend/app.js` if backend is on a different port

### Upload fails
- Ensure PDF file is under 50MB
- Check that database type is valid
- Verify Qdrant connection is working

## Development

### Running in Development Mode

Backend (Flask debug mode):
```bash
cd backend
python app.py
```

Frontend (with hot reload):
```bash
cd frontend
npm run dev
```

## License

This project is part of the RunAgent examples.

