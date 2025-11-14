import { BaseWebSocketClient } from './base.js';
import { RunAgentExecutionError } from '../errors/index.js';

interface IteratorResolverItem {
  resolve: (value: { done: boolean; value?: unknown }) => void;
  reject: (error: Error) => void;
}

export class NodeWebSocketClient extends BaseWebSocketClient {
  private WebSocketClass: any = null;

  private async loadWebSocket(): Promise<any> {
    if (this.WebSocketClass) return this.WebSocketClass;
    
    try {
      // Try dynamic import first (for pure ESM)
      const { default: WebSocket } = await import('ws');
      this.WebSocketClass = WebSocket;
      return WebSocket;
    } catch (error) {
      // Fallback to require for mixed environments
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const WebSocket = require('ws');
        this.WebSocketClass = WebSocket;
        return WebSocket;
      } catch (requireError) {
        throw new Error('WebSocket library "ws" is required for Node.js. Install it with: npm install ws');
      }
    }
  }

  async createWebSocket(
    url: string,
    headers?: Record<string, string>
  ): Promise<any> {
    const WebSocket = await this.loadWebSocket();
    return new WebSocket(url, headers ? { headers } : undefined);
  }

  protected async waitForConnection(websocket: unknown): Promise<void> {
    const ws = websocket as any;
    return new Promise((resolve, reject) => {
      ws.on('open', () => resolve());
      ws.on('error', (...args: unknown[]) => {
        const error = args[0] as Error;
        reject(new Error(`WebSocket connection failed: ${error.message}`))
      });
    });
  }

  protected sendMessage(websocket: unknown, message: string): void {
    const ws = websocket as any;
    ws.send(message);
  }

  protected isWebSocketOpen(websocket: unknown): boolean {
    const ws = websocket as any;
    return ws.readyState === 1; // WebSocket.OPEN
  }

  protected closeWebSocket(websocket: unknown): void {
    const ws = websocket as any;
    ws.close();
  }

  // Rest of the methods remain the same...
  protected async *createWebSocketIterator(websocket: unknown): AsyncGenerator<unknown, void, unknown> {
    const ws = websocket as any;
    const messageQueue: unknown[] = [];
    const resolvers: IteratorResolverItem[] = [];
    let finished = false;
    let error: Error | null = null;

    const rejectAll = (err: Error) => {
      while (resolvers.length > 0) {
        const resolver = resolvers.shift();
        if (resolver) {
          resolver.reject(err);
        }
      }
    };

    const resolveAll = () => {
      while (resolvers.length > 0) {
        const resolver = resolvers.shift();
        if (resolver) {
          resolver.resolve({ done: true, value: undefined });
        }
      }
    };

    const messageHandler = (...args: unknown[]) => {
      const data = args[0] as Buffer | string;
      try {
        const raw = typeof data === 'string' ? data : data.toString();
        const streamMessage = this.parseStreamMessage(raw);

        if (streamMessage.type === 'status') {
          const statusAction = this.handleStatusMessage(streamMessage);
          if (statusAction.action === 'complete') {
            finished = true;
            resolveAll();
          } else if (statusAction.action === 'error') {
            error = statusAction.error;
            rejectAll(error);
          }
          return;
        }

        if (streamMessage.type === 'error') {
          error = this.buildStreamError(streamMessage);
          rejectAll(error);
          return;
        }

        const payload = this.deserializeStreamPayload(streamMessage.payload);

        if (resolvers.length > 0) {
          const resolver = resolvers.shift();
          if (resolver) {
            resolver.resolve({ done: false, value: payload });
          }
        } else {
          messageQueue.push(payload);
        }
      } catch (err) {
        const normalized =
          err instanceof RunAgentExecutionError
            ? err
            : new RunAgentExecutionError(
                'STREAM_ERROR',
                this.cleanErrorMessage(
                  err instanceof Error ? err.message : err ?? 'Unknown error'
                )
              );
        error = normalized;
        rejectAll(normalized);
      }
    };

    const closeHandler = () => {
      if (!finished && !error) {
        error = new RunAgentExecutionError(
          'CONNECTION_ERROR',
          'Stream connection closed unexpectedly'
        );
        rejectAll(error);
      } else {
        resolveAll();
      }
      finished = true;
    };

    const errorHandler = (...args: unknown[]) => {
      const err = args[0] as Error;
      error = new RunAgentExecutionError(
        'CONNECTION_ERROR',
        this.cleanErrorMessage(err.message || err)
      );
      rejectAll(error);
    };

    ws.on('message', messageHandler);
    ws.on('close', closeHandler);
    ws.on('error', errorHandler);

    while (!finished && !error) {
      if (messageQueue.length > 0) {
        yield messageQueue.shift();
      } else {
        const result = await new Promise<{ done: boolean; value?: unknown }>((resolve, reject) => {
          resolvers.push({ resolve, reject });
        });

        if (result.done) break;
        yield result.value;
      }
    }

    if (error) throw error;
  }
}