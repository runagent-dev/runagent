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
  timeoutSeconds?: number;
  extraParams?: Record<string, unknown>;
  enableRegistry?: boolean;
}
  
export interface ApiResponse<T = JsonValue> {
  success: boolean;
  data?: T;
  output_data?: T;
  error?:
    | string
    | {
        code?: string;
        message?: string;
        suggestion?: string | null;
        details?: unknown;
        field?: string | null;
      };
  message?: string | null;
  timestamp?: string | null;
  request_id?: string | null;
}
  
export interface WebSocketMessage<T = unknown> {
    id: string;
    type: string;
    timestamp: string;
    data: T;
    metadata?: Record<string, unknown>;
    error?: string;
  }
  
export interface AgentEntrypoint {
  tag: string;
  name?: string;
  description?: string;
  file?: string;
  module?: string;
  extractor?: Record<string, unknown>;
}

export interface AgentArchitecture {
  agent_id?: string;
  agentId?: string;
  entrypoints: AgentEntrypoint[];
}
  
export interface ExecutionRequest {
  entrypoint_tag: string;
  input_args: unknown[];
  input_kwargs: Record<string, unknown>;
  timeout_seconds?: number;
  async_execution?: boolean;
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