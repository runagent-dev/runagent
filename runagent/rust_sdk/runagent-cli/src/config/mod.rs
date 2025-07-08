//! Configuration management for the RunAgent CLI
//!
//! This module handles CLI-specific configuration that extends
//! the base SDK configuration with CLI-specific settings.

pub mod cli_config;

// Re-export the main config type
pub use cli_config::CliConfig;