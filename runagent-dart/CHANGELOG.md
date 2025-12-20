# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.43] - 2024-XX-XX

### Added
- Support for `userId` parameter in `RunAgentClientConfig` for persistent storage
- Support for `persistentMemory` parameter in `RunAgentClientConfig` to enable persistent memory across agent executions
- `userId` and `persistentMemory` are now passed through REST and WebSocket clients to the backend API

### Changed
- `RunAgentClientConfig` now includes optional `userId` and `persistentMemory` fields
- `RestClient.runAgent()` now accepts and forwards `userId` and `persistentMemory` parameters
- `SocketClient.runStream()` now accepts and forwards `userId` and `persistentMemory` parameters

## [0.1.41] - 2024-XX-XX

### Added
- Initial release of RunAgent Dart SDK
- Support for REST and WebSocket communication with deployed AI agents
- `RunAgentClient` with support for local and cloud agents
- Streaming and non-streaming execution modes
- Type definitions for agent configuration and architecture
- Error handling with custom error types
- Unit tests for core type definitions

### Features
- REST client for synchronous agent execution
- WebSocket client for streaming agent execution
- Local agent support with registry lookup
- Cloud agent support with API key authentication
- Agent architecture introspection
- Comprehensive error handling

