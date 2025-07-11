interface ResponseLike {
    status: number;
    statusText: string;
    ok: boolean;
  }
  
export class HttpException extends Error {
    public statusCode?: number;
    public response?: ResponseLike;
  
    constructor(message: string, statusCode?: number, response?: ResponseLike) {
      super(message);
      this.name = 'HttpException';
      this.statusCode = statusCode;
      this.response = response;
    }
  }
  
  export class ClientError extends HttpException {
    constructor(message: string, statusCode?: number, response?: ResponseLike) {
      super(message, statusCode, response);
      this.name = 'ClientError';
    }
  }
  
  export class ServerError extends HttpException {
    constructor(message: string, statusCode?: number, response?: ResponseLike) {
      super(message, statusCode, response);
      this.name = 'ServerError';
    }
  }
  
  export class AuthenticationError extends ClientError {
    constructor(message: string, statusCode?: number, response?: ResponseLike) {
      super(message, statusCode, response);
      this.name = 'AuthenticationError';
    }
  }
  
  export class ValidationError extends ClientError {
    constructor(message: string, statusCode?: number, response?: ResponseLike) {
      super(message, statusCode, response);
      this.name = 'ValidationError';
    }
  }
  
  export class ConnectionError extends HttpException {
    constructor(message: string, statusCode?: number, response?: ResponseLike) {
      super(message, statusCode, response);
      this.name = 'ConnectionError';
    }
  }