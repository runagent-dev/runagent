import { CoreSerializer } from '../serializer/index.js';
import type { WebSocketMessage, ExecutionRequest } from '../types/index.js';

interface WebSocketConfig {
  baseSocketUrl?: string;
  apiKey?: string;
  apiPrefix?: string;
}

interface RunStreamOptions {
  inputArgs?: unknown[];
  inputKwargs?: Record<string, unknown>;
}

export abstract class BaseWebSocketClient {
  protected serializer: CoreSerializer;
  protected baseSocketUrl: string;
  protected apiKey?: string;

  constructor(config: WebSocketConfig) {
    const { baseSocketUrl = 'ws://localhost:8080', apiKey, apiPrefix = '/api/v1' } = config;
    
    this.baseSocketUrl = baseSocketUrl.replace(/\/$/, '') + apiPrefix;
    this.apiKey = apiKey;
    this.serializer = new CoreSerializer();
  }

  abstract createWebSocket(url: string): unknown | Promise<unknown>;

  async *runStream(
    agentId: string,
    entrypointTag: string,
    options: RunStreamOptions = {}
  ): AsyncGenerator<unknown, void, unknown> {
    const { inputArgs = null, inputKwargs = null } = options;
    const uri = `${this.baseSocketUrl}/agents/${agentId}/execute/${entrypointTag}`;

    let websocket: unknown;

    try {
        websocket = await Promise.resolve(this.createWebSocket(uri));
        await this.waitForConnection(websocket);

      const request: ExecutionRequest = {
        action: 'start_stream',
        agent_id: agentId,
        input_data: {
          input_args: inputArgs || [],
          input_kwargs: inputKwargs || {},
        },
      };

      const startMsg: Partial<WebSocketMessage> = {
        id: 'stream_start',
        type: 'status',
        timestamp: new Date().toISOString(),
        data: request,
      };

      const serializedMsg = this.serializer.serializeMessage(startMsg);
      this.sendMessage(websocket, serializedMsg);

      yield* this.createWebSocketIterator(websocket);
    } finally {
      if (websocket && this.isWebSocketOpen(websocket)) {
        this.closeWebSocket(websocket);
      }
    }
  }

  protected abstract waitForConnection(websocket: unknown): Promise<void>;
  protected abstract sendMessage(websocket: unknown, message: string): void;
  protected abstract isWebSocketOpen(websocket: unknown): boolean;
  protected abstract closeWebSocket(websocket: unknown): void;
  protected abstract createWebSocketIterator(websocket: unknown): AsyncGenerator<unknown, void, unknown>;
}