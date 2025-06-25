import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import AIMessage, HumanMessage
from langchain.tools import tool

# Load environment variables
load_dotenv()


# Define custom tools
@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    try:
        # Basic safety: only allow certain characters
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"

        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error in calculation: {str(e)}"


@tool
def search_knowledge(query: str) -> str:
    """Search for information in the knowledge base."""
    # This is a placeholder - implement your actual search logic
    knowledge_base = {
        "python": "Python is a high-level programming language known for its simplicity and readability.",
        "ai": "Artificial Intelligence (AI) refers to the simulation of human intelligence in machines.",
        "langchain": "LangChain is a framework for developing applications powered by language models.",
    }

    query_lower = query.lower()
    for key, value in knowledge_base.items():
        if key in query_lower:
            return f"Knowledge: {value}"

    return f"No specific knowledge found for: {query}. Try asking about Python, AI, or LangChain."


class LangChainAdvancedAgent:
    """Advanced LangChain agent with tools, memory, and custom prompts"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=self.config.get("temperature", 0.7),
            model_name=self.config.get("model", "gpt-4"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Initialize tools
        self.tools = [calculate, search_knowledge]

        # Create custom prompt
        system_prompt = self.config.get(
            "system_prompt",
            "You are a helpful AI assistant with access to tools for calculation and knowledge search. "
            "Use the tools when appropriate to provide accurate and helpful responses.",
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        # Initialize memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=self.config.get("memory_window", 5),
        )

        # Create agent
        self.agent = create_openai_functions_agent(
            llm=self.llm, tools=self.tools, prompt=self.prompt
        )

        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=self.config.get("verbose", False),
            handle_parsing_errors=True,
            max_iterations=self.config.get("max_iterations", 3),
        )

    def process_message(self, message: str) -> Dict[str, Any]:
        """Process a single message and return detailed response"""
        try:
            result = self.agent_executor.invoke({"input": message})

            return {
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
                "tools_used": [
                    step[0].tool for step in result.get("intermediate_steps", [])
                ],
            }
        except Exception as e:
            raise Exception(f"Error processing message: {str(e)}")

    def process_messages(self, messages: list) -> Dict[str, Any]:
        """Process a list of messages and return the final response"""
        if not messages:
            return {"output": "No messages provided", "tools_used": []}

        # Add previous messages to memory (except the last one)
        for msg in messages[:-1]:
            if msg.get("role") == "user":
                self.memory.chat_memory.add_user_message(msg["content"])
            elif msg.get("role") == "assistant":
                self.memory.chat_memory.add_ai_message(msg["content"])

        # Process the last message
        last_message = messages[-1]["content"]
        return self.process_message(last_message)

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return [tool.name for tool in self.tools]
