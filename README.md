# n8n Deploy

> 🚀 **Deploy n8n anywhere** - AWS Serverless, Docker, or On-Premise - with enterprise features at personal costs

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![AWS CDK](https://img.shields.io/badge/aws--cdk-2.0+-orange.svg)](https://aws.amazon.com/cdk/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![n8n](https://img.shields.io/badge/n8n-1.94.1-red.svg)](https://n8n.io/)
[![Tests](https://github.com/your-org/n8n-deploy/actions/workflows/test.yml/badge.svg)](https://github.com/your-org/n8n-deploy/actions/workflows/test.yml)

**n8n Deploy** is a comprehensive deployment platform for [n8n](https://n8n.io/) workflow automation. Whether you need a $5/month personal instance, a scalable cloud deployment, or an on-premise solution with zero-trust security, n8n Deploy has you covered.

## 🎯 Choose Your Deployment

<table>
<tr>
<td width="33%" align="center">

### ☁️ AWS Serverless
**From $5/month**

Perfect for personal projects and startups. Auto-scaling, managed infrastructure, pay-per-use.

[Deploy to AWS →](#aws-serverless-deployment)

</td>
<td width="33%" align="center">

### 🐳 Docker Local
**Free**

Ideal for development, testing, or self-hosted deployments. Full control, no cloud costs.

[Run Locally →](#docker-local-deployment)

</td>
<td width="33%" align="center">

### 🔒 Cloudflare Tunnel
**Zero-Trust Access**

Enterprise security without complexity. No public IPs, built-in DDoS protection.

[Setup Tunnel →](#cloudflare-tunnel-deployment)

</td>
</tr>
</table>

## 🌟 Why n8n Deploy?

- **🎛️ One Platform, Multiple Targets**: Same configuration deploys to AWS, Docker, or hybrid setups
- **💰 Cost-Optimized**: Start from $5/month on AWS, or run free locally
- **🔧 Production-Ready**: Monitoring, backups, auto-scaling, and disaster recovery included
- **🛡️ Enterprise Security**: Zero-trust options, secrets management, compliance templates
- **📊 Full Observability**: Built-in dashboards for n8n metrics, costs, and performance
- **🚀 Quick Start**: Deploy in under 5 minutes with sensible defaults

## 📊 Deployment Comparison

| Feature | AWS Serverless | Docker Local | Cloudflare Tunnel |
|---------|---------------|--------------|-------------------|
| **Starting Cost** | $5-10/month | Free | Free (<50 users) |
| **Scaling** | Auto-scaling | Manual | Manual |
| **Maintenance** | Fully managed | Self-managed | Self-managed |
| **Public IP Required** | No | Optional | No |
| **SSL/TLS** | Automatic | Manual/Let's Encrypt | Automatic |
| **Monitoring** | CloudWatch | Prometheus/Grafana | Cloudflare Analytics |
| **Backup** | Automated | Manual/Scripted | Manual/Scripted |
| **Best For** | SaaS, Startups | Development, On-premise | Zero-trust, Enterprise |

## 🚀 Quick Start

### AWS Serverless Deployment

```bash
# Install and deploy in one command
curl -sSL https://n8n-deploy.dev/install.sh | bash -s -- --aws

# Or use the manual approach
git clone https://github.com/your-org/n8n-deploy
cd n8n-deploy
make install
make deploy-aws environment=production
```

### Docker Local Deployment

```bash
# Development environment with UI
curl -sSL https://n8n-deploy.dev/install.sh | bash -s -- --docker

# Or use docker-compose directly
git clone https://github.com/your-org/n8n-deploy
cd n8n-deploy
make local-up
```

### Cloudflare Tunnel Deployment

```bash
# Deploy with zero-trust access
curl -sSL https://n8n-deploy.dev/install.sh | bash -s -- --cloudflare

# Or manual setup
git clone https://github.com/your-org/n8n-deploy
cd n8n-deploy
./scripts/setup-cloudflare-tunnel.sh
```

## 📋 Features

### Core Features
- ✅ **Multi-deployment support**: AWS, Docker, Kubernetes, Cloudflare
- ✅ **Configuration-driven**: Single `system.yaml` for all settings
- ✅ **Environment management**: Dev, staging, production presets
- ✅ **Cost optimization**: Spot instances, auto-scaling, resource limits
- ✅ **Security first**: Secrets management, IAM roles, network isolation

### AWS Serverless Features
- 🚀 **ECS Fargate**: Serverless containers with Spot support (70% savings)
- 💾 **Flexible Storage**: EFS for workflows, optional RDS for scale
- 🌐 **API Gateway**: Cost-effective alternative to load balancers
- 📊 **CloudWatch**: Full monitoring and alerting
- 🔄 **Auto-scaling**: CPU/memory-based scaling policies

### Docker Features
- 🐳 **Production-ready**: Nginx reverse proxy, SSL, health checks
- 📊 **Full monitoring**: Prometheus, Grafana, and n8n dashboards
- 💾 **Multiple databases**: SQLite, PostgreSQL, MySQL support
- 🔄 **Automated backups**: Scheduled backups with retention
- 🔧 **Development mode**: Hot-reload and debugging tools

### Cloudflare Tunnel Features
- 🔒 **Zero-trust networking**: No exposed ports or public IPs
- 🌍 **Global edge network**: Built-in DDoS protection
- 👥 **Access control**: Email/domain-based authentication
- 📊 **Analytics**: Real-time metrics and security insights
- 🚀 **Easy setup**: One-command tunnel creation

## 📁 Project Structure

```
n8n-deploy/
├── deployments/              # Deployment configurations
│   ├── aws/                 # AWS CDK infrastructure
│   │   ├── stacks/         # CDK stack definitions
│   │   └── constructs/     # Reusable components
│   ├── docker/             # Docker configurations
│   │   ├── compose/        # Docker Compose files
│   │   └── dockerfiles/    # Custom Dockerfiles
│   └── cloudflare/         # Tunnel configurations
├── scripts/                 # Automation scripts
│   ├── install.sh          # Universal installer
│   ├── deploy.sh           # Deployment automation
│   └── backup.sh           # Backup utilities
├── config/                  # Configuration files
│   ├── system.yaml         # Main configuration
│   └── examples/           # Example configs
├── monitoring/              # Monitoring configurations
│   ├── dashboards/         # Grafana dashboards
│   └── alerts/             # Alert rules
├── docs/                    # Documentation
└── tests/                   # Test suites
```

## 🔧 Configuration

All deployments use a unified `system.yaml` configuration:

```yaml
# config/system.yaml
project:
  name: "my-n8n"
  deployment_type: "aws"  # or "docker", "cloudflare"

environments:
  production:
    n8n:
      version: "1.94.1"
      encryption_key: "{{ secrets.n8n_encryption_key }}"
    
    # AWS-specific settings
    aws:
      account: "123456789012"
      region: "us-east-1"
      fargate:
        cpu: 512
        memory: 1024
        spot_enabled: true
    
    # Docker-specific settings
    docker:
      compose_profile: "production"
      postgres_enabled: true
      redis_enabled: true
    
    # Cloudflare-specific settings
    cloudflare:
      tunnel_name: "n8n-production"
      access_policy:
        allowed_emails: ["admin@example.com"]
        allowed_domains: ["example.com"]
```

## 📚 Documentation

- **[Getting Started](docs/getting-started.md)** - Interactive deployment guide
- **[Architecture Overview](docs/architecture.md)** - System design and components
- **[Deployment Guide](docs/deployment-guide.md)** - Detailed deployment instructions
- **[Cost Optimization](docs/cost-optimization.md)** - Save money on cloud deployments
- **[Security Best Practices](docs/security.md)** - Hardening and compliance
- **[Monitoring & Alerts](docs/monitoring.md)** - Observability setup
- **[Disaster Recovery](docs/disaster-recovery.md)** - Backup and restore procedures
- **[Local Development](docs/local-development.md)** - Development environment setup
- **[Migration Guide](docs/migration.md)** - Migrate from other n8n deployments

## 💰 Cost Examples

### Personal Use (AWS)
- **Minimal**: ~$5-10/month (256 CPU, 512MB RAM, SQLite)
- **Standard**: ~$15-20/month (512 CPU, 1GB RAM, PostgreSQL)

### Team Use (AWS)
- **Small Team**: ~$30-50/month (1024 CPU, 2GB RAM, RDS)
- **Medium Team**: ~$75-100/month (2048 CPU, 4GB RAM, Aurora)

### Enterprise (Hybrid)
- **Cloudflare + AWS**: ~$50-100/month (High availability, zero-trust)
- **On-premise + Cloudflare**: Infrastructure cost only

## 🛠️ Development

```bash
# Setup development environment
make install-dev

# Run tests
make test

# Run linting
make lint

# Start local development
make local-up

# Deploy to AWS dev environment
make deploy-dev

# View costs
make costs environment=production
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [n8n](https://n8n.io/) - The fantastic workflow automation tool
- [AWS CDK](https://aws.amazon.com/cdk/) - Infrastructure as code framework
- [Cloudflare](https://www.cloudflare.com/) - Zero-trust networking
- All our contributors and users

## 🔗 Links

- **Documentation**: [https://docs.n8n-deploy.dev](https://docs.n8n-deploy.dev)
- **Issues**: [GitHub Issues](https://github.com/your-org/n8n-deploy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/n8n-deploy/discussions)
- **Blog**: [https://blog.n8n-deploy.dev](https://blog.n8n-deploy.dev)

---

<p align="center">
  Made with ❤️ by the n8n Deploy community
</p>