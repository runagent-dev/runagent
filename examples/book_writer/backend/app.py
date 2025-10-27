from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from runagent import RunAgentClient
import os
import traceback
from datetime import datetime
import io

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    }
})

@app.route('/api/generate-outline', methods=['POST'])
def generate_outline():
    """
    Generate book outline
    
    Expected JSON body:
    {
        "agent_id": "your-agent-id",
        "title": "Book Title",
        "topic": "Book topic",
        "goal": "Book goal description"
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('agent_id'):
            return jsonify({'error': 'agent_id is required'}), 400
        
        if not data.get('topic'):
            return jsonify({'error': 'topic is required'}), 400
        
        agent_id = data['agent_id']
        title = data.get('title', 'Untitled Book')
        topic = data['topic']
        goal = data.get('goal', '')
        
        # Initialize RunAgent client for outline generation
        client = RunAgentClient(
            agent_id=agent_id,
            entrypoint_tag="generate_outline",
            local=True  # Set to False when using RunAgent Cloud
        )
        
        # Generate the outline
        result = client.run(
            title=title,
            topic=topic,
            goal=goal
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in generate_outline: {error_trace}")
        return jsonify({
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/write-book', methods=['POST'])
def write_book():
    """
    Write complete book with all chapters
    
    Expected JSON body:
    {
        "agent_id": "your-agent-id",
        "title": "Book Title",
        "topic": "Book topic",
        "goal": "Book goal description",
        "num_chapters": 5
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('agent_id'):
            return jsonify({'error': 'agent_id is required'}), 400
        
        if not data.get('topic'):
            return jsonify({'error': 'topic is required'}), 400
        
        agent_id = data['agent_id']
        title = data.get('title', 'Untitled Book')
        topic = data['topic']
        goal = data.get('goal', '')
        num_chapters = data.get('num_chapters', 5)
        
        # Initialize RunAgent client
        client = RunAgentClient(
            agent_id=agent_id,
            entrypoint_tag="write_full_book",
            local=True
        )
        
        # Write the complete book
        result = client.run(
            title=title,
            topic=topic,
            goal=goal,
            num_chapters=num_chapters
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in write_book: {error_trace}")
        return jsonify({
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/download-book', methods=['POST'])
def download_book():
    """
    Download book as markdown file
    
    Expected JSON body:
    {
        "title": "Book Title",
        "content": "Book content in markdown"
    }
    """
    try:
        data = request.json
        
        title = data.get('title', 'book')
        content = data.get('content', '')
        
        # Create filename
        filename = f"{title.replace(' ', '_')}.md"
        
        # Create file in memory
        file_stream = io.BytesIO(content.encode('utf-8'))
        file_stream.seek(0)
        
        return send_file(
            file_stream,
            mimetype='text/markdown',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in download_book: {error_trace}")
        return jsonify({
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'book-writer-api',
        'version': '1.0.0'
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)