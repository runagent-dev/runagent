from runagent import RunAgentClient
import os

# Configuration
AGENT_ID = "63751c14-0ed5-426c-ab44-aa94e5505bed"
LOCAL_MODE = False
USER_ID = "rad123"

# Initialize clients
ingest_client = RunAgentClient(
    agent_id=AGENT_ID,
    entrypoint_tag="ingest_text",
    local=LOCAL_MODE,
    user_id=USER_ID,
    persistent_memory=True
)

query_client = RunAgentClient(
    agent_id=AGENT_ID,
    entrypoint_tag="query_rag",
    local=LOCAL_MODE,
    user_id=USER_ID,
    persistent_memory=True
)


def ingest_from_file(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"Ingesting {len(text)} characters...")
    result = ingest_client.run(text=text)

    return result


def query_rag(question: str, mode: str = "hybrid"):
    print(f"\nQuerying: {question}")
    result = query_client.run(query=question, mode=mode)
    
    return result


if __name__ == "__main__":
    # Step 1: Ingest text
    print("="*60)
    print("STEP 1: Ingest Document")
    print("="*60)
    # ingest_from_file("/home/azureuser/runagent/test/rag_test.txt")
    
    # # Step 2: Query
    # print("\n" + "="*60)
    # print("STEP 2: Query RAG")
    # print("="*60)
    print(query_rag("globalization with megacity", mode="hybrid"))
    
    # print("\nDone!")