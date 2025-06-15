# n8n Deploy - Multi-Platform Architecture

This document describes the architecture options available in n8n Deploy, covering AWS Serverless, Docker/On-Premise, and Cloudflare Tunnel deployments.

## 🎯 Architecture Decision Matrix

| Requirement | AWS Serverless | Docker Local | Docker Production | Cloudflare Tunnel |
|------------|----------------|--------------|-------------------|-------------------|
| **Cost Sensitivity** | Medium | Low | Low | Low |
| **Scalability Needs** | High | Low | Medium | Medium |
| **Maintenance Effort** | Low | High | High | Medium |
| **Security Requirements** | High | Medium | Medium | Very High |
| **Compliance Needs** | Yes | Yes | Yes | Yes |
| **Internet Exposure** | Optional | Optional | Required | Not Required |
| **Team Size** | Any | 1-10 | 10-100 | Any |
| **DevOps Expertise** | Low | Medium | High | Medium |

## 🏗️ Architecture Overview

### Option 1: AWS Serverless Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   CloudFront    │─────▶│  API Gateway    │─────▶│  ECS Fargate    │
│  (CDN + Cache)  │      │  (HTTP API)     │      │  (n8n + Spot)   │
└─────────────────┘      └─────────────────┘      └────────┬────────┘
                                                            │
        ┌───────────────────────────────────────────────────┼───────────────────┐
        │                                                   │                   │
        ▼                         ▼                         ▼                   ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ ┌─────────────────┐
│       EFS       │      │  RDS/Aurora     │      │ Secrets Manager │ │   CloudWatch    │
│  (Workflows)    │      │  (PostgreSQL)   │      │  (Credentials)  │ │  (Monitoring)   │
└─────────────────┘      └─────────────────┘      └─────────────────┘ └─────────────────┘
```

**Key Components:**

- **API Gateway HTTP API**: Cost-effective serverless API ($1/million requests)
- **ECS Fargate**: Serverless containers with 70% cost savings using Spot
- **EFS**: Persistent storage for workflows and SQLite option
- **RDS/Aurora**: Optional managed PostgreSQL for production scale
- **CloudWatch**: Comprehensive monitoring and logging

**Best For:**

- SaaS applications
- Variable workloads
- Teams wanting managed infrastructure
- Cost-conscious deployments

### Option 2: Docker Local/Development Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│    Browser      │─────▶│  Host Machine   │─────▶│ Docker Network  │
│  (localhost)    │      │  (Port 5678)   │      │   (n8n_net)     │
└─────────────────┘      └─────────────────┘      └────────┬────────┘
                                                            │
        ┌───────────────────────────────────────────────────┼───────────────────┐
        │                         │                         │                   │
        ▼                         ▼                         ▼                   ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ ┌─────────────────┐
│   n8n Container │      │   PostgreSQL    │      │  Redis Container│ │    Grafana      │
│   (App Logic)   │      │   Container     │      │   (Queue/Cache) │ │  + Prometheus   │
└─────────────────┘      └─────────────────┘      └─────────────────┘ └─────────────────┘
        │
        ▼
┌─────────────────┐
│  Local Volume   │
│ (./n8n-data)    │
└─────────────────┘
```

**Key Components:**

- **Docker Compose**: Orchestrates all services
- **n8n Container**: Main application with hot-reload in dev mode
- **PostgreSQL/SQLite**: Database options based on needs
- **Redis**: Optional for scaling and queueing
- **Monitoring Stack**: Optional Prometheus + Grafana

**Best For:**

- Local development
- Testing and CI/CD
- Learning n8n
- Quick prototypes

### Option 3: Docker Production/On-Premise Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Internet      │─────▶│  Nginx/Traefik  │─────▶│ Docker Swarm/   │
│  (HTTPS:443)    │      │  (Reverse Proxy)│      │   Kubernetes    │
└─────────────────┘      └─────────────────┘      └────────┬────────┘
                                                            │
        ┌───────────────────────────────────────────────────┼───────────────────┐
        │                         │                         │                   │
        ▼                         ▼                         ▼                   ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐ ┌─────────────────┐
