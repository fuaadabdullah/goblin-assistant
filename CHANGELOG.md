# Changelog

All notable changes to Goblin Assistant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **WorkflowBuilder Component**: Visual orchestration workflow creation with drag-and-drop step management
  - Goblin selection dropdown with available AI assistants
  - Task input fields for specifying what each goblin should do
  - Condition handling (THEN/AND/IF_SUCCESS/IF_FAILURE) between steps
  - Step reordering and management capabilities
  - Automatic orchestration syntax generation from visual steps

- **CostEstimationPanel Component**: Pre-execution cost estimation and budget planning
  - Real-time cost calculation before running workflows
  - Step-by-step cost breakdown for orchestration tasks
  - Provider-specific pricing integration
  - Token estimation based on orchestration text and code input
  - Transparent cost visibility to help users manage budgets

- **Backend Cost Estimation**: New Tauri command for accurate cost calculation
  - `estimate_cost` IPC command in Rust backend
  - Token estimation logic with provider-specific pricing tables
  - Integration with existing cost tracking system

- **Comprehensive E2E Test Suite**: End-to-end testing for core workflows
  - Streaming execution flow tests (UI → backend → cost updates)
  - Cost estimation validation tests
  - Error handling and graceful degradation tests
  - Multi-execution cost accumulation tests
  - Playwright-based testing framework

- **UX Polish Features**: Enhanced user experience improvements
  - Visual workflow building interface
  - Pre-execution cost transparency
  - Improved component accessibility with ARIA labels
  - Better error handling and user feedback

### Security Enhancements

- **Multi-Layer Secret Scanning**: Comprehensive security implementation across the entire system
  - **Request-Level Protection**: Scans user prompts before queuing requests
  - **Worker-Level Safety**: Double-checks prompts before sending to AI providers
  - **Document Indexing Security**: Automatic redaction during ChromaDB indexing
  - **Comprehensive Detection**: API keys, passwords, tokens, certificates, private keys, and credentials

- **Security Event Logging**: Complete audit trail and monitoring
  - Security violation tracking with Datadog metrics
  - Detailed logging of detection points and secret types
  - Privacy-preserving user data hashing
  - Enterprise-grade security event management

- **Privacy Protection Features**: Enhanced data protection and compliance
  - User ID hashing for privacy in logs and metrics
  - Secure credential management and storage
  - Data minimization and retention policies
  - Compliance-ready security architecture

### Technical Improvements

- **Type Safety**: Fixed all TypeScript compilation errors (24 issues resolved)
  - Unused variable cleanup across all components
  - Chart component type fixes for Recharts integration
  - Datadog integration with graceful fallbacks for missing modules
  - Proper type casting for cost and chart data

- **Code Quality**: Enhanced maintainability and reliability
  - Comprehensive linting fixes
  - Improved error handling in async operations
  - Better separation of concerns in component architecture

### Changed

- Enhanced README with screenshots section and improved navigation
- Updated wiki documentation with visual references

## [1.0.0] - 2024-01-XX

- Initial release of Goblin Assistant
- Multi-provider AI chat interface (31+ providers supported)
- Desktop application built with Tauri + React + TypeScript
- FastAPI backend for AI routing and business logic
- Secure API key management with system keychain integration
- Modern UI with dark mode support
- Cross-platform support (macOS, Windows, Linux)
- Web version for browser-based usage

### Features

- **AI Provider Integration**: Support for OpenAI, Anthropic, Google Gemini, and 28+ other providers
- **Smart Routing**: Intelligent provider selection based on model capabilities and user preferences
- **Conversation Management**: Persistent chat history and context awareness
- **Security First**: Encrypted API key storage and secure communication
- **Performance Optimized**: Fast response times with efficient caching
- **User Experience**: Intuitive interface with keyboard shortcuts and accessibility features

### Technical Stack

- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Backend**: FastAPI (Python), async/await architecture
- **Desktop**: Tauri (Rust) for native performance
- **Database**: SQLite for local data storage
- **Security**: System keychain integration, TLS encryption

---

## Types of changes

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities

## Versioning

This project uses [Semantic Versioning](https://semver.org/). For the versions available, see the [tags on this repository](https://github.com/yourusername/goblin-assistant/tags).

