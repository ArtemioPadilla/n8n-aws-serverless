# Migration Guide: n8n-aws-serverless → n8n Deploy

This guide helps existing users migrate from `n8n-aws-serverless` to the new `n8n Deploy` platform.

## 🎯 What's Changed?

The project has evolved from a single-purpose AWS deployment tool to a comprehensive multi-platform deployment solution. The new name "n8n Deploy" better reflects this expanded scope.

### Key Changes:
- **Project name**: `n8n-aws-serverless` → `n8n-deploy`
- **Python module**: `n8n_aws_serverless` → `n8n_deploy`
- **Expanded capabilities**: Now supports Docker, Cloudflare Tunnel, and hybrid deployments
- **Unified configuration**: Same `system.yaml` works for all deployment types

## 📋 Migration Steps

### 1. Update Your Local Repository

```bash
# If you have an existing clone
cd n8n-aws-serverless
git pull origin main

# Or clone fresh
git clone https://github.com/your-org/n8n-deploy n8n-deploy
cd n8n-deploy
```

### 2. Update Python Dependencies

```bash
# Remove old virtual environment
rm -rf .venv

# Create new environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install updated dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Update Your Configuration

Your existing `system.yaml` should work as-is, but you can now add new deployment options:

```yaml
# Old configuration still works
environments:
  production:
    account: "123456789012"
    region: "us-east-1"
    # ... your existing AWS config

# New: Add deployment type (optional, defaults to AWS)
project:
  name: "my-n8n"
  deployment_type: "aws"  # or "docker", "cloudflare"

# New: Add Docker-specific settings (optional)
environments:
  production:
    docker:
      compose_profile: "production"
      postgres_enabled: true
      
# New: Add Cloudflare Tunnel (optional)
environments:
  production:
    cloudflare:
      tunnel_name: "n8n-production"
      access_policy:
        allowed_emails: ["admin@example.com"]
```

### 4. Update Your Scripts

If you have custom scripts that import the module:

```python
# Old
from n8n_aws_serverless.config import ConfigLoader
from n8n_aws_serverless.stacks import NetworkStack

# New
from n8n_deploy.config import ConfigLoader
from n8n_deploy.stacks import NetworkStack
```

### 5. Update CDK Context

The CDK context remains the same:

```bash
# Still works the same
cdk deploy -c environment=production
cdk deploy -c environment=dev -c stack_type=minimal
```

### 6. Update CI/CD Pipelines

If you have GitHub Actions or other CI/CD pipelines:

```yaml
# Old
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    
# New (same command, but in new repo)
- name: Install dependencies
  run: |
    pip install -r requirements.txt
```

## 🆕 New Features Available After Migration

### 1. Docker Deployment

```bash
# Run n8n locally for free
make local-up

# Deploy production Docker stack
cd docker/production
docker-compose up -d
```

### 2. Cloudflare Tunnel

```bash
# Add zero-trust access to any deployment
./scripts/setup-cloudflare-tunnel.sh

# Or use with AWS
cdk deploy -c environment=production -c access_type=cloudflare
```

### 3. Unified Commands

```bash
# New Makefile targets
make deploy-aws      # Deploy to AWS
make deploy-docker   # Deploy with Docker
make deploy-hybrid   # Deploy AWS + Cloudflare
```

## 🔄 Backward Compatibility

### What's Preserved:
- ✅ All existing AWS deployments continue to work
- ✅ Your `system.yaml` configuration is compatible
- ✅ CDK commands remain the same
- ✅ Stack names and resource naming unchanged
- ✅ CloudFormation stacks don't need updates

### What's New (Optional):
- 🆕 Docker deployment options
- 🆕 Cloudflare Tunnel support
- 🆕 Enhanced monitoring with Grafana
- 🆕 Multi-deployment management
- 🆕 Cost optimization features

## 🚨 Common Issues

### Issue: Import errors after update

```bash
ModuleNotFoundError: No module named 'n8n_aws_serverless'
```

**Solution**: Update all imports to use `n8n_deploy` instead.

### Issue: CDK bootstrap required

```bash
Error: This stack uses assets, so the toolkit stack must be deployed
```

**Solution**: Re-run CDK bootstrap:
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Issue: Configuration not found

```bash
Error: system.yaml not found
```

**Solution**: Ensure you're in the project root directory and have copied your `system.yaml`.

## 📦 Migration Script

For automated migration of existing deployments:

```bash
#!/bin/bash
# migrate-to-n8n-deploy.sh

echo "🚀 Migrating to n8n Deploy..."

# Update git remote (if needed)
if git remote -v | grep -q "n8n-aws-serverless"; then
    echo "Updating git remote..."
    git remote set-url origin https://github.com/your-org/n8n-deploy
fi

# Update Python imports in custom scripts
if [ -d "custom_scripts" ]; then
    echo "Updating Python imports..."
    find custom_scripts -name "*.py" -type f -exec sed -i '' 's/n8n_aws_serverless/n8n_deploy/g' {} +
fi

# Clean and reinstall
echo "Cleaning environment..."
rm -rf .venv __pycache__ .pytest_cache .coverage
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

echo "✅ Migration complete!"
echo "Run 'make test' to verify everything works."
```

## 🤝 Getting Help

- **Documentation**: [docs.n8n-deploy.dev](https://docs.n8n-deploy.dev)
- **Migration Support**: [GitHub Discussions](https://github.com/your-org/n8n-deploy/discussions)
- **Issues**: [GitHub Issues](https://github.com/your-org/n8n-deploy/issues)

## 🎉 Welcome to n8n Deploy!

You now have access to a much more powerful platform that can deploy n8n anywhere. Explore the new features and let us know if you need any help with the migration!