def rag_tool(query: str, mode: str = "local", text_to_insert: str = None) -> dict:
    """
    RAG tool for querying and inserting text into the knowledge base.

    Args:
        query (str): The query to search for in the RAG system
        mode (str): The search mode (naive, local, global, hybrid, mix)
        text_to_insert (str): Optional text to insert into the RAG system

    Returns:
        dict: JSON-compatible dictionary containing the RAG response
    """
    from lightrag import LightRAG, QueryParam
    from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
    from lightrag.kg.shared_storage import initialize_pipeline_status
    from lightrag.utils import setup_logger
    import asyncio
    import os

    try:
        # FIXED: Ensure OpenAI API key is set
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            return {
                "status": "error",
                "query": query,
                "mode": mode,
                "content": "",
                "message": "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
            }

        # Set the API key in environment
        os.environ['OPENAI_API_KEY'] = openai_api_key

        # Set up logger
        setup_logger("lightrag", level="INFO")

        # Create RAG instance with predefined working directory
        rag = LightRAG(
            working_dir="/final_rag_storage",
            embedding_func=openai_embed,
            llm_model_func=gpt_4o_mini_complete
        )

        # FIXED: Better async handling
        def run_async_operations():
            """Run async operations in a controlled manner"""
            try:
                # Create a new event loop for this operation
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def async_operations():
                    # Initialize storages
                    await rag.initialize_storages()
                    await initialize_pipeline_status()
                    
                    # Insert text if provided
                    if text_to_insert:
                        await rag.ainsert(text_to_insert)
                    
                    # Query the RAG system
                    result = await rag.aquery(query, param=QueryParam(mode=mode))
                    return result
                
                # Run the async operations
                result = loop.run_until_complete(async_operations())
                return result
                
            except Exception as e:
                print(f"Error in async operations: {e}")
                # Fallback to synchronous operations
                try:
                    if text_to_insert:
                        rag.insert(text_to_insert)
                    result = rag.query(query, param=QueryParam(mode=mode))
                    return result
                except Exception as sync_error:
                    print(f"Sync fallback also failed: {sync_error}")
                    raise e
            finally:
                # FIXED: Proper cleanup
                try:
                    if 'loop' in locals() and not loop.is_closed():
                        # Cancel all running tasks
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        
                        # Wait for tasks to complete cancellation
                        if pending:
                            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        
                        # Close the loop
                        loop.close()
                except Exception as cleanup_error:
                    print(f"Warning: Error during cleanup: {cleanup_error}")

        # Validate mode
        valid_modes = ["naive", "local", "global", "hybrid", "mix"]
        if mode not in valid_modes:
            mode = "mix"  # Default to mix if invalid mode

        # Run the RAG operations
        result = run_async_operations()

        # Handle the result correctly - check if it's a dictionary
        if isinstance(result, dict):
            answer = result.get("answer", "No answer found")
            sources = result.get("source_nodes", [])
        else:
            # If result is not a dictionary (e.g., it's a string or other type)
            answer = str(result)
            sources = []

        # Return a clean, simple response that the agent can easily parse
        return {
            "status": "success",
            "query": query,
            "mode": mode,
            "content": answer,  # This is the key field the agent should use
            "sources": sources,
            "message": "RAG research completed successfully. Please save this content to the database."
        }

    except Exception as e:
        # Handle any errors
        import traceback
        error_details = traceback.format_exc()
        print(f"RAG tool error: {error_details}")
        return {
            "status": "error",
            "query": query,
            "mode": mode,
            "content": "",
            "error_details": error_details,
            "message": f"Error in RAG tool: {str(e)}"
        }