from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
client = OpenAI()


def get_prompt(sender_name: str, recipient_name: str, subject: str) -> str:
    return (
        f"Write a professional email with the following details:\n"
        f"- Sender: {sender_name}\n"
        f"- Recipient: {recipient_name}\n"
        f"- Subject: {subject}\n\n"
        f"The email should be concise, polite, and use natural language. Include a greeting, body, and closing."
    )


def generate_email(sender_name: str, recipient_name: str, subject: str) -> str:
    prompt = get_prompt(sender_name, recipient_name, subject)

    response = client.responses.create(
        model="gpt-4",
        input=prompt
    )

    email_text = response.output_text.strip()
    return email_text


def generate_email_sream(sender_name: str, recipient_name: str, subject: str) -> str:
    prompt = get_prompt(sender_name, recipient_name, subject)

    stream_response = client.responses.create(
        model="gpt-4",
        input=prompt,
        stream=True
    )

    for chunk in stream_response:
        if isinstance(chunk, ResponseTextDeltaEvent):
            yield chunk.delta


# Example usage
if __name__ == "__main__":
    sender = "Alice Johnson"
    recipient = "Mr. Daniel Smith"
    subject = "Request for Meeting Next Week"

    email = generate_email(sender, recipient, subject)
    print("\n--- Generated Email ---\n")
    print(email)

    # print("\n--- Generated Email Stream---\n")
    # for chunk in generate_email_sream(sender, recipient, subject):
    #     print(chunk)
