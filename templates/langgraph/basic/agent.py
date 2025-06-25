import os
from typing import Any, Dict, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langgraph.graph import END, Graph

# Load environment variables
load_dotenv()


# Define state
class AgentState(TypedDict):
    messages: list
    response: str
    context: Dict[str, Any]


class LangGraphBasicAgent:
    """Basic LangGraph agent with simple workflow"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=self.config.get("temperature", 0.7),
            model_name=self.config.get("model", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Build the graph
        self.app = self._build_graph()

    def _build_graph(self) -> Graph:
        """Build the LangGraph workflow"""

        def process_message(state: AgentState) -> AgentState:
            """Process the message using LLM"""
            messages = state.get("messages", [])
            if messages:
                last_message = messages[-1]["content"]
                response = self.llm.invoke(last_message)
                state["response"] = response.content
            else:
                state["response"] = "No messages to process"
            return state

        # Create graph
        workflow = Graph()
        workflow.add_node("process", process_message)
        workflow.add_edge("process", END)
        workflow.set_entry_point("process")

        # Compile and return
        return workflow.compile()

    def process_messages(
        self, messages: list, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process messages through the graph"""
        try:
            initial_state = {
                "messages": messages,
                "response": "",
                "context": context or {},
            }

            # Run the graph
            result = self.app.invoke(initial_state)

            return {
                "response": result.get("response", ""),
                "final_state": result,
                "steps_taken": 1,  # Basic workflow has only one step
            }

        except Exception as e:
            raise Exception(f"Error processing messages: {str(e)}")

    def get_graph_structure(self) -> Dict[str, Any]:
        """Get information about the graph structure"""
        return {
            "nodes": ["process"],
            "edges": [("process", "END")],
            "entry_point": "process",
        }
