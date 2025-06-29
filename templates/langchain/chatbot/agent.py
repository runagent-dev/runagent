import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()


class LangChainBasicAgent:
    """Basic LangChain agent with conversation memory"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.llm = ChatOpenAI(
            temperature=self.config.get("temperature", 0.7),
            model=self.config.get("model", "gpt-4o-mini"),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.memory = ConversationBufferMemory()
        self.conversation = ConversationChain(
            llm=self.llm, memory=self.memory, verbose=self.config.get("verbose", False)
        )

    def process_message(self, message: str) -> str:
        """Process a single message and return response"""
        try:
            response = self.conversation.predict(input=message)
            return response
        except Exception as e:
            raise Exception(f"Error processing message: {str(e)}")

    def process_messages(self, messages: list) -> str:
        """Process a list of messages and return the final response"""
        if not messages:
            return "No messages provided"

        # Add previous messages to memory (except the last one)
        for msg in messages[:-1]:
            if msg.get("role") == "user":
                self.memory.chat_memory.add_user_message(msg["content"])
            elif msg.get("role") == "assistant":
                self.memory.chat_memory.add_ai_message(msg["content"])

        # Process the last message
        last_message = messages[-1]["content"]
        return self.process_message(last_message)

    def get_conversation_history(self) -> list:
        """Get the conversation history"""
        return self.memory.chat_memory.messages