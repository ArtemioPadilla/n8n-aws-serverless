#!/bin/bash
# Local n8n Deployment Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROFILE="default"
DETACH=true
MONITORING=false

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

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -p, --profile PROFILE    Docker Compose profile to use:"
    echo "                          - default: SQLite database"
    echo "                          - postgres: PostgreSQL database"
    echo "                          - scaling: Redis for scaling"
    echo "                          - cloudflare: Cloudflare Tunnel (requires token)"
    echo "                          - full: Everything (PostgreSQL + monitoring + Cloudflare if configured)"
    echo "  -m, --monitoring         Enable monitoring stack (Prometheus + Grafana)"
    echo "  -f, --foreground        Run in foreground (don't detach)"
    echo "  -d, --down              Stop and remove containers"
    echo "  -r, --restart           Restart containers"
    echo "  -l, --logs              Show logs"
    echo "  -s, --status            Show container status"
    echo "  --full                   Shortcut for '-p full' (deploy everything)"
    echo "  -h, --help              Show this help message"
    echo
    echo "Examples:"
    echo "  $0                      # Start with SQLite"
    echo "  $0 -p postgres          # Start with PostgreSQL"
    echo "  $0 -p cloudflare        # Start with Cloudflare Tunnel"
    echo "  $0 -p scaling -m        # Start with Redis and monitoring"
    echo "  $0 --full               # Start everything (PostgreSQL + monitoring + Cloudflare if configured)"
    echo "  $0 -d                   # Stop all containers"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -m|--monitoring)
            MONITORING=true
            shift
            ;;
        --full)
            PROFILE="full"
            shift
            ;;
        -f|--foreground)
            DETACH=false
            shift
            ;;
        -d|--down)
            ACTION="down"
            shift
            ;;
        -r|--restart)
            ACTION="restart"
            shift
            ;;
        -l|--logs)
            ACTION="logs"
            shift
            ;;
        -s|--status)
            ACTION="status"
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Change to docker directory
cd "$DOCKER_DIR"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error "Environment file not found. Please run './scripts/local-setup.sh' first."
    exit 1
fi

# Determine Docker Compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Build Docker Compose command
get_compose_files() {
    local files="-f docker-compose.yml"
    
    # Handle full profile - deploy everything
    if [ "$PROFILE" = "full" ]; then
        # Check if Cloudflare token exists
        if grep -q "CLOUDFLARE_TUNNEL_TOKEN=." ".env" 2>/dev/null; then
            files="$files --profile postgres --profile monitoring --profile cloudflare-postgres"
        else
            files="$files --profile postgres --profile monitoring"
        fi
        # Note: Not including prod compose file to avoid conflicts
        # files="$files -f docker-compose.prod.yml"
    elif [ "$PROFILE" = "default" ]; then
        files="$files --profile default"
    else
        files="$files --profile $PROFILE"
    fi
    
    # Add monitoring profile if requested (and not already in full mode)
    if [ "$MONITORING" = true ] && [ "$PROFILE" != "full" ]; then
        files="$files --profile monitoring"
    fi
    
    # For postgres profile, include both postgres and monitoring exporters if monitoring is enabled
    if [ "$PROFILE" = "postgres" ] && [ "$MONITORING" = true ]; then
        # postgres-exporter is already included with monitoring profile
        true
    fi
    
    echo "$files"
}

# Execute action
case "${ACTION:-up}" in
    down)
        print_info "Stopping n8n containers..."
        $DOCKER_COMPOSE $(get_compose_files) down -v
        print_success "All containers stopped and removed"
        ;;
        
    restart)
        print_info "Restarting n8n containers..."
        $DOCKER_COMPOSE $(get_compose_files) restart
        print_success "Containers restarted"
        ;;
        
    logs)
        print_info "Showing logs..."
        $DOCKER_COMPOSE $(get_compose_files) logs -f
        ;;
        
    status)
        print_info "Container status:"
        $DOCKER_COMPOSE $(get_compose_files) ps
        echo
        print_info "Container health:"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep n8n || true
        ;;
        
    up|*)
        print_info "Starting n8n with profile: $PROFILE"
        
        # Show info for full profile
        if [ "$PROFILE" = "full" ]; then
            if grep -q "CLOUDFLARE_TUNNEL_TOKEN=." ".env" 2>/dev/null; then
                print_info "Cloudflare Tunnel token detected - enabling Cloudflare"
            else
                print_info "No Cloudflare token found - deploying without Cloudflare Tunnel"
            fi
        fi
        
        # Pull latest images
        print_info "Pulling latest images..."
        $DOCKER_COMPOSE $(get_compose_files) pull
        
        # Start containers
        if [ "$DETACH" = true ]; then
            $DOCKER_COMPOSE $(get_compose_files) up -d
            
            print_success "n8n started successfully!"
            echo
            echo -e "${BLUE}Access n8n at:${NC}"
            echo "  - HTTP:  http://localhost:5678"
            
            if [ -f "ssl/cert.pem" ] && [ "$PROFILE" != "default" ]; then
                echo "  - HTTPS: https://localhost (with nginx)"
            fi
            
            # Check if Cloudflare is running
            if docker ps --format "{{.Names}}" | grep -q "cloudflared"; then
                echo
                echo -e "${BLUE}Cloudflare Tunnel:${NC}"
                echo "  - Status: Active"
                echo "  - Configure your tunnel domain in Cloudflare Zero Trust dashboard"
                echo "  - Tunnel will be accessible at your configured domain"
            fi
            
            if [ "$MONITORING" = true ] || [ "$PROFILE" = "full" ]; then
                echo
                echo -e "${BLUE}Monitoring stack:${NC}"
                echo "  - Prometheus: http://localhost:9090"
                echo "  - Grafana:    http://localhost:3000"
                echo "    Username: admin (check .env for password)"
            fi
            
            if [ "$PROFILE" = "full" ]; then
                echo
                echo -e "${BLUE}Full deployment includes:${NC}"
                echo "  ✓ PostgreSQL database"
                echo "  ✓ Redis for scaling"
                echo "  ✓ Prometheus + Grafana monitoring"
                if docker ps --format "{{.Names}}" | grep -q "cloudflared"; then
                    echo "  ✓ Cloudflare Tunnel (zero-trust access)"
                else
                    echo "  ○ Cloudflare Tunnel (add token to .env to enable)"
                fi
                echo
                echo -e "${YELLOW}Resource usage:${NC}"
                echo "  - Total containers: $(docker ps --format "{{.Names}}" | wc -l | tr -d ' ')"
                echo "  - Approximate memory: ~2GB"
            fi
            
            echo
            echo "Default credentials (if basic auth is enabled):"
            echo "  Username: $(grep N8N_BASIC_AUTH_USER .env | cut -d'=' -f2 || echo 'admin')"
            echo "  Password: Check your .env file"
            echo
            echo "To view logs: $0 -l"
            echo "To stop:      $0 -d"
        else
            $DOCKER_COMPOSE $(get_compose_files) up
        fi
        ;;
esac