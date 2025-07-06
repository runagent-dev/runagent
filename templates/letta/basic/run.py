from agent import letta_run, letta_run_stream


def run(input_data):
    """
    Entry point for basic Letta agent
    
    Args:
        input_data: Dict with messages list
        
    Returns:
        Response from Letta agent
    """
    return letta_run(input_data)


def run_stream(input_data):
    """
    Entry point for streaming Letta agent
    
    Args:
        input_data: Dict with messages list
        
    Yields:
        Streaming chunks from Letta agent
    """
    for chunk in letta_run_stream(input_data):
        yield chunk


# # Test function for development
# def test():
#     """Test the Letta functions"""
#     test_input = {
#         "messages": [
#             {"role": "user", "content": "Hello! Can you help me?"}
#         ]
#     }
    
#     print("Testing basic response:")
#     result = run(test_input)
#     print(f"Result: {result}")
    
#     print("\nTesting streaming response:")
#     chunk_count = 0
#     for chunk in run_stream(test_input):
#         chunk_count += 1
#         print(f"Chunk {chunk_count}: {chunk}")
#         if chunk_count >= 3:  # Limit for testing
#             print("... (limiting output)")
#             break


# if __name__ == "__main__":
#     test()