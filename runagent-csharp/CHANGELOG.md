# Changelog

All notable changes to the RunAgent C# SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.48] - 2026-02-03

### Fixed
- Fixed `Extractor` field type in `EntryPoint` class to support both string and object types from local server
- Fixed JSON deserialization for non-streaming responses when data is returned as JSON-encoded string
- Improved compatibility with local RunAgent server responses

## [0.1.47] - 2025-02-03

### Added
- Initial release of RunAgent C# SDK
- `RunAgentClient` with async/await support
- Support for both local and remote agent deployments
- REST API client for synchronous execution
- WebSocket client for streaming execution
- Comprehensive error handling with structured error types
- Persistent memory support with user isolation
- Configuration builder with fluent API
- Environment variable resolution
- Architecture discovery and entrypoint validation
- Stream vs non-stream entrypoint guardrails
- Health check functionality
- Complete documentation and examples

### Features
- **RunAgentClientConfig**: Fluent configuration builder
- **RunAgentClient**: Main client with initialization and execution
- **RestClient**: HTTP-based API interactions
- **SocketClient**: WebSocket streaming support
- **Error Taxonomy**: AuthenticationError, ValidationError, ConnectionError, ServerError, RunAgentExecutionError
- **Configuration Precedence**: Constructor args > Environment variables > Defaults
- **Persistent Memory**: User-scoped memory across executions
- **Multi-Framework Support**: Works with LangGraph, CrewAI, Letta, and all Python frameworks

### Examples
- BasicExample: Non-streaming agent execution
- StreamingExample: Real-time streaming responses
- LocalExample: Local agent deployment
- PersistentMemoryExample: Stateful interactions

### Dependencies
- .NET 6.0 or higher
- System.Text.Json 8.0.0

### Documentation
- Comprehensive README with quickstart guide
- Configuration reference table
- Error handling guide
- API reference
- Troubleshooting section
- Security best practices

## [Unreleased]

### Planned
- SQLite database support for local agent discovery
- Connection pooling and retry logic
- Request/response middleware hooks
- Enhanced logging and telemetry
- Support for .NET Framework 4.8+
- Additional examples and tutorials
