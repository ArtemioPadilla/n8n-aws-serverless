# n8n Local Monitoring Quick Start

This guide helps you quickly access and use the monitoring stack for your local n8n deployment.

## Prerequisites

Make sure you have started n8n with monitoring enabled:
```bash
./scripts/local-deploy.sh -p postgres -m
```

## Accessing the Monitoring Stack

### 1. Grafana (Dashboards)
- **URL**: http://localhost:3000
- **Default Username**: `admin`
- **Default Password**: Check your `.env` file or use `admin` if not changed

### 2. Prometheus (Metrics)
- **URL**: http://localhost:9090
- **Targets Status**: http://localhost:9090/targets
- **Available Metrics**: http://localhost:9090/graph

## Available Dashboards

After logging into Grafana, you'll find pre-configured dashboards:

### n8n Complete Monitoring
Located in the `n8n` folder, this dashboard includes:
- **n8n Status**: Overall health indicator
- **Executions/min**: Current workflow execution rate
- **Success Rate**: Percentage of successful executions
- **Workflow Status Distribution**: Pie chart of execution statuses
- **CPU & Memory Usage**: Resource consumption graphs
- **Webhook Metrics**: Request rates and response times

### PostgreSQL Monitoring
When using the postgres profile, this dashboard shows:
- **Connection Usage**: Active connections and pool utilization
- **Transaction Rates**: Commits and rollbacks per second
- **Cache Hit Ratio**: Database performance indicator
- **Row Operations**: Insert, update, delete, and fetch rates
- **Database Size**: Current database size

## Quick Troubleshooting

### No Data in Dashboards?

1. **Check if n8n is exposing metrics**:
   ```bash
   curl http://localhost:5678/metrics | grep n8n_
   ```

2. **Verify Prometheus is scraping n8n**:
   - Go to http://localhost:9090/targets
   - Look for the `n8n` target - it should show as "UP"

3. **Check time range in Grafana**:
   - Look at the top-right corner
   - Ensure it's set to "Last 1 hour" or similar recent range

### Import Additional Dashboards

1. Click the `+` icon in Grafana
2. Select "Import"
3. Upload JSON file or paste dashboard ID
4. Select "Prometheus" as the data source

### Common n8n Metrics to Monitor

```prometheus
# Workflow execution rate
rate(n8n_workflow_executions_total[5m])

# Success rate percentage
(sum(rate(n8n_workflow_executions_total{status="success"}[5m])) / sum(rate(n8n_workflow_executions_total[5m]))) * 100

# Average workflow duration
avg(n8n_workflow_execution_duration_seconds)

# Active workflows
n8n_active_workflow_count

# Memory usage
n8n_process_resident_memory_bytes
```

## Creating Custom Alerts

### In Grafana:
1. Edit any panel
2. Go to "Alert" tab
3. Set conditions (e.g., when success rate < 90%)
4. Configure notification channel

### Example Alert Conditions:
- **High Error Rate**: When `rate(n8n_workflow_executions_total{status="error"}[5m]) > 0.1`
- **High Memory Usage**: When `n8n_process_resident_memory_bytes > 1073741824` (1GB)
- **Slow Workflows**: When `avg(n8n_workflow_execution_duration_seconds) > 10`

## Monitoring Best Practices

1. **Start Simple**: Begin with the default dashboards
2. **Add Gradually**: Create custom panels as needed
3. **Set Baselines**: Understand normal metrics before setting alerts
4. **Regular Review**: Check dashboards daily during development

## Next Steps

- Explore [advanced monitoring features](local-monitoring.md)
- Learn about [Prometheus queries](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- Create [custom Grafana dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- Set up [alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)