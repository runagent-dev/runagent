//! Local server components for testing deployed agents
//!
//! This module provides a FastAPI-like local server implementation for testing
//! AI agents locally before deploying to production.

pub mod handlers;
pub mod local_server;

// Re-export main server
pub use local_server::LocalServer;