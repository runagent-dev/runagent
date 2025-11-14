import { 
    HttpException, 
    AuthenticationError, 
    ValidationError, 
    ClientError, 
    ServerError, 
    ConnectionError 
  } from '../errors/index.js';
  import type { RequestOptions, JsonValue } from '../types/index.js';
  
  // declare global {
  //   interface Response {
  //     status: number;
  //     statusText: string;
  //     ok: boolean;
  //     json(): Promise<unknown>;
  //     text(): Promise<string>;
  //   }
    
  //   interface RequestInit {
  //     method?: string;
  //     headers?: Record<string, string>;
  //     body?: string;
  //     signal?: AbortSignal;
  //   }
    
  //   function fetch(url: string, init?: RequestInit): Promise<Response>;
  // }
  
export class HttpHandler {
  private apiKey?: string;
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;

  constructor(apiKey?: string, baseUrl: string = '', _isLocal = true) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl.replace(/\/$/, '');

    this.defaultHeaders = {
      accept: 'application/json',
      'content-type': 'application/json',
      'User-Agent': 'RunAgent-TS/1.0',
    };

    if (this.apiKey) {
      this.defaultHeaders['Authorization'] = `Bearer ${this.apiKey}`;
    }
  }
  
    private _getUrl(path: string): string {
      return `${this.baseUrl}/${path.replace(/^\//, '')}`;
    }
  
    private async _handleErrorResponse(response: Response): Promise<never> {
      let errorMessage = `HTTP Error: ${response.status}`;
  
      try {
        const errorData = await response.json() as Record<string, unknown>;
        if (errorData && typeof errorData === 'object') {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (typeof errorData.message === 'string') {
            errorMessage = errorData.message;
          } else if (typeof errorData.error === 'string') {
            errorMessage = errorData.error;
          }
        }
      } catch (e) {
        const text = await response.text();
        if (text) {
          errorMessage = text;
        }
      }
  
      if (response.status === 401) {
        throw new AuthenticationError(errorMessage, response.status, response);
      } else if (response.status === 403) {
        throw new AuthenticationError(`Access denied: ${errorMessage}`, response.status, response);
      } else if (response.status === 400 || response.status === 422) {
        throw new ValidationError(errorMessage, response.status, response);
      } else if (response.status >= 400 && response.status < 500) {
        throw new ClientError(errorMessage, response.status, response);
      } else {
        throw new ServerError(`Server error: ${errorMessage}`, response.status, response);
      }
    }
  
    private async _request(
      method: string,
      path: string,
      options: RequestOptions = {}
    ): Promise<Response> {
      const {
        data = null,
        params = null,
        headers = null,
        timeout = 30000,
        handleErrors = true,
      } = options;
  
      const url = this._getUrl(path);
  
      const requestHeaders = { ...this.defaultHeaders };
      if (headers) {
        Object.assign(requestHeaders, headers);
      }
  
      const urlWithParams = params
        ? `${url}?${new URLSearchParams(params).toString()}`
        : url;
  
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
  
      const fetchOptions: RequestInit = {
        method: method.toUpperCase(),
        headers: requestHeaders,
        signal: controller.signal,
      };
  
      if (data && !['GET', 'DELETE'].includes(method.toUpperCase())) {
        fetchOptions.body = JSON.stringify(data);
      }
  
      try {
        const response = await fetch(urlWithParams, fetchOptions);
        clearTimeout(timeoutId);
  
        if (response.status >= 400) {
          if (handleErrors) {
            await this._handleErrorResponse(response);
          } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }
        }
  
        return response;
      } catch (error) {
        clearTimeout(timeoutId);
  
        if (error instanceof Error && error.name === 'AbortError') {
          throw new ConnectionError(`Request to ${url} timed out after ${timeout}ms`);
        } else if (error instanceof Error && error.message.includes('fetch')) {
          throw new ConnectionError(
            `Failed to connect to ${this.baseUrl}. Please check your connection.`
          );
        } else if (error instanceof HttpException) {
          throw error;
        } else {
          if (!handleErrors) {
            throw error;
          }
          throw new ClientError(`Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      }
    }
  
    async get(path: string, options: Omit<RequestOptions, 'data'> = {}): Promise<Response> {
      return this._request('GET', path, options);
    }
  
    async post(path: string, data?: JsonValue, options: Omit<RequestOptions, 'data'> = {}): Promise<Response> {
      return this._request('POST', path, { ...options, data });
    }
  
    async put(path: string, data?: JsonValue, options: Omit<RequestOptions, 'data'> = {}): Promise<Response> {
      return this._request('PUT', path, { ...options, data });
    }
  
    async delete(path: string, options: Omit<RequestOptions, 'data'> = {}): Promise<Response> {
      return this._request('DELETE', path, options);
    }
  
    async patch(path: string, data?: JsonValue, options: Omit<RequestOptions, 'data'> = {}): Promise<Response> {
      return this._request('PATCH', path, { ...options, data });
    }
  }