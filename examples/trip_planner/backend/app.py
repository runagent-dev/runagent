from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from runagent import RunAgentClient
import os
import json

app = Flask(__name__)
# Explicit CORS to avoid preflight failures from different hosts/ports
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)

# Initialize RunAgent client - UPDATE THESE WITH YOUR ACTUAL IDs
LOCAL_MODE="false"
AGENT_ID="be1eef6e-2700-4980-b808-e94b3394e747"
# Initialize RunAgent clients
trip_client = RunAgentClient(
    agent_id="be1eef6e-2700-4980-b808-e94b3394e747",
    entrypoint_tag="trip_create",
    local=False
)

stream_client = RunAgentClient(
    agent_id="be1eef6e-2700-4980-b808-e94b3394e747",
    entrypoint_tag="trip_stream",
    local=False
)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        mode = "remote"
        try:
            mode = "local" if getattr(trip_client, 'local', False) else "remote"
        except Exception:
            pass
        return jsonify({
            "status": "healthy",
            "agent_id": AGENT_ID,
            "mode": mode
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/trip', methods=['POST'])
def create_trip():
    """Create a trip itinerary (non-streaming)"""
    try:
        data = request.json
        destination = data.get('destination', '')
        num_days = data.get('num_days', 2)
        preferences = data.get('preferences', '')
        
        if not destination:
            return jsonify({"error": "Destination is required"}), 400
        
        # Call the agent
        result = trip_client.run(
            destination=destination,
            num_days=num_days,
            preferences=preferences
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/trip/stream', methods=['POST'])
def create_trip_stream():
    """Create a trip itinerary (streaming)"""
    try:
        data = request.json
        destination = data.get('destination', '')
        num_days = data.get('num_days', 2)
        preferences = data.get('preferences', '')
        
        if not destination:
            return jsonify({"error": "Destination is required"}), 400
        
        def generate():
            for chunk in stream_client.run(
                destination=destination,
                num_days=num_days,
                preferences=preferences
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/destinations', methods=['GET'])
def get_destinations():
    """Get example destinations"""
    destinations = [
        {
            "city": "Rome",
            "country": "Italy",
            "description": "Ancient city with historic landmarks",
            "popular_for": "History, Art, Food"
        },
        {
            "city": "Paris",
            "country": "France",
            "description": "City of lights and romance",
            "popular_for": "Art, Culture, Cuisine"
        },
        {
            "city": "Tokyo",
            "country": "Japan",
            "description": "Modern metropolis meets tradition",
            "popular_for": "Technology, Culture, Food"
        },
        {
            "city": "Barcelona",
            "country": "Spain",
            "description": "Mediterranean beauty and Gaudi architecture",
            "popular_for": "Architecture, Beaches, Culture"
        }
    ]
    return jsonify(destinations)


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get example trip queries"""
    examples = [
        {
            "name": "Rome Weekend Getaway",
            "destination": "Rome",
            "num_days": 2,
            "preferences": "historical sites, Italian cuisine, must-see landmarks"
        },
        {
            "name": "Rome Art & Culture",
            "destination": "Rome",
            "num_days": 3,
            "preferences": "museums, art galleries, Vatican, local restaurants"
        },
        {
            "name": "Rome Food Tour",
            "destination": "Rome",
            "num_days": 2,
            "preferences": "traditional Roman food, pasta, local trattorias"
        },
        {
            "name": "Rome Historic Journey",
            "destination": "Rome",
            "num_days": 4,
            "preferences": "ancient ruins, Colosseum, Roman Forum, historical churches"
        }
    ]
    return jsonify(examples)


if __name__ == '__main__':
    # Check if agent ID is set
    if AGENT_ID == "be1eef6e-2700-4980-b808-e94b3394e747":
        print("⚠️  WARNING: Please set AGENT_ID environment variable")
        print("   Run 'runagent serve .' in the agent directory first")
        print("   Then set AGENT_ID to the ID shown in the output\n")
    
    print(f"🚀 Starting Trip Planner Backend")
    print(f"   Agent ID: {AGENT_ID}")
    print(f"   Server: http://localhost:5000\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)