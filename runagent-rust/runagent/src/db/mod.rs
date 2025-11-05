//! Minimal database module for agent lookups
//!
//! This module provides a simple database interface for looking up local agent
//! metadata (host, port) by agent ID. This allows connecting to agents without
//! explicitly specifying the address.

pub mod service;

pub use service::DatabaseService;