│ n8n Replicas    │      │ PostgreSQL HA   │      │ Redis Sentinel  │ │ Monitoring Stack│
│ (Multi-instance)│      │ (Primary/Replica)│      │ (HA Redis)      │ │ (Prometheus)    │
└─────────────────┘      └─────────────────┘      └─────────────────┘ └─────────────────┘
        │                         │
        ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│   NFS/GlusterFS │      │ Backup Storage  │
│ (Shared Storage)│      │ (S3/NAS/Cloud)  │
└─────────────────┘      └─────────────────┘
```

**Key Components:**

- **Load Balancer**: Nginx/Traefik with SSL termination
- **Container Orchestration**: Docker Swarm or Kubernetes
- **High Availability**: Multiple n8n instances with shared storage
- **Database HA**: PostgreSQL with replication
- **Monitoring**: Full Prometheus/Grafana/AlertManager stack

**Best For:**

- On-premise requirements
- Full control needs
- Existing Docker infrastructure
- Air-gapped environments

### Option 4: Cloudflare Tunnel Architecture (Zero-Trust)

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│     Users       │─────▶│ Cloudflare Edge │─────▶│ Cloudflare      │
│  (Anywhere)     │      │   (Global PoP)  │      │   Tunnel        │
└─────────────────┘      └─────────────────┘      └────────┬────────┘
                                                            │ Outbound Only
                                                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Private Network (No Inbound)                  │
│  ┌─────────────────┐      ┌─────────────────┐      ┌─────────────┐ │
│  │ cloudflared     │─────▶│ n8n Container/  │─────▶│ PostgreSQL  │ │
│  │ (Tunnel Client) │      │   Instance      │      │   Database  │ │
│  └─────────────────┘      └─────────────────┘      └─────────────┘ │
│                                    │                                 │
│                                    ▼                                 │
│                           ┌─────────────────┐                       │
│                           │ Storage Volume  │                       │
│                           │ (EFS/NFS/Local) │                       │
│                           └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **Cloudflare Edge**: Global network with DDoS protection
- **Cloudflare Tunnel**: Secure outbound-only connection
- **Zero-Trust Access**: Email/domain-based authentication
- **No Public IPs**: All connections initiated from inside
- **Any Backend**: Works with AWS, Docker, or bare metal

**Best For:**

- Maximum security requirements
- No public IP allocation
- Global user base
- Compliance needs (SOC2, HIPAA)

## 🔄 Hybrid Architectures

### AWS + Cloudflare Tunnel

```
Cloudflare Edge ──► Cloudflare Tunnel ──► AWS Private Subnet ──► ECS Fargate
                                                                      │
                                                                      ▼
                                                                  EFS + RDS
```

**Benefits:**

- Zero-trust security with AWS scalability
- No API Gateway or Load Balancer costs
- Global edge network + auto-scaling

### Multi-Region with Cloudflare

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ US Users     │     │ EU Users     │     │ APAC Users   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────┐
│           Cloudflare Global Network                   │
└─────────────┬────────────┬────────────┬──────────────┘
              │            │            │
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌─────────┐
        │ US-East │  │ EU-West │  │ AP-South│
        │   AWS   │  │   AWS   │  │   AWS   │
        └─────────┘  └─────────┘  └─────────┘
```

## 📊 Performance Characteristics

### Latency Comparison

| Deployment Type | First Byte Time | API Response | Workflow Execution |
|----------------|-----------------|--------------|-------------------|
| AWS Serverless | 150-300ms | 50-100ms | Near-instant |
| Docker Local | 10-50ms | 10-30ms | Near-instant |
| Docker Production | 50-150ms | 30-80ms | Near-instant |
| Cloudflare Tunnel | 100-200ms | 40-90ms | Near-instant |

### Scalability Limits

