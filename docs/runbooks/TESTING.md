# Testing Guide for Goblin Assistant

This document provides comprehensive guidance on testing the Goblin Assistant application across different layers.

## Table of Contents

- [Quick Start](#quick-start)
- [Backend Tests (Python/pytest)](#backend-tests-pythonpytest)
- [Frontend Tests (TypeScript/Vitest)](#frontend-tests-typescriptvitest)
- [E2E Tests (Playwright)](#e2e-tests-playwright)
- [Coverage Goals](#coverage-goals)
- [Writing New Tests](#writing-new-tests)
- [CI/CD Integration](#cicd-integration)

## Quick Start

### Run All Tests Locally

```bash
# Backend tests
cd api && pytest --cov=. --cov-report=html

# Frontend tests
npm run test:unit

# E2E tests
npm run test:e2e

# All coverage reports
npm run test:coverage
```

## Backend Tests (Python/pytest)

### Setup

Tests are configured in `api/pytest.ini` and coverage in `.coveragerc`.

```bash
cd api
pip install -r requirements.txt
pytest
```

### Key Test Files

| File | Purpose |
|------|---------|
| `api/tests/test_auth_comprehensive.py` | Authentication endpoints (login, register, rate limiting) |
| `api/tests/test_sanitization_comprehensive.py` | PII detection and data masking |
| `api/tests/test_privacy.py` | GDPR/CCPA compliance |
| `api/tests/test_memory_stratification.py` | Memory promotion system |
| `api/tests/test_observability.py` | Monitoring and tracing |

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest api/tests/test_auth_comprehensive.py

# Run with coverage
pytest --cov=api --cov-report=html --cov-report=term-missing

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_login"

# Run with parallel execution
pytest -n auto
```

### Test Structure

Each test file follows this pattern:

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestFeatureName:
    """Group of related tests"""

    def test_happy_path(self):
        """Test successful scenario"""
        assert True

    def test_error_handling(self):
        """Test error scenarios"""
        with pytest.raises(ValueError):
            invalid_input()

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test async functions"""
        result = await async_operation()
        assert result is not None
```

### Fixtures & Mocking

Common patterns for tests:

```python
@pytest.fixture
def mock_db():
    """Provides mocked database session"""
    return AsyncMock(spec=AsyncSession)

# Use in tests
def test_with_db(mock_db):
    # mock_db is injected automatically
    pass

# Mocking external services
with patch('api.providers.openai.AIClient') as MockClient:
    mock_client = AsyncMock()
    MockClient.return_value = mock_client
    # Test code here
```

### Coverage Requirements

- **Minimum**: 70% overall coverage
- **Target**: 80% on critical paths (auth, chat, privacy)
- **Excluded**: migrations, __init__.py, test files themselves

Check coverage:

```bash
pytest --cov=api --cov-report=html
open htmlcov/index.html
```

## Frontend Tests (TypeScript/Vitest)

### Setup

Tests configured in `vitest.config.ts` with environment as `jsdom`.

```bash
npm install
npm run test:unit
```

### Key Test Files

| File | Purpose |
|------|---------|
| `src/components/auth/ModularLoginForm.test.tsx` | Login/registration form |
| `src/components/chat/ChatInterface.test.tsx` | Chat message display & input |
| `src/hooks/useAuth.test.ts` | Authentication hook |
| `src/services/api.test.ts` | API client |

### Running Tests

```bash
# Run all tests once
npm run test:unit

# Run in watch mode (auto-rerun on file changes)
npm run test:unit:watch

# Run with coverage
npm run test:coverage

# Run specific test file
npm run test:unit -- src/components/auth/ModularLoginForm.test.tsx

# Run tests matching pattern
npm run test:unit -- -t "login"
```

### Test Structure

Frontend tests using React Testing Library:

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MyComponent from '@/components/MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    render(<MyComponent />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('should handle user interaction', async () => {
    render(<MyComponent />);
    await userEvent.click(screen.getByRole('button'));
    await waitFor(() => {
      expect(screen.getByText('Success')).toBeInTheDocument();
    });
  });
});
```

### Mocking

API mocking with MSW (Mock Service Worker):

```typescript
import { mswServer } from '@/test/mswServer';

// Default handlers are set up in mswServer.ts
// Override handlers per test:
test('custom API response', () => {
  mswServer.use(
    http.post('/api/chat', () => {
      return HttpResponse.json({ message: 'custom response' });
    })
  );
  // Your test code
});
```

### Coverage Requirements

- **Target**: 80% on critical components (auth, chat, profile)
- **Excluded**: UI components from component libraries, .next, node_modules

Check coverage:

```bash
npm run test:coverage
```

## E2E Tests (Playwright)

### Setup

Tests use Playwright with cross-browser support (Chromium, Firefox, Safari).

```bash
npx playwright install  # Download browsers
npm run test:e2e
```

### Key Test Files

| File | Purpose |
|------|---------|
| `e2e/auth.spec.ts` | Login/register flows |
| `e2e/chat.spec.ts` | Chat message sending |
| `e2e/privacy.spec.ts` | PII masking, data privacy |
| `e2e/cross-browser.spec.ts` | Accessibility & responsiveness |

### Running Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run specific test file
npx playwright test e2e/auth.spec.ts

# Run in specific browser
npx playwright test --project=chromium

# Run in headed mode (see browser window)
npx playwright test --headed

# Run with debugging
npx playwright test --debug

# Generate trace for debugging
npx playwright test --trace on
```

### Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature', () => {
  test('should work correctly', async ({ page }) => {
    await page.goto('/');
    
    await expect(page.locator('button')).toBeVisible();
    await page.locator('button').click();
    
    await expect(page).toHaveURL('/success');
  });
});
```

### Best Practices

- **Isolate tests**: Each test should be independent
- **Avoid hardcoding waits**: Use `waitForLoadState()`, `waitFor()` instead
- **Use data-testid**: Add `data-testid` attributes to critical elements for reliable selection
- **Mock external APIs**: Use page.route() to control API responses
- **Clean up**: Reset state between tests

## Coverage Goals

### Current Baseline

- Backend: 0% (new, starting point)
- Frontend: 0% (new, starting point)
- E2E: Limited to 1 accessibility test

### Target (80% coverage)

| Layer | Target | Critical Paths |
|-------|--------|-----------------|
| Backend | 80% | Auth, Chat, Privacy |
| Frontend | 80% | Login form, Chat interface |
| E2E | 5-7 critical flows | Auth, Chat messaging, Privacy |

### Tracking Coverage

```bash
# Backend coverage report
cd api && pytest --cov=. --cov-report=html
open htmlcov/index.html

# Frontend coverage report
npm run test:coverage
open coverage/index.html
```

## Writing New Tests

### Backend Test Checklist

- [ ] Test happy path (success case)
- [ ] Test error cases (validation, authorization, exceptions)
- [ ] Test edge cases (empty input, max limits, special characters)
- [ ] Mock external dependencies (database, API clients)
- [ ] Use fixtures for common setup
- [ ] Include docstring explaining what's tested

Example:

```python
def test_user_login_with_invalid_password():
    """Test that login fails with incorrect password"""
    # Setup
    user = create_test_user("test@example.com", "correct_password")
    
    # Execute
    with pytest.raises(HTTPException) as exc_info:
        login_endpoint("test@example.com", "wrong_password")
    
    # Assert
    assert exc_info.value.status_code == 401
    assert "invalid password" in exc_info.value.detail.lower()
```

### Frontend Test Checklist

- [ ] Test rendering (component appears)
- [ ] Test user interactions (clicks, typing)
- [ ] Test state changes (form submission, navigation)
- [ ] Test error states (network errors, validation)
- [ ] Mock API calls with MSW
- [ ] Use `waitFor()` for async operations

Example:

```typescript
it('should show error on failed login', async () => {
  // Setup
  mswServer.use(
    http.post('/api/auth/login', () => {
      return HttpResponse.json({ error: 'Invalid credentials' }, { status: 401 });
    })
  );

  // Render & Interact
  render(<LoginForm />);
  await userEvent.type(screen.getByPlaceholderText(/email/i), 'test@example.com');
  await userEvent.click(screen.getByRole('button', { name: /login/i }));

  // Assert
  await waitFor(() => {
    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
  });
});
```

### E2E Test Checklist

- [ ] Test critical user journey end-to-end
- [ ] Verify navigation and page transitions
- [ ] Check for required elements on page
- [ ] Test form submission and validation
- [ ] Verify success/error messages
- [ ] Use data-testid for reliable element selection

Example:

```typescript
test('should complete login flow', async ({ page }) => {
  // Navigate
  await page.goto('/');

  // Fill form
  await page.fill('input[type="email"]', 'test@example.com');
  await page.fill('input[type="password"]', 'password123');

  // Submit
  await page.click('button:has-text("Login")');

  // Verify
  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('[data-testid="user-profile"]')).toBeVisible();
});
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests against `main` or `develop`

