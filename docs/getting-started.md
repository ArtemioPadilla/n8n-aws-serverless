# Getting Started with n8n AWS Serverless

This guide will help you get started with deploying n8n using AWS serverless infrastructure or running it locally/on-premise with Docker.

## Prerequisites

Before you begin, ensure you have the following installed:

### For AWS Deployment:
- **Python 3.8+**: Required for AWS CDK
- **Node.js 16+**: Required for AWS CDK CLI
- **AWS CLI**: For AWS account configuration
- **AWS CDK CLI**: For deploying infrastructure

### For Local/On-Premise Deployment:
- **Docker**: Required for running n8n
- **Docker Compose**: For orchestrating services
- **Make** (optional): For using the Makefile commands

### Install AWS CDK

```bash
npm install -g aws-cdk
```

### AWS Account Setup

1. Configure AWS credentials:
```bash
aws configure
```

2. Bootstrap CDK in your AWS account:
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

## Quick Start

Choose your deployment method:

- [Local/On-Premise Deployment](#local-on-premise-quick-start)
- [AWS Cloud Deployment](#aws-cloud-quick-start)

### Local/On-Premise Quick Start

#### 1. Clone the Repository

```bash
git clone https://github.com/your-org/n8n-aws-serverless.git
cd n8n-aws-serverless
```

#### 2. Setup Local Environment

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run setup script
./scripts/local-setup.sh
```

#### 3. Start n8n Locally

```bash
# Basic setup with SQLite
./scripts/local-deploy.sh

# With PostgreSQL (recommended for production)
./scripts/local-deploy.sh -p postgres

# With full monitoring stack
./scripts/local-deploy.sh -p postgres -m
```

#### 4. Access n8n

- n8n UI: http://localhost:5678
- Default credentials: Check `.env` file in docker directory

### AWS Cloud Quick Start

#### 1. Clone the Repository

```bash
git clone https://github.com/your-org/n8n-aws-serverless.git
cd n8n-aws-serverless
```

#### 2. Setup Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 3. Configure Your Deployment

Copy and edit the configuration file:
```bash
cp system.yaml.example system.yaml
```

Update the following in `system.yaml`:
- AWS account IDs
- Regions
- Domain names (if using custom domains)
- Email addresses for alerts

#### 4. Deploy to AWS

Deploy to development environment:
```bash
cdk deploy -c environment=dev
```

Deploy to production:
```bash
cdk deploy -c environment=production
```

#### 5. Access n8n

After deployment, you'll receive URLs to access n8n:
- API Gateway URL: `https://xxx.execute-api.region.amazonaws.com`
- CloudFront URL: `https://xxx.cloudfront.net` (if enabled)
- Custom domain: `https://n8n.yourdomain.com` (if configured)

## Local Development

### 1. Setup Local Environment

```bash
./scripts/local-setup.sh
```

This script will:
- Check prerequisites
- Create necessary directories
- Generate SSL certificates
- Setup environment files

### 2. Start n8n Locally

#### Available Profiles
- **default**: SQLite database (lightweight, good for testing)
- **postgres**: PostgreSQL database (recommended for production-like environment)
- **monitoring**: Adds Prometheus and Grafana for metrics
- **scaling**: Adds Redis for queue management (can be combined with postgres)

Basic setup (SQLite):
```bash
./scripts/local-deploy.sh
```

With PostgreSQL:
```bash
./scripts/local-deploy.sh -p postgres
```

With monitoring only:
```bash
./scripts/local-deploy.sh -m
```

With PostgreSQL and monitoring (recommended):
```bash
./scripts/local-deploy.sh -p postgres -m
```

### 3. Access Local Services

#### n8n
- URL: http://localhost:5678
- Default credentials: Check `.env` file in docker directory
- Basic Auth User: `admin` (default)
- Basic Auth Password: Check `N8N_BASIC_AUTH_PASSWORD` in `.env`

#### Monitoring Stack (when using -m flag)
- **Prometheus**: http://localhost:9090
  - Query metrics directly
  - View targets status
  - Explore available metrics
  
- **Grafana**: http://localhost:3000
  - Default login: admin / admin
  - Pre-configured dashboards for n8n
  - Data source: Prometheus (pre-configured)

### 4. Managing Your Local Deployment

```bash
# View logs
./scripts/local-deploy.sh -l

# Check container status
./scripts/local-deploy.sh -s

# Restart containers
./scripts/local-deploy.sh -r

# Stop and remove all containers
./scripts/local-deploy.sh -d
```

### 5. Troubleshooting Local Deployment

#### Containers not starting?
1. Check if ports are already in use:
   ```bash
   lsof -i :5678  # n8n
   lsof -i :9090  # Prometheus
   lsof -i :3000  # Grafana
   ```

2. View container logs:
   ```bash
   ./scripts/local-deploy.sh -l
   ```

3. Reset everything:
   ```bash
   ./scripts/local-deploy.sh -d
   docker volume prune -f
   ./scripts/local-deploy.sh -p postgres -m
   ```

#### PostgreSQL connection issues?
- Ensure the postgres service is healthy before n8n starts
- Check credentials in `.env` file
- Verify `DB_TYPE` is set correctly for your profile

## Configuration Options

### Environment Types

- **local**: Docker-based local development
- **dev**: Development AWS environment
- **staging**: Staging AWS environment
- **production**: Production AWS environment

### Stack Types

- **minimal**: Basic n8n deployment (lowest cost)
- **standard**: Includes monitoring and backups
- **enterprise**: Full features with high availability

Example:
```bash
cdk deploy -c environment=dev -c stack_type=minimal
```

## Cost Optimization

### Minimal Setup (~$5-10/month)
- Fargate Spot instances
- SQLite on EFS
- No load balancer (API Gateway only)

### Standard Setup (~$15-30/month)
- Includes CloudFront
- Basic monitoring
- Automated backups

### Enterprise Setup (~$50-100/month)
- PostgreSQL (Aurora Serverless)
- Multi-AZ deployment
- WAF protection
- Comprehensive monitoring

## Next Steps

1. Review the [Architecture Guide](architecture.md)
2. Configure your [deployment settings](configuration.md)
3. Set up [monitoring and alerts](monitoring.md)
4. Review [security best practices](security.md)

## Troubleshooting

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review CloudWatch logs in AWS Console
3. Run local tests: `./scripts/local-test.sh`
4. Submit an issue on GitHub

## Support

- Documentation: [docs/](.)
- Issues: [GitHub Issues](https://github.com/your-org/n8n-aws-serverless/issues)
- n8n Community: [community.n8n.io](https://community.n8n.io)