| Deployment Type | Concurrent Users | Workflows/Hour | Storage Limit |
|----------------|------------------|----------------|---------------|
| AWS Serverless | Unlimited* | Unlimited* | 16TB (EFS) |
| Docker Local | 10-50 | 1,000 | Host disk |
| Docker Production | 100-1,000 | 10,000 | NAS/SAN limit |
| Cloudflare Tunnel | Based on backend | Based on backend | Based on backend |

*Within AWS service limits

## 🛡️ Security Architecture

### Defense in Depth

```
Layer 1: Edge Security (CloudFront/Cloudflare)
  ├── DDoS Protection
  ├── WAF Rules
  └── Geographic Restrictions

Layer 2: Access Control
  ├── API Keys (API Gateway)
  ├── Zero-Trust (Cloudflare Access)
  └── OAuth2/SAML (All platforms)

Layer 3: Network Security
  ├── VPC Isolation (AWS)
  ├── Security Groups
  └── Network Policies (Kubernetes)

Layer 4: Application Security
  ├── n8n Authentication
  ├── Encryption at Rest
  └── Secrets Management

Layer 5: Data Security
  ├── Backup Encryption
  ├── Transit Encryption
  └── Audit Logging
```

## 🔧 Technology Stack

### Core Technologies

| Component | AWS Serverless | Docker | Cloudflare Tunnel |
|-----------|---------------|---------|-------------------|
| **Runtime** | ECS Fargate | Docker Engine | Any |
| **Database** | RDS/Aurora/SQLite | PostgreSQL/SQLite | Any |
| **Storage** | EFS | Local/NFS | Any |
| **Secrets** | AWS Secrets Manager | Docker Secrets | Environment |
| **Monitoring** | CloudWatch | Prometheus | Cloudflare Analytics |
| **Scaling** | Auto Scaling Groups | Manual/Swarm | Manual |
| **Load Balancing** | API Gateway | Nginx/Traefik | Cloudflare |

## 📈 Scaling Patterns

### Vertical Scaling

- **AWS**: Increase Fargate CPU/Memory
- **Docker**: Increase container resources
- **Cloudflare**: Scale backend resources

### Horizontal Scaling

- **AWS**: Auto Scaling with target tracking
- **Docker**: Swarm/Kubernetes replicas
- **Cloudflare**: Multiple tunnel instances

### Database Scaling

- **AWS**: RDS read replicas, Aurora Serverless
- **Docker**: PostgreSQL replication, pgpool
- **Hybrid**: Managed database services

## 🎯 Choosing the Right Architecture

### Decision Tree

```
Start
  │
  ├─ Need managed infrastructure? ──► Yes ──► AWS Serverless
  │
  ├─ Developing locally? ──► Yes ──► Docker Local
  │
  ├─ Have on-premise requirements? ──► Yes ──► Docker Production
  │
  ├─ Need zero-trust security? ──► Yes ──► Cloudflare Tunnel
  │
  └─ Want lowest cost? ──► Evaluate:
      ├─ < 100 users: Docker + Cloudflare Tunnel
      ├─ 100-1000 users: AWS Serverless
      └─ > 1000 users: AWS + CloudFront
```

## 🚀 Migration Paths

### From Docker to AWS

1. Export workflows and credentials
2. Deploy AWS infrastructure
3. Import data to EFS/RDS
4. Update DNS/access points
5. Validate and cutover

### From AWS to Docker

1. Create EFS backup
2. Export RDS data
3. Deploy Docker stack
4. Import data
5. Configure access method

### Adding Cloudflare Tunnel

1. Create tunnel in Cloudflare
2. Deploy cloudflared container/service
3. Configure access policies
4. Update DNS to Cloudflare
5. Remove public endpoints

## 📚 Further Reading

- [Deployment Guide](deployment-guide.md) - Step-by-step deployment instructions
- [Security Best Practices](security.md) - Hardening each architecture
- [Cost Optimization](cost-optimization.md) - Reducing deployment costs
- [Monitoring Setup](monitoring.md) - Observability for each platform
- [Disaster Recovery](disaster-recovery.md) - Backup and recovery strategies
