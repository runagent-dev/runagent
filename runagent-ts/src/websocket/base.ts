import { CoreSerializer } from '../serializer/index.js';
import type { ExecutionRequest, JsonValue } from '../types/index.js';

interface WebSocketConfig {
  baseSocketUrl?: string;
  apiKey?: string;
  apiPrefix?: string;
  isLocal?: boolean;
  timeoutSeconds?: number;
}

interface RunStreamOptions {
  inputArgs?: unknown[];
  inputKwargs?: Record<string, unknown>;
  timeoutSeconds?: number;
}

interface StreamMessage {
  type: string;
  status?: string;
  payload?: unknown;
  error?: unknown;
}

export abstract class BaseWebSocketClient {
  protected serializer: CoreSerializer;
  protected baseSocketUrl: string;
  protected apiKey?: string;
  protected apiPrefix: string;
  protected isLocal: boolean;
  protected timeoutSeconds: number;

  constructor(config: WebSocketConfig) {
    const {
      baseSocketUrl = 'ws://localhost:8080',
      apiKey,
      apiPrefix = '/api/v1',
      isLocal = true,
      timeoutSeconds = 300,
    } = config;

    this.baseSocketUrl = baseSocketUrl.replace(/\/$/, '') + apiPrefix;
    this.apiKey = apiKey;
    this.serializer = new CoreSerializer();
    this.apiPrefix = apiPrefix;
    this.isLocal = isLocal;
    this.timeoutSeconds = timeoutSeconds;
  }

  abstract createWebSocket(
    url: string,
    headers?: Record<string, string>
  ): unknown | Promise<unknown>;

  async *runStream(
    agentId: string,
    entrypointTag: string,
    options: RunStreamOptions = {}
  ): AsyncGenerator<unknown, void, unknown> {
    const { inputArgs = null, inputKwargs = null, timeoutSeconds } = options;
    const endpoint = `${this.baseSocketUrl}/agents/${agentId}/run-stream`;

    let uri = endpoint;
    if (!this.isLocal && this.apiKey) {
      const separator = endpoint.includes('?') ? '&' : '?';
      uri = `${endpoint}${separator}token=${encodeURIComponent(this.apiKey)}`;
    }

    const headers =
      !this.isLocal && this.apiKey
        ? { Authorization: `Bearer ${this.apiKey}` }
        : undefined;

    let websocket: unknown;

    try {
      websocket = await Promise.resolve(this.createWebSocket(uri, headers));
      await this.waitForConnection(websocket);

      const request: ExecutionRequest = {
        entrypoint_tag: entrypointTag,
        input_args: inputArgs || [],
        input_kwargs: inputKwargs || {},
        timeout_seconds: timeoutSeconds ?? this.timeoutSeconds,
        async_execution: false,
      };

      this.sendMessage(websocket, JSON.stringify(request));

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

  protected parseStreamMessage(raw: string): StreamMessage {
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      return { type: 'data', payload: raw };
    }

    if (parsed === null || typeof parsed !== 'object') {
      return { type: 'data', payload: parsed };
    }

    const message = parsed as Record<string, unknown>;
    const type =
      typeof message.type === 'string'
        ? message.type.toLowerCase()
        : 'data';

    const status =
      typeof message.status === 'string'
        ? message.status
        : typeof message.data === 'object' &&
          message.data !== null &&
          typeof (message.data as Record<string, unknown>).status === 'string'
        ? ((message.data as Record<string, unknown>).status as string)
        : undefined;

    const error =
      message.error ??
      message.detail ??
      (typeof message.data === 'object' &&
      message.data !== null &&
      'error' in (message.data as Record<string, unknown>)
        ? (message.data as Record<string, unknown>).error
        : undefined);

    const payload =
      message.content ??
      message.data ??
      message.payload ??
      message.delta ??
      undefined;

    return { type, status, payload, error };
  }

  protected cleanErrorMessage(error: unknown): string {
    if (!error) {
      return 'Unknown error';
    }

    let message =
      typeof error === 'string'
        ? error
        : error instanceof Error
        ? error.message
        : JSON.stringify(error);

    if (!message) {
      return 'Unknown error';
    }

    const prefixes = [
      'Streaming error: ',
      'Stream error: ',
      'Internal server error: ',
      'Server error: ',
      'Database error: ',
      'HTTP Error: ',
      'Error: ',
    ];

    for (const prefix of prefixes) {
      if (message.startsWith(prefix)) {
        message = message.slice(prefix.length).trim();
      }
    }

    message = message.replace(/^\d{3}:\s*/, '');

    const duplicateIndex = message.toLowerCase().indexOf('; then sent');
    if (duplicateIndex !== -1) {
      message = message.slice(0, duplicateIndex).trim();
    }

    return message.trim() || 'Unknown error';
  }

  protected deserializeStreamPayload(payload: unknown): unknown {
    if (payload === null || payload === undefined) {
      return payload;
    }

    if (typeof payload === 'string') {
      try {
        return this.serializer.deserializeObject(payload);
      } catch {
        return payload;
      }
    }

    if (typeof payload === 'object') {
      try {
        return this.serializer.deserializeObject(payload as JsonValue);
      } catch {
        return payload;
      }
    }

    return payload;
  }
}