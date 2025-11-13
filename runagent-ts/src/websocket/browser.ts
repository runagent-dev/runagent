import { BaseWebSocketClient } from './base.js';
import { RunAgentExecutionError } from '../errors/index.js';


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
  createWebSocket(
    url: string,
    _headers?: Record<string, string>
  ): WebSocket {
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
        const streamMessage = this.parseStreamMessage(event.data as string);

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

    const errorHandler = (err: Event) => {
      error = new RunAgentExecutionError(
        'CONNECTION_ERROR',
        this.cleanErrorMessage(err.toString())
      );
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