### Pipeline Stages

1. **Lint & Type Check** (blocks merge on failure)
   - ESLint
   - TypeScript type checking
   - Prettier formatting

2. **Unit Tests** (requires coverage report)
   - Backend: pytest with coverage
   - Frontend: Vitest with coverage
   - Uploads coverage to Codecov

3. **Build** (requires passing tests)
   - Next.js production build
   - Docker build (if applicable)

4. **Security** (informational)
   - npm audit
   - audit-ci
   - SAST scanning

5. **E2E Tests** (on PRs and main branch)
   - Playwright tests
   - Cross-browser
   - Uploads test artifacts

### Coverage Thresholds

CI will fail if:
- Frontend coverage drops below 80%
- Critical paths (auth, chat) below 70%
- Existing tests broken

View in CI: Check "Coverage" status on PR

## Troubleshooting

### Flaky Tests

E2E tests sometimes fail intermittently due to:
- Network delays: Use `waitFor()` with longer timeout
- Race conditions: Ensure proper test isolation
- Async issues: Use `await` for all async operations

Fix:
```typescript
// ❌ Bad
const button = page.locator('button');
await button.click();

// ✅ Good
await page.locator('button').waitFor({ state: 'visible' });
await page.locator('button').click();
```

### Test Isolation

Each test must be independent:

```python
# ✅ Good - Clean up after
def test_auth(mock_db):
    create_test_user()
    # test code
    # cleanup happens automatically with fixtures

# ❌ Bad - Tests depend on order
def test_login(): pass
def test_logout():  # Depends on user from previous test
    pass
```

### Debugging Failed Tests

Backend:
```bash
pytest -v -s --tb=long failed_test_name
```

Frontend:
```bash
npm run test:unit -- --reporter=verbose
# Then check output for detailed error
```

E2E:
```bash
npx playwright test --debug
# Opens Playwright Inspector to step through test
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright documentation](https://playwright.dev/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

## Questions?

See existing test files for examples, or check code comments for patterns used in this project.
