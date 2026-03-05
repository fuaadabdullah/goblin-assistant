# Contributing

## Welcome Contributors! 🎉

Thank you for your interest in contributing to GoblinOS Assistant! This document provides guidelines and information for contributors.

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## Getting Started

### Development Environment Setup

1. **Fork and Clone**:

   ```bash
   git clone https://github.com/your-username/forgemono.git
   cd forgemono/apps/goblin-assistant
   ```

2. **Install Dependencies**:

   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt

   # Frontend
   cd ../app
   npm install
   ```

3. **Environment Configuration**:

   ```bash
   # Copy environment templates
   cp backend/.env.example backend/.env.local
   cp .env.example .env.local

   # Configure your API keys and settings
   ```

4. **Run Development Servers**:

   ```bash
   # Backend (Terminal 1)
   cd backend
   uvicorn main:app --reload

   # Frontend (Terminal 2)
   cd app
   npm run dev
   ```

### Development Workflow

1. **Create a Branch**:

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make Changes**:
   - Write tests for new features
   - Follow the coding standards
   - Update documentation as needed

3. **Run Tests**:

   ```bash
   # Backend tests
   cd backend
   pytest

   # Frontend tests
   cd app
   npm test
   ```

4. **Commit Changes**:

   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and Create PR**:

   ```bash
   git push origin feature/your-feature-name
   # Create pull request on GitHub
   ```

## Contribution Guidelines

### Commit Message Format

We follow conventional commit format:

```text
type(scope): description

[optional body]

[optional footer]
```

**Types**:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions/modifications
- `chore`: Maintenance tasks

**Examples**:

```text
feat(auth): add Google OAuth integration
fix(api): resolve memory leak in model routing
docs(readme): update installation instructions
```

### Code Style

#### Python (Backend)

- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Maximum line length: 88 characters (Black formatter default)
- Use descriptive variable names
- Add docstrings to all public functions and classes

```python
def route_request(task: TaskAnalysis) -> ModelResponse:
    """
    Route a request to the appropriate AI model.

    Args:
        task: Analyzed task information

    Returns:
        Model response with routing decision
    """
    # Implementation here
    pass
```

#### TypeScript/JavaScript (Frontend)

- Use TypeScript for all new code
- Follow the project's ESLint configuration
- Use functional components with hooks
- Add PropTypes or TypeScript interfaces for component props

```typescript
interface UserProfileProps {
  user: User;
  onUpdate: (user: User) => void;
}

const UserProfile: React.FC<UserProfileProps> = ({ user, onUpdate }) => {
  // Component implementation
};
```

### Testing

#### Backend Testing

- Write unit tests for all new functions
- Use pytest framework
- Aim for >80% code coverage
- Mock external dependencies

```python
import pytest
from unittest.mock import Mock

def test_model_routing():
    router = ModelRouter()
    task = TaskAnalysis(complexity="simple")

    response = router.route(task)

    assert response.model == "raptor-mini"
    assert response.confidence > 0.8
```

#### Frontend Testing

- Use React Testing Library for component tests
- Write integration tests for user flows
- Mock API calls in tests

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInterface } from './ChatInterface';

test('sends message when form is submitted', async () => {
  const mockSendMessage = jest.fn();
  const user = userEvent.setup();

  render(<ChatInterface onSendMessage={mockSendMessage} />);

  const input = screen.getByRole('textbox');
  const button = screen.getByRole('button', { name: /send/i });

  await user.type(input, 'Hello world');
  await user.click(button);

  expect(mockSendMessage).toHaveBeenCalledWith('Hello world');
});
```

### Documentation

- Update README.md for significant feature changes
- Add JSDoc/TSDoc comments for public APIs
- Update API documentation for endpoint changes
- Include examples in documentation

## Pull Request Process

### Before Submitting

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commit messages follow conventional format
- [ ] Branch is up to date with main

### PR Template

When creating a pull request, please include:

1. **Description**: What changes were made and why
2. **Type of Change**: Bug fix, feature, documentation, etc.
3. **Testing**: How the changes were tested
4. **Breaking Changes**: Any breaking changes and migration guide
5. **Screenshots**: UI changes with before/after screenshots

### Review Process

1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: At least one maintainer reviews the code
3. **Approval**: PR is approved and merged
4. **Deployment**: Changes are automatically deployed

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Step-by-step instructions
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, browser, versions
- **Screenshots**: If applicable

### Feature Requests

For feature requests, please include:

- **Problem**: What problem are you trying to solve?
- **Solution**: Proposed solution
- **Alternatives**: Alternative solutions considered
- **Use Cases**: Specific use cases for the feature

## Development Tools

### Recommended Editor Setup

#### VS Code Extensions

- Python: `ms-python.python`
- TypeScript: `ms-vscode.vscode-typescript-next`
- Prettier: `esbenp.prettier-vscode`
- ESLint: `dbaeumer.vscode-eslint`
- GitLens: `eamodio.gitlens`

#### VS Code Settings

```json
{
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true
}
```

### Local Development Tools

#### Docker Setup

```bash
# Run full stack in Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Run tests in containers
docker-compose exec backend pytest
```

#### Database Management

```bash
# Reset development database
cd backend
rm goblin_assistant.db
alembic upgrade head

# View database schema
sqlite3 goblin_assistant.db .schema
```

## Security Considerations

### Reporting Security Issues

- **DO NOT** create public GitHub issues for security vulnerabilities
- Email security concerns to: `security@goblin.fuaad.ai`
- Include detailed reproduction steps and potential impact

### Security Best Practices

- Never commit API keys or secrets
- Use environment variables for configuration
- Validate all user inputs
- Keep dependencies updated
- Use HTTPS for all communications

## Community

### Getting Help

- **Documentation**: Check the docs folder first
- **Issues**: Search existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions
- **Discord**: Join our community Discord server

### Recognition

Contributors are recognized in:

- GitHub repository contributors list
- Changelog for significant contributions
- Project documentation credits

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

Thank you for contributing to GoblinOS Assistant! 🚀

