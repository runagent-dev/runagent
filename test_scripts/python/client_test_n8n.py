from pprint import pprint
from runagent import RunAgentClient

ra = RunAgentClient(
    agent_id="95d60499-b9c1-4cc4-8e7a-0382b6e085d7",
    entrypoint_tag="food_doctor",
    local=True
    )


agent_results = ra.run({
        "recipe_name": "Chocolate Chip Pancakes",
        "servings": 4,
        "ingredients": [
            "2 cups all-purpose flour",
            "2 tablespoons sugar",
            "2 teaspoons baking powder",
            "1 teaspoon salt",
            "2 large eggs",
            "1.5 cups whole milk",
            "1/4 cup melted butter",
            "1/2 cup chocolate chips"
        ]
    }
)

pprint(agent_results)
