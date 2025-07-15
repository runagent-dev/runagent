from openai import OpenAI


def get_response(user_msg: str) -> str:
    client = OpenAI()
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_msg}
        ]
    )


def get_response_stream(user_msg: str) -> str:
    client = OpenAI()
    return client.chat.completions.create(
        model="gpt-4o-mini",
        stream=True,
        messages=[
            {"role": "developer", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_msg}
        ]
    )
