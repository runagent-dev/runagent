import { BaseWebSocketClient } from './base.js';


// declare global {
//     interface WebSocket {
//         readonly OPEN: number;
//         readyState: number;
//         onopen: ((event: Event) => void) | null;
//         onclose: ((event: CloseEvent) => void) | null;
//         onerror: ((event: Event) => void) | null;
//         onmessage: ((event: MessageEvent) => void) | null;
//         send(data: string): void;
//         close(): void;
//         addEventListener(type: 'message', listener: (event: MessageEvent) => void): void;
//         addEventListener(type: 'close', listener: (event: CloseEvent) => void): void;
//         addEventListener(type: 'error', listener: (event: Event) => void): void;
//         addEventListener(type: string, listener: (event: Event) => void): void;
//     }
    
//     interface MessageEvent {
//       data: string;
//     }
//     interface CloseEvent extends Event {
//         code: number;
//         reason: string;
//         wasClean: boolean;
//       }
//     const WebSocket: {
//       new (url: string): WebSocket;
//       readonly OPEN: number;
//     };
//   }


interface IteratorResolverItem {
  resolve: (value: { done: boolean; value?: unknown }) => void;
  reject: (error: Error) => void;
}

export class BrowserWebSocketClient extends BaseWebSocketClient {
  createWebSocket(url: string): WebSocket {
    return new WebSocket(url);
  }

  protected async waitForConnection(websocket: unknown): Promise<void> {
    const ws = websocket as WebSocket;
    return new Promise((resolve, reject) => {
      ws.onopen = () => resolve();
      ws.onerror = (error: Event) =>
        reject(new Error(`WebSocket connection failed: ${error}`));
    });
  }

  protected sendMessage(websocket: unknown, message: string): void {
    const ws = websocket as WebSocket;
    ws.send(message);
  }

  protected isWebSocketOpen(websocket: unknown): boolean {
    const ws = websocket as WebSocket;
    return ws.readyState === WebSocket.OPEN;
  }

  protected closeWebSocket(websocket: unknown): void {
    const ws = websocket as WebSocket;
    ws.close();
  }

  protected async *createWebSocketIterator(websocket: unknown): AsyncGenerator<unknown, void, unknown> {
    const ws = websocket as WebSocket;
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

    const messageHandler = (event: MessageEvent) => {
      try {
        console.log('received=> ', event.data);
        const safeMsg = this.serializer.deserializeMessage(event.data as string);

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

    const errorHandler = (err: Event) => {
      error = new Error(`WebSocket error: ${err}`);
      rejectAll(error);
    };

    ws.addEventListener('message', messageHandler);
    ws.addEventListener('close', closeHandler);
    ws.addEventListener('error', errorHandler);

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