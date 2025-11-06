from flask import Flask, request, jsonify
from flask_cors import CORS
from runagent import RunAgentClient
import os
import json
from typing import List, Dict, Any
import traceback

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://10.1.0.5:5173",
            "http://20.84.81.110:5173"
        ]
    }
})

@app.route('/api/score-leads', methods=['POST'])
def score_leads():
    """
    API endpoint to score leads using RunAgent
    
    Expected JSON body:
    {
        "agent_id": "your-agent-id",
        "candidates": [...],
        "job_description": "...",
        "top_n": 3,
        "generate_emails": true
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('agent_id'):
            return jsonify({'error': 'agent_id is required'}), 400
        
        if not data.get('candidates'):
            return jsonify({'error': 'candidates list is required'}), 400
        
        agent_id = data['agent_id']
        candidates = data.get('candidates', [])
        top_n = data.get('top_n', 3)
        job_description = data.get('job_description', '')
        generate_emails = data.get('generate_emails', True)
        additional_instructions = data.get('additional_instructions', '')
        
        # Normalize candidates: ensure they're all dictionaries, not JSON strings
        normalized_candidates = []
        for candidate in candidates:
            if isinstance(candidate, str):
                # If it's a JSON string, parse it
                try:
                    candidate = json.loads(candidate)
                except json.JSONDecodeError:
                    return jsonify({'error': f'Invalid candidate format: expected dict or JSON string, got: {candidate}'}), 400
            if not isinstance(candidate, dict):
                return jsonify({'error': f'Invalid candidate format: expected dict or JSON string, got: {type(candidate)}'}), 400
            normalized_candidates.append(candidate)
        
        candidates = normalized_candidates
        
        # Debug: Log candidate types before sending to SDK
        print(f"[DEBUG] Number of candidates: {len(candidates)}")
        if candidates:
            print(f"[DEBUG] First candidate type: {type(candidates[0])}")
            print(f"[DEBUG] First candidate sample: {str(candidates[0])[:200]}")
        
        # Initialize RunAgent client
        client = RunAgentClient(
            agent_id=agent_id,
            entrypoint_tag="lead_score_flow",
            local=False  # Set to False when using RunAgent Cloud
        )
        
        # Run the lead scoring flow
        result = client.run(
            top_n=top_n,
            job_description=job_description,
            additional_instructions=additional_instructions,
            generate_emails=generate_emails,
            candidates=candidates
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in score_leads: {error_trace}")
        return jsonify({
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/score-single', methods=['POST'])
def score_single_candidate():
    """
    API endpoint to score a single candidate
    
    Expected JSON body:
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
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['agent_id', 'name', 'bio']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        agent_id = data['agent_id']
        
        # Initialize RunAgent client
        client = RunAgentClient(
            agent_id=agent_id,
            entrypoint_tag="score_candidate",
            local=True
        )
        
        # Score single candidate
        result = client.run(
            candidate_id=data.get('candidate_id', 'temp-id'),
            name=data['name'],
            email=data.get('email', ''),
            bio=data['bio'],
            skills=data.get('skills', ''),
            job_description=data.get('job_description', ''),
            additional_instructions=data.get('additional_instructions', '')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error in score_single_candidate: {error_trace}")
        return jsonify({
            'error': str(e),
            'traceback': error_trace
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'lead-score-api',
        'version': '1.0.0'
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)