# Contributing to n8n Deploy

Thank you for your interest in contributing to n8n Deploy! This guide will help you get started.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/n8n-deploy.git
   cd n8n-deploy
   ```

3. Set up your development environment:

   ```bash
   make install-dev
   ```

4. Install pre-commit hooks (recommended):

   ```bash
   ./scripts/setup-pre-commit.sh
   ```

   This will install hooks that automatically:
   - Format your code (black, isort)
   - Run linting checks
   - Run quick tests on commit
   - Run full test suite on push

## Development Process

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Follow the existing code style and patterns
- Add tests for new functionality
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_your_feature.py

# Run with coverage
pytest --cov
```

### 4. Check Code Quality

```bash
# Run linting
make lint

# Format code
make format

# Full check (lint + test)
make check
```

### 5. Commit Your Changes

Write clear, concise commit messages:

```bash
git commit -m "feat: add cloudflare tunnel support"
git commit -m "fix: resolve memory leak in fargate service"
git commit -m "docs: update deployment guide"
```

**Note**: If you've installed pre-commit hooks, they will automatically run before each commit. To skip hooks temporarily (not recommended), use:

```bash
git commit --no-verify -m "your message"
```

### 6. Submit a Pull Request

1. Push your branch to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

2. Open a pull request on GitHub
3. Describe your changes and link any related issues
4. Wait for review and address feedback

## Coding Standards

### Python Code Style

- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use descriptive variable names

### Infrastructure Code

- Follow AWS CDK best practices
- Use consistent resource naming via `get_resource_name()`
- Always tag resources appropriately
- Consider cost implications

### Testing

- Write unit tests for all new code
- Aim for 80%+ code coverage
- Use mocks for external dependencies
- Test error cases, not just happy paths

## Project Structure

When adding new features:

- **Stacks**: Add to `n8n_deploy/stacks/` for new CDK stacks
- **Constructs**: Add to `n8n_deploy/constructs/` for reusable components
- **Scripts**: Add to `scripts/` for automation tools
- **Tests**: Mirror the source structure in `tests/`
- **Documentation**: Update relevant docs in `docs/`

## Types of Contributions

### Bug Reports

- Use the GitHub issue tracker
- Include reproduction steps
- Provide environment details
- Include relevant logs/errors

### Feature Requests

- Open a discussion first for major features
- Explain the use case
- Consider implementation approach
- Think about backward compatibility

### Code Contributions

- Bug fixes
- New features
- Performance improvements
- Documentation updates
- Test improvements

### Documentation

- Fix typos and clarify existing docs
- Add examples
- Create tutorials
- Improve README

## Review Process

1. All PRs require at least one review
2. CI must pass (tests, linting)
3. Documentation must be updated
4. Changes should follow existing patterns

## Questions?

- Open a GitHub discussion for general questions
- Use issues for bugs and feature requests
- Check existing issues/discussions first

Thank you for contributing to n8n Deploy!
