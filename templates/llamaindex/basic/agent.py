import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

# Load environment variables
load_dotenv()


class LlamaIndexBasicAgent:
    """Basic LlamaIndex agent with document indexing and querying"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Configure LlamaIndex settings
        Settings.llm = OpenAI(
            model=self.config.get("model", "gpt-4"),
            temperature=self.config.get("temperature", 0.7),
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        Settings.embed_model = OpenAIEmbedding(api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize with some default documents
        self.documents = self._create_default_documents()
        self.index = self._build_index()
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=self.config.get("similarity_top_k", 3)
        )

    def _create_default_documents(self) -> List[Document]:
        """Create some default documents for the knowledge base"""
        default_docs = [
            Document(
                text="Python is a high-level, interpreted programming language with dynamic semantics. "
                "Its high-level built-in data structures, combined with dynamic typing and dynamic binding, "
                "make it very attractive for Rapid Application Development.",
                metadata={"topic": "python", "type": "programming"},
            ),
            Document(
                text="Artificial Intelligence (AI) refers to the simulation of human intelligence in machines "
                "that are programmed to think like humans and mimic their actions. AI can be categorized "
                "into narrow AI, general AI, and superintelligence.",
                metadata={"topic": "ai", "type": "technology"},
            ),
            Document(
                text="LlamaIndex is a data framework for LLM applications. It provides tools to ingest, "
                "structure, and access private or domain-specific data for use with large language models.",
                metadata={"topic": "llamaindex", "type": "framework"},
            ),
            Document(
                text="Machine learning is a subset of artificial intelligence that provides systems "
                "the ability to automatically learn and improve from experience without being "
                "explicitly programmed.",
                metadata={"topic": "machine learning", "type": "technology"},
            ),
        ]
        return default_docs

    def _build_index(self) -> VectorStoreIndex:
        """Build the vector store index from documents"""
        return VectorStoreIndex.from_documents(self.documents)

    def add_documents(self, documents: List[str]) -> None:
        """Add new documents to the index"""
        new_docs = [Document(text=doc) for doc in documents]
        self.documents.extend(new_docs)

        # Rebuild index with new documents
        self.index = VectorStoreIndex.from_documents(self.documents)
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=self.config.get("similarity_top_k", 3)
        )

    def query(self, question: str) -> Dict[str, Any]:
        """Query the knowledge base"""
        try:
            response = self.query_engine.query(question)

            return {
                "answer": str(response),
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
                "response_metadata": (
                    response.metadata if hasattr(response, "metadata") else {}
                ),
            }
        except Exception as e:
            raise Exception(f"Error querying index: {str(e)}")

    def process_messages(self, messages: list) -> Dict[str, Any]:
        """Process a list of messages and return response"""
        if not messages:
            return {"answer": "No messages provided", "source_nodes": []}

        # Get the last user message
        last_message = messages[-1]["content"]
        return self.query(last_message)

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index"""
        return {
            "total_documents": len(self.documents),
            "index_type": "VectorStoreIndex",
            "embedding_model": "text-embedding-ada-002",
            "llm_model": self.config.get("model", "gpt-4"),
        }
