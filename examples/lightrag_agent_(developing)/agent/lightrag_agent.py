"""
LightRAG Agent - Main Entrypoints for RunAgent
This module exposes all agent functionalities through RunAgent-compatible functions
"""

import asyncio
from typing import List, Dict, Optional, Any
from loguru import logger

from agent.config import get_config, get_agent_id
from agent.storage import initialize_neon_storage
from services.rag_service import RAGService
from services.document_processor import DocumentProcessor


# ============================================
# Global State Management
# ============================================

_rag_service: Optional[RAGService] = None
_initialized = False


async def _ensure_initialized():
    """Ensure RAG service is initialized"""
    global _rag_service, _initialized
    
    if _initialized and _rag_service is not None:
        return _rag_service
    
    try:
        # Load configuration
        config = get_config()
        logger.info(f"🔧 Loading configuration for agent: {get_agent_id()}")
        
        # Initialize storage
        logger.info("🗄️  Initializing Neon PostgreSQL storage...")
        storage_manager = await initialize_neon_storage(config)
        
        # Initialize RAG service
        logger.info("🤖 Initializing RAG service...")
        _rag_service = RAGService(config, storage_manager)
        await _rag_service.initialize()
        
        _initialized = True
        logger.info("✅ Agent initialization complete!")
        
        return _rag_service
        
    except Exception as e:
        logger.error(f"❌ Agent initialization failed: {e}")
        raise


