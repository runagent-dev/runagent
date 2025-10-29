from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.exa import ExaTools
from textwrap import dedent

recipe_agent = Agent(
    name="ChefGenius",
    tools=[ExaTools()],
    model=OpenAIChat(id="gpt-4o"),
    description=dedent("""\
        You are ChefGenius, a passionate culinary expert who creates personalized recipes! 🍳
        
        You help users create delicious meals based on their ingredients, dietary needs,
        and time constraints."""),
    instructions=dedent("""\
        When creating recipes:
        
        1. Analyze the user's ingredients and constraints
        2. Search for relevant recipes using Exa
        3. Provide a complete recipe with:
           - Recipe title
           - Prep & cook time
           - Ingredients with measurements
           - Step-by-step instructions
           - Nutritional info (if available)
           - Tips and variations
        
        Format your response clearly with:
        - Use markdown formatting
        - Add emojis: 🌱 Vegetarian, 🌿 Vegan, 🌾 Gluten-free, ⏱️ Quick
        - Include substitution suggestions
        - Note any allergen warnings"""),
    markdown=True,
)


def create_recipe(ingredients: str, dietary_restrictions: str = "", time_limit: str = ""):
    """
    Create a recipe based on ingredients and preferences
    
    Args:
        ingredients: Available ingredients (e.g., "chicken, rice, broccoli")
        dietary_restrictions: Any dietary needs (e.g., "vegetarian", "gluten-free")
        time_limit: Maximum cooking time (e.g., "30 minutes", "1 hour")
    """
    prompt = f"Create a recipe using these ingredients: {ingredients}."
    
    if dietary_restrictions:
        prompt += f" Dietary restrictions: {dietary_restrictions}."
    
    if time_limit:
        prompt += f" Must be ready in: {time_limit}."
    
    response = recipe_agent.run(prompt)
    return {
        "recipe": response.content,
        "success": True
    }


def create_recipe_stream(ingredients: str, dietary_restrictions: str = "", time_limit: str = ""):
    """Streaming version of recipe creation"""
    prompt = f"Create a recipe using these ingredients: {ingredients}."
    
    if dietary_restrictions:
        prompt += f" Dietary restrictions: {dietary_restrictions}."
    
    if time_limit:
        prompt += f" Must be ready in: {time_limit}."
    
    for chunk in recipe_agent.run(prompt, stream=True):
        yield {"content": chunk if hasattr(chunk, 'content') else str(chunk)}

        