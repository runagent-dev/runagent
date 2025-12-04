import os
import asyncio
from dotenv import load_dotenv
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

load_dotenv()

WORKING_DIR = "rag_storage"


async def get_rag_instance():
    if not os.path.exists(WORKING_DIR):
        os.makedirs(WORKING_DIR, exist_ok=True)
    
    rag = LightRAG(
        working_dir=WORKING_DIR,
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    
    await rag.initialize_storages()
    await initialize_pipeline_status()
    
    return rag


async def ingest_text_async(text: str = None, **kwargs):
    if text is None:
        text = kwargs.get('content', '')
    
    if not text:
        return {"status": "error", "message": "No text provided"}
    
    rag = None
    try:
        rag = await get_rag_instance()
        await rag.ainsert(text)
        return {"status": "success", "message": f"Ingested {len(text)} characters"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if rag:
            try:
                await rag.finalize_storages()
            except:
                pass


async def query_rag_async(query: str = None, mode: str = "hybrid", **kwargs):
    if query is None:
        query = kwargs.get('question', '')
    
    if not query:
        return {"status": "error", "message": "No query provided"}
    
    if mode not in ["naive", "local", "global", "hybrid"]:
        mode = "hybrid"
    
    rag = None
    try:
        rag = await get_rag_instance()
        result = await rag.aquery(query, param=QueryParam(mode=mode))
        return {"status": "success", "query": query, "mode": mode, "result": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if rag:
            try:
                await rag.finalize_storages()
            except:
                pass


def ingest_text(text: str = None, **kwargs):
    return asyncio.run(ingest_text_async(text, **kwargs))


def query_rag(query: str = None, mode: str = "hybrid", **kwargs):
    return asyncio.run(query_rag_async(query, mode, **kwargs))