# n8n AWS Serverless

> 🚀 Deploy n8n workflow automation on AWS using serverless infrastructure for maximum cost efficiency, or run it locally/on-premise with Docker

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![AWS CDK](https://img.shields.io/badge/aws--cdk-2.0+-orange.svg)](https://aws.amazon.com/cdk/)
[![n8n](https://img.shields.io/badge/n8n-1.94.1-red.svg)](https://n8n.io/)
[![Tests](https://github.com/your-org/n8n-aws-serverless/actions/workflows/test.yml/badge.svg)](https://github.com/your-org/n8n-aws-serverless/actions/workflows/test.yml)

Deploy [n8n](https://n8n.io/), the workflow automation tool, on AWS using a cost-optimized serverless architecture or run it locally/on-premise with Docker. This project uses AWS CDK to provision infrastructure that can scale from $5/month for personal use to enterprise-grade deployments, with full support for local development and on-premise installations.

## 🌟 Features

- **💰 Cost-Optimized**: Start from ~$5/month using Fargate Spot, API Gateway, and EFS
- **🔧 Flexible Deployment**: Support for SQLite (small workloads) or PostgreSQL (production)
- **🚀 Auto-Scaling**: Automatic scaling based on CPU/memory utilization
- **🔒 Secure by Default**: VPC isolation, secrets management, IAM roles
- **🌍 Multi-Environment**: Separate dev, staging, and production deployments
- **📊 Full Monitoring**: CloudWatch dashboards, alarms, and log aggregation
- **🐳 Local Development**: Docker Compose setup for local testing and on-premise deployments
- **♻️ Infrastructure as Code**: Fully automated with AWS CDK
- **🛡️ Enhanced Security**: Pinned versions, security scanning, IAM best practices
- **📈 Custom Metrics**: n8n-specific monitoring and performance tracking
- **🔄 Resilience**: Dead letter queues, circuit breakers, auto-recovery
- **🚨 Disaster Recovery**: Automated backups, cross-region replication, documented procedures

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Configuration](#-configuration)
- [Deployment Options](#-deployment-options)
- [Local Development](#-local-development)
- [Cost Optimization](#-cost-optimization)
- [Monitoring](#-monitoring)
- [Security](#-security)
- [Contributing](#-contributing)
- [License](#-license)

## 🏗 Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ CloudFront  │────▶│ API Gateway │────▶│   Fargate   │
│   (CDN)     │     │  (HTTP API) │     │    (n8n)    │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │     EFS     │     │ RDS/Aurora  │
                    │  (Storage)  │     │ (Optional)  │
                    └─────────────┘     └─────────────┘
```

### Key Components:
- **API Gateway HTTP API**: Cost-effective alternative to ALB ( \$1/million requests vs \$16/month)
- **ECS Fargate**: Serverless containers with Spot instance support (70% cost savings)
- **EFS**: Shared persistent storage for workflows and SQLite database
- **RDS/Aurora** (Optional): PostgreSQL for production workloads
- **CloudFront** (Optional): Global CDN with caching and WAF protection

## 📚 Prerequisites

- **AWS Account** with appropriate permissions
- **Python 3.8+** installed
- **Node.js 16+** installed (for CDK CLI)
- **Docker** installed (for local development)
- **AWS CLI** configured with credentials

### Quick Install:
```bash
# Install AWS CDK globally
npm install -g aws-cdk

# Install Python dependencies
pip install -r requirements.txt

# Bootstrap CDK (one-time per account/region)
cdk bootstrap
```

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/n8n-aws-serverless.git
cd n8n-aws-serverless
```

### 2. Configure Your Deployment
```bash
# Copy and edit configuration
cp system.yaml.example system.yaml

# Edit with your AWS account details
vim system.yaml
```

### 3. Deploy to AWS
```bash
# Deploy development environment
cdk deploy -c environment=dev

# Deploy production environment
cdk deploy -c environment=production
```

### 4. Access n8n
After deployment completes, you'll get URLs to access n8n:
- API Gateway: `https://xxxxxx.execute-api.region.amazonaws.com`
- CloudFront (if enabled): `https://xxxxxx.cloudfront.net`

## ⚙️ Configuration

The project uses `system.yaml` for all configuration. Key settings include:

```yaml
environments:
  dev:
    account: "123456789012"
    region: "us-east-1"
    settings:
      fargate:
        cpu: 256        # 0.25 vCPU
        memory: 512     # 0.5 GB
        spot_percentage: 80
      scaling:
        min_tasks: 1
        max_tasks: 3
      database:
        type: "sqlite"  # or "postgres"
```

See [docs/configuration.md](docs/configuration.md) for detailed configuration options.

## 🎯 Deployment Options

### Minimal ($5-10/month)
Perfect for personal use or testing:
```bash
cdk deploy -c environment=dev -c stack_type=minimal
```
- SQLite database
- Single Fargate task
- No backups or monitoring

### Standard ($15-30/month)
Recommended for small teams:
```bash
cdk deploy -c environment=staging -c stack_type=standard
```
- PostgreSQL database
- Auto-scaling (1-5 tasks)
- Basic monitoring and backups

### Enterprise ($50-100/month)
For production workloads:
```bash
cdk deploy -c environment=production -c stack_type=enterprise
```
- Aurora Serverless PostgreSQL
- Multi-AZ deployment
- Full monitoring, backups, and WAF

## 💻 Local Development & On-Premise Deployment

### Quick Start (Local/On-Premise)
```bash
# Setup local environment
./scripts/local-setup.sh

# Start n8n with Docker Compose
./scripts/local-deploy.sh

# Access at http://localhost:5678
```

### Development Options
```bash
# With PostgreSQL (recommended for production)
./scripts/local-deploy.sh -p postgres

# With monitoring stack (Prometheus + Grafana)
./scripts/local-deploy.sh -m

# With all features (PostgreSQL + Monitoring)
./scripts/local-deploy.sh -p postgres -m

# View logs
./scripts/local-deploy.sh -l

# Stop all containers
./scripts/local-deploy.sh -d
```

### Local Monitoring Stack
When using the `-m` flag, you get:
- **Prometheus**: http://localhost:9090 - Metrics collection and querying
- **Grafana**: http://localhost:3000 - Dashboards and visualization
  - Default login: admin / admin (check `.env` for custom password)
  - Pre-configured n8n dashboard
  - PostgreSQL and Redis metrics (when using respective profiles)

### On-Premise Production Deployment
```bash
# Use production Docker Compose
cd docker
docker-compose -f docker-compose.prod.yml up -d

# This includes:
# - n8n with PostgreSQL database
# - Nginx reverse proxy with SSL
# - Redis for queue management
# - Automated backups
```

## 💰 Cost Optimization

| Component | Strategy | Savings |
|-----------|----------|---------|
| Compute | Fargate Spot instances | 70% |
| Database | SQLite for <5K executions/day | 100% |
| API | API Gateway vs ALB | $15/month |
| Storage | EFS Lifecycle policies | 90% |

See [docs/cost-optimization.md](docs/cost-optimization.md) for detailed strategies.

## 📊 Monitoring

The stack includes comprehensive monitoring:

- **CloudWatch Dashboards**: CPU, memory, and custom metrics
- **Alarms**: Automated alerts for issues
- **Logs**: Centralized logging with search
- **X-Ray** (Optional): Distributed tracing

Access the dashboard:
```bash
# Get dashboard URL
aws cloudformation describe-stacks \
  --stack-name n8n-serverless-{env}-monitoring \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardUrl`].OutputValue'
```

## 🔒 Security

Built-in security features:

- **Network Isolation**: VPC with private subnets
- **Secrets Management**: AWS Secrets Manager integration
- **Encryption**: At-rest and in-transit
- **IAM Roles**: Least privilege access
- **WAF** (Optional): Protection against common attacks
- **Version Pinning**: All dependencies use specific versions
- **Security Scanning**: Automated secrets and vulnerability scanning
- **Compliance**: SOC2/HIPAA ready configurations available

### Security Testing
```bash
# Run security tests
pytest -m security

# Scan for secrets
make security-scan
```

## 🧪 Testing

### Unit & Integration Tests
```bash
# Run all tests
pytest

# Run with coverage (80% minimum required)
pytest --cov=n8n_aws_serverless

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests
pytest -m security      # Security tests
pytest -m performance   # Performance benchmarks
```

### Code Quality
```bash
# Run linting
black --check .
flake8 .
isort --check-only .

# Auto-fix formatting
make format

# Run all checks
make check
```

### Performance Testing
```bash
# Run performance benchmarks
./scripts/performance-test.sh -u https://n8n.example.com -t baseline

# Load testing
./scripts/performance-test.sh -u https://n8n.example.com -t load -c 50
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Run tests before committing
pytest
```

## 📖 Documentation

### Getting Started
- [Getting Started](docs/getting-started.md)
- [Local Development](docs/local-development.md)
- [Local Monitoring](docs/local-monitoring.md)

### Deployment & Operations
- [Architecture Overview](docs/architecture.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Configuration Reference](docs/configuration.md)
- [Monitoring & Alerts](docs/monitoring.md)

### Best Practices
- [Cost Optimization](docs/cost-optimization.md)
- [Security Best Practices](docs/security.md)
- [Disaster Recovery](docs/disaster-recovery.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🛟 Support

- **Documentation**: See the [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/your-org/n8n-aws-serverless/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/n8n-aws-serverless/discussions)
- **n8n Community**: [community.n8n.io](https://community.n8n.io)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [n8n](https://n8n.io/) - The workflow automation tool
- [AWS CDK](https://aws.amazon.com/cdk/) - Infrastructure as Code framework
- [AWS Fargate](https://aws.amazon.com/fargate/) - Serverless container platform

---

**Made with ❤️ by the community**

*If you find this project useful, please ⭐ star it on GitHub!*