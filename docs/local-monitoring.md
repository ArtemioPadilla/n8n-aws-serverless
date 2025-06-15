# Local Monitoring Guide

This guide covers the monitoring stack available for local n8n development using Prometheus and Grafana.

## Overview

The local monitoring stack provides real-time metrics and visualization for your n8n instance, including:

- Workflow execution metrics
- Resource utilization (CPU, memory)
- Database performance (when using PostgreSQL)
- Redis queue metrics (when using scaling profile)

## Quick Start

Enable monitoring with any deployment:

```bash
# With SQLite and monitoring
./scripts/local-deploy.sh -m

# With PostgreSQL and monitoring (recommended)
./scripts/local-deploy.sh -p postgres -m

# With full stack (PostgreSQL, Redis, monitoring)
./scripts/local-deploy.sh -p postgres -p scaling -m
```

## Access Points

### Prometheus

- URL: <http://localhost:9090>
- Purpose: Metrics collection and querying
- Features:
  - Direct metric queries
  - Target health monitoring
  - Alert management (if configured)

### Grafana

- URL: <http://localhost:3000>
- Default credentials:
  - Username: `admin`
  - Password: `admin` (or check `GRAFANA_PASSWORD` in `.env`)
- Pre-configured with:
  - Prometheus data source
  - n8n metrics dashboard
  - PostgreSQL dashboard (when using postgres profile)

## Available Metrics

### n8n Metrics

All n8n metrics are prefixed with `n8n_` (configurable via `N8N_METRICS_PREFIX`):

```prometheus
# Workflow metrics
n8n_workflow_executions_total
n8n_workflow_execution_duration_seconds
n8n_workflow_execution_errors_total

# Node metrics
n8n_node_execution_duration_seconds
n8n_node_execution_errors_total

# Webhook metrics
n8n_webhook_requests_total
n8n_webhook_response_time_seconds

# System metrics
n8n_system_memory_usage_bytes
n8n_system_cpu_usage_percent
```

### PostgreSQL Metrics (with postgres profile)

```prometheus
# Connection metrics
pg_stat_database_numbackends
pg_stat_database_xact_commit
pg_stat_database_xact_rollback

# Performance metrics
pg_stat_database_blks_read
pg_stat_database_blks_hit
pg_stat_database_tup_returned
pg_stat_database_tup_fetched

# Replication metrics (if configured)
pg_stat_replication_lag_bytes
```

### Redis Metrics (with scaling profile)

```prometheus
# Memory metrics
redis_memory_used_bytes
redis_memory_max_bytes

# Connection metrics
redis_connected_clients
redis_blocked_clients

# Command metrics
redis_commands_processed_total
redis_instantaneous_ops_per_sec

# Persistence metrics
redis_rdb_last_save_timestamp_seconds
redis_aof_last_rewrite_duration_sec
```

## Custom Dashboards

### Creating a Custom Dashboard

1. Access Grafana at <http://localhost:3000>
2. Navigate to Dashboards → New Dashboard
3. Add panels with relevant queries

Example queries for common use cases:

#### Workflow Success Rate

```prometheus
rate(n8n_workflow_executions_total{status="success"}[5m])
/
rate(n8n_workflow_executions_total[5m])
* 100
```

#### Average Workflow Duration

```prometheus
rate(n8n_workflow_execution_duration_seconds_sum[5m])
/
rate(n8n_workflow_execution_duration_seconds_count[5m])
```

#### Database Connection Pool Usage

```prometheus
pg_stat_database_numbackends{datname="n8n"}
/
pg_settings_max_connections
* 100
```

### Importing Pre-built Dashboards

The project includes pre-configured dashboards in `docker/grafana/dashboards/`:

- `n8n-dashboard.json` - Main n8n metrics
- Additional dashboards can be added to this directory

## Alerting (Local Development)

While full alerting is typically configured in production, you can set up basic alerts locally:

### Prometheus Alerts

Create `docker/prometheus-alerts.yml`:

```yaml
groups:
  - name: n8n_alerts
    rules:
      - alert: HighWorkflowErrorRate
        expr: rate(n8n_workflow_execution_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High workflow error rate detected"

      - alert: DatabaseConnectionsHigh
        expr: pg_stat_database_numbackends > 80
        for: 5m
        annotations:
          summary: "Database connections approaching limit"
```

### Grafana Alerts

1. Edit any panel in Grafana
2. Go to Alert tab
3. Create alert conditions
4. Configure notification channels (email, webhook, etc.)

## Performance Optimization

### Metrics Retention

For local development, Prometheus stores 15 days of data by default. Adjust in `docker/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s      # How often to scrape metrics
  evaluation_interval: 15s   # How often to evaluate rules
  retention: 30d            # How long to keep data
```

### Reducing Resource Usage

If monitoring impacts performance:

1. Increase scrape intervals:

```yaml
scrape_configs:
  - job_name: 'n8n'
    scrape_interval: 30s  # Instead of 15s
```

2. Disable unused exporters in docker-compose.yml

3. Limit Prometheus memory:

```yaml
services:
  prometheus:
    deploy:
      resources:
        limits:
          memory: 512M
```

## Troubleshooting

### Prometheus Not Scraping Metrics

1. Check targets at <http://localhost:9090/targets>
2. Verify n8n metrics endpoint:

```bash
curl http://localhost:5678/metrics
```

3. Check Prometheus logs:

```bash
docker logs n8n-prometheus
```

### Grafana Dashboards Empty

1. Verify data source configuration
2. Check time range (top right corner)
3. Test queries directly in Prometheus
4. Ensure services are running:

```bash
./scripts/local-deploy.sh -s
```

### Port Conflicts

If ports are already in use:

```bash
# Change ports in docker-compose.yml or use different ports
PROMETHEUS_PORT=9091 GRAFANA_PORT=3001 ./scripts/local-deploy.sh -m
```

## Best Practices

1. **Development vs Production Metrics**
   - Use shorter retention in development (7-15 days)
   - Higher scrape intervals in development (30s vs 15s)
   - Disable detailed metrics not needed locally

2. **Dashboard Organization**
   - Create separate dashboards for different concerns
   - Use variables for filtering (environment, instance)
   - Save custom dashboards to `docker/grafana/dashboards/`

3. **Metric Naming**
   - Follow Prometheus naming conventions
   - Use consistent labels
   - Document custom metrics

## Next Steps

- Review [AWS monitoring](monitoring.md) for production setup
- Explore [Grafana documentation](https://grafana.com/docs/)
- Learn [PromQL queries](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- Set up [custom exporters](https://prometheus.io/docs/instrumenting/writing_exporters/) for specific needs
