from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from runagent import RunAgentClient
import os
import json
import tempfile
from werkzeug.utils import secure_filename
from typing import Dict, Any

# Import DocumentManager from manage_documents
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from manage_documents import DocumentManager, COLLECTIONS

app = Flask(__name__)
# Configure CORS to allow all origins, methods, and headers
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": "*"}})

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize RunAgent clients
# Agent ID can be set via environment variable RAG_AGENT_ID or defaults to local mode
# For local mode, agent_id can be omitted or set to None
agent_id = os.getenv("RAG_AGENT_ID", "64f60008-5ed2-450c-a36a-53bdb662dfc2")  # Update with your agent ID or set via env var

rag_client = RunAgentClient(
    agent_id=agent_id,
    entrypoint_tag="query",
    local=False
)

stream_client = RunAgentClient(
    agent_id=agent_id,
    entrypoint_tag="query_stream",
    local=False
)

# Initialize DocumentManager
document_manager = None

def get_document_manager():
    """Get or create DocumentManager instance"""
    global document_manager
    if document_manager is None:
        document_manager = DocumentManager()
    return document_manager


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    # Log the request for debugging
    print(f"✅ Health check request from: {request.remote_addr}")
    print(f"   Headers: {dict(request.headers)}")
    
    return jsonify({
        "status": "healthy",
        "agent_id": agent_id,
        "mode": "local",
        "server_ip": request.host,
        "client_ip": request.remote_addr
    })


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Upload and process a PDF document"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        db_type = request.form.get('db_type', 'products').lower()
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        if db_type not in COLLECTIONS:
            return jsonify({
                "error": f"Invalid database type. Must be one of: {list(COLLECTIONS.keys())}"
            }), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # Process document using DocumentManager
            manager = get_document_manager()
            result = manager.add_document(temp_path, db_type)
            
            if result["success"]:
                return jsonify({
                    "success": True,
                    "message": result["message"],
                    "chunks_added": result["chunks_added"],
                    "database": result["database"]
                })
            else:
                return jsonify({"error": result["message"]}), 400
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/query', methods=['POST'])
def query_rag():
    """Query the RAG system (non-streaming)"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        # Call the agent
        result = rag_client.run(question=question)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/query/stream', methods=['POST'])
def query_rag_stream():
    """Query the RAG system (streaming)"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        def generate():
            try:
                for chunk in stream_client.run_stream(question=question):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics for all databases"""
    try:
        manager = get_document_manager()
        stats = []
        
        for db_type, config in COLLECTIONS.items():
            try:
                info = manager.client.get_collection(config["collection_name"])
                stats.append({
                    "name": config["name"],
                    "collection": config["collection_name"],
                    "documents": info.vectors_count,
                    "description": config["description"]
                })
            except Exception as e:
                stats.append({
                    "name": config["name"],
                    "collection": config["collection_name"],
                    "documents": 0,
                    "description": config["description"],
                    "error": str(e)
                })
        
        return jsonify({"success": True, "stats": stats})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/databases', methods=['GET'])
def get_databases():
    """Get available database types"""
    databases = [
        {
            "id": db_type,
            "name": config["name"],
            "description": config["description"]
        }
        for db_type, config in COLLECTIONS.items()
    ]
    return jsonify({"success": True, "databases": databases})


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get example queries"""
    examples = [
        {
            "name": "Product Information",
            "question": "What are the key features of our products?",
            "category": "products"
        },
        {
            "name": "Customer Support",
            "question": "How do I troubleshoot common issues?",
            "category": "support"
        },
        {
            "name": "Financial Data",
            "question": "What is the revenue breakdown by product category?",
            "category": "finance"
        },
        {
            "name": "General Query",
            "question": "What is the pricing strategy for our products?",
            "category": "general"
        }
    ]
    return jsonify(examples)


# Handle OPTIONS requests for CORS preflight
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        print(f"🔍 CORS preflight request from: {request.remote_addr}")
        response = Response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

@app.after_request
def after_request(response):
    """Log all requests for debugging"""
    print(f"📥 {request.method} {request.path} - {response.status_code} from {request.remote_addr}")
    return response


if __name__ == '__main__':
    import socket
    
    # Get the local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("=" * 60)
    print("🚀 RAG Agent Backend Server Starting...")
    print(f"📡 Server will run on all interfaces (0.0.0.0)")
    print(f"📡 Local access: http://localhost:5000")
    print(f"📡 Local IP access: http://{local_ip}:5000")
    print(f"📡 Health check: http://0.0.0.0:5000/health")
    print("=" * 60)
    # Run on all interfaces (0.0.0.0) to allow connections from other devices
    # This is necessary for remote access
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)

