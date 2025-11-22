# Contributing to Goblin Assistant

Thank you for your interest in contributing to Goblin Assistant! This document provides guidelines and information for contributors.

## Quick Start

1. **Fork and Clone**: Fork the repository and clone it locally
2. **Setup Environment**: Follow the [development setup guide](README.md#development)
3. **Create Feature Branch**: `git checkout -b feature/your-feature-name`
4. **Make Changes**: Implement your feature or fix
5. **Test**: Run tests and ensure everything works
6. **Submit PR**: Create a pull request with a clear description

## Development Setup

### Prerequisites

- Node.js 18+ and pnpm
- Python 3.8+ (for backend API)
- Rust (for Tauri desktop builds)

### Installation

```bash
# Install dependencies
pnpm install

# Setup Python environment (if working on backend)
cd api
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Development Commands

```bash
# Start development server
pnpm dev

# Run tests
pnpm test

# Build for production
pnpm build

# Run linting
pnpm lint

# Type checking
pnpm type-check
```

## Project Structure

```
goblin-assistant/
├── src/                    # Frontend React/TypeScript code
│   ├── components/        # Reusable UI components
│   ├── pages/            # Application pages/screens
│   ├── services/         # API clients and utilities
│   └── types/            # TypeScript type definitions
├── api/                   # FastAPI backend
│   ├── main.py          # FastAPI application
│   ├── routers/         # API route handlers
│   └── services/        # Business logic
├── src-tauri/            # Tauri desktop configuration
├── public/               # Static assets
└── screenshots/          # Application screenshots
```

## Coding Standards

### TypeScript/React

- Use TypeScript for all new code
- Follow React functional components with hooks
- Use Tailwind CSS for styling
- Maintain consistent naming conventions (PascalCase for components, camelCase for utilities)

### Python (Backend)

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write comprehensive docstrings
- Use async/await for I/O operations

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Guidelines

- **Title**: Clear, descriptive title following conventional commit format
- **Description**: Explain what changes and why
- **Testing**: Describe how you tested the changes
- **Screenshots**: Include before/after screenshots for UI changes
- **Breaking Changes**: Clearly mark any breaking changes

## Testing

### Frontend Tests

```bash
# Run unit tests
pnpm test

# Run tests with coverage
pnpm test:coverage

# Run E2E tests
pnpm test:e2e
```

### Backend Tests

```bash
cd api
pytest
```

## Documentation

- Update README.md for new features
- Add JSDoc/TSDoc comments for new functions
- Update screenshots if UI changes
- Keep the wiki documentation current

## Security Considerations

- Never commit API keys or sensitive credentials
- Use environment variables for configuration
- Follow secure coding practices
- Report security issues via [SECURITY.md](SECURITY.md)

## Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Discord**: Join our community Discord for real-time help

## Recognition

Contributors are recognized in:

- GitHub repository contributors list
- Release notes for significant contributions
- Project documentation

Thank you for contributing to Goblin Assistant! 🚀