def _run_async(coro):
    """Helper to run async functions"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)


# ============================================
# ENTRYPOINT 1: Initialize Agent
# ============================================

def initialize_agent() -> Dict[str, Any]:
    """
    Initialize the LightRAG agent with Neon PostgreSQL storage
    
    This should be called once when the agent is first deployed.
    Subsequent calls will return the existing instance.
    
    Returns:
        dict: Initialization status and agent information
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 INITIALIZING LIGHTRAG AGENT")
        logger.info("=" * 60)
        
        rag_service = _run_async(_ensure_initialized())
        stats = _run_async(rag_service.get_stats())
        
        return {
            "success": True,
            "message": "Agent initialized successfully",
            "agent_id": get_agent_id(),
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# ENTRYPOINT 2: Insert Documents
# ============================================

def insert_documents(
    documents: List[str],
    document_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Insert text documents into the knowledge base
    
    Args:
        documents: List of document texts to insert
        document_ids: Optional list of document IDs (auto-generated if not provided)
    
    Returns:
        dict: Insertion result with count and status
    
    Example:
        >>> result = insert_documents(
        ...     documents=["Document 1 text", "Document 2 text"],
        ...     document_ids=["doc1", "doc2"]
        ... )
    """
    try:
        logger.info(f"📝 Inserting {len(documents)} documents...")
        
        rag_service = _run_async(_ensure_initialized())
        result = _run_async(rag_service.insert_documents(documents, document_ids))
        
        logger.info(f"✅ {result['message']}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Document insertion failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# ENTRYPOINT 3: Batch Insert Documents
# ============================================

def insert_documents_batch(
    documents: List[str],
    document_ids: Optional[List[str]] = None,
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Insert documents in batches for better performance with large datasets
    
    Args:
        documents: List of document texts to insert
        document_ids: Optional list of document IDs
        batch_size: Number of documents per batch
    
    Returns:
        dict: Batch insertion results
    
    Example:
        >>> result = insert_documents_batch(
        ...     documents=large_document_list,
        ...     batch_size=20
        ... )
    """
    try:
        logger.info(f"📚 Batch inserting {len(documents)} documents (batch_size={batch_size})...")
        
        rag_service = _run_async(_ensure_initialized())
        
        total_inserted = 0
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_ids = document_ids[i:i + batch_size] if document_ids else None
            
            batch_num = i // batch_size + 1
            logger.info(f"  📦 Processing batch {batch_num}/{total_batches}...")
            
            result = _run_async(rag_service.insert_documents(batch_docs, batch_ids))
            
            if result['success']:
                total_inserted += result['document_count']
            else:
                logger.warning(f"  ⚠️  Batch {batch_num} failed: {result.get('error')}")
        
        return {
            "success": True,
            "total_documents": len(documents),
            "total_inserted": total_inserted,
            "batch_size": batch_size,
            "total_batches": total_batches,
            "message": f"Successfully inserted {total_inserted}/{len(documents)} documents"
        }
        
    except Exception as e:
        logger.error(f"❌ Batch insertion failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# ENTRYPOINT 4: Process Multimodal Document
# ============================================

def process_multimodal_document(
    file_path: str,
    parse_method: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a multimodal document (PDF, Office, images, etc.)
    Uses RAG-Anything to extract and process all content types
    
    Args:
        file_path: Path to the document file
        parse_method: Optional parse method override ("auto", "ocr", or "txt")
    
    Returns:
        dict: Processing result
    
    Example:
        >>> result = process_multimodal_document(
        ...     file_path="/path/to/research_paper.pdf",
        ...     parse_method="auto"
        ... )
    """
    try:
        # Validate file
        validation = DocumentProcessor.validate_file(file_path)
        if not validation['valid']:
            return {
                "success": False,
                "error": validation['error']
            }
        
        logger.info(f"📄 Processing multimodal document: {file_path}")
        logger.info(f"   Type: {validation['type']}, Size: {validation['size'] / 1024:.2f} KB")
        
        # Estimate processing time
        estimate = DocumentProcessor.estimate_processing_time(file_path)
        logger.info(f"   ⏱️  Estimated processing time: ~{estimate['estimated_seconds']}s")
        
        rag_service = _run_async(_ensure_initialized())
        result = _run_async(
            rag_service.process_multimodal_document(file_path, parse_method)
        )
        
        if result['success']:
            logger.info(f"✅ {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Document processing failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# ENTRYPOINT 5: Process Folder
# ============================================

def process_folder(
    folder_path: str,
    file_extensions: Optional[List[str]] = None,
    recursive: bool = True,
    max_workers: int = 4
) -> Dict[str, Any]:
    """
    Process all documents in a folder
    
    Args:
        folder_path: Path to the folder
        file_extensions: List of extensions to process (default: all supported)
        recursive: Whether to process subdirectories
        max_workers: Number of parallel workers
    
    Returns:
        dict: Processing results
    
    Example:
        >>> result = process_folder(
        ...     folder_path="/path/to/documents",
        ...     file_extensions=[".pdf", ".docx"],
        ...     recursive=True,
        ...     max_workers=4
        ... )
    """
    try:
        # Validate folder
        validation = DocumentProcessor.validate_folder(folder_path)
        if not validation['valid']:
            return {
                "success": False,
                "error": validation['error']
            }
        
        logger.info(f"📁 Processing folder: {folder_path}")
        logger.info(f"   Total files: {validation['file_count']}")
        logger.info(f"   Supported files: {validation['supported_files']}")
        logger.info(f"   Files by type: {validation['files_by_type']}")
        logger.info(f"   Recursive: {recursive}, Workers: {max_workers}")
        
        rag_service = _run_async(_ensure_initialized())
        result = _run_async(
            rag_service.process_folder(
                folder_path=folder_path,
                file_extensions=file_extensions,
                recursive=recursive,
                max_workers=max_workers
            )
        )
        
        if result['success']:
            logger.info(f"✅ {result['message']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Folder processing failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# ENTRYPOINT 6: Query RAG (Non-Streaming)
# ============================================

def query_rag(
    query: str,
    mode: str = "naive",
    top_k: Optional[int] = None,
    response_type: str = "Multiple Paragraphs"
) -> str:
    """
    Query the knowledge base (non-streaming)
    
    Args:
        query: The question or query text
        mode: Query mode - "local", "global", "hybrid", "naive", or "mix"
        top_k: Number of results to retrieve (default from config)
        response_type: Format of response ("Multiple Paragraphs", "Single Paragraph", "Bullet Points")
    
    Returns:
        str: The answer to the query
    
    Example:
        >>> answer = query_rag(
        ...     query="What are the main findings in the research papers?",
        ...     mode="hybrid",
        ...     response_type="Multiple Paragraphs"
        ... )
    """
    try:
        logger.info(f"🔍 Querying (mode={mode}): {query[:100]}...")
        
        rag_service = _run_async(_ensure_initialized())
        response = _run_async(
            rag_service.query(
                query=query,
                mode=mode,
                top_k=top_k,
                response_type=response_type
            )
        )
        
        logger.info("✅ Query completed")
        return response
        
    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        return f"Error: {str(e)}"


# ============================================
# ENTRYPOINT 7: Query RAG (Streaming)
# ============================================

async def query_rag_stream(
    query: str,
    mode: str = "naive",
    top_k: Optional[int] = None,
    response_type: str = "Multiple Paragraphs"
):
    """
    Query the knowledge base (streaming)
    
    Args:
        query: The question or query text
        mode: Query mode - "local", "global", "hybrid", "naive", or "mix"
        top_k: Number of results to retrieve
        response_type: Format of response
    
    Yields:
        str: Chunks of the response
    
    Example:
        >>> async for chunk in query_rag_stream(
        ...     query="Explain the methodology used in the papers",
        ...     mode="hybrid"
        ... ):
        ...     print(chunk, end="")
    """
    try:
        logger.info(f"🔍 Streaming query (mode={mode}): {query[:100]}...")
        
        rag_service = await _ensure_initialized()
        
        async for chunk in rag_service.query_stream(
            query=query,
            mode=mode,
            top_k=top_k,
            response_type=response_type
        ):
            yield chunk
        
        logger.info("✅ Streaming query completed")
        
    except Exception as e:
        logger.error(f"❌ Streaming query failed: {e}")
        yield f"Error: {str(e)}"


# ============================================
# ENTRYPOINT 8: Query with Multimodal Content
# ============================================

def query_multimodal(
    query: str,
    multimodal_content: List[Dict],
    mode: str = "naive"
) -> str:
    """
    Query with specific multimodal content (images, tables, equations)
    
    Args:
        query: The question or query text
        multimodal_content: List of multimodal content items
            - For images: {"type": "image", "image_path": "path/to/image.jpg"}
            - For tables: {"type": "table", "table_data": "markdown table"}
            - For equations: {"type": "equation", "latex": "LaTeX formula"}
        mode: Query mode
    
    Returns:
        str: The answer incorporating multimodal context
    """
    try:
        logger.info(f"🎨 Multimodal query: {query[:100]}...")
        logger.info(f"   Content items: {len(multimodal_content)}")
        
        rag_service = _run_async(_ensure_initialized())
        response = _run_async(
            rag_service.query_multimodal(
                query=query,
                multimodal_content=multimodal_content,
                mode=mode
            )
        )
        
        logger.info("✅ Multimodal query completed")
        return response
        
    except Exception as e:
        logger.error(f"❌ Multimodal query failed: {e}")
        return f"Error: {str(e)}"


# ============================================
# ENTRYPOINT 9: Query with VLM Enhancement
# ============================================

def query_with_vlm(
    query: str,
    mode: str = "naive",
    vlm_enhanced: bool = True
) -> str:
    """
    Query with VLM-enhanced multimodal analysis
    """
    try:
        logger.info(f"👁️  VLM-enhanced query: {query[:100]}...")
        
        rag_service = _run_async(_ensure_initialized())
        response = _run_async(
            rag_service.query(
                query=query,
                mode=mode,
                vlm_enhanced=vlm_enhanced
            )
        )
        
        logger.info("✅ VLM query completed")
        return response
        
    except Exception as e:
        logger.error(f"❌ VLM query failed: {e}")
        return f"Error: {str(e)}"


# ============================================
# ENTRYPOINT 10: Delete Documents
# ============================================

def delete_documents(document_ids: List[str]) -> Dict[str, Any]:
    """Delete documents from the knowledge base"""
    try:
        logger.info(f"🗑️  Deleting {len(document_ids)} documents...")
        
        rag_service = _run_async(_ensure_initialized())
        result = _run_async(rag_service.delete_documents(document_ids))
        
        if result['success']:
            logger.info(f"✅ Deleted {result['count']} documents")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Deletion failed: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# ENTRYPOINT 11: Get Agent Statistics
# ============================================

def get_agent_stats() -> Dict[str, Any]:
    """Get comprehensive agent statistics"""
    try:
        logger.info("📊 Fetching statistics...")
        
        rag_service = _run_async(_ensure_initialized())
        stats = _run_async(rag_service.get_stats())
        
        logger.info("✅ Statistics retrieved")
        return stats
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        return {"success": False, "error": str(e)}


# Helper functions
def validate_file(file_path: str) -> Dict[str, Any]:
    return DocumentProcessor.validate_file(file_path)

def validate_folder(folder_path: str) -> Dict[str, Any]:
    return DocumentProcessor.validate_folder(folder_path)

def list_supported_formats() -> Dict[str, List[str]]:
    return DocumentProcessor.SUPPORTED_EXTENSIONS

def get_file_info(file_path: str) -> Dict[str, Any]:
    return DocumentProcessor.get_file_info(file_path)