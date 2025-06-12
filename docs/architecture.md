# Architecture Overview

This document describes the architecture of the n8n AWS Serverless deployment.

## High-Level Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│   CloudFront    │─────▶│  API Gateway    │─────▶│  ECS Fargate    │
│  (CDN + WAF)    │      │  (HTTP API)     │      │  (n8n + Spot)   │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                                            │
                                                            ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│     Route53     │      │       EFS       │      │  RDS/Aurora     │
│     (DNS)       │      │  (File Storage) │      │  (PostgreSQL)   │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

## Components

### 1. Access Layer

#### CloudFront (Optional)
- **Purpose**: Global content delivery and caching
- **Features**:
  - HTTPS termination
  - DDoS protection
  - Geographic restrictions
  - Custom domain support
- **Cost**: Pay-per-use, often within free tier

#### API Gateway HTTP API
- **Purpose**: Serverless API endpoint
- **Features**:
  - Cost-effective ($1/million requests)
  - Auto-scaling
  - JWT authorization
  - Request throttling
- **Alternative to**: Application Load Balancer ($16/month)

### 2. Compute Layer

#### ECS Fargate
- **Purpose**: Serverless container hosting
- **Features**:
  - No server management
  - Auto-scaling
  - Spot instances (70% cost savings)
  - Pay-per-second billing
- **Configuration**:
  - CPU: 0.25-2 vCPU
  - Memory: 0.5-4 GB
  - Spot/On-demand mix

#### Task Definition
- **Container**: n8n:latest
- **Port**: 5678
- **Health Check**: /healthz endpoint
- **Environment Variables**: Configured via Secrets Manager

### 3. Storage Layer

#### EFS (Elastic File System)
- **Purpose**: Persistent storage for workflows and data
- **Features**:
  - Shared across containers
  - Automatic backups
  - Encryption at rest
  - Lifecycle management
- **Mount Point**: /home/node/.n8n

#### S3 (Optional)
- **Purpose**: Workflow backups and large file storage
- **Features**:
  - Lifecycle policies
  - Cross-region replication
  - Versioning

### 4. Database Layer

#### SQLite (Default)
- **Purpose**: Lightweight database for small deployments
- **Location**: Stored on EFS
- **Suitable for**: <5,000 daily executions
- **Cost**: $0 (uses EFS storage)

#### PostgreSQL (Optional)
- **Options**:
  - RDS PostgreSQL (db.t4g.micro)
  - Aurora Serverless v2
- **Features**:
  - Automated backups
  - Multi-AZ (production)
  - Encryption at rest
- **When to use**: >5,000 daily executions

### 5. Security Layer

#### Network Security
- **VPC**: Isolated network
- **Security Groups**: Stateful firewall rules
- **NACLs**: Subnet-level protection
- **Private Subnets**: For sensitive resources

#### Application Security
- **Secrets Manager**: Credential storage
- **IAM Roles**: Least privilege access
- **Encryption**: TLS 1.2+ for transit, AES-256 for rest
- **WAF** (Optional): Web application firewall

#### Authentication
- **Basic Auth**: Simple username/password
- **OAuth2**: Enterprise SSO integration
- **API Keys**: For webhook authentication

### 6. Monitoring & Operations

#### CloudWatch
- **Logs**: Centralized logging
- **Metrics**: CPU, memory, custom metrics
- **Alarms**: Automated alerting
- **Dashboards**: Visual monitoring

#### Backup Strategy
- **EFS Backups**: Daily snapshots
- **Database Backups**: Automated with retention
- **Cross-region**: Optional for DR

## Deployment Patterns

### 1. Minimal Deployment
```yaml
Components:
  - API Gateway → Fargate → SQLite on EFS
Cost: ~$5-10/month
Use Case: Personal projects, development
```

### 2. Standard Deployment
```yaml
Components:
  - CloudFront → API Gateway → Fargate → PostgreSQL
  - Monitoring and backups enabled
Cost: ~$15-30/month
Use Case: Small teams, production workloads
```

### 3. Enterprise Deployment
```yaml
Components:
  - CloudFront + WAF → API Gateway → Fargate (Multi-AZ)
  - Aurora Serverless PostgreSQL
  - Comprehensive monitoring
  - Cross-region backups
Cost: ~$50-100/month
Use Case: Large organizations, high availability
```

## Scaling Strategies

### Horizontal Scaling
- **Auto Scaling**: Based on CPU/memory metrics
- **Min Tasks**: 1-2 (based on environment)
- **Max Tasks**: 3-20 (configurable)
- **Target Utilization**: 70% CPU

### Vertical Scaling
- **Fargate Sizes**: 0.25-4 vCPU, 0.5-8 GB RAM
- **Database**: db.t4g.micro to db.r6g.xlarge
- **EFS**: Bursting to provisioned throughput

### Cost Optimization
1. **Spot Instances**: 70-90% for non-production
2. **Scheduled Scaling**: Reduce capacity during off-hours
3. **Reserved Instances**: For predictable workloads
4. **Graviton**: 20% cost savings with ARM

## High Availability

### Multi-AZ Deployment
- **Fargate**: Tasks across availability zones
- **RDS**: Multi-AZ for automatic failover
- **EFS**: Replicated across AZs
- **API Gateway**: Inherently multi-AZ

### Disaster Recovery
- **RTO**: 5-30 minutes
- **RPO**: 24 hours (configurable)
- **Backup Strategy**: Automated daily backups
- **Cross-region**: Optional replication

## Configuration Management

### system.yaml Structure
```yaml
environments:
  dev:
    account: "123456789012"
    region: "us-east-1"
    settings:
      fargate:
        cpu: 256
        memory: 512
      scaling:
        min_tasks: 1
        max_tasks: 3
```

### Environment Variables
- Stored in Secrets Manager
- Injected at container runtime
- Separate secrets per environment

## Best Practices

1. **Security**
   - Use private subnets for compute
   - Enable VPC endpoints for AWS services
   - Rotate credentials regularly
   - Enable CloudTrail logging

2. **Performance**
   - Use CloudFront for static assets
   - Enable EFS lifecycle management
   - Right-size Fargate tasks
   - Monitor burst credits

3. **Cost**
   - Use Spot instances for non-production
   - Enable auto-scaling
   - Set up budget alerts
   - Review unused resources monthly

4. **Reliability**
   - Implement health checks
   - Configure auto-recovery
   - Test disaster recovery
   - Monitor error rates