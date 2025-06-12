# Cloudflare Tunnel Setup Guide

This guide explains how to use Cloudflare Tunnel for zero-trust access to your n8n deployment, eliminating the need for public IPs, load balancers, or API Gateway.

## Table of Contents
- [Overview](#overview)
- [Benefits](#benefits)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Configuration Options](#configuration-options)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
- [Migration Guide](#migration-guide)
- [Cost Comparison](#cost-comparison)

## Overview

Cloudflare Tunnel creates a secure outbound-only connection from your infrastructure to Cloudflare's edge network. This means:
- No inbound ports need to be opened
- No public IP addresses required
- Built-in DDoS protection
- Global edge network for better performance
- Zero-trust security model

### Architecture Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    User     │────▶│ Cloudflare  │────▶│  Cloudflare │
│             │     │    Edge     │     │   Tunnel    │
└─────────────┘     └─────────────┘     └─────┬───────┘
                                              │ (Outbound Only)
                                              ▼
                                      ┌─────────────┐     ┌─────────────┐
                                      │   Fargate   │────▶│     EFS     │
                                      │  + Tunnel   │     │  (Storage)  │
                                      └─────────────┘     └─────────────┘
```

## Benefits

### Cost Savings
- **No API Gateway**: Save $1/million requests
- **No Load Balancer**: Save $16-25/month
- **No NAT Gateway**: Save $45/month for outbound traffic
- **Free tier**: Cloudflare Tunnel is free for up to 50 users

### Security Improvements
- **Zero-trust model**: No exposed public endpoints
- **Built-in DDoS protection**: Cloudflare's global network
- **Access policies**: Email, domain, or IP-based restrictions
- **No inbound rules**: Only outbound connections required

### Performance
- **Global edge network**: 300+ PoPs worldwide
- **Smart routing**: Optimized path selection
- **Connection pooling**: Reduced latency
- **HTTP/2 and QUIC**: Modern protocols

## Prerequisites

1. **Cloudflare Account**: Free or paid account at [dash.cloudflare.com](https://dash.cloudflare.com)
2. **Domain**: A domain added to your Cloudflare account
3. **Zero Trust Dashboard**: Access at [one.dash.cloudflare.com](https://one.dash.cloudflare.com)

## Setup Instructions

### Step 1: Create a Cloudflare Tunnel

1. Go to [Zero Trust Dashboard](https://one.dash.cloudflare.com)
2. Navigate to **Access** → **Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** as the connector
5. Name your tunnel (e.g., `n8n-production`)
6. Save the tunnel token - you'll need this later

### Step 2: Store Tunnel Token in AWS

For AWS deployments, store the token in AWS Secrets Manager:

```bash
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "n8n/production/cloudflare-tunnel-token" \
  --description "Cloudflare Tunnel token for n8n production" \
  --secret-string "YOUR_TUNNEL_TOKEN_HERE"
```

For local development, add to `.env` file:
```bash
CLOUDFLARE_TUNNEL_TOKEN=YOUR_TUNNEL_TOKEN_HERE
```

### Step 3: Configure n8n Deployment

Update your `system.yaml` configuration:

```yaml
environments:
  production:
    settings:
      access:
        type: "cloudflare"  # Use Cloudflare instead of API Gateway
        cloudflare:
          enabled: true
          tunnel_token_secret_name: "n8n/production/cloudflare-tunnel-token"
          tunnel_name: "n8n-production"
          tunnel_domain: "n8n.yourdomain.com"
          # Optional: Enable Cloudflare Access policies
          access_enabled: true
          access_allowed_emails:
            - "admin@yourdomain.com"
          access_allowed_domains:
            - "yourdomain.com"
```

### Step 4: Deploy Infrastructure

Deploy your n8n infrastructure with Cloudflare Tunnel:

```bash
# For AWS deployment
cdk deploy -c environment=production

# For local development
./scripts/local-deploy.sh -p cloudflare
```

### Step 5: Configure Tunnel Route

After deployment, configure the public hostname in Cloudflare:

1. Go to **Zero Trust** → **Access** → **Tunnels**
2. Find your tunnel and click **Configure**
3. Go to **Public Hostname** tab
4. Add a new public hostname:
   - **Subdomain**: `n8n` (or your preferred subdomain)
   - **Domain**: Select your domain
   - **Service**: 
     - For ECS: `http://localhost:5678`
     - For Docker: `http://n8n:5678`
   - **Additional settings** (optional):
     - Enable **No TLS Verify** for self-signed certificates
     - Set **HTTP Host Header** to your domain

### Step 6: Configure Access Policies (Optional)

If you enabled Cloudflare Access:

1. Go to **Access** → **Applications**
2. Add an application:
   - **Name**: n8n
   - **Domain**: `n8n.yourdomain.com`
3. Configure policies:
   - **Policy name**: Admin Access
   - **Action**: Allow
   - **Include**: Emails ending in `@yourdomain.com`
4. Save the application

## Configuration Options

### Basic Configuration

```yaml
access:
  type: "cloudflare"
  cloudflare:
    enabled: true
    tunnel_token_secret_name: "n8n/prod/cloudflare-tunnel-token"
    tunnel_name: "n8n-production"
    tunnel_domain: "n8n.example.com"
```

### With Access Policies

```yaml
access:
  type: "cloudflare"
  cloudflare:
    enabled: true
    tunnel_token_secret_name: "n8n/prod/cloudflare-tunnel-token"
    tunnel_name: "n8n-production"
    tunnel_domain: "n8n.example.com"
    access_enabled: true
    access_allowed_emails:
      - "admin@example.com"
      - "developer@example.com"
    access_allowed_domains:
      - "example.com"
      - "contractors.example.com"
```

### Environment Variables

The Cloudflare tunnel container uses these environment variables:

- `TUNNEL_TOKEN`: The tunnel authentication token (from Secrets Manager)
- `TUNNEL_METRICS`: Metrics endpoint (default: `0.0.0.0:2000`)
- `TUNNEL_LOGLEVEL`: Log verbosity (default: `info`)
- `TUNNEL_TRANSPORT_PROTOCOL`: Connection protocol (default: `quic`)

## Security Best Practices

### 1. Token Management

- **Never commit tokens**: Always use Secrets Manager or environment variables
- **Rotate regularly**: Update tokens every 90 days
- **Limit access**: Use IAM policies to restrict who can read the secret
- **Audit usage**: Enable CloudTrail logging for secret access

### 2. Access Policies

- **Principle of least privilege**: Only allow necessary users
- **Use groups**: Manage access through Cloudflare Access groups
- **Enable MFA**: Require multi-factor authentication
- **Session duration**: Set appropriate session timeouts

### 3. Network Security

- **No inbound rules**: Ensure security groups only allow outbound
- **Private subnets**: Deploy in private subnets only
- **VPC endpoints**: Use VPC endpoints for AWS services
- **Encryption**: Enable encryption for all data in transit

### 4. Monitoring

- **Enable logs**: Send Cloudflare logs to CloudWatch
- **Set up alerts**: Monitor tunnel health and connection status
- **Track access**: Review access logs regularly
- **Performance metrics**: Monitor latency and throughput

## Monitoring and Troubleshooting

### CloudWatch Metrics

Monitor these key metrics:

1. **Tunnel Health**
   - Metric: `cloudflare_tunnel_up`
   - Alert threshold: < 1 for 5 minutes

2. **Connection Count**
   - Metric: `cloudflare_tunnel_connections`
   - Alert threshold: > 1000 connections

3. **Request Rate**
   - Metric: `cloudflare_tunnel_requests_per_second`
   - Alert threshold: > 100 rps

### Common Issues

#### Tunnel Not Connecting

```bash
# Check container logs
aws logs tail /ecs/n8n-production --follow --filter-pattern "cloudflare"

# Verify secret exists
aws secretsmanager get-secret-value --secret-id "n8n/production/cloudflare-tunnel-token"

# Check ECS task status
aws ecs describe-tasks --cluster n8n-production --tasks <task-arn>
```

#### Access Denied

1. Verify Cloudflare Access policies
2. Check user email/domain matches policy
3. Clear browser cookies and retry
4. Review Cloudflare Access logs

#### Performance Issues

1. Check tunnel metrics endpoint: `http://localhost:2000/metrics`
2. Verify QUIC protocol is enabled
3. Review CloudWatch logs for errors
4. Consider adding more tunnel replicas

### Debugging Commands

```bash
# Local testing
docker exec -it n8n-cloudflared cloudflared tunnel info

# AWS ECS testing
aws ecs execute-command \
  --cluster n8n-production \
  --task <task-id> \
  --container cloudflare-tunnel \
  --command "/bin/sh" \
  --interactive

# Inside container
cloudflared tunnel info
wget -O - http://localhost:2000/metrics
```

## Migration Guide

### From API Gateway to Cloudflare Tunnel

1. **Preparation**
   - Create Cloudflare tunnel
   - Store token in Secrets Manager
   - Update `system.yaml` configuration

2. **Deployment**
   ```bash
   # Deploy with Cloudflare Tunnel
   cdk deploy -c environment=production
   ```

3. **DNS Migration**
   - Update DNS to point to Cloudflare
   - Test with a subdomain first
   - Monitor both endpoints during transition

4. **Cleanup**
   - Remove API Gateway resources
   - Update security groups
   - Remove unnecessary costs

### Rollback Plan

If issues occur, rollback by:

1. Updating `system.yaml` to use `api_gateway`
2. Redeploying: `cdk deploy -c environment=production`
3. Updating DNS back to API Gateway

## Cost Comparison

### Traditional API Gateway Setup
- API Gateway: ~$3.50/million requests
- ALB: $16-25/month
- CloudFront: $0.085/GB transfer
- **Total**: ~$50-100/month for moderate usage

### Cloudflare Tunnel Setup
- Tunnel: Free (up to 50 users)
- Cloudflare Access: Free (up to 50 users)
- No ALB needed: $0
- No API Gateway: $0
- **Total**: ~$0-20/month

### Savings Example

For a typical n8n deployment with:
- 10 million requests/month
- 100GB data transfer
- 24/7 availability

**Traditional**: 
- API Gateway: $35
- ALB: $20
- Data transfer: $8.50
- **Total: $63.50/month**

**Cloudflare Tunnel**:
- All included in free tier
- **Total: $0/month**

**Annual savings: $762**

## Advanced Features

### Multi-Region Deployment

Deploy tunnels in multiple regions for high availability:

```yaml
environments:
  production-us:
    region: "us-east-1"
    settings:
      access:
        type: "cloudflare"
        cloudflare:
          tunnel_name: "n8n-prod-us"
          tunnel_domain: "n8n-us.example.com"
  
  production-eu:
    region: "eu-west-1"
    settings:
      access:
        type: "cloudflare"
        cloudflare:
          tunnel_name: "n8n-prod-eu"
          tunnel_domain: "n8n-eu.example.com"
```

### Load Balancing

Use Cloudflare Load Balancing across multiple tunnels:

1. Create multiple tunnels in different regions
2. Add all tunnels as origins in Cloudflare
3. Configure health checks
4. Set up load balancing rules

### Custom Headers

Add custom headers for authentication or routing:

```yaml
tunnel_config:
  ingress:
    - hostname: n8n.example.com
      service: http://localhost:5678
      originRequest:
        httpHostHeader: n8n.internal
        customHeaders:
          X-Custom-Auth: "${SECRET_VALUE}"
```

## Conclusion

Cloudflare Tunnel provides a secure, cost-effective, and performant way to expose n8n to the internet without traditional networking complexity. By eliminating public IPs and load balancers, you can save significant costs while improving security and global performance.

For additional help, consult:
- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Access Documentation](https://developers.cloudflare.com/cloudflare-one/policies/access/)
- [n8n AWS Serverless GitHub Issues](https://github.com/your-org/n8n-aws-serverless/issues)