export interface RunAgentConfig {
    agentId: string;
    entrypointTag: string;
    local?: boolean;
    host?: string;
    port?: number;
    apiKey?: string;
    baseUrl?: string;
    baseSocketUrl?: string;
    apiPrefix?: string;
  }
  
export interface ApiResponse<T = unknown> {
    success: boolean;
    output_data?: T;
    error?: string;
    data?: T;
  }
  
export interface WebSocketMessage<T = unknown> {
    id: string;
    type: string;
    timestamp: string;
    data: T;
    metadata?: Record<string, unknown>;
    error?: string;
  }
  
export interface AgentArchitecture {
    entrypoints: Array<{
      tag: string;
      name?: string;
      description?: string;
    }>;
  }
  
export interface ExecutionRequest {
    action: string;
    agent_id: string;
    input_data: {
      input_args: unknown[];
      input_kwargs: Record<string, unknown>;
    };
  }
  
export interface SerializedObject {
    content: unknown;
    strategy: 'direct' | 'object_extract' | 'string_repr' | 'error_fallback';
    className?: string;
    type?: string;
    error?: string;
  }
  
export type JsonValue = 
    | string 
    | number 
    | boolean 
    | null 
    | undefined
    | JsonValue[] 
    | { [key: string]: JsonValue };
  
export interface RequestOptions {
    data?: JsonValue;
    params?: Record<string, string>;
    headers?: Record<string, string>;
    timeout?: number;
    handleErrors?: boolean;
  }