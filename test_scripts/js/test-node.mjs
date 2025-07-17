import { RunAgentClient } from 'runagent';

// Example 1: Non-streaming
async function testStandard() {
  console.log('=== Testing Standard Execution ===');

  const ra = new RunAgentClient({
    agentId: 'f7066c98-0eb2-488c-bb37-a869a93d51ce',
    entrypointTag: 'minimal',
    host: 'localhost',
    port: 8451,
    local: true,
  });

  await ra.initialize();
  console.log(`✅ Environment: ${ra.environment}`);

  const result = await ra.run({
    message: 'How do I fix my broken phone?',
  });

  console.log('Result:', result);
}

await testStandard();

// ========================================================

// // Example 2: Streaming
// async function testStream() {
//   console.log('\n=== Testing Stream Execution ===');

//   const ra = new RunAgentClient({
//     agentId: 'f7066c98-0eb2-488c-bb37-a869a93d51ce',
//     entrypointTag: 'minimal',
//     host: 'localhost',
//     port: 8451,
//     local: true,
//   });

//   await ra.initialize();

//   const stream = await ra.run({
//     message: 'How do I fix my broken phone?',
//   });

//   let count = 0;
//   for await (const chunk of stream) {
//     count++;
//     // console.log(`Chunk ${count}:`, chunk);
//     process.stdout.write(chunk);
//   }
//   console.log(`✅ Received ${count} chunks`);
// }

// await testStream()
