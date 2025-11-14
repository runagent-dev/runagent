declare const __IS_NODE__: boolean | undefined;
declare const __IS_BROWSER__: boolean | undefined;

const isNode = Boolean(__IS_NODE__);
const isBrowser = Boolean(__IS_BROWSER__);

import { RestClient } from '../rest/index.js';
import { BrowserWebSocketClient } from '../websocket/browser.js';
import { NodeWebSocketClient } from '../websocket/node.js';
import { CoreSerializer } from '../serializer/index.js';
import type {
  RunAgentConfig,
  AgentArchitecture,
  JsonValue,
  ApiResponse,
} from '../types/index.js';
import type { RunAgentRegistry } from '../database/index.js';
import { RunAgentExecutionError } from '../errors/index.js';

type WebSocketClientType = BrowserWebSocketClient | NodeWebSocketClient;

const DEFAULT_REMOTE_BASE_URL = 'https://backend.run-agent.ai';
const DEFAULT_API_PREFIX = '/api/v1';
const DEFAULT_TIMEOUT_SECONDS = 300;
const API_KEY_ENV = 'RUNAGENT_API_KEY';
const BASE_URL_ENV = 'RUNAGENT_BASE_URL';

interface ClientEndpoints {
  restBaseUrl: string;
  socketBaseUrl: string;
  apiPrefix: string;
  isLocal: boolean;
}

const sanitizeBaseUrl = (baseUrl: string): string =>
  baseUrl.replace(/\/$/, '');

