import { HttpHandler } from '../http/index.js';
import {
  AuthenticationError,
  ClientError,
  ConnectionError,
  ServerError,
  ValidationError,
} from '../errors/index.js';
import type { ApiResponse, AgentArchitecture, JsonValue } from '../types/index.js';

interface RunAgentOptions {
  inputArgs?: unknown[];
  inputKwargs?: Record<string, unknown>;
  timeoutSeconds?: number;
}

interface RestClientConfig {
  baseUrl?: string;
  apiKey?: string;
  apiPrefix?: string;
  isLocal?: boolean;
  timeoutSeconds?: number;
}

export class RestClient {
  private http: HttpHandler;
  private baseUrl: string;
  private apiKey?: string;
  private defaultTimeoutSeconds: number;

  constructor(options: RestClientConfig = {}) {
    const {
      baseUrl = 'http://localhost:8080',
      apiKey,
      apiPrefix = '/api/v1',
      isLocal = true,
      timeoutSeconds = 300,
    } = options;

    this.baseUrl = baseUrl.replace(/\/$/, '') + apiPrefix;
    this.apiKey = apiKey;
    this.defaultTimeoutSeconds = timeoutSeconds;
    this.http = new HttpHandler(this.apiKey, this.baseUrl, isLocal);
  }

  async runAgent(
    agentId: string,
    entrypointTag: string,
    options: RunAgentOptions = {}
  ): Promise<ApiResponse> {
    const {
      inputArgs = [],
      inputKwargs = {},
      timeoutSeconds = this.defaultTimeoutSeconds,
    } = options;

    const requestData = {
      entrypoint_tag: entrypointTag,
      input_args: inputArgs,
      input_kwargs: inputKwargs,
      timeout_seconds: timeoutSeconds,
      async_execution: false,
    } as JsonValue;

    const timeoutMs = timeoutSeconds * 1000 + 10_000; // Add buffer similar to Python SDK

    try {
      const response = await this.http.post(
        `/agents/${agentId}/run`,
        requestData,
        { timeout: timeoutMs }
      );

      return (await response.json()) as ApiResponse;
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';

      if (error instanceof AuthenticationError) {
        const code =
          error.statusCode === 403 ? 'PERMISSION_ERROR' : 'AUTHENTICATION_ERROR';
        return {
          success: false,
          error: {
            code,
            message: errorMessage,
          },
        };
      }

      if (error instanceof ValidationError) {
        return {
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: errorMessage,
          },
        };
      }

      if (error instanceof ConnectionError) {
        return {
          success: false,
          error: {
            code: 'CONNECTION_ERROR',
            message: errorMessage,
          },
        };
      }

      if (error instanceof ServerError) {
        return {
          success: false,
          error: {
            code: 'SERVER_ERROR',
            message: errorMessage,
          },
        };
      }

      if (error instanceof ClientError) {
        return {
          success: false,
          error: {
            code: 'CLIENT_ERROR',
            message: errorMessage,
          },
        };
      }

      return {
        success: false,
        error: {
          code: 'UNKNOWN_ERROR',
          message: errorMessage,
        },
      };
    }
  }

  async getAgentArchitecture(agentId: string): Promise<AgentArchitecture> {
    try {
      const response = await this.http.get(`/agents/${agentId}/architecture`);
      return (await response.json()) as AgentArchitecture;
    } catch (error) {
      throw new Error(
        `Failed to get architecture: ${
          error instanceof Error ? error.message : 'Unknown error'
        }`
      );
    }
  }

  close(): void {
    // HTTP handler cleanup if needed
  }
}