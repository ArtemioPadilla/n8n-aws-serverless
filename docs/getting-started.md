# Getting Started with n8n Deploy

Welcome to n8n Deploy! This guide will help you choose the best deployment option and get n8n running in under 5 minutes.

## 🎯 Quick Deployment Selector

Answer these questions to find your ideal deployment:

<details>
<summary><b>1. What's your primary goal?</b></summary>

- **Just trying n8n** → [Docker Local](#docker-local-quick-start)
- **Personal automation** → [AWS Minimal](#aws-minimal-deployment)
- **Team collaboration** → [AWS Standard](#aws-standard-deployment)
- **Enterprise deployment** → [AWS Enterprise](#aws-enterprise-deployment)
- **Maximum security** → [Cloudflare Tunnel](#cloudflare-tunnel-deployment)

</details>

<details>
<summary><b>2. What's your budget?</b></summary>

- **Free** → [Docker Local](#docker-local-quick-start)
- **$5-10/month** → [AWS Minimal](#aws-minimal-deployment)
- **$15-50/month** → [AWS Standard](#aws-standard-deployment)
- **$50+/month** → [AWS Enterprise](#aws-enterprise-deployment)

</details>

<details>
<summary><b>3. What's your technical expertise?</b></summary>

- **Beginner** → [Docker Local](#docker-local-quick-start) or [AWS Minimal](#aws-minimal-deployment)
- **Intermediate** → [AWS Standard](#aws-standard-deployment) or [Docker Production](#docker-production-deployment)
- **Advanced** → [Any option with custom configuration](#advanced-configuration)

</details>

## 🚀 Deployment Options

### Docker Local Quick Start

**Perfect for**: Development, testing, learning n8n

```bash
# One-command setup
curl -sSL https://raw.githubusercontent.com/your-org/n8n-deploy/main/scripts/install.sh | bash -s -- --local

# Or manual setup
git clone https://github.com/your-org/n8n-deploy
cd n8n-deploy
make local-up
```

**What you get:**

- n8n running on <http://localhost:5678>
- SQLite database (upgradeable to PostgreSQL)
- Persistent data in `./n8n-data`
- Optional monitoring with Grafana

[📖 Detailed Local Setup Guide →](local-development.md)

### AWS Minimal Deployment

**Perfect for**: Personal projects, cost-conscious users

```bash
# Prerequisites
npm install -g aws-cdk
pip install -r requirements.txt

# Deploy
cdk bootstrap  # First time only
cdk deploy -c environment=production -c stack_type=minimal
```

**What you get:**

- ECS Fargate with Spot instances (256 CPU, 512MB RAM)
- API Gateway endpoint
- EFS storage with SQLite
- ~$5-10/month cost

**Configuration** (`config/system.yaml`):

```yaml
environments:
  production:
    stack_type: minimal
    n8n:
      resources:
        cpu: 256
        memory: 512
    database:
      type: sqlite
```

[📖 AWS Deployment Details →](deployment-guide.md#aws-minimal)

### AWS Standard Deployment

**Perfect for**: Small teams, production workloads

```bash
# Deploy with monitoring and PostgreSQL
cdk deploy -c environment=production -c stack_type=standard
```

**What you get:**

- ECS Fargate (512 CPU, 1GB RAM)
- RDS PostgreSQL database
- CloudWatch monitoring
- Auto-scaling enabled
- ~$15-30/month cost

**Configuration** (`config/system.yaml`):

```yaml
environments:
  production:
    stack_type: standard
    n8n:
      resources:
        cpu: 512
        memory: 1024
    database:
      type: postgresql
      instance_class: db.t4g.micro
    monitoring:
      enabled: true
```

[📖 AWS Standard Setup →](deployment-guide.md#aws-standard)

### AWS Enterprise Deployment

**Perfect for**: Large teams, high availability requirements

```bash
# Deploy with all features
cdk deploy -c environment=production -c stack_type=enterprise
```

**What you get:**

- High-performance Fargate (2048 CPU, 4GB RAM)
- Aurora PostgreSQL Serverless
- Multi-AZ deployment
- Advanced monitoring and alerting
- Backup and disaster recovery
- ~$50-100/month cost

[📖 Enterprise Setup Guide →](deployment-guide.md#aws-enterprise)

### Cloudflare Tunnel Deployment

**Perfect for**: Zero-trust security, no public IPs

```bash
# Setup Cloudflare Tunnel with any backend
./scripts/setup-cloudflare-tunnel.sh

# Or use with AWS
cdk deploy -c environment=production -c access_type=cloudflare
```

**What you get:**

- No exposed ports or public IPs
- Global edge network
- Built-in DDoS protection
- Email/domain-based access control
- Works with any backend (AWS, Docker, on-premise)

[📖 Cloudflare Tunnel Guide →](cloudflare-tunnel.md)

### Docker Production Deployment

**Perfect for**: On-premise, full control

```bash
# Deploy production Docker stack
cd docker/production
docker-compose up -d

# With monitoring
docker-compose --profile monitoring up -d
```

**What you get:**

- Production-ready Docker stack
- Nginx reverse proxy with SSL
- PostgreSQL database
- Automated backups
- Optional monitoring stack

[📖 Docker Production Guide →](deployment-guide.md#docker-production)

## 📋 Pre-Deployment Checklist

### For AWS Deployments

- [ ] AWS Account with appropriate permissions
- [ ] AWS CLI configured (`aws configure`)
- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] Domain name (optional)

### For Docker Deployments

- [ ] Docker Engine installed
- [ ] Docker Compose v2+
- [ ] 2GB+ free disk space
- [ ] Domain name (for production)

### For Cloudflare Tunnel

- [ ] Cloudflare account (free tier works)
- [ ] Domain added to Cloudflare
- [ ] Backend deployment ready

## 🔧 Initial Configuration

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/n8n-deploy
cd n8n-deploy
```

### 2. Configure Your Deployment

```bash
# Copy example configuration
cp config/examples/system.yaml config/system.yaml

# Edit with your settings
nano config/system.yaml
```

### 3. Set Required Secrets

#### For AWS

```bash
# Create n8n encryption key
aws secretsmanager create-secret \
  --name /n8n/prod/encryption-key \
  --secret-string $(openssl rand -base64 32)
```

#### For Docker

```bash
# Create .env file
cp .env.example .env
nano .env

# Generate encryption key
echo "N8N_ENCRYPTION_KEY=$(openssl rand -base64 32)" >> .env
```

## 🎯 Post-Deployment Steps

### 1. Access n8n

- **Docker Local**: <http://localhost:5678>
- **AWS**: Check CloudFormation outputs for URL
- **Cloudflare**: <https://your-domain.com>

### 2. Create Admin Account

1. Navigate to n8n URL
2. Click "Setup owner account"
3. Enter email and password
4. Save credentials securely

### 3. Configure Workflows

1. Import existing workflows (if any)
2. Set up credentials for integrations
3. Test a simple workflow

### 4. Setup Monitoring

#### AWS

```bash
# View CloudWatch dashboard
make view-dashboard environment=production
```

#### Docker

```bash
# Access Grafana
open http://localhost:3000
# Default: admin/admin
```

## 🚨 Troubleshooting

### Common Issues

<details>
<summary><b>Cannot access n8n</b></summary>

1. Check container/task is running:

   ```bash
   # Docker
   docker ps

   # AWS
   aws ecs list-tasks --cluster n8n-prod
   ```

2. Check logs:

   ```bash
   # Docker
   docker logs n8n

   # AWS
   make logs environment=production
   ```

3. Verify security groups/firewall rules

</details>

<details>
<summary><b>Database connection errors</b></summary>

1. Verify database is running
2. Check connection string in environment
3. Ensure network connectivity
4. Review database logs

</details>

<details>
<summary><b>Workflows not persisting</b></summary>

1. Check volume mounts (Docker)
2. Verify EFS mount (AWS)
3. Check file permissions
4. Review n8n logs for errors

</details>

## 📚 Next Steps

### Essential Reading

1. [Architecture Overview](architecture.md) - Understand the system design
2. [Security Best Practices](security.md) - Harden your deployment
3. [Backup & Recovery](disaster-recovery.md) - Protect your data

### Advanced Topics

1. [Cost Optimization](cost-optimization.md) - Reduce your AWS bill
2. [Monitoring Setup](monitoring.md) - Deep observability
3. [Scaling Guide](scaling.md) - Handle growth
4. [CI/CD Integration](ci-cd.md) - Automate deployments

### Get Help

- 📖 [Full Documentation](https://docs.n8n-deploy.dev)
- 💬 [GitHub Discussions](https://github.com/your-org/n8n-deploy/discussions)
- 🐛 [Report Issues](https://github.com/your-org/n8n-deploy/issues)
- 📧 [Email Support](mailto:support@n8n-deploy.dev)

## 🎉 You're Ready

Congratulations! You now have n8n running with enterprise features. Start building your automation workflows and join our community for tips and best practices.

---

**Pro Tip**: Star the repository to stay updated with new features and improvements! ⭐
