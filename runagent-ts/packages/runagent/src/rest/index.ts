import { HttpHandler } from '../http/index.js';
import type { ApiResponse, AgentArchitecture, JsonValue } from '../types/index.js';

interface RunAgentOptions {
  inputArgs?: unknown[];
  inputKwargs?: Record<string, unknown>;
  executionType?: string;
}

interface RestClientConfig {
  baseUrl?: string;
  apiKey?: string;
  apiPrefix?: string;
}

export class RestClient {
  private http: HttpHandler;
  private baseUrl: string;
  private apiKey?: string;

  constructor(options: RestClientConfig = {}) {
    const { baseUrl = 'http://localhost:8080', apiKey, apiPrefix = '/api/v1' } = options;
    
    this.baseUrl = baseUrl.replace(/\/$/, '') + apiPrefix;
    this.apiKey = apiKey;
    this.http = new HttpHandler(this.apiKey, this.baseUrl);
  }

  async runAgent(
    agentId: string,
    entrypointTag: string,
    options: RunAgentOptions = {}
  ): Promise<ApiResponse> {
    const { inputArgs = null, inputKwargs = null } = options;

    try {
      console.log(`🤖 Executing agent: ${agentId}`);

      const requestData = {
        input_data: {
          input_args: inputArgs,
          input_kwargs: inputKwargs,
        },
      } as JsonValue;
      

      try {
        const response = await this.http.post(
          `/agents/${agentId}/execute/${entrypointTag}`,
          requestData,
          { timeout: 120000 }
        );

        const result = await response.json() as ApiResponse;

        if (result.success !== false) {
          console.log('✅ Agent execution completed!');
          return result;
        } else {
          console.log(`❌ Agent execution failed: ${result.error || 'Unknown error'}`);
          return result;
        }
      } catch (error) {
        return {
          success: false,
          error: `Agent execution failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        };
      }
    } catch (error) {
      return {
        success: false,
        error: `Execute agent failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      };
    }
  }

  async getAgentArchitecture(agentId: string): Promise<AgentArchitecture> {
    try {
      const response = await this.http.get(`/agents/${agentId}/architecture`);
      return response.json() as Promise<AgentArchitecture>;
    } catch (error) {
      throw new Error(`Failed to get architecture: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  close(): void {
    // HTTP handler cleanup if needed
  }
}