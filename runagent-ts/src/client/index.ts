declare const __IS_NODE__: boolean;
declare const __IS_BROWSER__: boolean;

const isNode = __IS_NODE__;
const isBrowser = __IS_BROWSER__;

import { RestClient } from '../rest/index.js';
import { BrowserWebSocketClient } from '../websocket/browser.js';
import { NodeWebSocketClient } from '../websocket/node.js';
import { CoreSerializer } from '../serializer/index.js';
import type {
  RunAgentConfig,
  AgentArchitecture,
  JsonValue,
} from '../types/index.js';
import { RunAgentRegistry } from '../database/index.js';

// Environment detection
// const isNode = (() => {
//   try {
//     return (
//       typeof process !== 'undefined' &&
//       typeof process.versions !== 'undefined' &&
//       typeof process.versions.node !== 'undefined'
//     );
//   } catch {
//     return false;
//   }
// })();

// const isBrowser = (() => {
//   try {
//     // eslint-disable-next-line @typescript-eslint/no-explicit-any
//     return typeof (globalThis as any).window !== 'undefined';
//   } catch {
//     return false;
//   }
// })();

type WebSocketClientType = BrowserWebSocketClient | NodeWebSocketClient;

export class RunAgentClient {
  private serializer: CoreSerializer;
  private local: boolean;
  private agentId: string;
  private entrypointTag: string;
  private config: RunAgentConfig; // Store original config
  // private apiKey?: string;
  private restClient!: RestClient; // Will be initialized in initialize()
  private socketClient!: WebSocketClientType; // Will be initialized in initialize()
  private agentArchitecture?: AgentArchitecture;
  private static registry: RunAgentRegistry | null = null;
  private static registryInitialized: boolean = false;

  /**
   * Get or create registry instance (Node.js only)
   */
  private static async getRegistry(): Promise<RunAgentRegistry | null> {
    if (isBrowser) {
      return null; // Registry not available in browser
    }

    if (!this.registry && !this.registryInitialized) {
      try {
        // Check if registry features are available
        const isAvailable = await RunAgentRegistry.isAvailable();
        if (isAvailable) {
          this.registry = new RunAgentRegistry();
          await this.registry.initialize();
          console.log('🗃️ Agent registry initialized successfully');
        } else {
          console.log(
            '📋 Agent registry unavailable (better-sqlite3 not installed)'
          );
        }
      } catch (error) {
        console.warn('📋 Failed to initialize agent registry:', error);
      } finally {
        this.registryInitialized = true;
      }
    }

    return this.registry;
  }

  /**
   * Try to lookup agent in registry, with graceful fallback
   */
  private async lookupAgent(
    agentId: string
  ): Promise<{ host: string; port: number } | null> {
    try {
      const registry = await RunAgentClient.getRegistry();
      if (registry) {
        return registry.lookupAgent(agentId);
      }
    } catch (error) {
      console.warn(`🔍 Agent lookup failed for ${agentId}:`, error);
    }
    return null;
  }

  constructor(config: RunAgentConfig) {
    this.serializer = new CoreSerializer();
    this.local = config.local ?? false;
    this.agentId = config.agentId;
    this.entrypointTag = config.entrypointTag;
    this.config = config; // Store original config
    // this.apiKey = config.apiKey;

    if (!this.local) {
      throw new Error(
        'Non-local (remote) RunAgent deployment is not available yet. Coming soon.'
      );
    }

    // For browser, initialize clients immediately if host/port provided
    if (isBrowser && config.host && config.port) {
      this.initializeClients(config.host, config.port);
    }
  }

  async initialize(): Promise<RunAgentClient> {
    // Step 1: Determine connection details
    let agentHost: string;
    let agentPort: number;

    if (isBrowser) {
      // Browser: host + port are mandatory for local mode
      if (!this.config.host || !this.config.port) {
        throw new Error(
          "For browser environments, both 'host' and 'port' are required when local=true"
        );
      }
      agentHost = this.config.host;
      agentPort = this.config.port;
      console.log(`🌐 Browser mode - connecting to: ${agentHost}:${agentPort}`);

      // Initialize clients if not already done
      if (!this.restClient) {
        this.initializeClients(agentHost, agentPort);
      }
    } else {
      // Node.js: support both direct connection and agent discovery
      if (this.config.host && this.config.port) {
        // Direct connection mode
        agentHost = this.config.host;
        agentPort = this.config.port;
        console.log(`🔌 Direct connection: ${agentHost}:${agentPort}`);
      } else {
        // Try agent discovery first
        const agentInfo = await this.lookupAgent(this.agentId);

        if (agentInfo) {
          agentHost = agentInfo.host;
          agentPort = agentInfo.port;
          console.log(
            `🔍 Discovered agent ${this.agentId}: ${agentHost}:${agentPort}`
          );
        } else {
          // No registry lookup successful - require explicit config
          throw new Error(
            `Failed to discover agent ${this.agentId}. ` +
              `Please provide explicit 'host' and 'port' in config, or ensure agent is registered.`
          );
        }
      }

      // Initialize clients
      this.initializeClients(agentHost, agentPort);
    }

    // Step 2: Get agent architecture
    try {
      this.agentArchitecture = await this.restClient.getAgentArchitecture(
        this.agentId
      );

      const selectedEntrypoint = this.agentArchitecture.entrypoints?.find(
        (entrypoint) => entrypoint.tag === this.entrypointTag
      );

      if (!selectedEntrypoint) {
        throw new Error(
          `Entrypoint \`${this.entrypointTag}\` not found in agent ${this.agentId}`
        );
      }

      console.log(`✅ Agent ${this.agentId} initialized successfully`);
      return this;
    } catch (error) {
      console.error('❌ Failed to initialize agent:', error);
      throw error;
    }
  }

  /**
   * Initialize REST and WebSocket clients
   */
  private initializeClients(host: string, port: number): void {
    const agentBaseUrl = `http://${host}:${port}`;
    const agentSocketUrl = `ws://${host}:${port}`;

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
  }

  private async _run(inputKwargs: Record<string, unknown>): Promise<unknown> {
    const response = await this.restClient.runAgent(
      this.agentId,
      this.entrypointTag,
      {
        inputArgs: [],
        inputKwargs: inputKwargs,
      }
    );

    if (response.success !== false) {
      const responseData = response.output_data;
      return this.serializer.deserializeObject(responseData as JsonValue);
    } else {
      throw new Error(response.error || 'Agent execution failed');
    }
  }

  private async *_runStream(
    inputKwargs: Record<string, unknown>
  ): AsyncGenerator<unknown, void, unknown> {
    yield* this.socketClient.runStream(this.agentId, this.entrypointTag, {
      inputArgs: [],
      inputKwargs: inputKwargs,
    });
  }

  // Main run method - matches your Python interface exactly!
  async run(
    inputKwargs: Record<string, unknown>
  ): Promise<unknown | AsyncGenerator<unknown, void, unknown>> {
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

  /**
   * Check if registry features are available
   */
  static async hasRegistry(): Promise<boolean> {
    if (isBrowser) return false;
    return await RunAgentRegistry.isAvailable();
  }

  /**
   * Get registry instance (for advanced users)
   */
  static async getRegistryInstance(): Promise<RunAgentRegistry | null> {
    return await this.getRegistry();
  }
}
