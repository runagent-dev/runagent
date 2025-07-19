import { BaseWebSocketClient } from './base.js';

interface IteratorResolverItem {
  resolve: (value: { done: boolean; value?: unknown }) => void;
  reject: (error: Error) => void;
}

interface NodeWebSocket {
  on(event: string, callback: (...args: unknown[]) => void): void;
  send(data: string): void;
  close(): void;
  readyState: number;
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

  async createWebSocket(url: string): Promise<NodeWebSocket> {
    const WebSocket = await this.loadWebSocket();
    return new WebSocket(url) as NodeWebSocket;
  }

  protected async waitForConnection(websocket: unknown): Promise<void> {
    const ws = websocket as NodeWebSocket;
    return new Promise((resolve, reject) => {
      ws.on('open', () => resolve());
      ws.on('error', (...args: unknown[]) => {
        const error = args[0] as Error;
        reject(new Error(`WebSocket connection failed: ${error.message}`))
      });
    });
  }

  protected sendMessage(websocket: unknown, message: string): void {
    const ws = websocket as NodeWebSocket;
    ws.send(message);
  }

  protected isWebSocketOpen(websocket: unknown): boolean {
    const ws = websocket as NodeWebSocket;
    return ws.readyState === 1; // WebSocket.OPEN
  }

  protected closeWebSocket(websocket: unknown): void {
    const ws = websocket as NodeWebSocket;
    ws.close();
  }

  // Rest of the methods remain the same...
  protected async *createWebSocketIterator(websocket: unknown): AsyncGenerator<unknown, void, unknown> {
    const ws = websocket as NodeWebSocket;
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
        console.log('received=> ', data.toString());
        const safeMsg = this.serializer.deserializeMessage(data.toString());

        if (safeMsg.error) {
          error = new Error(`Stream error: ${safeMsg.error}`);
          rejectAll(error);
          return;
        }

        if (safeMsg.type === 'status') {
          const status = (safeMsg.data as Record<string, unknown>)?.status;
          if (status === 'stream_completed') {
            finished = true;
            resolveAll();
            return;
          } else if (status === 'stream_started') {
            return;
          }
        } else if (safeMsg.type === 'ERROR') {
          error = new Error(`Agent error: ${JSON.stringify(safeMsg.data)}`);
          rejectAll(error);
          return;
        } else {
          if (resolvers.length > 0) {
            console.log('resolving immediately');
            const resolver = resolvers.shift();
            if (resolver) {
              resolver.resolve({ done: false, value: safeMsg.data });
            }
          } else {
            console.log('queueing message');
            messageQueue.push(safeMsg.data);
          }
        }
      } catch (err) {
        error = err instanceof Error ? err : new Error('Unknown error');
        rejectAll(error);
      }
    };

    const closeHandler = () => {
      finished = true;
      resolveAll();
    };

    const errorHandler = (...args: unknown[]) => {
      const err = args[0] as Error;
      error = new Error(`WebSocket error: ${err.message || 'Unknown error'}`);
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