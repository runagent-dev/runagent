# Changelog

All notable changes to the RunAgent PHP SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-11-27

### Added
- Initial release of RunAgent PHP SDK
- `RunAgentClient` class with `run()` and `runStream()` methods
- REST client for non-streaming agent execution
- WebSocket client for streaming agent execution
- Complete error taxonomy (AUTHENTICATION_ERROR, VALIDATION_ERROR, etc.)
- Configuration precedence: explicit > env > defaults
- Support for local and remote agent deployments
- WordPress integration support and example plugin
- Streaming and non-streaming guardrails
- Architecture validation with entrypoint checking
- Extra params support for future metadata features
- Comprehensive documentation and examples
- PSR-4 autoloading
- Composer package configuration

### Features
- **Local Agent Support**: Connect to locally running agents with optional database discovery
- **Remote Agent Support**: Connect to cloud-deployed agents with Bearer token authentication
- **Streaming**: Full WebSocket streaming support with Generator-based API
- **Error Handling**: Structured error responses with code, message, suggestion, and details
- **WordPress Compatible**: Designed to work seamlessly in WordPress environments
- **Configuration Flexibility**: Multiple ways to configure (constructor, env vars, defaults)
- **Architecture Introspection**: Query agent architecture and available entrypoints
- **Health Checks**: Built-in health check endpoint support

### Examples
- `basic_example.php` - Basic remote agent usage
- `local_example.php` - Local agent with health check
- `streaming_example.php` - Streaming responses with WebSocket
- `wordpress_plugin_example.php` - Complete WordPress plugin implementation

### Documentation
- Comprehensive README with installation, configuration, and usage instructions
- PUBLISH.md with packaging and release instructions
- Inline code documentation following PHPDoc standards
- WordPress integration guide

[Unreleased]: https://github.com/runagent/runagent/compare/runagent-php-v0.1.0...HEAD
[0.1.0]: https://github.com/runagent/runagent/releases/tag/runagent-php-v0.1.0
