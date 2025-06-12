# Deployment Guide

This guide covers deploying n8n to AWS using the CDK infrastructure.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Deployment Options](#deployment-options)
- [Step-by-Step Deployment](#step-by-step-deployment)
- [Post-Deployment](#post-deployment)
- [Updating Deployments](#updating-deployments)
- [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Tools
```bash
# Check versions
python --version  # 3.8+
node --version    # 16+
aws --version     # 2.0+
cdk --version     # 2.0+
```

### AWS Permissions
Your AWS user/role needs the following permissions:
- CloudFormation full access
- IAM role creation
- VPC and networking
- ECS and Fargate
- EFS file systems
- Secrets Manager
- CloudWatch logs
- (Optional) RDS, CloudFront, Route53

### AWS Account Preparation
```bash
# Configure AWS credentials
aws configure

# Set your AWS account ID and region
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

# Bootstrap CDK
cdk bootstrap aws://$AWS_ACCOUNT_ID/$AWS_REGION
```

## Initial Setup

### 1. Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd n8n-aws-serverless

# Setup Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure system.yaml

```bash
# Copy example configuration
cp system.yaml.example system.yaml

# Edit configuration
vim system.yaml
```

Key configuration items:
```yaml
environments:
  dev:
    account: "YOUR_AWS_ACCOUNT_ID"
    region: "us-east-1"
    settings:
      access:
        domain_name: "n8n-dev.yourdomain.com"  # Optional
      monitoring:
        alarm_email: "your-email@example.com"
```

### 3. Validate Configuration

```bash
# Validate system.yaml
python -c "from n8n_deploy.config import ConfigLoader; ConfigLoader().validate_config_file()"

# List available environments
python -c "from n8n_deploy.config import ConfigLoader; print(ConfigLoader().get_available_environments())"
```

## Deployment Options

### Environment-Based Deployment

#### Development Environment
```bash
# Minimal cost, basic features
cdk deploy -c environment=dev
```

#### Staging Environment
```bash
# Production-like, with PostgreSQL
cdk deploy -c environment=staging
```

#### Production Environment
```bash
# Full features, high availability
cdk deploy -c environment=production
```

### Stack Type Deployment

#### Minimal Stack (~$5-10/month)
```bash
cdk deploy -c environment=dev -c stack_type=minimal
```
- Basic n8n with SQLite
- No monitoring or backups
- Single availability zone

#### Standard Stack (~$15-30/month)
```bash
cdk deploy -c environment=staging -c stack_type=standard
```
- PostgreSQL database
- CloudWatch monitoring
- Automated backups
- CloudFront CDN

#### Enterprise Stack (~$50-100/month)
```bash
cdk deploy -c environment=production -c stack_type=enterprise
```
- Aurora Serverless PostgreSQL
- Multi-AZ deployment
- WAF protection
- Cross-region backups

## Step-by-Step Deployment

### 1. Pre-deployment Checks

```bash
# Check what will be deployed
cdk diff -c environment=dev

# Synthesize CloudFormation templates
cdk synth -c environment=dev

# Review the generated templates
ls -la cdk.out/
```

### 2. Deploy Infrastructure

#### Option A: Deploy All Stacks
```bash
cdk deploy -c environment=dev --all
```

#### Option B: Deploy Individual Stacks
```bash
# Deploy in order
cdk deploy -c environment=dev n8n-serverless-dev-network
cdk deploy -c environment=dev n8n-serverless-dev-storage
cdk deploy -c environment=dev n8n-serverless-dev-compute
cdk deploy -c environment=dev n8n-serverless-dev-access
```

### 3. Monitor Deployment

```bash
# Watch CloudFormation progress
aws cloudformation describe-stacks \
  --stack-name n8n-serverless-dev-compute \
  --query 'Stacks[0].StackStatus'

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name n8n-serverless-dev-access \
  --query 'Stacks[0].Outputs'
```

## Post-Deployment

### 1. Get Access URLs

```bash
# Get API Gateway URL
aws cloudformation describe-stacks \
  --stack-name n8n-serverless-dev-access \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text

# Get CloudFront URL (if enabled)
aws cloudformation describe-stacks \
  --stack-name n8n-serverless-dev-access \
  --query 'Stacks[0].Outputs[?OutputKey==`DistributionUrl`].OutputValue' \
  --output text
```

### 2. Access n8n

1. Navigate to the URL from the previous step
2. Login with credentials:
   - If using basic auth: Check Secrets Manager
   - If using OAuth: Use your SSO credentials

### 3. Verify Health

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster n8n-serverless-dev-ecs-cluster \
  --services n8n-dev \
  --query 'services[0].runningCount'

# Check application health
curl -s https://your-api-url/healthz
```

### 4. Configure n8n

1. Set up SMTP for email notifications
2. Configure webhook URL if using custom domain
3. Set up integrations and credentials
4. Import existing workflows

## Updating Deployments

### 1. Update Configuration

```bash
# Edit system.yaml
vim system.yaml

# Validate changes
cdk diff -c environment=dev
```

### 2. Deploy Updates

```bash
# Deploy changes
cdk deploy -c environment=dev

# For production, use manual approval
cdk deploy -c environment=production --require-approval broadening
```

### 3. Update Container Image

To update n8n version:
```yaml
# In system.yaml
defaults:
  fargate:
    n8n_version: "1.94.1"  # Update this version

# For local development, update docker-compose.yml:
services:
  n8n:
    image: n8nio/n8n:1.94.1  # Match the version above
```

**Important**: Always use a specific version tag instead of `latest` for production deployments to ensure stability and reproducibility.

```bash
# Force new deployment
aws ecs update-service \
  --cluster n8n-serverless-dev-ecs-cluster \
  --service n8n-dev \
  --force-new-deployment
```

## Rollback Procedures

### 1. Quick Rollback

```bash
# Get previous task definition
PREVIOUS_TASK_DEF=$(aws ecs describe-services \
  --cluster n8n-serverless-dev-ecs-cluster \
  --services n8n-dev \
  --query 'services[0].taskDefinition' \
  --output text)

# Update service to previous version
aws ecs update-service \
  --cluster n8n-serverless-dev-ecs-cluster \
  --service n8n-dev \
  --task-definition $PREVIOUS_TASK_DEF
```

### 2. Infrastructure Rollback

```bash
# Using CloudFormation
aws cloudformation cancel-update-stack \
  --stack-name n8n-serverless-dev-compute

# Or restore from backup
aws backup start-restore-job \
  --recovery-point-arn <backup-arn> \
  --iam-role-arn <role-arn>
```

### 3. Database Rollback

For RDS/Aurora:
```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier n8n-dev-restored \
  --db-snapshot-identifier <snapshot-id>
```

## Deployment Best Practices

### 1. Use Separate Environments
- Never deploy directly to production
- Test in dev/staging first
- Use different AWS accounts for isolation

### 2. Version Control
- Tag releases in git
- Document changes in CHANGELOG
- Use semantic versioning

### 3. Monitoring
- Set up CloudWatch alarms
- Configure SNS notifications
- Review logs regularly

### 4. Security
- Rotate credentials quarterly
- Review IAM permissions
- Enable AWS GuardDuty
- Use PrivateLink for AWS services

### 5. Cost Management
- Set up AWS Budgets
- Use Spot instances for non-production
- Review Cost Explorer monthly
- Enable S3 lifecycle policies

## Troubleshooting Deployment

### Common Issues

1. **CDK Bootstrap Required**
   ```bash
   cdk bootstrap aws://ACCOUNT-ID/REGION
   ```

2. **Insufficient Permissions**
   - Check IAM role/user permissions
   - Ensure CDK execution role exists

3. **Resource Limits**
   - Check service quotas in AWS
   - Request limit increases if needed

4. **Deployment Failures**
   - Check CloudFormation events
   - Review CloudWatch logs
   - Verify network connectivity

### Debug Commands

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name n8n-serverless-dev-compute \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'

# Check ECS task logs
aws logs tail /ecs/n8n/dev --follow

# Describe ECS task failures
aws ecs describe-tasks \
  --cluster n8n-serverless-dev-ecs-cluster \
  --tasks <task-arn> \
  --query 'tasks[0].stoppedReason'
```

## CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
- name: Deploy to AWS
  run: |
    cdk deploy -c environment=${{ github.event.inputs.environment }} \
      --require-approval never
```

### GitLab CI
```yaml
# .gitlab-ci.yml
deploy:
  script:
    - cdk deploy -c environment=$CI_COMMIT_BRANCH
```

## Next Steps

1. Set up [monitoring and alerts](monitoring.md)
2. Configure [backup strategies](backup-guide.md)
3. Review [security best practices](security.md)
4. Optimize [costs](cost-optimization.md)