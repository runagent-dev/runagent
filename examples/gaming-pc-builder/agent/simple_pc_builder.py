from functools import partial
from agno.agent import Agent
from agno.models.openai import OpenAIChat
import json
import requests
from typing import Dict, List
import time
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file (optional)
load_dotenv()

# Tavily API configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Optional: Add error handling
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable is not set")

print(f"API Key loaded: {'✓' if TAVILY_API_KEY else '✗'}")

# Global conversation memory
conversation_memory = []
user_context = {
    "budget": None,
    "resolution": None,
    "game_type": None,
    "performance_target": None,
    "current_build": None
}

def search_web_for_components(query: str) -> str:
    """Search the web using Tavily API for PC components"""
    try:
        if not TAVILY_API_KEY or TAVILY_API_KEY == "your-tavily-api-key":
            # Return mock data if API key not set
            return f"Mock search results for: {query} - Found relevant PC components with current pricing and availability."
        
        response = requests.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "max_results": 5,
                "include_domains": ["newegg.com", "amazon.com", "bestbuy.com", "pcpartpicker.com"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("answer", "No results found")
        else:
            return f"Search API error: {response.status_code}"
            
    except Exception as e:
        return f"Search error: {str(e)}"

def extract_user_preferences(user_query: str) -> Dict:
    """Extract user preferences from their message - IMPROVED VERSION"""
    query_lower = user_query.lower()
    preferences = {}
    
    # Extract budget - IMPROVED to handle multiple formats
    budget_patterns = [
        r'\$(\d+(?:,\d+)*)',           # $3000, $3,000
        r'(\d+(?:,\d+)*)\s*usd',       # 3000usd, 3000 usd
        r'(\d+(?:,\d+)*)\s*dollars?',  # 3000 dollars
        r'under\s+(\d+(?:,\d+)*)',     # under 3000
        r'around\s+\$?(\d+(?:,\d+)*)', # around $3000
        r'budget\s+of\s+\$?(\d+(?:,\d+)*)', # budget of $3000
        r'(\d+(?:,\d+)*)\s*buck',      # 3000 bucks
        r'max\s+\$?(\d+(?:,\d+)*)',    # max $3000
        r'up\s+to\s+\$?(\d+(?:,\d+)*)', # up to $3000
    ]
    
    for pattern in budget_patterns:
        budget_match = re.search(pattern, query_lower)
        if budget_match:
            budget_value = budget_match.group(1).replace(',', '')
            preferences['budget'] = float(budget_value)
            print(f"DEBUG: Extracted budget: {preferences['budget']} from pattern: {pattern}")
            break
    
    # Extract resolution
    if '4k' in query_lower or '2160p' in query_lower:
        preferences['resolution'] = '4K'
    elif '1440p' in query_lower or '2k' in query_lower:
        preferences['resolution'] = '1440p'
    elif '1080p' in query_lower:
        preferences['resolution'] = '1080p'
    
    # Extract game type
    if 'aaa' in query_lower or 'triple-a' in query_lower:
        preferences['game_type'] = 'AAA'
    elif 'esports' in query_lower or 'competitive' in query_lower:
        preferences['game_type'] = 'eSports'
    elif 'indie' in query_lower:
        preferences['game_type'] = 'Indie'
    elif 'workstation' in query_lower or 'content creation' in query_lower:
        preferences['game_type'] = 'Workstation'
    
    # Extract performance target
    if 'budget' in query_lower or 'cheap' in query_lower or 'affordable' in query_lower:
        preferences['performance_target'] = 'budget'
    elif 'high-end' in query_lower or 'enthusiast' in query_lower or 'premium' in query_lower or 'top-tier' in query_lower:
        preferences['performance_target'] = 'enthusiast'
    elif 'high' in query_lower:
        preferences['performance_target'] = 'high'
    elif 'medium' in query_lower or 'mid' in query_lower:
        preferences['performance_target'] = 'medium'
    
    return preferences

def update_user_context(preferences: Dict):
    """Update global user context with new preferences"""
    global user_context
    for key, value in preferences.items():
        if value is not None:
            user_context[key] = value

def get_context_string() -> str:
    """Get current user context as a string"""
    context_parts = []
    if user_context['budget']:
        context_parts.append(f"Budget: ${user_context['budget']}")
    if user_context['resolution']:
        context_parts.append(f"Resolution: {user_context['resolution']}")
    if user_context['game_type']:
        context_parts.append(f"Games: {user_context['game_type']}")
    if user_context['performance_target']:
        context_parts.append(f"Performance: {user_context['performance_target']}")
    
    return " | ".join(context_parts) if context_parts else "No specific preferences set"

def add_to_memory(role: str, content: str):
    """Add message to conversation memory"""
    global conversation_memory
    conversation_memory.append({"role": role, "content": content})
    
    # Keep only last 10 messages to prevent context overflow
    if len(conversation_memory) > 10:
        conversation_memory = conversation_memory[-10:]

def get_conversation_history() -> str:
    """Get formatted conversation history"""
    if not conversation_memory:
        return "This is the start of our conversation."
    
    history = "CONVERSATION HISTORY:\n"
    for msg in conversation_memory[-6:]:  # Last 6 messages
        role_display = "USER" if msg["role"] == "user" else "ASSISTANT"
        history += f"{role_display}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}\n"
    
    return history

def determine_build_specs(user_query: str, extracted_budget: float = None) -> Dict:
    """Determine build specifications based on user query and budget"""
    query_lower = user_query.lower()
    
    # Determine budget
    budget = extracted_budget
    if not budget:
        # Look for budget indicators in the query
        if any(word in query_lower for word in ['budget', 'cheap', 'affordable']) and any(word in query_lower for word in ['800', '900', '1000']):
            budget = 1000
        elif any(word in query_lower for word in ['4k', 'high-end', 'premium', 'enthusiast']) or any(word in query_lower for word in ['3000', '2800', '2900']):
            budget = 3000
        elif any(word in query_lower for word in ['1440p', 'mid-range']) or any(word in query_lower for word in ['2000', '1800', '1900']):
            budget = 2000
        elif any(word in query_lower for word in ['1500', '1600', '1700']):
            budget = 1600
        else:
            budget = 1500  # Default
    
    # Determine resolution based on budget and query
    if '4k' in query_lower or budget >= 2500:
        resolution = '4K'
    elif '1440p' in query_lower or (budget >= 1500 and budget < 2500):
        resolution = '1440p'
    else:
        resolution = '1080p'
    
    # Determine performance target
    if budget >= 2500:
        performance = 'enthusiast'
    elif budget >= 1800:
        performance = 'high'
    elif budget >= 1200:
        performance = 'medium'
    else:
        performance = 'budget'
    
    # Check for workstation requirements
    if 'workstation' in query_lower or 'content creation' in query_lower:
        performance = 'workstation'
    
    return {
        'budget': budget,
        'resolution': resolution,
        'performance': performance
    }

def generate_build_recommendation(budget: float, resolution: str, performance: str) -> str:
    """Generate a specific build recommendation based on specifications"""
    
    if budget <= 1200:  # Budget Build
        return f"""### Budget Gaming PC Build for ${int(budget)} (1080p Gaming)

**CPU:** AMD Ryzen 5 5600G - $129
**GPU:** NVIDIA RTX 4060 - $299
**Motherboard:** ASRock B450M Pro4 - $69
**RAM:** Corsair Vengeance LPX 16GB DDR4-3200 - $59
**Storage:** Kingston NV2 1TB NVMe SSD - $49
**PSU:** EVGA BR 600W 80+ Bronze - $59
**Case:** Cooler Master MasterBox Q300L - $39
**CPU Cooler:** Stock AMD Cooler - $0

**Total Cost:** $703

**Performance:** Solid 1080p gaming at high settings, 60-75 FPS in most modern games, 100+ FPS in eSports titles like CS2, Valorant, and League of Legends

**Why This Build:** Excellent entry-level gaming performance with room for GPU upgrades later. The Ryzen 5 5600G provides great value and includes integrated graphics as backup. Perfect for gamers on a tight budget who want reliable 1080p performance."""

    elif budget <= 1800:  # Mid-Range Build
        return f"""### Mid-Range Gaming PC Build for ${int(budget)} (1440p Gaming)

**CPU:** AMD Ryzen 5 7600X - $229
**GPU:** NVIDIA RTX 4070 - $549
**Motherboard:** MSI B650 Gaming Plus WiFi - $179
**RAM:** Corsair Vengeance 32GB DDR5-5600 - $129
**Storage:** Samsung 980 Pro 1TB NVMe SSD - $89
**PSU:** Corsair RM750e 750W 80+ Gold - $109
**Case:** Fractal Design Core 1000 - $59
**CPU Cooler:** Noctua NH-U12S - $69

**Total Cost:** $1,412

**Performance:** Excellent 1440p gaming at ultra settings, 80-100+ FPS in most games including Cyberpunk 2077, Call of Duty, and Assassin's Creed. Great for AAA titles and competitive gaming

**Why This Build:** Perfect balance of performance and value for high-resolution gaming with future-proofing. The RTX 4070 handles 1440p beautifully and supports ray tracing for enhanced visuals."""

    elif budget <= 2500:  # High-End Build
        return f"""### High-End Gaming PC Build for ${int(budget)} (1440p/4K Gaming)

**CPU:** AMD Ryzen 7 7700X - $299
**GPU:** NVIDIA RTX 4070 Ti Super - $799
**Motherboard:** ASUS ROG Strix B650E-F Gaming WiFi - $279
**RAM:** G.Skill Trident Z5 32GB DDR5-6000 - $179
**Storage:** Samsung 980 Pro 2TB NVMe SSD - $169
**PSU:** Corsair RM850x 850W 80+ Gold - $139
**Case:** Lian Li PC-O11 Dynamic - $149
**CPU Cooler:** Noctua NH-D15 - $109

**Total Cost:** $2,222

**Performance:** Exceptional 1440p gaming at ultra settings with ray tracing (100+ FPS), solid 4K gaming at high settings (60-80 FPS) in demanding games like Cyberpunk 2077, Red Dead Redemption 2, and modern AAA titles

**Why This Build:** High-performance components for maximum gaming experience and excellent future-proofing. Handles any current game at maximum settings and will remain relevant for years to come."""

    elif performance == 'workstation':  # Workstation Build
        return f"""### High-End Workstation Gaming PC Build for ${int(budget)} (Gaming + Content Creation)

**CPU:** AMD Ryzen 9 7900X - $429
**GPU:** NVIDIA RTX 4080 Super - $999
**Motherboard:** ASUS ROG Strix X670E-E Gaming WiFi - $379
**RAM:** G.Skill Trident Z5 64GB DDR5-5600 - $299
**Storage:** Samsung 980 Pro 2TB NVMe SSD - $169
**Storage 2:** Samsung 980 Pro 1TB NVMe SSD - $89
**PSU:** Corsair RM1000x 1000W 80+ Gold - $179
**Case:** Fractal Design Define 7 XL - $199
**CPU Cooler:** NZXT Kraken X63 280mm AIO - $149

**Total Cost:** $2,891

**Performance:** Outstanding 4K gaming (80+ FPS ultra settings), exceptional content creation performance for video editing, 3D rendering, streaming, and professional workloads

**Why This Build:** Perfect for gamers who also do content creation, streaming, or professional work. The 12-core CPU and 64GB RAM handle any workload while the RTX 4080 Super delivers top-tier gaming performance."""

    else:  # Enthusiast Build ($3000+)
        return f"""### Enthusiast Gaming PC Build for ${int(budget)} (4K Gaming)

**CPU:** AMD Ryzen 9 7900X - $429
**GPU:** NVIDIA RTX 4080 Super - $999
**Motherboard:** ASUS ROG Strix X670E-E Gaming WiFi - $379
**RAM:** G.Skill Trident Z5 32GB DDR5-6000 CL30 - $199
**Storage:** Samsung 980 Pro 2TB NVMe SSD - $169
**PSU:** Corsair RM1000x 1000W 80+ Gold - $179
**Case:** Lian Li PC-O11 Dynamic XL - $199
**CPU Cooler:** NZXT Kraken X63 280mm AIO - $149

**Total Cost:** $2,702

**Performance:** Outstanding 4K gaming at ultra settings with ray tracing (80+ FPS), exceptional 1440p performance (120+ FPS), perfect for high-refresh rate gaming on any resolution

**Why This Build:** Top-tier components for maximum gaming performance, content creation, and future-proofing. Handles any game at maximum settings including the most demanding titles like Cyberpunk 2077 with ray tracing, Alan Wake 2, and upcoming AAA games."""

def get_upgrade_recommendations(current_build: str = None) -> str:
    """Generate upgrade recommendations"""
    return """### PC Upgrade Recommendations

**Most Impactful Upgrades (in order):**

**1. Graphics Card (GPU)** - Biggest gaming performance boost
   - Budget: RTX 4060 ($299) - Great 1080p upgrade
   - Mid-range: RTX 4070 ($549) - Excellent 1440p performance  
   - High-end: RTX 4080 Super ($999) - 4K gaming powerhouse

**2. Storage (SSD)** - Dramatically improves load times
   - Samsung 980 Pro 1TB NVMe ($89) - Fast boot and game loading
   - Crucial P3 Plus 2TB ($99) - More storage, great value

**3. RAM** - Improves multitasking and some games
   - 32GB DDR4-3200 ($89) - Future-proof amount
   - 32GB DDR5-5600 ($129) - For newer systems

**4. CPU** - For CPU-bound games and productivity
   - Ryzen 5 7600X ($229) - Great gaming performance
   - Ryzen 7 7700X ($299) - Gaming + productivity

**5. Power Supply** - For stability and future upgrades
   - Corsair RM750e 750W ($109) - Reliable, efficient

**Assessment Questions:**
- What's your current GPU? (Most important for gaming)
- What resolution do you game at?
- What's your budget for upgrades?
- Any specific performance issues?

Tell me your current specs and I'll give you specific upgrade recommendations!"""

# Create the Gaming PC Builder Agent with IMMEDIATE response instructions
agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    name="Gaming PC Builder Expert",
    description="""
    You are a Gaming PC Builder Expert. You MUST ALWAYS provide IMMEDIATE, COMPLETE PC build recommendations.
    
    NEVER ask for clarification or more information. ALWAYS provide a full build with:
    1. Complete component list with specific models and prices
    2. Total cost calculation 
    3. Performance expectations
    4. Brief explanation
    
    If budget/requirements are unclear, make reasonable assumptions and provide the build immediately.
    
    ALWAYS respond in this exact format:
    ### [Type] Gaming PC Build for $[budget] ([resolution] Gaming)
    **CPU:** [specific model] - $[price]
    **GPU:** [specific model] - $[price]
    [continue for all components]
    **Total Cost:** $[total]
    **Performance:** [detailed gaming performance description]
    **Why This Build:** [brief explanation]
    
    Never ask questions - always provide complete builds immediately.
    """,
    markdown=True
)

