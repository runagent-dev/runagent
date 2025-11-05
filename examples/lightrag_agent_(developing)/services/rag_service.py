"""
RAG Service - Core LightRAG and RAG-Anything integration
Handles document processing, insertion, and querying
"""

import os
import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status
from raganything import RAGAnything, RAGAnythingConfig

from loguru import logger

from agent.config import LightRAGConfig, get_agent_id
from agent.storage import NeonStorageManager


class RAGService:
    """
    Main RAG service integrating LightRAG and RAG-Anything
    """
    
    def __init__(self, config: LightRAGConfig, storage_manager: NeonStorageManager):
        self.config = config
        self.storage_manager = storage_manager
        self.agent_id = get_agent_id()
        
        # Set environment variables
        config.set_env_vars()
        
        # Initialize instances
        self._lightrag: Optional[LightRAG] = None
        self._raganything: Optional[RAGAnything] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize LightRAG and RAG-Anything"""
        if self._initialized:
            logger.info("✅ RAG service already initialized")
            return
        
        try:
            # Register agent in storage
            await self.storage_manager.register_agent(
                self.agent_id,
                self.config.workspace
            )
            
            # Create working directory
            os.makedirs(self.config.working_dir, exist_ok=True)
            os.makedirs(self.config.output_dir, exist_ok=True)
            
            # Initialize LightRAG
            logger.info("🚀 Initializing LightRAG...")
            self._lightrag = await self._create_lightrag_instance()
            
            # Initialize RAG-Anything
            logger.info("🚀 Initializing RAG-Anything...")
            self._raganything = await self._create_raganything_instance()
            
            self._initialized = True
            logger.info("✅ RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize RAG service: {e}")
            raise
    
    async def _create_lightrag_instance(self) -> LightRAG:
        """Create and initialize LightRAG instance"""
        
        # Define LLM function
        def llm_model_func(
            prompt,
            system_prompt=None,
            history_messages=[],
            **kwargs
        ):
            return openai_complete_if_cache(
                self.config.llm_model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
                **kwargs
            )
        
        # Define embedding function
        embedding_func = EmbeddingFunc(
            embedding_dim=self.config.embedding_dim,
            max_token_size=8192,
            func=lambda texts: openai_embed(
                texts,
                model=self.config.embedding_model,
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url
            )
        )
        
        # Create LightRAG instance
        rag = LightRAG(
            working_dir=self.config.working_dir,
            workspace=self.config.workspace,
            
            # Storage backends
            kv_storage=self.config.kv_storage,
            vector_storage=self.config.vector_storage,
            graph_storage="NetworkXStorage",
            doc_status_storage=self.config.doc_status_storage,
            
            # Vector storage configuration
            vector_db_storage_cls_kwargs={
                "embedding_dim": self.config.embedding_dim,
                "cosine_better_than_threshold": self.config.cosine_threshold
            },
            
            # Model functions
            llm_model_func=llm_model_func,
            embedding_func=embedding_func,
            
            # Performance settings
            llm_model_max_async=self.config.llm_model_max_async,
            embedding_func_max_async=self.config.embedding_func_max_async,
            embedding_batch_num=self.config.embedding_batch_num,
            
            # Optional settings
            enable_llm_cache=self.config.enable_llm_cache,
        )
        
        # Initialize storages
        await rag.initialize_storages()
        await initialize_pipeline_status()
        
        logger.info("✅ LightRAG instance created")
        return rag
    
    async def _create_raganything_instance(self) -> RAGAnything:
        """Create and initialize RAG-Anything instance"""
        
        # Define vision model function for multimodal processing
        def vision_model_func(
            prompt,
            system_prompt=None,
            history_messages=[],
            image_data=None,
            messages=None,
            **kwargs
        ):
            # If messages format is provided (for multimodal VLM enhanced query)
            if messages:
                return openai_complete_if_cache(
                    self.config.vision_model,
                    "",
                    system_prompt=None,
                    history_messages=[],
                    messages=messages,
                    api_key=self.config.openai_api_key,
                    base_url=self.config.openai_base_url,
                    **kwargs
                )
            # Traditional single image format
            elif image_data:
                return openai_complete_if_cache(
                    self.config.vision_model,
                    "",
                    system_prompt=None,
                    history_messages=[],
                    messages=[
                        {"role": "system", "content": system_prompt} if system_prompt else None,
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                                }
                            ]
                        } if image_data else {"role": "user", "content": prompt}
                    ],
                    api_key=self.config.openai_api_key,
                    base_url=self.config.openai_base_url,
                    **kwargs
                )
            # Pure text format
            else:
                return openai_complete_if_cache(
                    self.config.llm_model,
                    prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    api_key=self.config.openai_api_key,
                    base_url=self.config.openai_base_url,
                    **kwargs
                )
        
        # Create RAG-Anything configuration
        rag_config = RAGAnythingConfig(
            working_dir=self.config.working_dir,
            parser=self.config.parser,
            parse_method=self.config.parse_method,
            enable_image_processing=self.config.enable_image_processing,
            enable_table_processing=self.config.enable_table_processing,
            enable_equation_processing=self.config.enable_equation_processing,
        )
        
        # Create RAG-Anything instance using existing LightRAG
        rag_anything = RAGAnything(
            lightrag=self._lightrag,
            vision_model_func=vision_model_func,
            config=rag_config
        )
        
        logger.info("✅ RAG-Anything instance created")
        return rag_anything
    
    @property
    def lightrag(self) -> LightRAG:
        """Get LightRAG instance"""
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")
        return self._lightrag
    
    @property
    def raganything(self) -> RAGAnything:
        """Get RAG-Anything instance"""
        if not self._initialized:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")
        return self._raganything
    
    async def insert_documents(
        self,
        documents: List[str],
        document_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Insert text documents into the knowledge base"""
        try:
            if document_ids:
                await self.lightrag.ainsert(documents, ids=document_ids)
            else:
                await self.lightrag.ainsert(documents)
            
            # Update stats
            await self.storage_manager.update_agent_stats(
                self.agent_id,
                self.config.workspace,
                document_count=len(documents)
            )
            
            return {
                "success": True,
                "document_count": len(documents),
                "message": f"Successfully inserted {len(documents)} documents"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to insert documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_multimodal_document(
        self,
        file_path: str,
        parse_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a multimodal document (PDF, images, tables, etc.)"""
        try:
            await self.raganything.process_document_complete(
                file_path=file_path,
                output_dir=self.config.output_dir,
                parse_method=parse_method or self.config.parse_method
            )
            
            return {
                "success": True,
                "file_path": file_path,
                "message": f"Successfully processed document: {file_path}"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_folder(
        self,
        folder_path: str,
        file_extensions: Optional[List[str]] = None,
        recursive: bool = True,
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """Process all documents in a folder"""
        try:
            await self.raganything.process_folder_complete(
                folder_path=folder_path,
                output_dir=self.config.output_dir,
                file_extensions=file_extensions or [".pdf", ".docx", ".pptx", ".txt"],
                recursive=recursive,
                max_workers=max_workers
            )
            
            return {
                "success": True,
                "folder_path": folder_path,
                "message": f"Successfully processed folder: {folder_path}"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process folder: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def query(
        self,
        query: str,
        mode: str = "naive",
        top_k: Optional[int] = None,
        **kwargs
    ) -> str:
        """Query the knowledge base (non-streaming)"""
        try:
            params = QueryParam(
                mode=mode,
                top_k=top_k or self.config.top_k,
                chunk_top_k=self.config.chunk_top_k,
                max_entity_tokens=0,
                max_relation_tokens=0,
                max_total_tokens=self.config.max_total_tokens,
                enable_rerank=self.config.enable_rerank,
                **kwargs
            )
            
            response = await self.lightrag.aquery(query, param=params)
            return response
            
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            raise
    
    async def query_stream(
        self,
        query: str,
        mode: str = "naive",
        top_k: Optional[int] = None,
        **kwargs
    ):
        """Query the knowledge base (streaming)"""
        try:
            params = QueryParam(
                mode=mode,
                stream=True,
                top_k=top_k or self.config.top_k,
                chunk_top_k=self.config.chunk_top_k,
                max_entity_tokens=0,
                max_relation_tokens=0,
                max_total_tokens=self.config.max_total_tokens,
                enable_rerank=self.config.enable_rerank,
                **kwargs
            )
            
            async for chunk in self.lightrag.aquery(query, param=params):
                yield chunk
                
        except Exception as e:
            logger.error(f"❌ Streaming query failed: {e}")
            raise
    
    async def query_multimodal(
        self,
        query: str,
        multimodal_content: List[Dict],
        mode: str = "hybrid",
        **kwargs
    ) -> str:
        """Query with multimodal content"""
        try:
            response = await self.raganything.aquery_with_multimodal(
                query,
                multimodal_content=multimodal_content,
                mode=mode,
                **kwargs
            )
            return response
            
        except Exception as e:
            logger.error(f"❌ Multimodal query failed: {e}")
            raise
    
    async def delete_documents(self, document_ids: List[str]) -> Dict[str, Any]:
        """Delete documents by IDs"""
        try:
            results = []
            for doc_id in document_ids:
                await self.lightrag.adelete_by_doc_id(doc_id)
                results.append(doc_id)
            
            return {
                "success": True,
                "deleted_ids": results,
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to delete documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        try:
            stats = await self.storage_manager.get_agent_stats(
                self.agent_id,
                self.config.workspace
            )
            
            # Add health check
            health = await self.storage_manager.health_check()
            
            return {
                "agent_id": self.agent_id,
                "workspace": self.config.workspace,
                "stats": stats,
                "storage_health": health,
                "config": {
                    "embedding_model": self.config.embedding_model,
                    "llm_model": self.config.llm_model,
                    "parser": self.config.parser,
                    "storage_backends": {
                        "kv": self.config.kv_storage,
                        "vector": self.config.vector_storage,
                        "graph": self.config.graph_storage,
                        "doc_status": self.config.doc_status_storage
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {
                "error": str(e)
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self._lightrag:
                await self._lightrag.finalize_storages()
            
            if self.storage_manager:
                await self.storage_manager.close()
            
            logger.info("✅ RAG service cleanup complete")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")