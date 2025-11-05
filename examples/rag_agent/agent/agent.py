import os
from typing import List, Dict, Any, Literal, Optional, Tuple
from dataclasses import dataclass
import tempfile

# --- LangChain v0.2+/0.3+ imports ---
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Qdrant
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# Qdrant
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

# Agno (routing agent)
from agno.agent import Agent
from agno.models.openai import OpenAIChat


DatabaseType = Literal["products", "support", "finance"]

@dataclass
class CollectionConfig:
    name: str
    description: str
    collection_name: str

# Collection configurations
COLLECTIONS: Dict[DatabaseType, CollectionConfig] = {
    "products": CollectionConfig(
        name="Product Information",
        description="Product details, specifications, and features",
        collection_name="products_collection"
    ),
    "support": CollectionConfig(
        name="Customer Support & FAQ",
        description="Customer support information, frequently asked questions, and guides",
        collection_name="support_collection"
    ),
    "finance": CollectionConfig(
        name="Financial Information",
        description="Financial data, revenue, costs, and liabilities",
        collection_name="finance_collection"
    )
}


class RAGRouterAgent:
    """RAG Agent with intelligent database routing"""

    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if not all([self.openai_api_key, self.qdrant_url, self.qdrant_api_key]):
            raise ValueError("Missing required environment variables: OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY")

        # OpenAI models
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=self.openai_api_key
        )
        # Pick a concrete model name to avoid defaults changing
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=self.openai_api_key)

        self.databases: Dict[DatabaseType, Qdrant] = {}
        self._initialize_databases()

    def _initialize_databases(self):
        """Initialize Qdrant databases (collections)"""
        try:
            client = QdrantClient(
                url=self.qdrant_url,
                api_key=self.qdrant_api_key
            )

            # Test connection
            client.get_collections()
            vector_size = 1536  # text-embedding-3-small dimensionality

            for db_type, config in COLLECTIONS.items():
                try:
                    client.get_collection(config.collection_name)
                except Exception:
                    # Create collection if it doesn't exist
                    client.create_collection(
                        collection_name=config.collection_name,
                        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                    )

                self.databases[db_type] = Qdrant(
                    client=client,
                    collection_name=config.collection_name,
                    embeddings=self.embeddings
                )
        except Exception as e:
            raise Exception(f"Failed to initialize Qdrant: {str(e)}")

    def create_routing_agent(self) -> Agent:
        """Creates a routing agent using agno framework"""
        return Agent(
            model=OpenAIChat(
                id="gpt-4o-mini",
                api_key=self.openai_api_key
            ),
            tools=[],
            description="You are a query routing expert. Analyze questions and determine which database they should be routed to.",
            instructions=[
                "Follow these rules strictly:",
                "1. For questions about products, features, specifications, or item details → return 'products'",
                "2. For questions about help, guidance, troubleshooting, customer service, or FAQ → return 'support'",
                "3. For questions about costs, revenue, pricing, financial data, or reports → return 'finance'",
                "4. Return ONLY the database name, no other text or explanation",
                "5. If you're not confident about the routing, return an empty response"
            ],
            markdown=False,
            show_tool_calls=False
        )

    def route_query(self, question: str) -> Optional[DatabaseType]:
        """Route query using vector similarity and LLM fallback"""
        try:
            best_score = float("-inf")
            best_db_type: Optional[DatabaseType] = None
            all_scores: Dict[DatabaseType, float] = {}

            # Search each database and compare scores
            for db_type, db in self.databases.items():
                results = db.similarity_search_with_score(question, k=3)
                if results:
                    # In LC Qdrant, higher score = closer match (cosine similarity)
                    avg_score = sum(score for _, score in results) / len(results)
                    all_scores[db_type] = avg_score
                    if avg_score > best_score:
                        best_score = avg_score
                        best_db_type = db_type

            confidence_threshold = 0.5
            if best_score >= confidence_threshold and best_db_type:
                return best_db_type

            # Fallback to LLM routing
            routing_agent = self.create_routing_agent()
            response = routing_agent.run(question)

            db_type = (
                response.content.strip().lower().translate(str.maketrans('', '', '`\'"'))
            )

            if db_type in COLLECTIONS:
                return db_type  # type: ignore[return-value]

            return None

        except Exception as e:
            print(f"Routing error: {str(e)}")
            return None

    def _build_rag_chain(self, retriever):
        """Build an LCEL runnable: retrieval → prompt → LLM → parse"""
        prompt = ChatPromptTemplate.from_messages([
            ("system",
            "You are a helpful assistant. Use ONLY the provided context to answer factually. "
            "If the answer isn't in the context, say you don't know."),
            ("human", "Question: {question}\n\nContext:\n{context}")
        ])

        def format_docs(docs: List[Document]) -> str:
            return "\n\n".join(d.page_content for d in docs)

        return (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def query_database(self, db: Qdrant, question: str) -> Tuple[str, List[Document]]:
        """Query the database and return answer and relevant documents"""
        try:
            # VectorStoreRetriever is a Runnable; call .invoke() to get docs
            retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})
            relevant_docs: List[Document] = retriever.invoke(question)

            if not relevant_docs:
                raise ValueError("No relevant documents found in database")

            # Build and run the RAG chain (retrieval → prompt → LLM → parse)
            rag_chain = self._build_rag_chain(retriever)
            answer: str = rag_chain.invoke(question)
            return answer, relevant_docs

        except Exception as e:
            return f"Error: {str(e)}", []

    def web_fallback(self, question: str) -> str:
        """Fallback to web search when no relevant documents found"""
        try:
            # Simple: run DDG search and summarize with the LLM
            ddg = DuckDuckGoSearchRun(num_results=5)
            hits_text = ddg.run(question)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a careful researcher. Summarize the findings concisely and cite sources inline if available."),
                ("human", "Question: {q}\n\nSearch Results:\n{hits}\n\nWrite a short, factual answer:")
            ])
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"q": question, "hits": hits_text})
        except Exception:
            # Final fallback to general LLM response
            return self.llm.invoke(question).content  # type: ignore[attr-defined]

    def query(self, question: str) -> Dict[str, Any]:
        """Main query function for RunAgent"""
        try:
            # Route the question
            collection_type = self.route_query(question)

            if collection_type is None:
                # Use web search fallback
                answer = self.web_fallback(question)
                return {
                    "success": True,
                    "answer": answer,
                    "source": "web_search",
                    "database_used": None,
                    "question": question
                }
            else:
                # Query the routed database
                db = self.databases[collection_type]
                answer, relevant_docs = self.query_database(db, question)

                return {
                    "success": True,
                    "answer": answer,
                    "source": "database",
                    "database_used": COLLECTIONS[collection_type].name,
                    "question": question,
                    "num_documents": len(relevant_docs)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "question": question
            }


# RunAgent entrypoint functions
_agent_instance = None

def get_agent():
    """Get or create agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RAGRouterAgent()
    return _agent_instance


def query_rag(question: str) -> Dict[str, Any]:
    """
    Query the RAG system with intelligent routing

    Args:
        question: The question to ask

    Returns:
        Dictionary with answer, source, and metadata
    """
    agent = get_agent()
    return agent.query(question)


# Streaming version for query
async def query_rag_stream(question: str):
    """
    Stream the RAG query response

    Args:
        question: The question to ask

    Yields:
        Chunks of the response
    """
    agent = get_agent()
    result = agent.query(question)

    # Stream the answer in chunks
    if result.get("success"):
        answer: str = result["answer"]
        chunk_size = 50

        # First yield metadata
        yield {
            "type": "metadata",
            "source": result["source"],
            "database_used": result.get("database_used"),
            "question": question
        }

        # Stream answer in chunks
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i:i + chunk_size]
            yield {"type": "content", "content": chunk}

        # Final completion signal
        yield {"type": "complete", "total_length": len(answer)}
    else:
        yield {"type": "error", "error": result.get("error", "Unknown error")}
