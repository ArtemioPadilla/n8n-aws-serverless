# Disaster Recovery Guide for n8n AWS Serverless

This guide provides comprehensive disaster recovery (DR) procedures for the n8n AWS Serverless deployment.

## Table of Contents
- [Overview](#overview)
- [RTO and RPO Objectives](#rto-and-rpo-objectives)
- [Backup Strategy](#backup-strategy)
- [Recovery Procedures](#recovery-procedures)
- [Testing DR Plans](#testing-dr-plans)
- [Preventive Measures](#preventive-measures)

## Overview

The n8n AWS Serverless deployment is designed with resilience in mind, featuring:
- Automated backups for EFS and RDS
- Multi-AZ deployments for production
- Dead Letter Queues for failed operations
- Circuit breakers for external service failures
- Automated health checks and recovery

## RTO and RPO Objectives

### Recovery Time Objective (RTO)
The maximum acceptable time to restore service after a disaster.

| Component | RTO Target | Notes |
|-----------|------------|-------|
| n8n Service | 15 minutes | Automated ECS recovery |
| Database | 30 minutes | From automated backup |
| File Storage | 30 minutes | From EFS backup |
| Complete Stack | 2 hours | Full CDK redeploy |

### Recovery Point Objective (RPO)
The maximum acceptable data loss measured in time.

| Component | RPO Target | Backup Frequency |
|-----------|------------|------------------|
| Database | 24 hours | Daily automated backups |
| File Storage | 24 hours | Daily EFS backups |
| Workflows | 1 hour | Continuous sync to EFS |
| Webhooks | 5 minutes | DLQ retention |

## Backup Strategy

### 1. Automated Backups

#### EFS Backups
```yaml
# Configured in system.yaml
backup:
  enabled: true
  retention_days: 30
  cross_region_backup: true
  backup_regions:
    - us-west-2  # DR region
```

#### RDS Backups
- Automated daily backups at 03:00 UTC
- 30-day retention for production
- Point-in-time recovery enabled

### 2. Manual Backup Procedures

#### Backup n8n Workflows
```bash
# Export all workflows
curl -X GET https://n8n.example.com/rest/workflows \
  -H "Authorization: Bearer $API_KEY" \
  > workflows-backup-$(date +%Y%m%d).json

# Store in S3
aws s3 cp workflows-backup-*.json s3://backup-bucket/n8n/workflows/
```

#### Backup Credentials and Secrets
```bash
# Backup secrets to secure location
aws secretsmanager get-secret-value \
  --secret-id n8n/production/encryption-key \
  --query SecretString \
  --output text > encryption-key-backup.txt

# Encrypt and store securely
gpg -c encryption-key-backup.txt
aws s3 cp encryption-key-backup.txt.gpg s3://backup-bucket/n8n/secrets/
```

### 3. Cross-Region Replication

For critical production deployments:

```bash
# Enable S3 cross-region replication for backups
aws s3api put-bucket-replication \
  --bucket backup-bucket \
  --replication-configuration file://replication-config.json
```

## Recovery Procedures

### 1. Service Recovery (RTO: 15 minutes)

#### Scenario: n8n service is down

**Automatic Recovery** (already configured):
- ECS automatically restarts failed tasks
- Health checks trigger auto-recovery

**Manual Recovery**:
```bash
# Force new deployment
aws ecs update-service \
  --cluster n8n-production-ecs-cluster \
  --service n8n-production \
  --force-new-deployment

# Monitor deployment
aws ecs wait services-stable \
  --cluster n8n-production-ecs-cluster \
  --services n8n-production
```

### 2. Database Recovery (RTO: 30 minutes)

#### Scenario: Database corruption or failure

**From Automated Backup**:
```bash
# List available backups
aws rds describe-db-snapshots \
  --db-instance-identifier n8n-production-rds

# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier n8n-production-rds-restored \
  --db-snapshot-identifier <snapshot-id>

# Update n8n to use new database endpoint
aws ecs update-service \
  --cluster n8n-production-ecs-cluster \
  --service n8n-production \
  --task-definition <new-task-def-with-updated-endpoint>
```

**Point-in-Time Recovery**:
```bash
# Restore to specific time
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier n8n-production-rds \
  --target-db-instance-identifier n8n-production-rds-pitr \
  --restore-time 2024-01-20T03:00:00Z
```

### 3. File Storage Recovery (RTO: 30 minutes)

#### Scenario: EFS data loss or corruption

**From AWS Backup**:
```bash
# List recovery points
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name n8n-production-backup-vault

# Start restore job
aws backup start-restore-job \
  --recovery-point-arn <recovery-point-arn> \
  --iam-role-arn <backup-restore-role-arn> \
  --resource-type EFS \
  --metadata file://restore-metadata.json
```

### 4. Complete Stack Recovery (RTO: 2 hours)

#### Scenario: Complete region failure or stack deletion

**Deploy to DR Region**:
```bash
# Update CDK context for DR region
export CDK_DEFAULT_REGION=us-west-2

# Deploy all stacks to DR region
cdk deploy -c environment=production-dr --all

# Restore data from cross-region backups
./scripts/restore-from-backup.sh --region us-west-2
```

### 5. Workflow Recovery

#### Scenario: Lost or corrupted workflows

**From Backup**:
```bash
# Download backup from S3
aws s3 cp s3://backup-bucket/n8n/workflows/workflows-backup-20240120.json .

# Import workflows via API
curl -X POST https://n8n.example.com/rest/workflows \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @workflows-backup-20240120.json
```

### 6. Failed Webhook Recovery

#### Scenario: Webhooks failed and need reprocessing

**From Dead Letter Queue**:
```bash
# Process messages from DLQ
aws sqs receive-message \
  --queue-url https://sqs.region.amazonaws.com/account/n8n-production-webhook-dlq \
  --max-number-of-messages 10 \
  > failed-webhooks.json

# Reprocess webhooks
python scripts/reprocess-webhooks.py failed-webhooks.json
```

## Testing DR Plans

### 1. Monthly DR Drills

```bash
# Run DR test script
./scripts/dr-test.sh --environment staging --scenario service-failure

# Test scenarios:
# - service-failure: Kill ECS tasks
# - database-failure: Failover to replica
# - region-failure: Deploy to DR region
```

### 2. Backup Restoration Tests

```bash
# Weekly backup restoration test
./scripts/test-backup-restore.sh --component database --environment staging
./scripts/test-backup-restore.sh --component efs --environment staging
```

### 3. Chaos Engineering

```bash
# Use AWS Fault Injection Simulator
aws fis create-experiment-template \
  --cli-input-json file://chaos-experiments/ecs-task-failure.json

# Run experiment
aws fis start-experiment --experiment-template-id <template-id>
```

## Preventive Measures

### 1. Monitoring and Alerting

Ensure these alarms are configured:
- Service health checks
- Database connection failures
- High error rates
- DLQ message count
- Backup job failures

### 2. Regular Maintenance

- **Weekly**: Review backup job status
- **Monthly**: Test restore procedures
- **Quarterly**: Full DR drill
- **Annually**: Review and update RTO/RPO objectives

### 3. Documentation Updates

Keep these documents current:
- Runbook with step-by-step procedures
- Contact list for escalations
- Architecture diagrams
- Recovery scripts

## Recovery Scripts

### restore-from-backup.sh
```bash
#!/bin/bash
# Automated restore script

ENVIRONMENT=$1
COMPONENT=$2
BACKUP_DATE=$3

case $COMPONENT in
  database)
    restore_database
    ;;
  efs)
    restore_efs
    ;;
  workflows)
    restore_workflows
    ;;
  all)
    restore_database
    restore_efs
    restore_workflows
    ;;
esac
```

### health-check.sh
```bash
#!/bin/bash
# Service health verification

check_ecs_service() {
  aws ecs describe-services \
    --cluster n8n-$ENVIRONMENT-ecs-cluster \
    --services n8n-$ENVIRONMENT \
    --query 'services[0].runningCount'
}

check_database() {
  aws rds describe-db-instances \
    --db-instance-identifier n8n-$ENVIRONMENT-rds \
    --query 'DBInstances[0].DBInstanceStatus'
}

check_n8n_api() {
  curl -s -o /dev/null -w "%{http_code}" \
    https://n8n-$ENVIRONMENT.example.com/healthz
}
```

## Emergency Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| Primary On-Call | DevOps Team | PagerDuty |
| Secondary On-Call | Platform Team | PagerDuty |
| AWS Support | Enterprise Support | AWS Console |
| Management | CTO | Phone |

## Appendix

### A. Required IAM Permissions for DR

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "rds:RestoreDBInstanceFromDBSnapshot",
        "rds:RestoreDBInstanceToPointInTime",
        "backup:StartRestoreJob",
        "backup:ListRecoveryPoints*",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage"
      ],
      "Resource": "*"
    }
  ]
}
```

### B. Backup Metadata Template

```json
{
  "FileSystemId": "fs-12345678",
  "Encrypted": true,
  "KmsKeyId": "arn:aws:kms:region:account:key/key-id",
  "PerformanceMode": "generalPurpose",
  "CreationToken": "n8n-production-efs-restore",
  "newFileSystem": true,
  "ItemsToRestore": "OVERWRITE"
}
```

### C. Monitoring Dashboard

Access the DR monitoring dashboard:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=n8n-production-dr-dashboard
```

Key metrics to monitor:
- Backup job success rate
- RTO achievement (actual vs target)
- RPO compliance
- DR drill results

## Summary

This disaster recovery plan ensures:
1. **Minimal downtime** through automated recovery
2. **Data protection** via regular backups
3. **Quick recovery** with documented procedures
4. **Confidence** through regular testing

Remember: The best disaster recovery is disaster prevention. Keep systems updated, monitor actively, and test regularly.