import type { WebSocketMessage, SerializedObject, JsonValue } from '../types/index.js';

export class CoreSerializer {
//   private maxSizeBytes: number;

//   constructor(maxSizeMb: number = 10.0) {
//     this.maxSizeBytes = Math.floor(maxSizeMb * 1024 * 1024);
//   }

  serializeObject(obj: unknown): string {
    try {
      const serializedJson = this._trySerializeStrategies(obj);
      return JSON.stringify(serializedJson);
    } catch (error) {
      console.error('Core serialization failed:', error);
      const fallback: SerializedObject = {
        content: `<Serialization Error: ${error instanceof Error ? error.message : 'Unknown error'}>`,
        strategy: 'error_fallback',
        type: typeof obj,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
      return JSON.stringify(fallback);
    }
  }

  deserializeObject(jsonResp: string | JsonValue, reconstruct: boolean = false): unknown {
    try {
      const deserializedData = typeof jsonResp === 'string' ? JSON.parse(jsonResp) : jsonResp;

      if (
        deserializedData &&
        typeof deserializedData === 'object' &&
        deserializedData !== null &&
        'type' in (deserializedData as Record<string, unknown>) &&
        'payload' in (deserializedData as Record<string, unknown>)
      ) {
        const structured = deserializedData as { type?: string; payload?: unknown };
        const payload = structured.payload;

        if (typeof payload === 'string') {
          try {
            const parsedPayload = JSON.parse(payload);
            return this._reconstructNestedJson(parsedPayload);
          } catch {
            return payload;
          }
        }

        return this._reconstructNestedJson(payload);
      }

      if (!reconstruct) {
        return this._reconstructNestedJson(
          (deserializedData as Record<string, unknown>)?.content || deserializedData
        );
      }

      return this._reconstructObject(deserializedData);
    } catch (error) {
      console.error('Deserialization failed:', error);
      throw new Error(`Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  serializeMessage(message: Partial<WebSocketMessage>): string {
    try {
      const messageDict = {
        id: message.id || 'unknown',
        type: message.type || 'unknown',
        timestamp: message.timestamp || new Date().toISOString(),
        data: message.data,
        metadata: message.metadata || null,
      };

      if (messageDict.data) {
        messageDict.data = this._deepSerializeValue(messageDict.data);
      }

      if (messageDict.metadata) {
        messageDict.metadata = this._deepSerializeValue(messageDict.metadata) as Record<string, unknown>;
      }

      return JSON.stringify(messageDict);
    } catch (error) {
      console.error('Message serialization failed:', error);
      const fallback = {
        id: message.id || 'unknown',
        type: message.type || 'unknown',
        timestamp: message.timestamp || new Date().toISOString(),
        data: { error: `Serialization failed: ${error instanceof Error ? error.message : 'Unknown error'}` },
        metadata: null,
        error: `Serialization Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      };
      return JSON.stringify(fallback);
    }
  }

  deserializeMessage(jsonStr: string): WebSocketMessage {
    try {
      const deserializedData = JSON.parse(jsonStr) as Record<string, unknown>;

      if (typeof deserializedData !== 'object' || deserializedData === null) {
        throw new Error('JSON must deserialize to an object');
      }

      if (deserializedData.data) {
        deserializedData.data = this._reconstructNestedJson(deserializedData.data);
      }

      if (deserializedData.metadata) {
        deserializedData.metadata = this._reconstructNestedJson(deserializedData.metadata) as Record<string, unknown>;
      }

      return {
        id: deserializedData.id as string,
        type: deserializedData.type as string,
        timestamp: deserializedData.timestamp as string,
        data: deserializedData.data,
        metadata: deserializedData.metadata as Record<string, unknown>,
        error: deserializedData.error as string,
      };
    } catch (error) {
      console.error('Message deserialization failed:', error);
      throw new Error(`Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private _deepSerializeValue(value: unknown): JsonValue {
    if (value === null || value === undefined) {
        return value as JsonValue;
      }

    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return value;
    }

    if (Array.isArray(value)) {
      return value.map((item) => this._deepSerializeValue(item));
    }

    if (typeof value === 'object' && value !== null) {
      const result: Record<string, JsonValue> = {};
      for (const [key, val] of Object.entries(value)) {
        result[key] = this._deepSerializeValue(val);
      }
      return result;
    }

    return String(value);
  }

  private _reconstructNestedJson(data: unknown): unknown {
    if (data === null || data === undefined) {
      return data;
    }

    if (Array.isArray(data)) {
      return data.map((item) => this._reconstructNestedJson(item));
    }

    if (typeof data === 'object' && data !== null) {
      const result: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(data)) {
        result[key] = this._reconstructNestedJson(value);
      }
      return result;
    }

    return data;
  }

  private _reconstructObject(data: unknown): unknown {
    if (typeof data !== 'object' || data === null) {
      return this._reconstructNestedJson(data);
    }

    const serializedData = data as SerializedObject;
    const strategy = serializedData.strategy;
    const content = serializedData.content;

    if (strategy === 'direct') {
      return this._reconstructNestedJson(content);
    }

    return this._reconstructNestedJson(data);
  }

  private _trySerializeStrategies(obj: unknown): SerializedObject {
    if (obj === null || obj === undefined) {
      return { content: obj, strategy: 'direct' };
    }

    try {
      JSON.stringify(obj);
      return { content: obj, strategy: 'direct' };
    } catch (error) {
      if (typeof obj === 'object' && obj !== null) {
        try {
          const content = this._safeObjectExtract(obj);
          return {
            content: content,
            strategy: 'object_extract',
            className: (obj as { constructor: { name: string } }).constructor.name,
          };
        } catch (error) {
          // Fallback to string representation
        }
      }

      return {
        content: String(obj),
        strategy: 'string_repr',
        type: typeof obj,
      };
    }
  }

  private _safeObjectExtract(obj: unknown): Record<string, JsonValue> {
    if (typeof obj !== 'object' || obj === null) {
      return { value: this._deepSerializeValue(obj) };
    }

    const result: Record<string, JsonValue> = {};
    for (const [key, value] of Object.entries(obj)) {
      try {
        JSON.stringify(value);
        result[key] = this._deepSerializeValue(value);
      } catch (error) {
        result[key] = this._deepSerializeValue(value);
      }
    }
    return result;
  }
}