const toWebSocketBase = (baseUrl: string): string => {
  if (baseUrl.startsWith('wss://') || baseUrl.startsWith('ws://')) {
    return sanitizeBaseUrl(baseUrl);
  }
  if (baseUrl.startsWith('https://')) {
    return sanitizeBaseUrl(baseUrl.replace(/^https:\/\//, 'wss://'));
  }
  if (baseUrl.startsWith('http://')) {
    return sanitizeBaseUrl(baseUrl.replace(/^http:\/\//, 'ws://'));
  }
  return `wss://${sanitizeBaseUrl(baseUrl)}`;
};

const getEnvVar = (name: string): string | undefined => {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const globalProcessEnv = (globalThis as any)?.process?.env;
    if (globalProcessEnv && typeof globalProcessEnv[name] === 'string') {
      return globalProcessEnv[name] as string;
    }
  } catch {
    // Ignore environment probing errors
  }

  try {
    // Allow browser builds to inject env via globalThis.RUNAGENT_ENV
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const runtimeEnv = (globalThis as any)?.RUNAGENT_ENV;
    if (runtimeEnv && typeof runtimeEnv[name] === 'string') {
      return runtimeEnv[name] as string;
    }
  } catch {
    // Ignore missing global object
  }

  return undefined;
};

export class RunAgentClient {
  private serializer: CoreSerializer;
  private local: boolean;
  private agentId: string;
  private entrypointTag: string;
  private config: RunAgentConfig;
  private restClient?: RestClient;
  private socketClient?: WebSocketClientType;
  private agentArchitecture?: AgentArchitecture;
  private static registry: RunAgentRegistry | null = null;
  private static registryInitialized = false;
  private initialized = false;
  private apiKey?: string;
  private baseUrl?: string;
  private baseSocketUrl?: string;
  private timeoutSeconds: number;
  private extraParams?: Record<string, unknown>;
  private enableRegistry: boolean;

  constructor(config: RunAgentConfig) {
    this.serializer = new CoreSerializer();
    this.config = config;
    this.agentId = config.agentId;
    this.entrypointTag = config.entrypointTag;
    this.local = config.local ?? false;
    this.timeoutSeconds = config.timeoutSeconds ?? DEFAULT_TIMEOUT_SECONDS;
    this.extraParams = config.extraParams;
    this.enableRegistry = config.enableRegistry ?? isNode;

    this.apiKey = config.apiKey ?? getEnvVar(API_KEY_ENV);
    this.baseUrl = config.baseUrl ?? getEnvVar(BASE_URL_ENV);
    this.baseSocketUrl = config.baseSocketUrl;

    if (!this.baseUrl && !this.local) {
      this.baseUrl = DEFAULT_REMOTE_BASE_URL;
    }
  }

  // ------------------------------------------------------------------
  // Initialization helpers
  // ------------------------------------------------------------------

  private static async getRegistry(
    enableRegistry: boolean
  ): Promise<RunAgentRegistry | null> {
    if (!enableRegistry || !isNode) {
      return null;
    }

    if (!this.registry && !this.registryInitialized) {
      try {
        const { RunAgentRegistry } = await import('../database/index.js');
        const available = await RunAgentRegistry.isAvailable();
        if (available) {
          this.registry = new RunAgentRegistry();
          await this.registry.initialize();
        }
      } catch (error) {
        console.warn('📋 Failed to initialize agent registry:', error);
      } finally {
        this.registryInitialized = true;
      }
    }

    return this.registry;
  }

  private async lookupAgent(
    agentId: string
  ): Promise<{ host: string; port: number } | null> {
    try {
      const registry = await RunAgentClient.getRegistry(this.enableRegistry);
      if (registry) {
        return registry.lookupAgent(agentId);
      }
    } catch (error) {
      console.warn(`🔍 Agent lookup failed for ${agentId}:`, error);
    }
    return null;
  }

  private initializeClients(endpoints: ClientEndpoints): void {
    this.restClient = new RestClient({
      baseUrl: endpoints.restBaseUrl,
      apiKey: endpoints.isLocal ? undefined : this.apiKey,
      apiPrefix: endpoints.apiPrefix,
      isLocal: endpoints.isLocal,
      timeoutSeconds: this.timeoutSeconds,
    });

    const socketConfig = {
      baseSocketUrl: endpoints.socketBaseUrl,
      apiKey: endpoints.isLocal ? undefined : this.apiKey,
      apiPrefix: endpoints.apiPrefix,
      isLocal: endpoints.isLocal,
      timeoutSeconds: this.timeoutSeconds,
    };

    this.socketClient = isNode
      ? new NodeWebSocketClient(socketConfig)
      : new BrowserWebSocketClient(socketConfig);
  }

  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }
  }

  async initialize(): Promise<RunAgentClient> {
    if (this.initialized) {
      return this;
    }

    const apiPrefix = this.config.apiPrefix ?? DEFAULT_API_PREFIX;

    if (this.local) {
      const resolved = await this.resolveLocalConnection();
      this.initializeClients({
        restBaseUrl: resolved.baseUrl,
        socketBaseUrl: resolved.socketBaseUrl,
        apiPrefix,
        isLocal: true,
      });
    } else {
      const resolvedBaseUrl = sanitizeBaseUrl(
        this.baseUrl ?? DEFAULT_REMOTE_BASE_URL
      );
      let socketBaseUrl = sanitizeBaseUrl(
        this.baseSocketUrl ?? toWebSocketBase(resolvedBaseUrl)
      );

      if (socketBaseUrl.endsWith(apiPrefix)) {
        socketBaseUrl = sanitizeBaseUrl(
          socketBaseUrl.slice(0, socketBaseUrl.length - apiPrefix.length)
        );
      }

      if (!socketBaseUrl) {
        socketBaseUrl = toWebSocketBase(resolvedBaseUrl);
      }

      this.initializeClients({
        restBaseUrl: resolvedBaseUrl,
        socketBaseUrl,
        apiPrefix,
        isLocal: false,
      });
    }

    await this.loadAgentMetadata();
    this.initialized = true;
    return this;
  }

  private async resolveLocalConnection(): Promise<{
    baseUrl: string;
    socketBaseUrl: string;
  }> {
    let host = this.config.host;
    let port = this.config.port;

    if (!host || !port) {
      const info = await this.lookupAgent(this.agentId);
      if (info) {
        host = info.host;
        port = info.port;
      }
    }

    if (!host || !port) {
      throw new RunAgentExecutionError(
        'AGENT_ADDRESS_NOT_FOUND',
        `Unable to determine host/port for local agent ${this.agentId}`,
        "Provide 'host' and 'port' in RunAgentClient config or register the agent locally."
      );
    }

    const baseUrl = sanitizeBaseUrl(`http://${host}:${port}`);
    const socketBaseUrl = sanitizeBaseUrl(`ws://${host}:${port}`);

    return { baseUrl, socketBaseUrl };
  }

  private async loadAgentMetadata(): Promise<void> {
    if (!this.restClient) {
      throw new Error('REST client not initialized');
    }
    try {
      this.agentArchitecture = await this.restClient.getAgentArchitecture(
        this.agentId
      );

      const selectedEntrypoint = this.agentArchitecture.entrypoints?.find(
        (entrypoint) => entrypoint.tag === this.entrypointTag
      );

      if (!selectedEntrypoint) {
        const availableEntrypoints =
          this.agentArchitecture.entrypoints
            ?.map((entrypoint) => entrypoint.tag)
            .filter(Boolean) || [];

        console.error('[RunAgentClient] Entrypoint not found.', {
          requested: this.entrypointTag,
          agentId: this.agentId,
          availableEntrypoints,
          architecture: this.agentArchitecture,
        });

        throw new Error(
          `Entrypoint \`${this.entrypointTag}\` not found in agent ${this.agentId}`
        );
      }
    } catch (error) {
      console.error('❌ Failed to initialize agent:', error);
      if (error instanceof RunAgentExecutionError) {
        throw error;
      }
      const message =
        error instanceof Error ? error.message : 'Unknown initialization error';
      throw new RunAgentExecutionError(
        'INITIALIZATION_ERROR',
        this.sanitizeMessage(message) ?? 'Failed to initialize agent',
        'Verify the agent configuration and connection settings.'
      );
    }
  }

  // ------------------------------------------------------------------
  // Public execution methods
  // ------------------------------------------------------------------

  async run(
    inputKwargs: Record<string, unknown> = {}
  ): Promise<unknown> {
    await this.ensureInitialized();

    if (this.entrypointTag.endsWith('_stream')) {
      throw new RunAgentExecutionError(
        'STREAM_ENTRYPOINT',
        `Entrypoint \`${this.entrypointTag}\` is streaming. Use runStream() instead.`
      );
    }

    return this.executeRun(inputKwargs);
  }

  async *runStream(
    inputKwargs: Record<string, unknown> = {}
  ): AsyncGenerator<unknown, void, unknown> {
    await this.ensureInitialized();

    if (!this.entrypointTag.endsWith('_stream')) {
      throw new RunAgentExecutionError(
        'NON_STREAM_ENTRYPOINT',
        `Entrypoint \`${this.entrypointTag}\` is not streaming. Use run() instead.`
      );
    }

    yield* this.executeStream(inputKwargs);
  }

  // ------------------------------------------------------------------
  // Internal execution helpers
  // ------------------------------------------------------------------

  private async executeRun(
    inputKwargs: Record<string, unknown>
  ): Promise<unknown> {
    if (!this.restClient) {
      throw new Error('REST client not initialized');
    }

    const response = await this.restClient.runAgent(
      this.agentId,
      this.entrypointTag,
      {
        inputArgs: [],
        inputKwargs,
        timeoutSeconds: this.timeoutSeconds,
      }
    );

    if (response.success !== false) {
      let payload: unknown = null;

      if (typeof response.data === 'string') {
        payload = this.serializer.deserializeObject(response.data);
      } else if (
        response.data &&
        typeof response.data === 'object' &&
        'result_data' in (response.data as Record<string, unknown>)
      ) {
        const resultData = (response.data as Record<string, unknown>)['result_data'];
        if (
          resultData &&
          typeof resultData === 'object' &&
          'data' in (resultData as Record<string, unknown>)
        ) {
          payload = this.serializer.deserializeObject(
            (resultData as Record<string, unknown>)['data'] as JsonValue
          );
        }
      } else if (response.output_data !== undefined) {
        payload = this.serializer.deserializeObject(response.output_data as JsonValue);
      }

      return payload ?? null;
    }

    throw this.buildExecutionError(
      response.error,
      response.message,
      'EXECUTION_ERROR'
    );
  }

  private executeStream(
    inputKwargs: Record<string, unknown>
  ): AsyncGenerator<unknown, void, unknown> {
    if (!this.socketClient) {
      throw new Error('WebSocket client not initialized');
    }

    return this.socketClient.runStream(
      this.agentId,
      this.entrypointTag,
      {
        inputArgs: [],
        inputKwargs,
        timeoutSeconds: this.timeoutSeconds,
      }
    );
  }

  // ------------------------------------------------------------------
  // Utility getters
  // ------------------------------------------------------------------

  get environment(): 'node' | 'browser' {
    return isNode ? 'node' : 'browser';
  }

  get isNode(): boolean {
    return isNode;
  }

  get isBrowser(): boolean {
    return isBrowser;
  }

  getExtraParams(): Record<string, unknown> | undefined {
    return this.extraParams;
  }

  /**
   * Check if registry features are available.
   */
  static async hasRegistry(): Promise<boolean> {
    if (!isNode) return false;
    try {
      const { RunAgentRegistry } = await import('../database/index.js');
      return await RunAgentRegistry.isAvailable();
    } catch {
      return false;
    }
  }

  /**
   * Get registry instance (for advanced Node.js users).
   */
  static async getRegistryInstance(): Promise<RunAgentRegistry | null> {
    return await this.getRegistry(true);
  }

  private buildExecutionError(
    errorInfo: ApiResponse['error'],
    fallbackMessage?: string | null,
    defaultCode = 'UNKNOWN_ERROR'
  ): RunAgentExecutionError {
    const fallback = this.sanitizeMessage(fallbackMessage) ?? 'Unknown error';

    if (!errorInfo) {
      return new RunAgentExecutionError(defaultCode, fallback);
    }

    if (typeof errorInfo === 'string') {
      return new RunAgentExecutionError(
        defaultCode,
        this.sanitizeMessage(errorInfo) ?? fallback
      );
    }

    const { code, message, suggestion, details } = errorInfo;
    const normalizedMessage =
      this.sanitizeMessage(message) ?? fallback;

    return new RunAgentExecutionError(
      code ?? defaultCode,
      normalizedMessage,
      suggestion,
      details
    );
  }

  private sanitizeMessage(value?: string | null): string | undefined {
    if (!value) return undefined;
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : undefined;
  }
}
