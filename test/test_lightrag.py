#!/usr/bin/env python3
"""
Simple standalone LightRAG test - NO RunAgent needed
"""
import os
import asyncio
import shutil
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

WORKING_DIR = "prova/test_rag_storage"

async def main():
    # Step 1: Clear old data to start fresh
    print("\n" + "="*60)
    print("STEP 1: Clearing old data")
    print("="*60)
    if os.path.exists(WORKING_DIR):
        shutil.rmtree(WORKING_DIR)
        print(f"✅ Cleared {WORKING_DIR}")
    else:
        print(f"ℹ️  No existing data")
    
    # Step 2: Create RAG instance
    print("\n" + "="*60)
    print("STEP 2: Initializing LightRAG")
    print("="*60)
    
    rag = LightRAG(
        working_dir=WORKING_DIR,
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )
    
    await rag.initialize_storages()
    await initialize_pipeline_status()  # Add this line!
    print("✅ Storage initialized")
    
    # Step 3: Insert text
    print("\n" + "="*60)
    print("STEP 3: Inserting text")
    print("="*60)
    
    sample_text = """
    The global economy showed signs of recovery in 2024. 
    Major indicators including GDP growth, employment rates, and consumer spending 
    all demonstrated positive trends. Economists predict continued growth 
    through 2025, driven by technological innovation and sustainable practices.
    """
    
    print(f"Text length: {len(sample_text)} characters")
    print("Starting insertion (this may take a minute for entity extraction)...")
    
    await rag.ainsert(sample_text)
    
    print("✅ Text inserted and processed")
    
    # Step 4: Check what was created
    print("\n" + "="*60)
    print("STEP 4: Checking created files")
    print("="*60)
    
    files = os.listdir(WORKING_DIR)
    for f in sorted(files):
        path = os.path.join(WORKING_DIR, f)
        size = os.path.getsize(path)
        print(f"  📄 {f}: {size} bytes")
    
    # Step 5: Query
    print("\n" + "="*60)
    print("STEP 5: Querying")
    print("="*60)
    
    result = await rag.aquery(
        "What are the economic trends?",
        param=QueryParam(mode="hybrid")
    )
    
    print(f"\n📊 Query Result:\n{result}\n")
    
    # Cleanup
    await rag.finalize_storages()
    
    print("="*60)
    print("✅ Test completed successfully!")
    print("="*60)

if __name__ == "__main__":
    # Make sure you have OPENAI_API_KEY set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set!")
        print("Set it with: export OPENAI_API_KEY='sk-...'")
        exit(1)
    
    asyncio.run(main())