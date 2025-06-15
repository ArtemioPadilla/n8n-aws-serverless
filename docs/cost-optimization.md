# Cost Optimization Guide

This guide provides strategies to minimize costs while running n8n on AWS serverless infrastructure.

## Cost Breakdown

### Typical Monthly Costs by Configuration

| Component | Minimal | Standard | Enterprise |
|-----------|---------|----------|------------|
| Fargate (Spot) | $3-5 | $10-15 | $30-50 |
| API Gateway | $0-1 | $1-3 | $5-10 |
| EFS Storage | $0.30 | $1-2 | $5-10 |
| Database | $0 (SQLite) | $13 (RDS) | $45 (Aurora) |
| CloudFront | $0 | $0-5 | $10-20 |
| Backups | $0 | $1-2 | $5-10 |
| **Total** | **$5-10** | **$25-40** | **$100-150** |

## Cost Optimization Strategies

### 1. Compute Optimization

#### Use Fargate Spot Instances

```yaml
# In system.yaml
fargate:
  spot_percentage: 80  # 70% cost reduction
```

Benefits:

- 70% discount vs on-demand
- Automatic failover to on-demand
- Suitable for non-critical workloads

#### Right-Size Container Resources

```yaml
# Development
fargate:
  cpu: 256      # 0.25 vCPU
  memory: 512   # 0.5 GB

# Production
fargate:
  cpu: 512      # 0.5 vCPU
  memory: 1024  # 1 GB
```

Cost impact:

- 256 CPU + 512 MB: ~$9/month
- 512 CPU + 1024 MB: ~$18/month
- 1024 CPU + 2048 MB: ~$36/month

#### Implement Auto-Scaling

```yaml
scaling:
  min_tasks: 1
  max_tasks: 3
  target_cpu_utilization: 70
  scale_in_cooldown: 300
```

Savings:

- Scale down during low usage
- Prevent over-provisioning
- 40-60% cost reduction

### 2. Storage Optimization

#### EFS Lifecycle Management

```yaml
efs:
  lifecycle_days: 30  # Move to Infrequent Access
```

Cost impact:

- Standard: $0.30/GB/month
- Infrequent Access: $0.025/GB/month
- 90% savings on cold data

#### Optimize Backup Retention

```yaml
backup:
  retention_days: 7   # Reduce from 30 days
  cross_region_backup: false  # Avoid cross-region costs
```

### 3. Database Optimization

#### Use SQLite for Small Workloads

- Cost: $0 (uses EFS storage)
- Suitable for: <5,000 executions/day
- Migration path to PostgreSQL when needed

#### Aurora Serverless v2 Configuration

```yaml
aurora_serverless:
  min_capacity: 0.5   # Scale to zero
  max_capacity: 1.0   # Cap maximum
```

Cost comparison:

- RDS t4g.micro: ~$13/month
- Aurora Serverless: ~$45/month (but scales to zero)

#### Database Optimization Tips

```sql
-- Enable data pruning
EXECUTIONS_DATA_MAX_AGE=7  # Keep only 7 days

-- Compress large data
EXECUTIONS_DATA_SAVE_DATA_ON_ERROR=false
EXECUTIONS_DATA_SAVE_DATA_ON_SUCCESS=false
```

### 4. Network Optimization

#### Avoid Load Balancers

- ALB cost: $16-25/month
- Alternative: API Gateway HTTP API ($1/million requests)

#### Minimize Data Transfer

```yaml
# Use same region for all services
region: us-east-1  # Lowest costs

# Enable compression
n8n:
  compression_enabled: true
```

#### Use VPC Endpoints

```python
# Avoid NAT Gateway costs ($45/month)
vpc_endpoints:
  - s3
  - secretsmanager
  - ecs
```

### 5. Monitoring Cost Optimization

#### CloudWatch Logs

```yaml
monitoring:
  log_retention_days: 7    # Reduce from 30
  log_group_class: INFREQUENT_ACCESS  # 50% cheaper
```

#### Metrics and Alarms

- Use basic metrics (free)
- Limit custom metrics
- Consolidate alarms

### 6. Environment-Specific Optimization

#### Development Environment

```yaml
dev:
  settings:
    # Minimal resources
    fargate:
      cpu: 256
      memory: 512
      spot_percentage: 100

    # No redundancy
    scaling:
      min_tasks: 1
      max_tasks: 1

    # Minimal monitoring
    monitoring:
      enable_container_insights: false
```

#### Production Environment

