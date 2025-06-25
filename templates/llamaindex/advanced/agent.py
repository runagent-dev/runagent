import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
from llama_index.core import (
    Document,
    Settings,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool, QueryEngineTool, ToolMetadata
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

# Load environment variables
load_dotenv()


# Custom tool functions
def calculate_expression(expression: str) -> str:
    """Calculate mathematical expressions safely."""
    try:
        # Basic safety check
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression"

        result = eval(expression)
        return f"Calculation result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


def get_current_time() -> str:
    """Get the current time and date."""
    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def analyze_text(text: str) -> str:
    """Analyze text for basic statistics."""
    words = text.split()
    sentences = text.split(".")

    analysis = {
        "word_count": len(words),
        "sentence_count": len([s for s in sentences if s.strip()]),
        "character_count": len(text),
        "average_word_length": (
            sum(len(word) for word in words) / len(words) if words else 0
        ),
    }

    return f"Text analysis: {analysis}"


class LlamaIndexAdvancedAgent:
    """Advanced LlamaIndex agent with RAG, tools, memory, and ReAct capabilities"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Configure LlamaIndex settings
        Settings.llm = OpenAI(
            model=self.config.get("model", "gpt-4"),
            temperature=self.config.get("temperature", 0.7),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        Settings.embed_model = OpenAIEmbedding(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize components
        self.documents = self._create_default_documents()
        self.index = self._build_index()
        self.memory = self._initialize_memory()
        self.tools = self._create_tools()
        self.agent = self._create_agent()

    def _create_default_documents(self) -> List[Document]:
        """Create comprehensive default documents"""
        return [
            Document(
                text="Python Programming: Python is a versatile, high-level programming language known for its "
                "readability and simplicity. It supports multiple programming paradigms including procedural, "
                "object-oriented, and functional programming. Python is widely used in web development, "
                "data science, artificial intelligence, automation, and scientific computing.",
                metadata={
                    "topic": "python",
                    "category": "programming",
                    "difficulty": "beginner",
                },
            ),
            Document(
                text="Artificial Intelligence Overview: AI encompasses machine learning, deep learning, natural "
                "language processing, computer vision, and robotics. Modern AI systems use neural networks, "
                "particularly transformer architectures like GPT and BERT, to process and generate human-like text. "
                "AI applications include chatbots, recommendation systems, autonomous vehicles, and medical diagnosis.",
                metadata={
                    "topic": "ai",
                    "category": "technology",
                    "difficulty": "intermediate",
                },
            ),
            Document(
                text="LlamaIndex Framework: LlamaIndex is a powerful data framework designed for LLM applications. "
                "It provides tools for data ingestion, indexing, querying, and retrieval-augmented generation (RAG). "
                "Key features include vector stores, query engines, agents, and integration with various LLMs and "
                "embedding models. It supports multiple data sources and storage backends.",
                metadata={
                    "topic": "llamaindex",
                    "category": "framework",
                    "difficulty": "advanced",
                },
            ),
            Document(
                text="Machine Learning Fundamentals: ML algorithms learn patterns from data to make predictions or "
                "decisions. Main types include supervised learning (classification, regression), unsupervised "
                "learning (clustering, dimensionality reduction), and reinforcement learning. Popular algorithms "
                "include linear regression, decision trees, random forests, SVM, and neural networks.",
                metadata={
                    "topic": "machine-learning",
                    "category": "technology",
                    "difficulty": "intermediate",
                },
            ),
            Document(
                text="Data Science Workflow: The data science process involves data collection, cleaning, exploration, "
                "feature engineering, model selection, training, evaluation, and deployment. Tools commonly used "
                "include Python libraries (pandas, numpy, scikit-learn), R, SQL, Jupyter notebooks, and "
                "visualization libraries like matplotlib and seaborn.",
                metadata={
                    "topic": "data-science",
                    "category": "methodology",
                    "difficulty": "intermediate",
                },
            ),
        ]

    def _build_index(self) -> VectorStoreIndex:
        """Build the vector store index with advanced configuration"""
        # Check if persistent storage exists
        persist_dir = self.config.get("persist_dir", "./storage")

        if os.path.exists(persist_dir):
            try:
                # Load existing index
                storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
                index = load_index_from_storage(storage_context)
                return index
            except:
                # If loading fails, create new index
                pass

        # Create new index
        index = VectorStoreIndex.from_documents(
            self.documents, show_progress=self.config.get("show_progress", False)
        )

        # Persist if directory is specified
        if persist_dir:
            index.storage_context.persist(persist_dir=persist_dir)

        return index

    def _initialize_memory(self) -> ChatMemoryBuffer:
        """Initialize chat memory with configuration"""
        return ChatMemoryBuffer.from_defaults(
            token_limit=self.config.get("memory_token_limit", 3000)
        )

    def _create_tools(self) -> List:
        """Create comprehensive tool set"""
        # Query engine tool for RAG
        query_engine = self.index.as_query_engine(
            similarity_top_k=self.config.get("similarity_top_k", 3),
            response_mode=self.config.get("response_mode", "compact"),
        )

        query_tool = QueryEngineTool(
            query_engine=query_engine,
            metadata=ToolMetadata(
                name="knowledge_base",
                description="Search through the comprehensive knowledge base for information about "
                "programming, AI, machine learning, data science, and LlamaIndex framework",
            ),
        )

        # Function tools
        calc_tool = FunctionTool.from_defaults(
            fn=calculate_expression,
            name="calculator",
            description="Perform mathematical calculations and evaluate expressions",
        )

        time_tool = FunctionTool.from_defaults(
            fn=get_current_time,
            name="current_time",
            description="Get the current date and time",
        )

        analysis_tool = FunctionTool.from_defaults(
            fn=analyze_text,
            name="text_analyzer",
            description="Analyze text for statistics like word count, sentence count, etc.",
        )

        return [query_tool, calc_tool, time_tool, analysis_tool]

    def _create_agent(self) -> ReActAgent:
        """Create ReAct agent with tools and memory"""
        return ReActAgent.from_tools(
            tools=self.tools,
            llm=Settings.llm,
            memory=self.memory,
            verbose=self.config.get("verbose", False),
            max_iterations=self.config.get("max_iterations", 5),
        )

    def add_documents(self, documents: List[str]) -> None:
        """Add new documents to the index"""
        new_docs = [Document(text=doc) for doc in documents]
        self.documents.extend(new_docs)

        # Rebuild index
        self.index = VectorStoreIndex.from_documents(self.documents)

        # Update query engine tool
        self.tools[0] = QueryEngineTool(
            query_engine=self.index.as_query_engine(
                similarity_top_k=self.config.get("similarity_top_k", 3)
            ),
            metadata=ToolMetadata(
                name="knowledge_base",
                description="Search through the knowledge base for relevant information",
            ),
        )

        # Recreate agent with updated tools
        self.agent = self._create_agent()

    def chat(self, message: str) -> Dict[str, Any]:
        """Chat with the agent"""
        try:
            response = self.agent.chat(message)

            return {
                "response": str(response),
                "sources": response.sources if hasattr(response, "sources") else [],
                "source_nodes": [
                    {
                        "text": (
                            node.text[:200] + "..."
                            if len(node.text) > 200
                            else node.text
                        ),
                        "score": node.score if hasattr(node, "score") else None,
                        "metadata": node.metadata if hasattr(node, "metadata") else {},
                    }
                    for node in (
                        response.source_nodes
                        if hasattr(response, "source_nodes")
                        else []
                    )
                ],
            }
        except Exception as e:
            raise Exception(f"Error in agent chat: {str(e)}")

    def process_messages(self, messages: list) -> Dict[str, Any]:
        """Process conversation messages"""
        if not messages:
            return {"response": "No messages provided", "sources": []}

        # Add conversation history to memory (except the last message)
        for msg in messages[:-1]:
            if msg.get("role") == "user":
                self.memory.put({"role": "user", "content": msg["content"]})
            elif msg.get("role") == "assistant":
                self.memory.put({"role": "assistant", "content": msg["content"]})

        # Process the last message
        last_message = messages[-1]["content"]
        return self.chat(last_message)

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return [tool.metadata.name for tool in self.tools]

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get comprehensive agent statistics"""
        return {
            "total_documents": len(self.documents),
            "tools_available": self.get_available_tools(),
            "memory_token_limit": self.config.get("memory_token_limit", 3000),
            "index_type": "VectorStoreIndex",
            "agent_type": "ReActAgent",
            "llm_model": self.config.get("model", "gpt-4"),
            "embedding_model": "text-embedding-ada-002",
            "max_iterations": self.config.get("max_iterations", 5),
        }
