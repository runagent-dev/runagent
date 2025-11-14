import { HttpHandler } from '../http/index.js';
import {
  AuthenticationError,
  ClientError,
  ConnectionError,
  RunAgentExecutionError,
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
  private isLocal: boolean;

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
    this.isLocal = isLocal;
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
            suggestion:
              code === 'PERMISSION_ERROR'
                ? 'Verify the agent ID and ensure your API key has access to this agent.'
                : 'Check that RUNAGENT_API_KEY is set correctly and has not expired.',
          },
        };
      }

      if (error instanceof ValidationError) {
        return {
          success: false,
          error: {
            code: 'VALIDATION_ERROR',
            message: errorMessage,
            suggestion:
              'Inspect the input arguments and ensure they match the agent entrypoint schema.',
          },
        };
      }

      if (error instanceof ConnectionError) {
        return {
          success: false,
          error: {
            code: 'CONNECTION_ERROR',
            message: errorMessage,
            suggestion:
              'Check your network connection and confirm the RunAgent service URL is reachable.',
          },
        };
      }

      if (error instanceof ServerError) {
        return {
          success: false,
          error: {
            code: 'SERVER_ERROR',
            message: errorMessage,
            suggestion: 'Try the request again. If the issue persists, contact RunAgent support.',
          },
        };
      }

      if (error instanceof ClientError) {
        return {
          success: false,
          error: {
            code: 'CLIENT_ERROR',
            message: errorMessage,
            suggestion:
              'Review the request payload or configuration for potential mistakes.',
          },
        };
      }

      return {
        success: false,
        error: {
          code: 'UNKNOWN_ERROR',
          message: errorMessage,
          suggestion: 'Retry the request or inspect the agent logs for more detail.',
        },
      };
    }
  }

  async getAgentArchitecture(agentId: string): Promise<AgentArchitecture> {
    try {
      const response = await this.http.get(`/agents/${agentId}/architecture`);
      const parsed = (await response.json()) as
        | ApiResponse<AgentArchitecture>
        | AgentArchitecture;

      if (parsed && typeof parsed === 'object' && 'success' in parsed) {
        const envelope = parsed as ApiResponse<AgentArchitecture>;

        if (envelope.success === false) {
          const { code, message, suggestion, details } =
            this.extractArchitectureError(envelope);
          throw new RunAgentExecutionError(code, message, suggestion, details);
        }

        if (!envelope.data) {
          throw new RunAgentExecutionError(
            'ARCHITECTURE_MISSING',
            'Response did not include agent architecture data.'
          );
        }

        return this.normalizeArchitecture(envelope.data);
      }

      return this.normalizeArchitecture(parsed as AgentArchitecture);
    } catch (error) {
      if (error instanceof RunAgentExecutionError) {
        throw error;
      }

      if (error instanceof ClientError && error.statusCode === 404) {
        if (this.isLocal) {
          throw new RunAgentExecutionError(
            'AGENT_NOT_FOUND_LOCAL',
            `Agent ${agentId} is not registered in your local RunAgent database.`,
            "Start the agent locally with `runagent serve` or provide the agent's host and port."
          );
        }
        throw new RunAgentExecutionError(
          'AGENT_NOT_FOUND_REMOTE',
          `Agent ${agentId} was not found in RunAgent Cloud.`,
          'Confirm the agent ID in the dashboard or set `local: true` with host/port to call a local agent.'
        );
      }

      if (error instanceof AuthenticationError) {
        throw new RunAgentExecutionError(
          'AUTHENTICATION_ERROR',
          error.message,
          'Verify that RUNAGENT_API_KEY is set and valid.'
        );
      }

      if (error instanceof ValidationError) {
        throw new RunAgentExecutionError(
          'VALIDATION_ERROR',
          error.message,
          'Check the request configuration or agent settings.'
        );
      }

      if (error instanceof ConnectionError) {
        throw new RunAgentExecutionError(
          'CONNECTION_ERROR',
          error.message,
          'Ensure the RunAgent service URL is reachable.'
        );
      }

      if (error instanceof ServerError) {
        throw new RunAgentExecutionError(
          'SERVER_ERROR',
          error.message,
          'Try again later or contact support if the issue persists.'
        );
      }

      if (error instanceof ClientError) {
        throw new RunAgentExecutionError(
          'CLIENT_ERROR',
          error.message,
          'Review the request and agent configuration.'
        );
      }

      const message =
        error instanceof Error
          ? error.message
          : 'Failed to retrieve agent architecture.';

      throw new RunAgentExecutionError(
        this.isLocal
          ? 'ARCHITECTURE_FETCH_LOCAL_ERROR'
          : 'ARCHITECTURE_FETCH_REMOTE_ERROR',
        message,
        this.isLocal
          ? 'Ensure the agent is running locally or provide host/port explicitly.'
          : 'Verify the agent exists and that your API key/base URL are correct.'
      );
    }
  }

  private normalizeArchitecture(
    data?: AgentArchitecture
  ): AgentArchitecture {
    if (!data) {
      return { entrypoints: [] };
    }

    const agentId =
      data.agentId ??
      (data as AgentArchitecture & { agent_id?: string }).agent_id;

    const entrypoints = Array.isArray(data.entrypoints)
      ? data.entrypoints.map((entry) => ({ ...entry }))
      : [];

    return {
      ...data,
      agentId,
      agent_id:
        (data as AgentArchitecture & { agent_id?: string }).agent_id ?? agentId,
      entrypoints,
    };
  }

  private extractArchitectureError(
    envelope: ApiResponse<AgentArchitecture>
  ): {
    code: string;
    message: string;
    suggestion?: string | null;
    details?: unknown;
  } {
    const defaultCode = this.isLocal
      ? 'AGENT_NOT_FOUND_LOCAL'
      : 'AGENT_NOT_FOUND_REMOTE';

    if (!envelope.error) {
      return {
        code: defaultCode,
        message: envelope.message ?? 'Failed to retrieve agent architecture.',
        suggestion: this.isLocal
          ? 'Ensure the agent is running locally or provide host/port explicitly.'
          : 'Verify the agent exists and that your API key/base URL are correct.',
      };
    }

    if (typeof envelope.error === 'string') {
      return {
        code: defaultCode,
        message: envelope.error,
        suggestion: this.isLocal
          ? 'Ensure the agent is running locally or provide host/port explicitly.'
          : 'Verify the agent exists and that your API key/base URL are correct.',
      };
    }

    return {
      code: envelope.error.code ?? defaultCode,
      message:
        envelope.error.message ??
        envelope.message ??
        'Failed to retrieve agent architecture.',
      suggestion: envelope.error.suggestion ?? undefined,
      details: envelope.error.details,
    };
  }

  close(): void {
    // HTTP handler cleanup if needed
  }
}