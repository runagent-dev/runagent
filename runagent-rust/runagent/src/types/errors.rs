//! Error types for the RunAgent SDK

use serde_json::Value;
use std::fmt;
use thiserror::Error;

/// Main error type for the RunAgent SDK
#[derive(Error, Debug)]
pub enum RunAgentError {
    /// Authentication and authorization errors
    #[error("Authentication error: {message}")]
    Authentication { message: String },

    /// Input validation errors
    #[error("Validation error: {message}")]
    Validation { message: String },

    /// Network and connection errors
    #[error("Connection error: {message}")]
    Connection { message: String },

    /// Server-side errors
    #[error("Server error: {message}")]
    Server { message: String },

    /// Template-related errors
    #[error("Template error: {message}")]
    Template { message: String },

    /// Deployment-related errors
    #[error("Deployment error: {message}")]
    Deployment { message: String },

    /// Database-related errors
    #[error("Database error: {message}")]
    Database { message: String },

    /// Configuration errors
    #[error("Configuration error: {message}")]
    Config { message: String },

    /// Execution/SDK errors with structured details
    #[error("{code}: {message}")]
    Execution {
        code: String,
        message: String,
        suggestion: Option<String>,
        details: Option<Value>,
    },

    /// IO errors
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// JSON serialization/deserialization errors
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    /// HTTP request errors
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),

    /// Generic error with context
    #[error("RunAgent error: {message}")]
    Generic { message: String },
}

impl RunAgentError {
    /// Create a new authentication error
    pub fn authentication<S: Into<String>>(message: S) -> Self {
        Self::Authentication {
            message: message.into(),
        }
    }

    /// Create a new validation error
    pub fn validation<S: Into<String>>(message: S) -> Self {
        Self::Validation {
            message: message.into(),
        }
    }

    /// Create a new connection error
    pub fn connection<S: Into<String>>(message: S) -> Self {
        Self::Connection {
            message: message.into(),
        }
    }

    /// Create a new server error
    pub fn server<S: Into<String>>(message: S) -> Self {
        Self::Server {
            message: message.into(),
        }
    }

    /// Create a new template error
    pub fn template<S: Into<String>>(message: S) -> Self {
        Self::Template {
            message: message.into(),
        }
    }

    /// Create a new deployment error
    pub fn deployment<S: Into<String>>(message: S) -> Self {
        Self::Deployment {
            message: message.into(),
        }
    }

    /// Create a new database error
    pub fn database<S: Into<String>>(message: S) -> Self {
        Self::Database {
            message: message.into(),
        }
    }

    /// Create a new configuration error
    pub fn config<S: Into<String>>(message: S) -> Self {
        Self::Config {
            message: message.into(),
        }
    }

    /// Create a new execution error with structured metadata
    pub fn execution<S: Into<String>>(
        code: S,
        message: S,
        suggestion: Option<String>,
        details: Option<Value>,
    ) -> Self {
        Self::Execution {
            code: code.into(),
            message: message.into(),
            suggestion,
            details,
        }
    }

    /// Create a new generic error
    pub fn generic<S: Into<String>>(message: S) -> Self {
        Self::Generic {
            message: message.into(),
        }
    }

    /// Get the error category as a string
    pub fn category(&self) -> &'static str {
        match self {
            Self::Authentication { .. } => "authentication",
            Self::Validation { .. } => "validation",
            Self::Connection { .. } => "connection",
            Self::Server { .. } => "server",
            Self::Template { .. } => "template",
            Self::Deployment { .. } => "deployment",
            Self::Database { .. } => "database",
            Self::Config { .. } => "config",
            Self::Execution { .. } => "execution",
            Self::Io(_) => "io",
            Self::Json(_) => "json",
            Self::Http(_) => "http",
            Self::Generic { .. } => "generic",
        }
    }

    /// Check if the error is retryable
    pub fn is_retryable(&self) -> bool {
        matches!(
            self,
            Self::Connection { .. } | Self::Server { .. } | Self::Http(_)
        ) || matches!(self, Self::Execution { code, .. } if code == "CONNECTION_ERROR" || code == "SERVER_ERROR")
    }
}

/// Result type alias for RunAgent operations
pub type RunAgentResult<T> = Result<T, RunAgentError>;

/// HTTP-specific error details
#[derive(Debug, Clone)]
pub struct HttpErrorDetails {
    pub status_code: Option<u16>,
    pub headers: std::collections::HashMap<String, String>,
    pub body: Option<String>,
}

impl fmt::Display for HttpErrorDetails {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "HTTP Error")?;
        if let Some(status) = self.status_code {
            write!(f, " {}", status)?;
        }
        if let Some(body) = &self.body {
            write!(f, ": {}", body)?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_creation() {
        let err = RunAgentError::authentication("Invalid API key");
        assert_eq!(err.category(), "authentication");
        assert!(!err.is_retryable());
    }

    #[test]
    fn test_error_categories() {
        let validation_err = RunAgentError::validation("Invalid input");
        assert_eq!(validation_err.category(), "validation");

        let connection_err = RunAgentError::connection("Network timeout");
        assert_eq!(connection_err.category(), "connection");
        assert!(connection_err.is_retryable());
    }

    #[test]
    fn test_error_display() {
        let err = RunAgentError::server("Internal server error");
        let error_string = format!("{}", err);
        assert!(error_string.contains("Server error"));
        assert!(error_string.contains("Internal server error"));
    }
}