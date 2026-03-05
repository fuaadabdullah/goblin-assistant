# Goblin Assistant CI/CD Setup

This document outlines the comprehensive CI/CD pipeline for the Goblin Assistant application, including GitHub Actions workflows, pre-push validation, and quality gates.

## 🚀 Overview

The CI/CD pipeline ensures code quality, security, and reliability through automated testing, linting, and deployment processes.

### Key Features

- **Automated Testing**: Unit tests, E2E tests, and coverage reporting
- **Code Quality**: ESLint, TypeScript type checking, and Prettier formatting
- **Security Scanning**: NPM audit and vulnerability checks
- **Pre-push Validation**: Local quality checks before pushing code
- **Branch Protection**: Required status checks and reviews for main branch
- **Preview Deployments**: Automatic preview environments for pull requests

## 📋 CI/CD Pipeline Jobs

### 1. Lint & Type Check

- **ESLint**: Code linting with custom rules
- **TypeScript**: Type checking with strict mode
- **Prettier**: Code formatting validation

### 2. Unit Tests

- **Jest**: Test runner with React Testing Library
- **Coverage**: Minimum 80% coverage required
- **Codecov**: Coverage reporting and tracking

### 3. Build & Bundle Analysis

- **Vite Build**: Production build verification
- **Bundle Analysis**: Build artifact generation
- **Artifact Upload**: Build artifacts for deployment

### 4. Security Scan

- **NPM Audit**: Dependency vulnerability scanning
- **Audit CI**: Automated security gate checking

### 5. E2E Tests (Optional)

- **Playwright**: End-to-end testing
- **Visual Testing**: Screenshot comparison
- **Test Results**: Detailed reporting

### 6. Quality Gate

- **Status Check**: Validates all previous jobs passed
- **Deployment Gate**: Ensures quality before deployment

### 7. Deployment

- **Preview**: PR-based preview deployments
- **Production**: Main branch production deployments

## 🔧 Local Development Setup

### Pre-commit Hooks (Husky)

The project uses Husky for Git hooks that run automatically:

```bash
# Pre-commit (runs on git commit)
npx lint-staged  # Runs ESLint and Prettier on staged files
npm run validate-env  # Validates environment configuration

# Pre-push (runs on git push)
npm run lint      # Full ESLint check
npm run type-check # TypeScript type checking
npm run test      # Run test suite
```

### Manual Quality Checks

Run these commands locally before pushing:

```bash
# Run all quality checks
npm run lint
npm run type-check
npm run test
npm run test:coverage
npm run security:audit

# Build verification
npm run build

# E2E tests (if applicable)
npm run test:e2e
```

## 🛡️ Branch Protection

### Required Status Checks

All of these must pass before merging to `main`:

- `Goblin Assistant CI/CD (lint-and-type-check)`
- `Goblin Assistant CI/CD (test)`
- `Goblin Assistant CI/CD (build)`
- `Goblin Assistant CI/CD (security-scan)`
- `Goblin Assistant CI/CD (quality-gate)`

### Pull Request Requirements

- At least 1 approving review required
- Code owner reviews required
- Stale reviews dismissed automatically
- Admin enforcement enabled

### Setup Branch Protection

Run the setup script to configure branch protection:

```bash
# Requires GitHub CLI authentication
./scripts/setup-branch-protection.sh
```

## 📊 Monitoring & Reporting

### Coverage Reports

- **Codecov**: Integrated coverage tracking
- **Minimum Threshold**: 80% coverage required
- **Report Location**: `apps/goblin-assistant/coverage/`

### Security Reports

- **NPM Audit**: Weekly security scans
- **Vulnerability Tracking**: Automated alerts
- **Report Location**: `apps/goblin-assistant/reports/`

### Test Results

- **JUnit XML**: Test results for CI integration
- **Coverage XML**: Coverage data for external tools
- **Artifact Storage**: 7-day retention

## 🚀 Deployment Process

### Preview Deployments

- **Trigger**: Pull request creation/update
- **Environment**: `preview`
- **URL Pattern**: `https://goblin-assistant-preview-{PR_NUMBER}.vercel.app`

### Production Deployments

- **Trigger**: Push to `main` branch
- **Environment**: `production`
- **URL**: `https://goblin.fuaad.ai`

### Deployment Verification

```bash
# Check deployment health
curl -f https://goblin.fuaad.ai/api/health

# Verify build artifacts
npm run build && ls -la dist/
```

## 🔍 Troubleshooting

### Common Issues

#### Tests Failing Locally but Passing in CI

- Check Node.js version matches CI (`NODE_VERSION: '20'`)
- Ensure all dependencies are installed: `npm ci`
- Clear cache: `npm run clean && npm ci`

#### Pre-push Hook Blocking Commits

```bash
# Skip hooks temporarily (not recommended)
git commit --no-verify

# Debug hook execution
npm run lint --verbose
npm run test --verbose
```

#### Branch Protection Issues

- Ensure all required status checks are configured
- Verify GitHub Actions permissions
- Check repository settings for branch protection

### Debug Commands

```bash
# Run CI pipeline locally
act -j lint-and-type-check
act -j test
act -j build

# Check GitHub Actions logs
gh run list --limit 5
gh run view <run-id> --log

# Validate workflow syntax
npm install -g @action-validator/cli
action-validator .github/workflows/ci.yml
```

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Jest Testing Framework](https://jestjs.io/docs/getting-started)
- [ESLint Configuration](https://eslint.org/docs/user-guide/configuring/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Husky Git Hooks](https://typicode.github.io/husky/)
- [Codecov Coverage](https://docs.codecov.com/)

## 🤝 Contributing

When contributing to the CI/CD pipeline:

1. **Test Locally**: Run all quality checks before pushing
2. **Update Documentation**: Keep this document current
3. **Review Changes**: Ensure CI passes for all changes
4. **Security First**: Never commit secrets or sensitive data

### Adding New Checks

1. Update the GitHub Actions workflow in `.github/workflows/ci.yml`
2. Add corresponding npm scripts in `package.json`
3. Update branch protection requirements
4. Document the new check in this file
5. Test the changes thoroughly

---

**Last Updated**: December 12, 2025
**CI Status**: ✅ Active
**Coverage**: 80% minimum required
