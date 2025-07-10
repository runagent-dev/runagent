import { RestClient } from '../rest/index.js';
import { BrowserWebSocketClient } from '../websocket/browser.js';
import { NodeWebSocketClient } from '../websocket/node.js';
import { CoreSerializer } from '../serializer/index.js';
import type { RunAgentConfig, AgentArchitecture, JsonValue } from '../types/index.js';

// Environment detection
const isNode = (() => {
    try {
      return typeof process !== 'undefined' && 
             typeof process.versions !== 'undefined' &&
             typeof process.versions.node !== 'undefined';
    } catch {
      return false;
    }
  })();
  
  const isBrowser = (() => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return typeof (globalThis as any).window !== 'undefined';
    } catch {
      return false;
    }
  })();

type WebSocketClientType = BrowserWebSocketClient | NodeWebSocketClient;

export class RunAgentClient {
  private serializer: CoreSerializer;
  private local: boolean;
  private agentId: string;
  private entrypointTag: string;
  private apiKey?: string;
  private restClient: RestClient;
  private socketClient: WebSocketClientType;
  private agentArchitecture?: AgentArchitecture;

  constructor(config: RunAgentConfig) {
    this.serializer = new CoreSerializer();
    this.local = config.local ?? true;
    this.agentId = config.agentId;
    this.entrypointTag = config.entrypointTag;
    this.apiKey = config.apiKey;

    if (this.local) {
      let agentHost: string;
      let agentPort: number;

      if (config.host && config.port) {
        agentHost = config.host;
        agentPort = config.port;
        console.log(`🔌 Using explicit address: ${agentHost}:${agentPort}`);
      } else {
        agentHost = 'localhost';
        agentPort = 8080;
        console.log(`🔍 Auto-resolved address for agent ${this.agentId}: ${agentHost}:${agentPort}`);
      }

      const agentBaseUrl = `http://${agentHost}:${agentPort}`;
      const agentSocketUrl = `ws://${agentHost}:${agentPort}`;

      this.restClient = new RestClient({
        baseUrl: agentBaseUrl,
        apiPrefix: '/api/v1',
      });

      if (isNode) {
        this.socketClient = new NodeWebSocketClient({
          baseSocketUrl: agentSocketUrl,
          apiPrefix: '/api/v1',
        });
      } else {
        this.socketClient = new BrowserWebSocketClient({
          baseSocketUrl: agentSocketUrl,
          apiPrefix: '/api/v1',
        });
      }
    } else {
      this.restClient = new RestClient({ 
        baseUrl: config.baseUrl,
        apiKey: this.apiKey,
        apiPrefix: config.apiPrefix 
      });
      
      if (isNode) {
        this.socketClient = new NodeWebSocketClient({ 
          baseSocketUrl: config.baseSocketUrl,
          apiKey: this.apiKey,
          apiPrefix: config.apiPrefix 
        });
      } else {
        this.socketClient = new BrowserWebSocketClient({ 
          baseSocketUrl: config.baseSocketUrl,
          apiKey: this.apiKey,
          apiPrefix: config.apiPrefix 
        });
      }
    }
  }

  async initialize(): Promise<RunAgentClient> {
    try {
      this.agentArchitecture = await this.restClient.getAgentArchitecture(this.agentId);
      
      const selectedEntrypoint = this.agentArchitecture.entrypoints?.find(
        (entrypoint) => entrypoint.tag === this.entrypointTag
      );

      if (!selectedEntrypoint) {
        throw new Error(
          `Entrypoint \`${this.entrypointTag}\` not found in agent ${this.agentId}`
        );
      }

      return this;
    } catch (error) {
      console.error('Failed to initialize agent:', error);
      throw error;
    }
  }

  private async _run(inputKwargs: Record<string, unknown>): Promise<unknown> {
    const response = await this.restClient.runAgent(this.agentId, this.entrypointTag, {
      inputArgs: [],
      inputKwargs: inputKwargs,
    });

    if (response.success !== false) {
      const responseData = response.output_data;
      return this.serializer.deserializeObject(responseData as JsonValue);
    } else {
      throw new Error(response.error || 'Agent execution failed');
    }
  }

  private async *_runStream(inputKwargs: Record<string, unknown>): AsyncGenerator<unknown, void, unknown> {
    yield* this.socketClient.runStream(this.agentId, this.entrypointTag, {
      inputArgs: [],
      inputKwargs: inputKwargs,
    });
  }

  // Main run method - matches your Python interface exactly!
  async run(inputKwargs: Record<string, unknown>): Promise<unknown | AsyncGenerator<unknown, void, unknown>> {
    if (this.entrypointTag.endsWith('_stream')) {
      return this._runStream(inputKwargs);
    } else {
      return this._run(inputKwargs);
    }
  }

  // Utility methods
  get environment(): 'node' | 'browser' {
    return isNode ? 'node' : 'browser';
  }

  get isNode(): boolean {
    return isNode;
  }

  get isBrowser(): boolean {
    return isBrowser;
  }
}