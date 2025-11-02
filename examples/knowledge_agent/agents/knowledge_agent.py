from pathlib import Path
from typing import Dict, Generator

from agno.agent import Agent
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.chroma import ChromaDb


def _get_knowledge_base() -> Knowledge:
    base_dir = Path(__file__).resolve().parents[1]
    chroma_path = base_dir / "tmp" / "chromadb"
    chroma_path.mkdir(parents=True, exist_ok=True)

    knowledge = Knowledge(
        name="Basic SDK Knowledge Base",
        description="Agno 2.0 Knowledge Implementation with ChromaDB",
        vector_db=ChromaDb(collection="vectors", path=str(chroma_path), persistent_client=True),
    )

    return knowledge


def _ensure_sample_content(knowledge: Knowledge) -> None:
    # Idempotent-ish add; underlying DB can handle duplicates or you can check existing entries.
    knowledge.add_content(
        name="Recipes",
        url="https://agno-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf",
        metadata={"doc_type": "recipe_book"},
    )


def kb_query(prompt: str) -> Dict[str, object]:
    """
    Initialize knowledge base, add sample content (Thai recipes), and answer the prompt.
    """
    knowledge = _get_knowledge_base()
    _ensure_sample_content(knowledge)

    agent = Agent(knowledge=knowledge)
    response = agent.run(prompt)

    return {
        "content": getattr(response, "content", str(response)),
        "success": True,
    }


def kb_query_stream(prompt: str) -> Generator[Dict[str, str], None, None]:
    knowledge = _get_knowledge_base()
    _ensure_sample_content(knowledge)

    agent = Agent(knowledge=knowledge)
    for chunk in agent.run(prompt, stream=True):
        yield {"content": chunk if hasattr(chunk, "content") else str(chunk)}


def kb_delete_by_name(name: str) -> Dict[str, object]:
    knowledge = _get_knowledge_base()
    knowledge.vector_db.delete_by_name(name)
    return {"content": f"Deleted entries with name '{name}'", "success": True}


def kb_delete_by_metadata(key: str, value: str) -> Dict[str, object]:
    knowledge = _get_knowledge_base()
    knowledge.vector_db.delete_by_metadata({key: value})
    return {"content": f"Deleted entries with metadata {key}={value}", "success": True}


