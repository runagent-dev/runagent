# RunAgent TypeScript SDK

A modern, type-safe SDK for interacting with RunAgent servers. Built with TypeScript and designed to work seamlessly in both browser and Node.js environments.

## ✨ Features

- 🚀 **Universal**: Works in both Browser and Node.js with automatic environment detection
- 🛡️ **Type Safe**: Full TypeScript support with comprehensive type definitions
- 📡 **Real-time Streaming**: Built-in WebSocket support for streaming responses
- 🔄 **REST API**: Complete REST client for standard request/response patterns
- 🎯 **Simple API**: Clean, intuitive interface that matches existing RunAgent patterns
- ⚡ **Modern**: Built with ES modules and modern JavaScript features

## 📦 Installation

```bash
npm install runagent
```

## 🚀 Quick Start

### Basic Usage

```typescript
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient({
  agentId: 'your-agent-id',
  entrypointTag: 'generic',
  host: 'localhost',
  port: 8450,
  local: true
});

// Initialize the client
await client.initialize();

// Execute a standard request
const result = await client.run({
  input: {
    query: 'How do I fix my broken phone?',
    num_solutions: 4
  }
});

console.log(result);
```

### Streaming Usage

```typescript
const streamClient = new RunAgentClient({
  agentId: 'your-agent-id',
  entrypointTag: 'generic_stream', // Note the _stream suffix
  host: 'localhost',
  port: 8450,
  local: true
});

await streamClient.initialize();

const stream = await streamClient.run({
  input: {
    query: 'Generate a detailed solution',
    num_solutions: 4
  }
});

// Process streaming results
for await (const chunk of stream) {
  console.log('Received:', chunk);
}
```

## 🌐 Environment Support

The SDK automatically detects your environment and uses the appropriate implementation:

### Node.js
```javascript
// Works out of the box in Node.js
import { RunAgentClient } from 'runagent';

const client = new RunAgentClient(config);
console.log(client.environment); // 'node'
```

### Browser
```html
<!DOCTYPE html>
<html>
<head>
    <title>RunAgent Demo</title>
</head>
<body>
    <script type="module">
        import { RunAgentClient } from 'runagent';
        
        const client = new RunAgentClient(config);
        console.log(client.environment); // 'browser'
        
        const result = await client.run(inputData);
    </script>
</body>
</html>
```

### React/Vue/Other Frameworks
```typescript
// Works seamlessly in any modern framework
import { RunAgentClient } from 'runagent';

function MyComponent() {
  const [result, setResult] = useState(null);
  
  const runAgent = async () => {
    const client = new RunAgentClient(config);
    await client.initialize();
    const data = await client.run(inputData);
    setResult(data);
  };
  
  return <button onClick={runAgent}>Run Agent</button>;
}
```

## ⚙️ Configuration

```typescript
interface RunAgentConfig {
  agentId: string;           // Your agent identifier
  entrypointTag: string;     // The entrypoint to call ('generic', 'generic_stream', etc.)
  local?: boolean;           // Use local server (default: true)
  host?: string;             // Server host (default: 'localhost')
  port?: number;             // Server port (default: 8080)
  apiKey?: string;           // API key for remote servers
  baseUrl?: string;          // Custom base URL for remote servers
  baseSocketUrl?: string;    // Custom WebSocket URL for remote servers
  apiPrefix?: string;        // API prefix (default: '/api/v1')
}
```

### Local Development
```typescript
const client = new RunAgentClient({
  agentId: 'my-agent',
  entrypointTag: 'generic',
  host: 'localhost',
  port: 8450,
  local: true
});
```

### Production/Remote Server
```typescript
const client = new RunAgentClient({
  agentId: 'my-agent',
  entrypointTag: 'generic',
  local: false,
  baseUrl: 'https://api.myrunagent.com',
  baseSocketUrl: 'wss://ws.myrunagent.com',
  apiKey: 'your-api-key'
});
```

## 🔄 Execution Modes

### Standard Execution
For regular request/response patterns:

```typescript
const client = new RunAgentClient({
  agentId: 'your-agent',
  entrypointTag: 'generic', // No _stream suffix
  // ... config
});

const result = await client.run(inputData);
// Returns the complete result
```

### Streaming Execution
For real-time streaming responses:

