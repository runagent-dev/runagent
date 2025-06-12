import typing as t
from .agent import ask_agent


# DO NOT MODIFY THIS SECTION - This is a template function that must remain unchanged
def run(input_data: t.Dict[str, t.Any]) -> t.Dict[str, t.Any]:
    query = input_data["query"]
    result = ask_agent(query)
    return result
