# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**n8n Deploy** is a comprehensive deployment platform for n8n workflow automation that supports multiple deployment targets:

- **AWS Serverless**: Cost-optimized cloud deployment using ECS Fargate, API Gateway, and managed services
- **Docker**: Local development and on-premise production deployments
- **Cloudflare Tunnel**: Zero-trust access layer that works with any backend
- **Hybrid**: Combinations like AWS + Cloudflare or Docker + Cloudflare

The platform provides enterprise-grade features at costs ranging from free (local Docker) to $5-100/month (AWS), making it suitable for everything from personal projects to enterprise deployments.

## Key Features

- **Multi-deployment support**: AWS, Docker, Kubernetes, Cloudflare Tunnel
- **Configuration-driven**: Single `system.yaml` controls all deployment types
- **Cost-optimized**: From free (Docker) to $5/month (AWS minimal) to enterprise
- **Zero-trust security**: Optional Cloudflare Tunnel with no public IPs
- **Production-ready**: Monitoring, backups, auto-scaling, disaster recovery
- **Developer-friendly**: Local development, hot-reload, comprehensive testing
- **CI/CD ready**: GitHub Actions, automated testing, multi-environment deployments

## Development Commands

### Quick Start

```bash
# Setup environment
make install

# Run tests
make test

# Start local n8n
make local-up

# Deploy to AWS
make deploy-dev
```

### Common Commands

```bash
# CDK deployment
cdk deploy -c environment=dev
cdk deploy -c environment=production
cdk deploy -c environment=dev -c stack_type=minimal

# Local development
./scripts/local-setup.sh    # One-time setup
./scripts/local-deploy.sh   # Start n8n locally
./scripts/local-test.sh     # Test local deployment

# Testing
pytest                      # Run all tests
pytest --cov               # With coverage
tox                        # Multi-environment testing
make lint                  # Run linting
make format                # Format code
```

## Project Architecture

### Directory Structure

```
n8n-deploy/
├── deployments/              # Deployment configurations
│   ├── aws/                 # AWS CDK infrastructure
│   │   ├── stacks/         # CDK stack definitions
│   │   │   ├── base_stack.py
│   │   │   ├── network_stack.py
│   │   │   ├── storage_stack.py
│   │   │   ├── compute_stack.py
│   │   │   ├── database_stack.py
│   │   │   ├── access_stack.py
│   │   │   └── monitoring_stack.py
│   │   └── constructs/     # Reusable CDK constructs
│   ├── docker/             # Docker configurations
│   │   ├── local/         # Development setup
│   │   ├── production/    # Production deployment
│   │   └── compose/       # Docker Compose files
│   └── cloudflare/        # Tunnel configurations
├── config/                  # Configuration management
│   ├── system.yaml         # Main configuration
│   └── examples/           # Example configs
├── scripts/                # Automation scripts
├── tests/                  # Test suite
├── docs/                   # Documentation
└── monitoring/             # Dashboards and alerts
```

### Configuration-Driven Architecture

All deployment types use the unified `system.yaml`:

```yaml
project:
  name: "my-n8n"
  deployment_type: "aws"  # or "docker", "cloudflare"

environments:
  production:
    # Common settings
    n8n:
      version: "1.94.1"
      encryption_key: "{{ secrets.n8n_encryption_key }}"

    # AWS-specific
    aws:
      account: "123456789012"
      region: "us-east-1"
      fargate:
        cpu: 512
        memory: 1024
        spot_enabled: true

    # Docker-specific
    docker:
      compose_profile: "production"
      postgres_enabled: true

    # Cloudflare-specific
    cloudflare:
      tunnel_name: "n8n-production"
      access_policy:
        allowed_emails: ["admin@example.com"]
```

### Stack Dependencies

1. **NetworkStack**: VPC, subnets, security groups
2. **StorageStack**: EFS for persistent storage (depends on Network)
3. **DatabaseStack**: Optional RDS/Aurora (depends on Network)
4. **ComputeStack**: ECS Fargate service (depends on Network, Storage)
5. **AccessStack**: API Gateway + CloudFront OR Cloudflare Tunnel (depends on Compute)
6. **MonitoringStack**: CloudWatch dashboards and alarms (depends on all)

## Testing Strategy

### Unit Tests

- Test each stack independently with mocked dependencies
- Verify resource creation and configuration
- Check IAM policies and security settings

