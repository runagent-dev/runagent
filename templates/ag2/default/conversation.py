from autogen import ConversableAgent, LLMConfig

# It uses the OPENAI_API_KEY environment variable
llm_config = LLMConfig(api_type="openai", model="gpt-4o-mini")


with llm_config:
    assistant = ConversableAgent(
        name="assistant",
        system_message="You are an assistant that responds concisely. ",
    )

    fact_checker = ConversableAgent(
        name="fact_checker",
        system_message="You are a fact-checking assistant.",
    )


def invoke(message, max_turns):
    result = assistant.initiate_chat(
        recipient=fact_checker,
        message=message,
        max_turns=max_turns
    )
    # result = response.process()
    print("RESULT", result)
    return result


def stream(message, max_turns):
    response = assistant.run(
        recipient=fact_checker,
        message=message,
        max_turns=max_turns
    )
    for resp in response.events:
        if resp.type == "text":
            yield resp.content
