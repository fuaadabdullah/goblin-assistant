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

## Responsible Disclosure

We kindly ask that you:

- Give us reasonable time to fix the issue before public disclosure
- Avoid accessing or modifying user data
- Respect the privacy and security of our users
- Follow ethical disclosure practices

Thank you for helping keep Goblin Assistant and its users secure!
