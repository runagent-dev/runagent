from openai import OpenAI
client = OpenAI()

response = client.responses.create(
    model="gpt-5-mini",
    input="Draw simple a mermaid graph of weather agent",
    reasoning={
        "effort": "minimal"
    }
)

print(response)