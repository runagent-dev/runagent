import { RunAgentClient } from 'runagent';

// Example 1: Non-streaming
async function testStandard() {
  console.log('=== Testing Standard Execution ===');

  const ra = new RunAgentClient({
    agentId: '95d60499-b9c1-4cc4-8e7a-0382b6e085d7',
    entrypointTag: 'food_doctor',
    // host: 'localhost',
    // port: 8451,
    local: true,
  });

  await ra.initialize();
  console.log(`✅ Environment: ${ra.environment}`);

  const result = await ra.run({
    payload: {
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
      ]}
  });

  console.log('Result:', result);
}

await testStandard();
