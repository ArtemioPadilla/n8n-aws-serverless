#!/bin/bash
# Local n8n Development Setup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose is installed"
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon is running"
}

# Create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    
    mkdir -p "$DOCKER_DIR/workflows"
    mkdir -p "$DOCKER_DIR/ssl"
    mkdir -p "$DOCKER_DIR/grafana/dashboards"
    mkdir -p "$DOCKER_DIR/grafana/datasources"
    
    print_success "Directories created"
}

# Setup environment file
setup_env_file() {
    print_info "Setting up environment file..."
    
    if [ ! -f "$DOCKER_DIR/.env" ]; then
        cp "$DOCKER_DIR/.env.example" "$DOCKER_DIR/.env"
        
        # Generate encryption key
        ENCRYPTION_KEY=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 64 | head -n 1)
        
        # Update .env file based on OS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/your-32-character-encryption-key-here/$ENCRYPTION_KEY/" "$DOCKER_DIR/.env"
        else
            # Linux
            sed -i "s/your-32-character-encryption-key-here/$ENCRYPTION_KEY/" "$DOCKER_DIR/.env"
        fi
        
        print_success "Environment file created with generated encryption key"
        print_info "Please review and update $DOCKER_DIR/.env with your settings"
    else
        print_success "Environment file already exists"
    fi
}

# Generate self-signed SSL certificates for local HTTPS
generate_ssl_certs() {
    print_info "Generating self-signed SSL certificates..."
    
    if [ ! -f "$DOCKER_DIR/ssl/cert.pem" ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$DOCKER_DIR/ssl/key.pem" \
            -out "$DOCKER_DIR/ssl/cert.pem" \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
            2>/dev/null
        
        print_success "SSL certificates generated"
    else
        print_success "SSL certificates already exist"
    fi
}

# Create Prometheus configuration
create_prometheus_config() {
    print_info "Creating Prometheus configuration..."
    
    cat > "$DOCKER_DIR/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'n8n'
    static_configs:
      - targets: ['n8n:5678']
    metrics_path: '/metrics'
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
      
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
      
  - job_name: 'cloudflared'
    static_configs:
      - targets: ['cloudflared:2000']
    metrics_path: '/metrics'
EOF
    
    print_success "Prometheus configuration created"
}

# Create Grafana datasource configuration
create_grafana_datasource() {
    print_info "Creating Grafana datasource configuration..."
    
    cat > "$DOCKER_DIR/grafana/datasources/prometheus.yml" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF
    
    print_success "Grafana datasource configuration created"
}

# Create sample n8n dashboard for Grafana
create_grafana_dashboard() {
    print_info "Creating sample Grafana dashboard..."
    
    cat > "$DOCKER_DIR/grafana/dashboards/n8n-dashboard.json" << 'EOF'
{
  "dashboard": {
    "id": null,
    "uid": "n8n-metrics",
    "title": "n8n Metrics Dashboard",
    "timezone": "browser",
    "schemaVersion": 16,
    "version": 0,
    "refresh": "30s",
    "panels": [
      {
        "datasource": "Prometheus",
        "fieldConfig": {
          "defaults": {
            "custom": {}
          },
          "overrides": []
        },
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 0
        },
        "id": 1,
        "options": {
          "showLegend": true
        },
        "targets": [
          {
            "expr": "n8n_workflow_executions_total",
            "refId": "A"
          }
        ],
        "title": "Workflow Executions",
        "type": "graph"
      }
    ]
  }
}
EOF
    
    # Create dashboard provider configuration
    cat > "$DOCKER_DIR/grafana/dashboards/provider.yml" << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF
    
    print_success "Grafana dashboard created"
}

# Setup Cloudflare Tunnel configuration
setup_cloudflare_tunnel() {
    print_info "Checking Cloudflare Tunnel configuration..."
    
    # Check if user wants to set up Cloudflare Tunnel
    echo
    read -p "Do you want to configure Cloudflare Tunnel for secure remote access? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Setting up Cloudflare Tunnel configuration..."
        
        echo
        echo "To use Cloudflare Tunnel, you need to:"
        echo "1. Create a tunnel in your Cloudflare Zero Trust dashboard"
        echo "2. Copy the tunnel token"
        echo
        
        read -p "Do you have a Cloudflare Tunnel token? (y/N): " -n 1 -r
        echo
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter your Cloudflare Tunnel token: " TUNNEL_TOKEN
            
            if [ ! -z "$TUNNEL_TOKEN" ]; then
                # Validate token format (base64-like string, typically 40+ characters)
                if [[ ! "$TUNNEL_TOKEN" =~ ^[a-zA-Z0-9_-]{40,}$ ]]; then
                    print_error "Invalid token format. Cloudflare Tunnel tokens are typically long base64-like strings."
                    echo "Please check your token and try again."
                    return 1
                fi
                
                # Update .env file with the token
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    # macOS
                    sed -i '' "s/CLOUDFLARE_TUNNEL_TOKEN=$/CLOUDFLARE_TUNNEL_TOKEN=$TUNNEL_TOKEN/" "$DOCKER_DIR/.env"
                else
                    # Linux
                    sed -i "s/CLOUDFLARE_TUNNEL_TOKEN=$/CLOUDFLARE_TUNNEL_TOKEN=$TUNNEL_TOKEN/" "$DOCKER_DIR/.env"
                fi
                
                print_success "Cloudflare Tunnel token configured"
                echo
                echo "To use Cloudflare Tunnel, run:"
                echo "  ./scripts/local-deploy.sh -p cloudflare"
                echo
            else
                print_error "No token provided. Skipping Cloudflare Tunnel configuration."
            fi
        else
            print_info "You can add the token later by editing $DOCKER_DIR/.env"
            echo
            echo "Instructions:"
            echo "1. Go to https://one.dash.cloudflare.com/"
            echo "2. Navigate to Access > Tunnels"
            echo "3. Create a new tunnel or use an existing one"
            echo "4. Copy the tunnel token"
            echo "5. Add it to CLOUDFLARE_TUNNEL_TOKEN in $DOCKER_DIR/.env"
            echo
        fi
    else
        print_info "Skipping Cloudflare Tunnel configuration"
    fi
}

# Main setup
main() {
    echo "🚀 n8n Local Development Setup"
    echo "=============================="
    echo
    
    check_prerequisites
    create_directories
    setup_env_file
    generate_ssl_certs
    create_prometheus_config
    create_grafana_datasource
    create_grafana_dashboard
    setup_cloudflare_tunnel
    
    echo
    print_success "Local setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Review and update the environment file: $DOCKER_DIR/.env"
    echo "2. Run './scripts/local-deploy.sh' to start n8n locally"
    echo "3. Access n8n at http://localhost:5678"
    echo
}

# Run main function
main "$@"