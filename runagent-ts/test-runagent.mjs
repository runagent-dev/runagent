import { RunAgentClient } from './packages/runagent/dist/index.js';

// Example 1: Non-streaming (matches your first Python example)
async function example1() {
  console.log('=== Example 1: Non-Streaming ===');

  const ra = new RunAgentClient({
    agentId: '23859089-fa28-4b8c-8efb-a28d21902393',
    entrypointTag: 'generic',
    host: 'localhost',
    port: 8450,
    local: true,
  });

  // Initialize (this replaces the automatic architecture loading in Python)
  await ra.initialize();

  const solutionResult = await ra.run({
    input: {
      query: 'How do I fix my broken phone?',
      num_solutions: 4,
    },
  });

  console.log(solutionResult);
}

// Example 2: Streaming (matches your second Python example)
async function example2() {
  console.log('\n=== Example 2: Streaming ===');

  const ra = new RunAgentClient({
    agentId: '23859089-fa28-4b8c-8efb-a28d21902393',
    entrypointTag: 'generic_stream', // _stream suffix triggers streaming
    host: 'localhost',
    port: 8450,
    local: true,
  });

  // Initialize
  await ra.initialize();

  const stream = await ra.run({
    input: {
      query: 'How do I fix my broken phone?',
      num_solutions: 4,
    },
  });

  for await (const out of stream) {
    console.log('=====??');
    console.log(out);
    console.log('??====');
  }
}

// Run examples
async function runExamples() {
  console.log('🎯 RunAgent TypeScript SDK Examples\n');
  console.log('These examples match your original JavaScript usage exactly!\n');

  try {
    await example1();
    // Uncomment to test streaming:
    // await example2();

    console.log('\n🎉 Example completed!');
  } catch (error) {
    console.error('❌ Example failed:', error.message);
    console.error('Full error:', error);
  }
}

runExamples();