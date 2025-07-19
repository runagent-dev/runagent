// import { RunAgentClient } from 'runagent';

// // Example 1: Non-streaming
// async function testStandard() {
//   console.log('=== Testing Standard Execution ===');

//   const ra = new RunAgentClient({
//     agentId: 'daa3ddf0-03cf-4fd7-a2e7-e08196cef692',
//     entrypointTag: 'simple_assistant_extracted',
//     // host: 'localhost',
//     // port: 8451,
//     local: true,
//   });

//   await ra.initialize();
//   console.log(`✅ Environment: ${ra.environment}`);

//   const result = await ra.run({
//     user_msg: 'Analyze the benefits of remote work for software teams',
//   });

//   console.log('Result:', result);
// }

// await testStandard();

// ========================================================

import { RunAgentClient } from 'runagent';

// Example 2: Streaming
async function testStream() {
  console.log('\n=== Testing Stream Execution ===');

  const ra = new RunAgentClient({
    agentId: 'daa3ddf0-03cf-4fd7-a2e7-e08196cef692',
    entrypointTag: 'simple_assistant_extracted_stream',
    local: true,
  });

  await ra.initialize();

  const stream = await ra.run({
    user_msg: 'Analyze the benefits of remote work for software teams',
  });

  let count = 0;
  for await (const chunk of stream) {
    count++;
    // console.log(`Chunk ${count}:`, chunk);
    console.log(chunk);
  }
  console.log(`✅ Received ${count} chunks`);
}

await testStream();