```typescript
const client = new RunAgentClient({
  agentId: 'your-agent',
  entrypointTag: 'generic_stream', // _stream suffix triggers streaming
  // ... config
});

const stream = await client.run(inputData);

for await (const chunk of stream) {
  // Process each chunk as it arrives
  console.log('Chunk:', chunk);
}
```

## 🛠️ Advanced Usage

### Error Handling
```typescript
import { 
  RunAgentClient, 
  AuthenticationError, 
  ConnectionError, 
  ValidationError 
} from 'runagent';

try {
  const result = await client.run(inputData);
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.log('Authentication failed');
  } else if (error instanceof ConnectionError) {
    console.log('Connection failed');
  } else if (error instanceof ValidationError) {
    console.log('Invalid input data');
  }
}
```

### Environment Detection
```typescript
const client = new RunAgentClient(config);

console.log(client.environment); // 'node' | 'browser'
console.log(client.isNode);      // boolean
console.log(client.isBrowser);   // boolean

// Conditional logic based on environment
if (client.isNode) {
  // Node.js specific code
} else {
  // Browser specific code
}
```

### Custom Serialization
```typescript
import { CoreSerializer } from 'runagent';

const serializer = new CoreSerializer();
const serialized = serializer.serializeObject(complexObject);
const deserialized = serializer.deserializeObject(serialized);
```

## 📚 Examples

### Complete Node.js Example
```typescript
import { RunAgentClient } from 'runagent';

async function main() {
  const client = new RunAgentClient({
    agentId: '23859089-fa28-4b8c-8efb-a28d21902393',
    entrypointTag: 'generic',
    host: 'localhost',
    port: 8450,
    local: true
  });

  try {
    await client.initialize();
    
    const result = await client.run({
      input: {
        query: 'What are the best practices for Node.js development?',
        num_solutions: 3
      }
    });
    
    console.log('Result:', result);
  } catch (error) {
    console.error('Error:', error.message);
  }
}

main();
```

### Complete Browser Example
```html
<!DOCTYPE html>
<html>
<head>
    <title>RunAgent Browser Demo</title>
</head>
<body>
    <div id="result"></div>
    <button id="runBtn">Run Agent</button>

    <script type="module">
        import { RunAgentClient } from 'runagent';

        document.getElementById('runBtn').addEventListener('click', async () => {
            const client = new RunAgentClient({
                agentId: 'your-agent-id',
                entrypointTag: 'generic',
                host: 'localhost',
                port: 8450,
                local: true
            });

            try {
                await client.initialize();
                
                const result = await client.run({
                    input: { query: 'Hello from browser!' }
                });
                
                document.getElementById('result').textContent = JSON.stringify(result, null, 2);
            } catch (error) {
                console.error('Error:', error);
            }
        });
    </script>
</body>
</html>
```

## 🏗️ Migration from JavaScript

If you're migrating from the original JavaScript clients, the API is identical:

```javascript
// Old JavaScript way
const { RunAgentClient } = require('./runagent-client.js');

// New TypeScript way  
import { RunAgentClient } from 'runagent';

// Same API, same usage patterns!
const client = new RunAgentClient(config);
await client.initialize();
const result = await client.run(inputData);
```

## 🔍 TypeScript Support

Full TypeScript support with comprehensive type definitions:

```typescript
import type { 
  RunAgentConfig, 
  ApiResponse, 
  WebSocketMessage,
  AgentArchitecture 
} from 'runagent';

// All types are exported for your use
const config: RunAgentConfig = {
  agentId: 'my-agent',
  entrypointTag: 'generic'
};
```

## 🆘 Troubleshooting

### Common Issues

**"WebSocket library 'ws' is required"**
```bash
npm install ws @types/ws
```

**"Cannot find module 'runagent'"**
```bash
npm install runagent
# or
npm install --save runagent
```

**Connection errors**
- Ensure your RunAgent server is running
- Check host/port configuration
- Verify firewall settings

### Debug Mode
```typescript
// Enable detailed logging
console.log('Environment:', client.environment);
console.log('Config:', config);
```

## 📄 License

MIT License - see the main RunAgent project for details.

---

**Part of the [RunAgent](https://github.com/yourusername/runagent) project** | Built with ❤️ and TypeScript