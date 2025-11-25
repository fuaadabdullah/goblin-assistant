# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Goblin Assistant, please report it to us as follows:

### Contact

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

- **`security@goblinassistant.app`** (preferred)
- Or create a private security advisory on GitHub

### What to Include

When reporting a vulnerability, please include:

1. A clear description of the vulnerability
2. Steps to reproduce the issue
3. Potential impact and severity
4. Any suggested fixes or mitigations
5. Your contact information for follow-up

### Response Timeline

- **Initial Response**: Within 24 hours
- **Vulnerability Assessment**: Within 72 hours
- **Fix Development**: Within 1-2 weeks for critical issues
- **Public Disclosure**: After fix is deployed and tested

### Recognition

We appreciate security researchers who help keep our users safe. With your permission, we'll acknowledge your contribution in our security advisory.

## Security Considerations

### API Key Handling

- API keys are stored securely using system keychain/keyring
- Keys are never transmitted in plain text
- Keys are encrypted at rest

### Network Security

- All API calls use HTTPS/TLS 1.3+
- Certificate pinning for critical services
- Rate limiting and abuse prevention

### Desktop Security

- Built with Tauri for sandboxed execution
- No arbitrary code execution capabilities
- Secure file system access controls

## 🔒 Advanced Security Features

### Comprehensive Secret Scanning

Goblin Assistant implements multi-layer secret detection and prevention to protect sensitive data:

#### Detection Capabilities
- **API Keys**: OpenAI, Anthropic, Google Cloud, AWS, Azure, and other major providers
- **Authentication Tokens**: JWT tokens, Bearer tokens, OAuth tokens, API tokens
- **Passwords**: Common password patterns and credential formats
- **Private Keys**: RSA, ECDSA, and other cryptographic keys
- **Certificates**: SSL certificates, SSH keys, and digital certificates
- **Database Credentials**: Connection strings and database passwords
- **Environment Variables**: Sensitive configuration values

#### Security Layers
1. **Request Creation**: Scans user prompts before queuing requests
2. **Worker Processing**: Double-checks prompts before sending to AI providers
3. **Document Indexing**: Automatically redacts secrets during ChromaDB indexing
4. **Audit Logging**: Complete security event logging and monitoring

#### Response to Violations
- **Immediate Blocking**: Requests containing secrets are rejected with clear error messages
- **Security Metrics**: Comprehensive monitoring of security events with Datadog
- **Audit Trail**: Detailed logging of detection points and violation types
- **Graceful Degradation**: System continues operating while blocking malicious requests

### Privacy Protection

- **User Data Hashing**: User IDs are hashed for privacy in logs and metrics
- **Secure Credential Storage**: API keys stored in system keychain/keyring
- **Data Minimization**: Only necessary data retained for functionality
- **Compliance Ready**: Enterprise-grade security for sensitive environments

### Enterprise Security Architecture

- **Model Control Plane (MCP)**: Centralized security policy enforcement
- **Circuit Breaker Pattern**: Automatic security response to threats
- **Real-time Monitoring**: Security events tracked with Datadog integration
- **Fail-safe Design**: Multiple security layers prevent data leakage

## Responsible Disclosure

We kindly ask that you:

- Give us reasonable time to fix the issue before public disclosure
- Avoid accessing or modifying user data
- Respect the privacy and security of our users
- Follow ethical disclosure practices

Thank you for helping keep Goblin Assistant and its users secure!
