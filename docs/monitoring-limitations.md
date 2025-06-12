# n8n Monitoring Limitations and Workarounds

## Current Limitations (n8n v1.94.1)

### Missing Workflow Metrics

n8n v1.94.1 does not expose detailed workflow execution metrics through the `/metrics` endpoint. The following metrics are **NOT available**:

- `n8n_workflow_executions_total` - Total number of workflow executions
- `n8n_workflow_execution_duration_seconds` - Workflow execution duration
- `n8n_workflow_execution_errors_total` - Workflow errors count
- `n8n_webhook_requests_total` - Webhook request counts
- `n8n_webhook_response_time_seconds` - Webhook response times

### Available Metrics

n8n v1.94.1 **DOES** expose the following metrics:

1. **Basic Service Metrics**:
   - `up` - Service availability (1 = up, 0 = down)
   - `n8n_version_info` - n8n version information
   - `n8n_active_workflow_count` - Number of active workflows

2. **Process Metrics**:
   - `n8n_process_cpu_seconds_total` - CPU usage
   - `n8n_process_resident_memory_bytes` - Memory usage
   - `n8n_process_start_time_seconds` - Process start time

3. **Node.js Metrics**:
   - `n8n_nodejs_heap_size_used_bytes` - Heap memory usage
   - `n8n_nodejs_eventloop_lag_seconds` - Event loop lag
   - `n8n_nodejs_gc_duration_seconds` - Garbage collection duration
   - `n8n_nodejs_active_handles_total` - Active handles count

## Working Dashboard

The **n8n Basic Monitoring** dashboard has been created to work with the available metrics. It includes:

- Service status and version
- CPU and memory usage graphs
- Event loop performance
- Node.js internals monitoring
- Service availability history

### Accessing the Working Dashboard

1. Go to Grafana: http://localhost:3000
2. Login with admin / secure-grafana-password
3. Navigate to Dashboards → Browse
4. Open "n8n Basic Monitoring"

## Workarounds for Workflow Monitoring

Since workflow metrics are not available via Prometheus, here are alternative approaches:

### 1. Use n8n's Built-in Execution History

Access the execution history directly in n8n:
- http://localhost:5678/workflow/executions

This shows:
- Execution status (success/error)
- Execution duration
- Error messages
- Execution timestamps

### 2. Use n8n API for Custom Metrics

Create a script to pull execution data from n8n's API:

```bash
# Get executions via API
curl -u admin:Secure-n8n-password \
  http://localhost:5678/rest/executions
```

### 3. Parse n8n Logs

Monitor n8n logs for execution information:

```bash
# Watch for execution logs
docker logs -f n8n-local | grep -E "Execution|Workflow"
```

### 4. Create Custom Monitoring Workflow

Create a workflow in n8n that:
1. Runs periodically (cron)
2. Queries execution history via n8n API
3. Sends metrics to a custom endpoint or database
4. Visualize in Grafana using a different data source

## Future Improvements

### When n8n Adds Workflow Metrics

Once n8n exposes workflow execution metrics, you can:
1. Switch back to the "n8n Complete Monitoring" dashboard
2. All panels will automatically start showing data
3. No configuration changes needed

### Check for Updates

Monitor n8n releases for metric improvements:
- https://github.com/n8n-io/n8n/releases
- Look for mentions of "metrics", "prometheus", or "monitoring"

## Alternative Monitoring Solutions

### 1. Use n8n's Execution Data API

Create a Python/Node.js script that:
```python
import requests
import time
from prometheus_client import Counter, Histogram, start_http_server

# Define custom metrics
workflow_executions = Counter('custom_n8n_workflow_executions_total', 
                            'Total workflow executions', 
                            ['status'])
workflow_duration = Histogram('custom_n8n_workflow_duration_seconds',
                            'Workflow execution duration')

# Poll n8n API and update metrics
while True:
    executions = requests.get('http://localhost:5678/rest/executions',
                            auth=('admin', 'password')).json()
    # Process and update metrics
    time.sleep(60)
```

### 2. Use Application Performance Monitoring (APM)

Consider adding APM tools that can monitor Node.js applications:
- New Relic
- DataDog
- AppDynamics
- Elastic APM

### 3. Custom Logging Solution

Configure n8n to output structured logs and use:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Loki + Grafana
- CloudWatch Logs (if on AWS)

## Summary

While n8n v1.94.1 has limited metrics support, the basic monitoring dashboard provides:
- ✅ Service health monitoring
- ✅ Resource usage tracking
- ✅ Performance indicators (event loop, GC)
- ❌ Workflow execution metrics (not available)

For comprehensive workflow monitoring, combine the basic dashboard with n8n's built-in execution history or implement custom monitoring solutions.