```yaml
production:
  settings:
    # Balanced resources
    fargate:
      cpu: 512
      memory: 1024
      spot_percentage: 50  # Mix for reliability

    # Auto-scaling
    scaling:
      min_tasks: 2
      max_tasks: 10

    # Scheduled scaling
    scheduled_scaling:
      - schedule: "cron(0 18 * * ? *)"  # 6 PM
        min_tasks: 1
      - schedule: "cron(0 8 * * ? *)"   # 8 AM
        min_tasks: 2
```

### 7. AWS Cost Optimization Tools

#### Enable AWS Budgets

```bash
aws budgets create-budget \
  --account-id $AWS_ACCOUNT_ID \
  --budget "BudgetName=n8n-monthly,BudgetLimit={Amount=50,Unit=USD}"
```

#### Use Cost Allocation Tags

```yaml
global:
  tags:
    Project: "n8n"
    Environment: "{{ environment }}"
    CostCenter: "engineering"
```

#### Regular Cost Reviews

```bash
# Monthly cost report
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=Project
```

### 8. Reserved Capacity

#### Compute Savings Plans

- 1-year commitment: 30% savings
- 3-year commitment: 50% savings

```bash
# Calculate savings
aws ce get-savings-plans-purchase-recommendation \
  --lookback-period-in-days SIXTY_DAYS \
  --term-in-years ONE_YEAR \
  --payment-option NO_UPFRONT
```

### 9. Architectural Decisions

#### When to Use Each Database

| Workload | Database | Cost | Use When |
|----------|----------|------|----------|
| Light | SQLite | $0 | <5K executions/day |
| Medium | RDS t4g.micro | $13/mo | 5K-50K executions/day |
| Heavy | Aurora Serverless | $45+/mo | Variable load, HA required |

#### API Access Strategy

| Option | Cost | Use When |
|--------|------|----------|
| Direct API Gateway | $1/M requests | Low traffic, simple setup |
| CloudFront + API GW | $5-10/mo | Global users, caching needed |
| CloudFront + WAF | $20+/mo | Security critical |

### 10. Cost Monitoring Scripts

#### Daily Cost Check

```bash
#!/bin/bash
# Get yesterday's costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "yesterday" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --filter file://cost-filter.json
```

#### Resource Utilization

```python
# Check Fargate utilization
import boto3

cloudwatch = boto3.client('cloudwatch')

response = cloudwatch.get_metric_statistics(
    Namespace='AWS/ECS',
    MetricName='CPUUtilization',
    Dimensions=[
        {'Name': 'ServiceName', 'Value': 'n8n-production'},
        {'Name': 'ClusterName', 'Value': 'n8n-cluster'}
    ],
    StartTime=datetime.now() - timedelta(days=7),
    EndTime=datetime.now(),
    Period=3600,
    Statistics=['Average']
)
```

## Cost Optimization Checklist

### Initial Deployment

- [ ] Use Spot instances for non-production
- [ ] Start with minimal resources
- [ ] Enable EFS lifecycle management
- [ ] Use SQLite instead of RDS
- [ ] Skip CloudFront initially

### After 1 Month

- [ ] Review CloudWatch metrics
- [ ] Right-size Fargate tasks
- [ ] Enable auto-scaling
- [ ] Clean up unused resources
- [ ] Set up cost alerts

### After 3 Months

- [ ] Consider Reserved Instances
- [ ] Evaluate Savings Plans
- [ ] Optimize backup retention
- [ ] Review data transfer costs
- [ ] Consolidate resources

### Ongoing

- [ ] Monthly cost reviews
- [ ] Quarterly architecture review
- [ ] Annual reserved capacity evaluation
- [ ] Regular resource cleanup
- [ ] Update to latest n8n version

## Example Cost Scenarios

### Personal Use (<$10/month)

```yaml
settings:
  fargate:
    cpu: 256
    memory: 512
    spot_percentage: 100
  database:
    type: sqlite
  scaling:
    min_tasks: 1
    max_tasks: 1
  features:
    monitoring: false
    backups: false
```

### Small Team (~$25/month)

```yaml
settings:
  fargate:
    cpu: 512
    memory: 1024
    spot_percentage: 80
  database:
    type: postgres
    instance_class: db.t4g.micro
  scaling:
    min_tasks: 1
    max_tasks: 3
  monitoring:
    basic_only: true
```

### Enterprise (~$100/month)

```yaml
settings:
  fargate:
    cpu: 1024
    memory: 2048
    spot_percentage: 50
  database:
    type: postgres
    aurora_serverless:
      min_capacity: 0.5
      max_capacity: 2
  scaling:
    min_tasks: 2
    max_tasks: 10
  high_availability:
    multi_az: true
```

## Additional Resources

- [AWS Pricing Calculator](https://calculator.aws/)
- [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [n8n Resource Requirements](https://docs.n8n.io/hosting/)
