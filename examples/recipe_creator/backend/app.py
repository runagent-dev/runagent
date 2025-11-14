from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from runagent import RunAgentClient
import os
import json

app = Flask(__name__)
CORS(app)

# Initialize RunAgent client
recipe_client = RunAgentClient(
    agent_id="7cd7f85d-248c-4931-831a-5b4d43a01a78",
    entrypoint_tag="recipe_create",
    local=False
)

stream_client = RunAgentClient(
    agent_id="7cd7f85d-248c-4931-831a-5b4d43a01a78",
    entrypoint_tag="recipe_stream",
    local=False
)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "agent_id": "00efd47c-2c3d-492b-97ec-c6b79eeb93c4",
        "mode": "local"
    })


@app.route('/api/recipe', methods=['POST'])
def create_recipe():
    """Create a recipe (non-streaming)"""
    try:
        data = request.json
        ingredients = data.get('ingredients', '')
        dietary_restrictions = data.get('dietary_restrictions', '')
        time_limit = data.get('time_limit', '')
        
        if not ingredients:
            return jsonify({"error": "Ingredients are required"}), 400
        
        # Call the agent
        result = recipe_client.run(
            ingredients=ingredients,
            dietary_restrictions=dietary_restrictions,
            time_limit=time_limit
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/recipe/stream', methods=['POST'])
def create_recipe_stream():
    """Create a recipe (streaming)"""
    try:
        data = request.json
        ingredients = data.get('ingredients', '')
        dietary_restrictions = data.get('dietary_restrictions', '')
        time_limit = data.get('time_limit', '')
        
        if not ingredients:
            return jsonify({"error": "Ingredients are required"}), 400
        
        def generate():
            for chunk in stream_client.run(
                ingredients=ingredients,
                dietary_restrictions=dietary_restrictions,
                time_limit=time_limit
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/examples', methods=['GET'])
def get_examples():
    """Get example recipe queries"""
    examples = [
        {
            "name": "Quick Chicken Dinner",
            "ingredients": "chicken breast, broccoli, rice, garlic",
            "dietary_restrictions": "",
            "time_limit": "30 minutes"
        },
        {
            "name": "Vegetarian Pasta",
            "ingredients": "pasta, mushrooms, spinach, cream, parmesan",
            "dietary_restrictions": "vegetarian",
            "time_limit": "25 minutes"
        },
        {
            "name": "Healthy Breakfast",
            "ingredients": "oats, banana, honey, almonds, milk",
            "dietary_restrictions": "",
            "time_limit": "15 minutes"
        },
        {
            "name": "Vegan Buddha Bowl",
            "ingredients": "quinoa, chickpeas, sweet potato, kale, tahini",
            "dietary_restrictions": "vegan",
            "time_limit": "45 minutes"
        }
    ]
    return jsonify(examples)


if __name__ == '__main__':
    app.run(debug=True, port=5000)