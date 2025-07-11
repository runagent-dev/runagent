from .email_agent import MockOpenAIClient
from typing import Iterator


def mock_response(message, role="user"):
    """Test the mock agent with non-streaming responses"""
    client = MockOpenAIClient()

    prompt = [
        {
            "role": role,
            "content": message
        }
    ]
    response = client.create(model="gpt-4", messages=prompt)

    print(response.content)
    print(f"\nTokens used: {response.usage_tokens}")
    print(f"Response time: {response.response_time:.2f}s")

    return response.content


def mock_response_stream(message, role="user") -> Iterator[str]:
    """Test the mock agent with streaming responses"""
    client = MockOpenAIClient()
    prompt = [
        {
            "role": role,
            "content": message
        }
    ]
    for chunk in client.create(
        model="gpt-4",
        messages=prompt,
        stream=True
    ):
        if not chunk.finished:
            yield chunk.delta
        else:
            yield "\n[STREAM COMPLETE]"


# Example usage and testing
def test_mock_agent():
    """Test the mock agent with various scenarios"""

    print("=== Testing Email Generation (Streaming) ===")
    email_prompt = [
        {"role": "user", "content": "Write a professional email with sender: "
         "Alice Johnson, recipient: Mr. Daniel Smith, subject: "
         "Request for Meeting Next Week"}
    ]

    for chunk in mock_response_stream(email_prompt):
        print(chunk, end="", flush=True)

    print("\n=== Testing Code Generation ===")
    code_prompt = [
        {"role": "user", "content": "Write a Python function to sort a "
         "list of numbers"}
    ]
    response = mock_response(code_prompt)
    print(response)

    print("\n=== Testing Analysis ===")
    analysis_prompt = [
        {"role": "user", "content": "Analyze the benefits of remote work "
         "for software teams"}
    ]

    response = mock_response(analysis_prompt)
    print(response)


if __name__ == "__main__":
    test_mock_agent()