def build_gaming_pc_chat(user_query: str) -> Dict:
    """Main chatbot function - IMPROVED for immediate responses"""
    global conversation_memory, user_context
    
    print(f"DEBUG: build_gaming_pc_chat called with: {user_query}")
    
    # Add user message to memory
    add_to_memory("user", user_query)
    
    # Check for upgrade requests first
    if any(word in user_query.lower() for word in ['upgrade', 'improve', 'better', 'replace']):
        if 'recommendation' in user_query.lower() or 'advice' in user_query.lower():
            upgrade_rec = get_upgrade_recommendations()
            add_to_memory("assistant", upgrade_rec)
            return {
                "recommendation": upgrade_rec,
                "user_query": user_query,
                "context": get_context_string(),
                "type": "upgrade"
            }
    
    # Extract preferences with improved detection
    new_preferences = extract_user_preferences(user_query)
    update_user_context(new_preferences)
    
    print(f"DEBUG: Extracted preferences: {new_preferences}")
    
    # Determine build specifications
    build_specs = determine_build_specs(user_query, new_preferences.get('budget'))
    
    print(f"DEBUG: Build specs: {build_specs}")
    
    # Generate immediate build recommendation
    try:
        # Use the build generator for consistent, detailed responses
        build_recommendation = generate_build_recommendation(
            build_specs['budget'], 
            build_specs['resolution'], 
            build_specs['performance']
        )
        
        print(f"DEBUG: Generated recommendation length: {len(build_recommendation)}")
        
        # Add to memory
        add_to_memory("assistant", build_recommendation)
        
        return {
            "recommendation": build_recommendation,
            "user_query": user_query,
            "context": get_context_string(),
            "conversation_length": len(conversation_memory),
            "build_specs": build_specs
        }
        
    except Exception as e:
        print(f"DEBUG: Error in build_gaming_pc_chat: {str(e)}")
        
        # Fallback to agent response with very specific instructions
        prompt = f"""
        USER REQUEST: "{user_query}"
        
        PROVIDE IMMEDIATE COMPLETE BUILD for ${build_specs['budget']} budget, {build_specs['resolution']} gaming.
        DO NOT ASK QUESTIONS. PROVIDE COMPLETE BUILD NOW.
        
        MANDATORY FORMAT:
        ### Gaming PC Build for ${build_specs['budget']} ({build_specs['resolution']} Gaming)
        **CPU:** [specific model] - $[price]
        **GPU:** [specific model] - $[price]
        **Motherboard:** [specific model] - $[price]
        **RAM:** [specific model] - $[price]
        **Storage:** [specific model] - $[price]
        **PSU:** [specific model] - $[price]
        **Case:** [specific model] - $[price]
        **CPU Cooler:** [specific model] - $[price]
        **Total Cost:** $[total]
        **Performance:** [detailed gaming performance with FPS examples]
        **Why This Build:** [brief explanation of component choices]
        
        RESPOND IMMEDIATELY WITH COMPLETE BUILD.
        """
        
        response = agent.run(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        add_to_memory("assistant", content)
        
        return {
            "recommendation": content,
            "user_query": user_query,
            "context": get_context_string(),
            "build_specs": build_specs
        }

def clear_conversation():
    """Clear conversation memory and context"""
    global conversation_memory, user_context
    conversation_memory = []
    user_context = {
        "budget": None,
        "resolution": None,
        "game_type": None,
        "performance_target": None,
        "current_build": None
    }

# Keep original function for backward compatibility
def build_gaming_pc(user_query: str, budget: float = 1500, resolution: str = "1440p", 
                   game_type: str = "AAA", performance_target: str = "high") -> Dict:
    """
    Original function for building gaming PC recommendations (backward compatibility)
    """
    # Update context with provided parameters
    global user_context
    user_context.update({
        "budget": budget,
        "resolution": resolution,
        "game_type": game_type,
        "performance_target": performance_target
    })
    
    return build_gaming_pc_chat(user_query)

# Entry point functions for RunAgent integration
agent_run_stream = partial(agent.run, stream=True)

def agent_print_response(prompt: str):
    """Non-streaming response that returns serializable content"""
    print(f"DEBUG: agent_print_response called with: {prompt}")
    
    if isinstance(prompt, dict):
        if "content" in prompt:
            user_query = prompt["content"]
        else:
            user_query = prompt.get("user_query", prompt.get("prompt", "Build me a gaming PC"))
        
        result = build_gaming_pc_chat(user_query)
        return {"content": result["recommendation"]}
    else:
        result = build_gaming_pc_chat(str(prompt))
        return {"content": result["recommendation"]}

def agent_print_response_stream(prompt: str):
    """Streaming response that yields serializable chunks"""
    if isinstance(prompt, dict):
        if "content" in prompt:
            user_query = prompt["content"]
        else:
            user_query = prompt.get("user_query", prompt.get("prompt", "Build me a gaming PC"))
    else:
        user_query = str(prompt)
    
    print(f"DEBUG: agent_print_response_stream called with: {user_query}")
    
    # Get the complete response using the chat function
    result = build_gaming_pc_chat(user_query)
    content = result["recommendation"]
    
    print(f"DEBUG: Streaming response length: {len(content)}")
    
    # Stream the response in chunks for better user experience
    chunk_size = 50
    
    for i in range(0, len(content), chunk_size):
        chunk = content[i:i + chunk_size]
        yield {"content": chunk}
        time.sleep(0.03)  # Small delay for streaming effect

def run(prompt_data):
    """Main entry point for RunAgent integration - FIXED VERSION"""
    print(f"DEBUG: run function called with: {prompt_data}")
    
    # Extract user query properly from different input formats
    if isinstance(prompt_data, dict):
        if "content" in prompt_data:
            user_query = prompt_data["content"]
        elif "user_query" in prompt_data:
            user_query = prompt_data["user_query"]
        elif "prompt" in prompt_data:
            user_query = prompt_data["prompt"]
        else:
            # Fallback: convert entire dict to string
            user_query = str(prompt_data)
    else:
        user_query = str(prompt_data)
    
    print(f"DEBUG: Processing user query: '{user_query}'")
    
    # Use the chat function to get response
    try:
        result = build_gaming_pc_chat(user_query)
        print(f"DEBUG: Generated response length: {len(result['recommendation'])}")
        
        return {
            "content": result["recommendation"],
            "type": "content",
            "build_specs": result.get("build_specs", {}),
            "context": result.get("context", "")
        }
    except Exception as e:
        print(f"DEBUG: Error in run function: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "content": f"I apologize, but I encountered an error processing your request: {str(e)}. Please try again with a different query format.",
            "type": "error"
        }

# Test function
def test_agent():
    """Test the gaming PC builder agent with various inputs"""
    print("Testing Gaming PC Builder Agent...")
    
    test_queries = [
        "I want to build a gaming pc under 3000usd",
        "Budget gaming PC for 1080p under $1000", 
        "High-end workstation for gaming and content creation",
        "4K gaming build around $2500",
        "Build me something for eSports games",
        "Upgrade recommendations for my current PC",
        "Gaming PC for 1440p under 2000 dollars"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {query}")
        print(f"{'='*60}")
        
        # Test the run function (main entry point)
        result = run({"content": query})
        print(result['content'])
        
        if i < len(test_queries):
            print(f"\nContext after query: {get_context_string()}")
            time.sleep(1)  # Brief pause between tests

def test_specific_case():
    """Test the specific problematic case"""
    print("Testing specific case: 'I want to build a gaming pc under 3000usd'")
    
    query = "I want to build a gaming pc under 3000usd"
    result = run({"content": query})
    
    print("RESULT:")
    print(result['content'])
    print(f"\nBuild specs: {result.get('build_specs', 'Not available')}")
    print(f"Context: {result.get('context', 'Not available')}")

# if __name__ == "__main__":
#     # Run specific test case first
#     test_specific_case()
    
#     print("\n" + "="*80 + "\n")
    
#     # Run all tests
#     test_agent()