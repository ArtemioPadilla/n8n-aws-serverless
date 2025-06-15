# Local Development Guide

This guide provides comprehensive information for developing and testing n8n locally using Docker Compose.

## Table of Contents

- [Overview](#overview)
- [Docker Compose Architecture](#docker-compose-architecture)
- [Development Profiles](#development-profiles)
- [Environment Configuration](#environment-configuration)
- [Common Development Tasks](#common-development-tasks)
- [Debugging](#debugging)
- [Best Practices](#best-practices)

## Overview

The local development environment uses Docker Compose with profiles to provide flexible deployment options:

- **SQLite** for lightweight development
- **PostgreSQL** for production-like testing
- **Redis** for queue-based execution
- **Monitoring stack** for metrics and observability

## Docker Compose Architecture

### Service Structure

```yaml
services:
  n8n:           # Default n8n with SQLite (profile: default)
  n8n-postgres:  # n8n with PostgreSQL (profile: postgres)
  postgres:      # PostgreSQL database (profile: postgres)
  redis:         # Redis for queues (profile: scaling)
  prometheus:    # Metrics collection (profile: monitoring)
  grafana:       # Metrics visualization (profile: monitoring)
  postgres-exporter: # PostgreSQL metrics (profile: monitoring)
  redis-exporter:    # Redis metrics (profile: monitoring)
```

### Profile System

Docker Compose profiles allow selective service deployment:

| Profile | Services | Use Case |
|---------|----------|----------|
| default | n8n (SQLite) | Quick testing, lightweight development |
| postgres | n8n-postgres, postgres | Production-like database testing |
| scaling | redis | Queue-based execution, multi-worker setup |
| monitoring | prometheus, grafana, exporters | Metrics and observability |

## Development Profiles

### 1. Default Profile (SQLite)

Simplest setup for quick testing:

```bash
./scripts/local-deploy.sh
```

**When to use:**

- Rapid prototyping
- Testing workflows
- Learning n8n
- Limited resources

**Limitations:**

- No concurrent executions
- Basic performance
- Not suitable for production testing

### 2. PostgreSQL Profile

Production-like database setup:

```bash
./scripts/local-deploy.sh -p postgres
```

**When to use:**

- Testing production workflows
- Database-specific features
- Performance testing
- Multi-user scenarios

**Benefits:**

- Better performance
- Concurrent executions
- Production parity
- Advanced queries

### 3. Scaling Profile

Adds Redis for distributed execution:

```bash
./scripts/local-deploy.sh -p scaling
```

**When to use:**

- Testing queue mode
- Multi-worker setups
- High-volume workflows
- Distributed execution

**Configuration:**

- Uses Redis for job queues
- Enables `EXECUTIONS_MODE=queue`
- Supports multiple n8n workers

### 4. Monitoring Profile

Adds Prometheus and Grafana:

```bash
./scripts/local-deploy.sh -m
```

**When to use:**

- Performance analysis
- Debugging issues
- Resource monitoring
- Metric collection

**Access:**

- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000>

### 5. Combined Profiles

Mix profiles for comprehensive testing:

```bash
# PostgreSQL with monitoring
./scripts/local-deploy.sh -p postgres -m

# Full stack (PostgreSQL + Redis + Monitoring)
./scripts/local-deploy.sh -p postgres -p scaling -m
```

## Environment Configuration

### Core Environment Variables

The `.env` file controls all service configurations:

```bash
# n8n Configuration
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=password
N8N_ENCRYPTION_KEY=<generated-key>
GENERIC_TIMEZONE=America/New_York

# Database Configuration
POSTGRES_USER=n8n
POSTGRES_PASSWORD=n8n
DB_TYPE=sqlite  # or postgresdb when using postgres profile

# Monitoring Configuration
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin

# Redis Configuration
REDIS_PASSWORD=redis_password
```

### Per-Profile Configuration

Override defaults for specific profiles:

```bash
# For PostgreSQL development
export DB_TYPE=postgresdb
./scripts/local-deploy.sh -p postgres

# For custom ports
export N8N_PORT=5679
./scripts/local-deploy.sh
```

## Common Development Tasks

### 1. Workflow Development

#### Import/Export Workflows

```bash
# Export all workflows
docker exec n8n-local n8n export:workflow --all --output=/home/node/.n8n/workflows/

# Import workflows
docker exec n8n-local n8n import:workflow --input=/home/node/.n8n/workflows/my-workflow.json
```

#### Access Workflow Files

Workflows are synced to `docker/workflows/` for version control:

```bash
ls docker/workflows/
git add docker/workflows/my-workflow.json
```

### 2. Database Management

#### PostgreSQL Access

```bash
# Connect to PostgreSQL
docker exec -it n8n-postgres psql -U n8n -d n8n

# Backup database
docker exec n8n-postgres pg_dump -U n8n n8n > backup.sql

# Restore database
docker exec -i n8n-postgres psql -U n8n n8n < backup.sql
```

#### SQLite Access

```bash
# Access SQLite database
docker exec -it n8n-local sqlite3 /home/node/.n8n/database.sqlite

# Backup SQLite
docker cp n8n-local:/home/node/.n8n/database.sqlite ./backup.sqlite
```

### 3. Testing Workflows

#### Using the CLI

```bash
# Execute specific workflow
docker exec n8n-local n8n execute --id=<workflow-id>

# Test webhook
curl -X POST http://localhost:5678/webhook/test-webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

#### Load Testing

```bash
# Run performance tests
./scripts/performance-test.sh -u http://localhost:5678 -t baseline

# Stress test with monitoring
./scripts/local-deploy.sh -p postgres -m
./scripts/performance-test.sh -u http://localhost:5678 -t stress -c 50
```

### 4. Log Management

#### View Logs

```bash
# All services
./scripts/local-deploy.sh -l

# Specific service
docker logs -f n8n-local

# With timestamps
docker logs -f --timestamps n8n-local

# Filter logs
docker logs n8n-local 2>&1 | grep ERROR
```

#### Log Rotation

Configure in docker-compose.yml:

```yaml
services:
  n8n:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Debugging

### 1. Container Debugging

#### Interactive Shell

```bash
# Access n8n container
docker exec -it n8n-local /bin/sh

# Check processes
docker exec n8n-local ps aux

# View environment
docker exec n8n-local env | grep N8N
```

#### Health Checks

```bash
# Check service health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Manual health check
curl http://localhost:5678/healthz
```

### 2. Network Debugging

#### Test Connectivity

```bash
# From n8n to postgres
docker exec n8n-local ping postgres

# Check exposed ports
docker port n8n-local

# Inspect network
docker network inspect n8n_network
```

### 3. Performance Debugging

#### Resource Usage

```bash
# Real-time stats
docker stats

# Detailed inspection
docker inspect n8n-local | jq '.[0].HostConfig.Memory'

# With monitoring stack
# Visit http://localhost:3000 for Grafana dashboards
```

## Best Practices

### 1. Development Workflow

1. **Start Simple**: Begin with default profile
2. **Add Complexity**: Gradually add postgres/monitoring as needed
3. **Version Control**: Commit workflows and configurations
4. **Clean Regularly**: `docker system prune` to free space

### 2. Configuration Management

```bash
# Development settings
cp .env.example .env.development
cp .env.example .env.testing

# Switch environments
ln -sf .env.development .env
```

### 3. Data Persistence

- Workflows: `docker/workflows/`
- SQLite: Docker volume `n8n_data`
- PostgreSQL: Docker volume `n8n_postgres_data`
- Backups: Regular automated backups

### 4. Security in Development

1. **Never commit .env files**
2. **Use strong passwords even locally**
3. **Rotate encryption keys between environments**
4. **Don't expose ports unnecessarily**

### 5. Performance Optimization

1. **Resource Limits**: Set container limits in docker-compose.yml
2. **Volume Mounts**: Use named volumes over bind mounts
3. **Build Cache**: Leverage Docker build cache
4. **Cleanup**: Regular cleanup of unused resources

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find process using port
lsof -i :5678

# Use different port
N8N_PORT=5679 ./scripts/local-deploy.sh
```

#### 2. Container Won't Start

```bash
# Check logs
docker logs n8n-local

# Reset completely
./scripts/local-deploy.sh -d
docker volume prune -f
./scripts/local-setup.sh
./scripts/local-deploy.sh
```

#### 3. Database Connection Failed

```bash
# Verify postgres is running
docker ps | grep postgres

# Check credentials
docker exec n8n-postgres psql -U $POSTGRES_USER -c "SELECT 1"

# Reset database
docker volume rm n8n_postgres_data
```

#### 4. Monitoring Not Working

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify n8n metrics
curl http://localhost:5678/metrics

# Check Grafana datasource
curl http://localhost:3000/api/datasources
```

## Next Steps

- Set up [automated testing](testing.md)
- Configure [CI/CD pipelines](ci-cd.md)
- Review [monitoring guide](local-monitoring.md)
- Explore [production deployment](deployment-guide.md)
