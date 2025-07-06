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