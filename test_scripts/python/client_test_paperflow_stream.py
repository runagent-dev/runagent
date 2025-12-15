"""
Test PaperFlow agent with streaming support
Shows real-time progress updates as the agent processes papers
"""
from runagent import RunAgentClient
import asyncio

async def test_streaming():
    """Test the streaming entrypoint"""
    client = RunAgentClient(
        agent_id="62f7a781-41bb-4d62-a68f-24dc4f2bfd0b",
        entrypoint_tag="check_papers_stream",  # Use streaming entrypoint
        local=False,
        user_id="prova3",
        persistent_memory=True
    )
    
    print("🚀 Starting streaming agent...")
    print("=" * 70)
    
    # Use streaming mode if available
    try:
        # Check if client supports streaming
        if hasattr(client, 'run_stream'):
            async for update in client.run_stream(
                topics=["reinforcement learning"],
                max_results=20,
                days_back=100
            ):
                update_type = update.get("type", "unknown")
                
                if update_type == "status":
                    print(f"📊 {update.get('message', '')} [{update.get('progress', 0)}%]")
                elif update_type == "paper":
                    paper = update.get("paper", "")
                    is_new = update.get("is_new", False)
                    status = "🆕 NEW" if is_new else "📄"
                    print(f"\n{status} Paper found:")
                    print(paper)
                    print(f"Progress: {update.get('progress', 0)}%")
                elif update_type == "progress":
                    print(f"⏳ {update.get('message', '')} [{update.get('progress', 0)}%]")
                elif update_type == "complete":
                    print("\n" + "=" * 70)
                    print("✅ Processing Complete!")
                    print("=" * 70)
                    print(f"Total processed: {update.get('total_processed', 0)}")
                    print(f"Total relevant: {update.get('total_relevant', 0)}")
                    print(f"New papers: {update.get('new_papers', 0)}")
                    print(f"Cached hits: {update.get('cached_hits', 0)}")
                    print(f"LLM calls: {update.get('llm_calls', 0)}")
                    print(f"Email sent: {update.get('email_sent', False)}")
                elif update_type == "error":
                    print(f"\n❌ Error: {update.get('error', 'Unknown error')}")
        else:
            # Fallback to regular async call
            print("⚠️  Streaming not available, using async mode...")
            result = await client.run_async(
                topics=["reinforcement learning"],
                max_results=20,
                days_back=100
            )
            print(f"\n✅ Found {result['total_relevant']} relevant papers")
            print(f"Email sent: {result['email_sent']}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_async():
    """Test the async entrypoint (faster, but no streaming)"""
    client = RunAgentClient(
        agent_id="62f7a781-41bb-4d62-a68f-24dc4f2bfd0b",
        entrypoint_tag="check_papers_async",  # Use async entrypoint
        local=False,
        user_id="prova3",
        persistent_memory=True
    )
    
    print("🚀 Starting async agent (parallel processing)...")
    print("=" * 70)
    
    # Run async entrypoint
    result = asyncio.run(client.run(
        topics=["reinforcement learning"],
        max_results=20,
        days_back=100
    ))
    
    print("\n" + "=" * 70)
    print("✅ Results:")
    print("=" * 70)
    print(f"Total processed: {result.get('total_processed', 0)}")
    print(f"Total relevant: {result.get('total_relevant', 0)}")
    print(f"New papers: {result.get('new_papers', 0)}")
    print(f"Cached hits: {result.get('cached_hits', 0)}")
    print(f"LLM calls: {result.get('llm_calls', 0)}")
    print(f"Email sent: {result.get('email_sent', False)}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "async":
        test_async()
    else:
        # Default to streaming
        asyncio.run(test_streaming())