### Integration Tests

- Test stack interactions
- Verify end-to-end deployment
- Local Docker Compose testing

### Coverage Requirements

- Minimum 80% code coverage
- Coverage reports in HTML and XML formats
- Pre-commit hooks for code quality

## Cost Optimization

The project is designed for cost efficiency:

1. **Fargate Spot**: 70% cost reduction
2. **API Gateway**: $1/million requests (vs $16/month for ALB)
3. **Cloudflare Tunnel**: $0/month (free tier) vs API Gateway + ALB costs
4. **SQLite on EFS**: Free database for small workloads
5. **Auto-scaling**: Scale down during low usage

## Security Considerations

- VPC isolation with private subnets
- Secrets Manager for credentials
- IAM roles with least privilege
- Encryption at rest and in transit
- Optional WAF for production

## Local Development

### Docker Compose Setup

- Development configuration with SQLite
- Production-like setup with PostgreSQL
- Optional monitoring stack (Prometheus + Grafana)

### Testing Locally

```bash
# Start services
./scripts/local-deploy.sh

# Run with PostgreSQL
./scripts/local-deploy.sh -p postgres

# With monitoring
./scripts/local-deploy.sh -m

# With Cloudflare Tunnel
./scripts/local-deploy.sh -p cloudflare
```

## Deployment Patterns

### Environment Types

- **local**: Docker-based development
- **dev**: Minimal AWS resources
- **staging**: Production-like with lower scale
- **production**: Full HA with monitoring

### Stack Types

- **minimal**: Basic n8n ($5-10/month)
- **standard**: With monitoring ($15-30/month)
- **enterprise**: Full features ($50-100/month)

## Best Practices

1. **Always run tests before deployment**

   ```bash
   make check  # Runs lint + test
   ```

2. **Use configuration for all settings**
   - Avoid hardcoding values
   - Use system.yaml for environment-specific config

3. **Follow the existing patterns**
   - Inherit from N8nBaseStack
   - Use consistent naming via get_resource_name()
   - Apply proper tagging

4. **Security first**
   - Never commit secrets
   - Use Secrets Manager for sensitive data
   - Follow least privilege for IAM

5. **Cost awareness**
   - Use Spot instances for non-production
   - Enable auto-scaling
   - Set up cost alerts
   - Consider Cloudflare Tunnel for zero-cost access

## Cloudflare Tunnel Support

The project supports Cloudflare Tunnel as an alternative to API Gateway:

### Benefits

- **Zero cost**: Free tier supports up to 50 users
- **No public IPs**: Outbound-only connections
- **Built-in DDoS protection**: Cloudflare's global network
- **Zero-trust security**: Email/domain-based access policies

### Configuration

```yaml
access:
  type: "cloudflare"  # Instead of "api_gateway"
  cloudflare:
    enabled: true
    tunnel_token_secret_name: "n8n/prod/cloudflare-tunnel-token"
    tunnel_name: "n8n-production"
    tunnel_domain: "n8n.example.com"
    access_enabled: true
    access_allowed_emails:
      - "admin@example.com"
    access_allowed_domains:
      - "example.com"
```

### Token Rotation

```bash
# Rotate Cloudflare tunnel token
./scripts/cloudflare-tunnel-rotate.sh -e production -r
```

## Project Evolution

This project has evolved from a simple AWS serverless deployment tool into a comprehensive n8n deployment platform. Key additions include:

### Multi-Platform Support

- **AWS Serverless**: Original focus, now enhanced with more options
- **Docker Local**: Full development environment with monitoring
- **Docker Production**: Enterprise-ready on-premise deployment
- **Cloudflare Tunnel**: Zero-trust networking for any backend

### Advanced Features

- **Unified Configuration**: One `system.yaml` for all deployment types
- **Cost Tiers**: From free to enterprise with clear pricing
- **Security Options**: Basic auth to zero-trust with Cloudflare
- **Monitoring**: Built-in Prometheus/Grafana for all deployments
- **Backup/Recovery**: Automated across all platforms

### Use Cases

- **Personal**: Free local or $5/month AWS
- **Startup**: $15-30/month with auto-scaling
- **Enterprise**: $50-100/month with HA and compliance
- **Hybrid**: Mix platforms (e.g., AWS + Cloudflare)

The name "n8n Deploy" better reflects this expanded scope as a complete deployment solution rather than just an AWS tool.
