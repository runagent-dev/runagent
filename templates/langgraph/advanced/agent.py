import json
import os
from typing import Any, Dict, List, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor, ToolInvocation

# Load environment variables
load_dotenv()


# Define state
class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    current_step: str
    tool_calls: List[ToolInvocation]
    final_answer: str
    context: Dict[str, Any]
    step_count: int


# Define tools
@tool
def search_database(query: str) -> str:
    """Search the database for information."""
    # Placeholder database
    database = {
        "users": "User management system with authentication and profiles",
        "orders": "Order processing system with payment integration",
        "products": "Product catalog with inventory management",
    }

    query_lower = query.lower()
    for key, value in database.items():
        if key in query_lower:
            return f"Database result: {value}"

    return f"No database results found for: {query}"


@tool
def calculate(expression: str) -> str:
    """Perform mathematical calculations."""
    try:
        # Basic safety check
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"

        result = eval(expression)
        return f"Calculation result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


@tool
def analyze_sentiment(text: str) -> str:
    """Analyze sentiment of the given text."""
    # Simple rule-based sentiment analysis
    positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic"]
    negative_words = ["bad", "terrible", "awful", "horrible", "disappointing", "poor"]

    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    if positive_count > negative_count:
        sentiment = "Positive"
    elif negative_count > positive_count:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    return f"Sentiment analysis: {sentiment} (positive: {positive_count}, negative: {negative_count})"


class LangGraphAdvancedAgent:
    """Advanced LangGraph agent with conditional routing and tools"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=self.config.get("temperature", 0.7),
            model_name=self.config.get("model", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Initialize tools
        self.tools = [search_database, calculate, analyze_sentiment]
        self.tool_executor = ToolExecutor(self.tools)

        # Initialize memory
        self.memory = MemorySaver()

        # Build the graph
        self.app = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the advanced LangGraph workflow"""

        def agent_node(state: AgentState) -> AgentState:
            """Agent node that decides what to do next"""
            messages = state["messages"]
            last_message = messages[-1]["content"] if messages else ""
            step_count = state.get("step_count", 0)

            # Use LLM to decide next action
            prompt = f"""Based on the user query: '{last_message}'
            Current step: {step_count}
            
            Decide what action to take:
            1. Use a tool (search_database, calculate, analyze_sentiment)
            2. Provide a final answer
            3. Ask for clarification
            
            Respond with JSON: {{"action": "tool|answer|clarify", "tool": "tool_name", "input": "tool_input", "reasoning": "why this action"}}"""

            try:
                response = self.llm.invoke(prompt)
                decision = json.loads(response.content)
            except:
                # Fallback decision
                decision = {"action": "answer", "reasoning": "Failed to parse decision"}

            state["step_count"] = step_count + 1

            if decision["action"] == "tool" and "tool" in decision:
                state["current_step"] = "tool"
                state["tool_calls"] = [
                    ToolInvocation(
                        tool=decision["tool"], tool_input=decision.get("input", "")
                    )
                ]
            elif decision["action"] == "answer":
                state["current_step"] = "answer"
            else:
                state["current_step"] = "clarify"

            return state

        def tool_node(state: AgentState) -> AgentState:
            """Execute tools"""
            if state["tool_calls"]:
                tool_call = state["tool_calls"][-1]
                try:
                    result = self.tool_executor.invoke(tool_call)
                    state["messages"].append(
                        {
                            "role": "system",
                            "content": f"Tool '{tool_call.tool}' returned: {result}",
                        }
                    )
                except Exception as e:
                    state["messages"].append(
                        {
                            "role": "system",
                            "content": f"Tool '{tool_call.tool}' failed: {str(e)}",
                        }
                    )

            state["current_step"] = "agent"  # Go back to agent for next decision
            return state

        def answer_node(state: AgentState) -> AgentState:
            """Generate final answer"""
            messages = state["messages"]

            # Create a summary of the conversation
            conversation_summary = "\n".join(
                [
                    f"{msg['role']}: {msg['content']}"
                    for msg in messages[-5:]  # Last 5 messages
                ]
            )

            prompt = f"Based on this conversation, provide a helpful final answer:\n{conversation_summary}"

            try:
                response = self.llm.invoke(prompt)
                state["final_answer"] = response.content
            except Exception as e:
                state["final_answer"] = (
                    f"I apologize, but I encountered an error: {str(e)}"
                )

            return state

        def should_continue(state: AgentState) -> str:
            """Determine the next node based on current step"""
            current_step = state.get("current_step", "agent")
            step_count = state.get("step_count", 0)

            # Prevent infinite loops
            if step_count > self.config.get("max_steps", 5):
                return "answer"

            if current_step == "tool":
                return "tool"
            elif current_step == "answer":
                return "answer"
            else:
                return "agent"

        # Build the state graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tool", tool_node)
        workflow.add_node("answer", answer_node)

        # Add edges
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tool", "agent")
        workflow.add_edge("answer", END)

        # Set entry point
        workflow.set_entry_point("agent")

        # Compile with memory
        return workflow.compile(checkpointer=self.memory)

    def process_messages(
        self, messages: list, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process messages through the advanced graph"""
        try:
            # Prepare initial state
            initial_state = {
                "messages": messages.copy(),
                "current_step": "agent",
                "tool_calls": [],
                "final_answer": "",
                "context": context or {},
                "step_count": 0,
            }

            # Run the graph
            config = {
                "configurable": {"thread_id": self.config.get("thread_id", "default")}
            }
            result = self.app.invoke(initial_state, config)

            return {
                "final_answer": result["final_answer"],
                "tools_used": [tc.tool for tc in result.get("tool_calls", [])],
                "steps_taken": result.get("step_count", 0),
                "final_state": result,
            }

        except Exception as e:
            raise Exception(f"Error processing messages: {str(e)}")

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return [tool.name for tool in self.tools]

    def get_graph_structure(self) -> Dict[str, Any]:
        """Get information about the graph structure"""
        return {
            "nodes": ["agent", "tool", "answer"],
            "edges": [
                ("agent", "conditional -> tool/answer/agent"),
                ("tool", "agent"),
                ("answer", "END"),
            ],
            "entry_point": "agent",
            "tools_available": self.get_available_tools(),
        }
