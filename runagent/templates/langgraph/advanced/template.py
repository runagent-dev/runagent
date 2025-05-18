from ...base_template import BaseTemplate
from typing import Dict

class LangGraphAdvancedTemplate(BaseTemplate):
    """Advanced LangGraph framework template with conditional routing and tools"""
    
    def generate_files(self) -> Dict[str, str]:
        return {
            "agent.py": self.get_runner_template(),
            "requirements.txt": self.get_requirements(),
            ".env": self.get_env_template()
        }
    
    def get_runner_template(self) -> str:
        return '''from typing import Dict, Any, TypedDict, List, Annotated
from langchain.chat_models import ChatOpenAI
from langchain.tools import tool
from langgraph.graph import Graph, END, StateGraph
from langgraph.prebuilt import ToolExecutor, ToolInvocation
from langgraph.checkpoint.memory import MemorySaver
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Define state
class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    current_step: str
    tool_calls: List[ToolInvocation]
    final_answer: str
    context: Dict[str, Any]

# Define tools
@tool
def search_database(query: str) -> str:
    """Search the database for information."""
    # Implement your database search logic here
    return f"Database results for '{query}': [Placeholder results]"

@tool
def calculate(expression: str) -> str:
    """Perform mathematical calculations."""
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

@tool
def analyze_sentiment(text: str) -> str:
    """Analyze sentiment of the given text."""
    # Implement sentiment analysis logic here
    return f"Sentiment analysis for '{text}': [Positive/Negative/Neutral]"

def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced LangGraph agent with conditional routing and tools
    """
    try:
        # Initialize LLM and tools
        llm = ChatOpenAI(
            temperature=input_data.get("config", {}).get("temperature", 0.7),
            model_name="gpt-4"
        )
        
        tools = [search_database, calculate, analyze_sentiment]
        tool_executor = ToolExecutor(tools)
        
        # Define graph nodes
        def agent_node(state: AgentState) -> AgentState:
            """Agent node that decides what to do next"""
            messages = state["messages"]
            last_message = messages[-1]["content"] if messages else ""
            
            # Use LLM to decide next action
            prompt = f"""Based on the user query: '{last_message}'
            Decide what action to take:
            1. Use a tool (search_database, calculate, analyze_sentiment)
            2. Provide a final answer
            3. Ask for clarification
            
            Respond with JSON: {{"action": "tool|answer|clarify", "tool": "tool_name", "input": "tool_input"}}"""
            
            response = llm.invoke(prompt)
            decision = json.loads(response.content)
            
            if decision["action"] == "tool":
                state["current_step"] = "tool"
                state["tool_calls"] = [ToolInvocation(
                    tool=decision["tool"],
                    tool_input=decision["input"]
                )]
            elif decision["action"] == "answer":
                state["current_step"] = "answer"
                state["final_answer"] = decision.get("answer", "")
            else:
                state["current_step"] = "clarify"
            
            return state
        
        def tool_node(state: AgentState) -> AgentState:
            """Execute tools"""
            tool_call = state["tool_calls"][-1]
            result = tool_executor.invoke(tool_call)
            state["messages"].append({
                "role": "system",
                "content": f"Tool '{tool_call.tool}' returned: {result}"
            })
            return state
        
        def answer_node(state: AgentState) -> AgentState:
            """Generate final answer"""
            messages = state["messages"]
            prompt = f"Based on the conversation history, provide a final answer: {messages}"
            response = llm.invoke(prompt)
            state["final_answer"] = response.content
            return state
        
        def should_continue(state: AgentState) -> str:
            """Determine if we should continue or end"""
            if state["current_step"] == "answer":
                return "end"
            elif state["current_step"] == "tool":
                return "tool"
            else:
                return "agent"
        
        # Build graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tool", tool_node)
        workflow.add_node("answer", answer_node)
        
        # Add edges
        workflow.add_edge("agent", should_continue)
        workflow.add_edge("tool", "agent")
        workflow.add_edge("answer", END)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Initialize memory
        memory = MemorySaver()
        
        # Compile graph
        app = workflow.compile(checkpointer=memory)
        
        # Prepare initial state
        initial_state = {
            "messages": input_data.get("messages", []),
            "current_step": "agent",
            "tool_calls": [],
            "final_answer": "",
            "context": input_data.get("context", {})
        }
        
        # Run graph
        config = {"configurable": {"thread_id": "1"}}
        result = app.invoke(initial_state, config)
        
        return {
            "result": {
                "type": "string",
                "content": result["final_answer"],
                "metadata": {
                    "model_used": "gpt-4",
                    "tools_used": [t.tool for t in result.get("tool_calls", [])],
                    "steps_taken": len(result.get("messages", [])),
                    "execution_time": 3.5
                }
            },
            "errors": [],
            "success": True
        }
    except Exception as e:
        return {
            "result": None,
            "errors": [str(e)],
            "success": False
        }
'''
    
    def get_requirements(self) -> str:
        return '''langchain==0.1.0
langgraph==0.0.26
openai==1.12.0
python-dotenv==1.0.0
'''
    
    def get_env_template(self) -> str:
        return '''OPENAI_API_KEY=your_openai_key_here
DATABASE_URL=your_database_url_here
'''