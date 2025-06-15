# Local CI/CD Testing with Act

This guide explains how to test GitHub Actions workflows locally using [act](https://github.com/nektos/act).

## Prerequisites

1. Install act:

   ```bash
   # macOS
   brew install act

   # Linux
   curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

   # Windows (via Chocolatey)
   choco install act-cli
   ```

2. Docker must be running

## Configuration

### 1. Act Configuration (.actrc)

The `.actrc` file configures act to use Docker images with Node.js pre-installed:

```bash
# Use full images with Node.js
-P ubuntu-latest=catthehacker/ubuntu:full-latest
-P ubuntu-22.04=catthehacker/ubuntu:full-22.04
-P ubuntu-20.04=catthehacker/ubuntu:full-20.04

# Default platform
--platform ubuntu-latest=catthehacker/ubuntu:full-latest

# Reuse containers for better performance
--reuse

# Use local .env file for secrets
--env-file .env.act
```

### 2. Environment Variables (.env.act)

Copy `.env.act.example` to `.env.act` and fill in required values:

```bash
cp .env.act.example .env.act
# Edit .env.act with your tokens
```

Key variables:

- `GITHUB_TOKEN`: For actions that interact with GitHub API
- `AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY`: For AWS deployment tests
- `CLOUDFLARE_TUNNEL_TOKEN`: Set to dummy value for local tests
- `SKIP_SECURITY_SCAN`: Set to true to skip Trivy scans locally

## Running Tests

### Using the Helper Script

```bash
# Run all workflows
./scripts/act-test.sh

# Run specific workflow
./scripts/act-test.sh -w test.yml

# Run specific job
./scripts/act-test.sh -j lint

# Run with specific event
./scripts/act-test.sh -e pull_request
```

### Direct Act Commands

```bash
# Run all push event workflows
act push

# Run specific workflow
act push -W .github/workflows/test.yml

# Run specific job
act push -j test

# Run with secrets from file
act push --secret-file .env.act

# List available workflows
act -l

# Dry run (show what would be executed)
act -n
```

## Common Issues and Solutions

### 1. Node.js Not Found

**Error**: `exec: "node": executable file not found in $PATH`

**Solution**: Ensure `.actrc` uses `full` images:

```bash
-P ubuntu-latest=catthehacker/ubuntu:full-latest
```

### 2. Docker Not Available

**Error**: `Cannot connect to the Docker daemon`

**Solution**:

- Ensure Docker Desktop is running
- For Docker-in-Docker, use `full` images with Docker installed

### 3. Token Errors

**Error**: `Input required and not supplied: token`

**Solution**: Add required tokens to `.env.act`:

```bash
GITHUB_TOKEN=your_token_here
```

### 4. Resource Limits

**Error**: Out of memory or disk space

**Solution**:

- Increase Docker Desktop resources
- Use `--rm` flag to remove containers after runs
- Clean up: `docker system prune -a`

### 5. Platform Issues

**Error**: `image platform does not match host platform`

**Solution**: Add to `.actrc`:

```bash
--container-architecture linux/amd64
```

## Testing Specific Scenarios

### Test Python Matrix

```bash
# Test all Python versions
act push -W .github/workflows/test.yml

# Test specific Python version
act push -W .github/workflows/test.yml -j "Test Python 3.11"
```

### Test CDK Deployment

```bash
# Requires AWS credentials in .env.act
act push -W .github/workflows/deploy.yml -j "Deploy to dev"
```

### Test Docker Builds

```bash
act push -W .github/workflows/test.yml -j "Docker Build Test"
```

## Debugging

### Verbose Output

```bash
act -v push  # Verbose
act -vv push # Very verbose
```

### Interactive Shell

```bash
# Drop into shell when action fails
act push --container-options "--entrypoint /bin/bash"
```

### Keep Containers Running

```bash
# Don't remove containers after run
act push --reuse --no-remove
```

## Performance Tips

1. **Use Container Reuse**: Add `--reuse` to `.actrc`
2. **Cache Dependencies**: Mount local cache directories
3. **Skip Unnecessary Steps**: Use `act -j <job>` to run specific jobs
4. **Use Smaller Images**: For simple tests, use `node:16-buster-slim`

## Limitations

Act has some limitations compared to GitHub Actions:

1. **Services**: Database services may not work exactly the same
2. **Artifacts**: Upload/download artifacts work differently
3. **Caching**: GitHub's caching API is not available
4. **Secrets**: Must be provided via `.env.act` or command line
5. **GitHub Context**: Some context variables may be missing

## Alternative: Running Tests Directly

For faster feedback during development:

```bash
# Run tests directly
make test

# Run specific test file
pytest tests/unit/test_config_loader.py

# Run with coverage
pytest --cov=n8n_deploy

# Run linting
make lint
```
