#!/bin/bash
# Script to rotate Cloudflare Tunnel token

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
SECRET_NAME=""
NEW_TOKEN=""
RESTART_SERVICE=false

# Function to print colored output
print_error() { echo -e "${RED}ERROR: $1${NC}" >&2; }
print_success() { echo -e "${GREEN}SUCCESS: $1${NC}"; }
print_warning() { echo -e "${YELLOW}WARNING: $1${NC}"; }
print_info() { echo -e "INFO: $1"; }

# Function to show usage
usage() {
    echo "Usage: $0 -e ENVIRONMENT [-s SECRET_NAME] [-t TOKEN] [-r]"
    echo
    echo "Options:"
    echo "  -e ENVIRONMENT    Environment name (required)"
    echo "  -s SECRET_NAME    Secret name (optional, defaults to n8n/ENVIRONMENT/cloudflare-tunnel-token)"
    echo "  -t TOKEN          New tunnel token (optional, will prompt if not provided)"
    echo "  -r                Restart ECS service after rotation"
    echo "  -h                Show this help message"
    echo
    echo "Examples:"
    echo "  $0 -e production -t eyJhIjoiYTY4Nz..."
    echo "  $0 -e production -r"
    echo "  $0 -e dev -s custom-secret-name"
}

# Parse command line arguments
while getopts "e:s:t:rh" opt; do
    case ${opt} in
        e)
            ENVIRONMENT=$OPTARG
            ;;
        s)
            SECRET_NAME=$OPTARG
            ;;
        t)
            NEW_TOKEN=$OPTARG
            ;;
        r)
            RESTART_SERVICE=true
            ;;
        h)
            usage
            exit 0
            ;;
        \?)
            print_error "Invalid option: -$OPTARG"
            usage
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$ENVIRONMENT" ]; then
    print_error "Environment is required"
    usage
    exit 1
fi

# Set default secret name if not provided
if [ -z "$SECRET_NAME" ]; then
    SECRET_NAME="n8n/${ENVIRONMENT}/cloudflare-tunnel-token"
fi

# Function to check if AWS CLI is installed
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
}

# Function to verify AWS credentials
verify_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi
}

# Function to check if secret exists
check_secret_exists() {
    if ! aws secretsmanager describe-secret --secret-id "$SECRET_NAME" &> /dev/null; then
        print_error "Secret '$SECRET_NAME' does not exist"
        exit 1
    fi
}

# Function to create backup of current token
backup_current_token() {
    local current_token
    current_token=$(aws secretsmanager get-secret-value --secret-id "$SECRET_NAME" --query 'SecretString' --output text 2>/dev/null || echo "")
    
    if [ -n "$current_token" ]; then
        local backup_name="${SECRET_NAME}-backup-$(date +%Y%m%d-%H%M%S)"
        print_info "Creating backup of current token: $backup_name"
        
        aws secretsmanager create-secret \
            --name "$backup_name" \
            --description "Backup of Cloudflare tunnel token before rotation" \
            --secret-string "$current_token" \
            --tags Key=Purpose,Value=backup Key=OriginalSecret,Value="$SECRET_NAME" \
            > /dev/null
        
        print_success "Backup created successfully"
    fi
}

# Function to validate tunnel token format
validate_token() {
    local token=$1
    
    # Basic validation - token should be a long base64-like string
    if [[ ! "$token" =~ ^[a-zA-Z0-9_-]{40,}$ ]]; then
        print_error "Invalid token format. Cloudflare tunnel tokens are typically long base64-like strings."
        return 1
    fi
    
    return 0
}

# Function to update the secret
update_secret() {
    local token=$1
    
    print_info "Updating secret '$SECRET_NAME'..."
    
    if aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "$token" \
        > /dev/null; then
        print_success "Secret updated successfully"
        return 0
    else
        print_error "Failed to update secret"
        return 1
    fi
}

# Function to restart ECS service
restart_ecs_service() {
    local cluster_name="n8n-${ENVIRONMENT}"
    local service_name="n8n-${ENVIRONMENT}"
    
    print_info "Restarting ECS service '$service_name' in cluster '$cluster_name'..."
    
    # Force new deployment to pick up the new secret
    if aws ecs update-service \
        --cluster "$cluster_name" \
        --service "$service_name" \
        --force-new-deployment \
        > /dev/null; then
        print_success "ECS service restart initiated"
        
        # Wait for service to stabilize
        print_info "Waiting for service to stabilize..."
        aws ecs wait services-stable \
            --cluster "$cluster_name" \
            --services "$service_name" \
            2>/dev/null || print_warning "Service is taking longer than expected to stabilize"
    else
        print_error "Failed to restart ECS service"
        return 1
    fi
}

# Function to verify tunnel health
verify_tunnel_health() {
    local cluster_name="n8n-${ENVIRONMENT}"
    
    print_info "Verifying tunnel health..."
    
    # Get the latest task ARN
    local task_arn=$(aws ecs list-tasks \
        --cluster "$cluster_name" \
        --service-name "n8n-${ENVIRONMENT}" \
        --desired-status RUNNING \
        --query 'taskArns[0]' \
        --output text)
    
    if [ "$task_arn" != "None" ] && [ -n "$task_arn" ]; then
        # Check task health
        local task_health=$(aws ecs describe-tasks \
            --cluster "$cluster_name" \
            --tasks "$task_arn" \
            --query 'tasks[0].healthStatus' \
            --output text)
        
        if [ "$task_health" == "HEALTHY" ]; then
            print_success "Tunnel is healthy"
            return 0
        else
            print_warning "Tunnel health status: $task_health"
            return 1
        fi
    else
        print_warning "No running tasks found"
        return 1
    fi
}

# Main execution
main() {
    print_info "Cloudflare Tunnel Token Rotation"
    print_info "================================"
    echo
    
    # Check prerequisites
    check_aws_cli
    verify_aws_credentials
    check_secret_exists
    
    # Get new token if not provided
    if [ -z "$NEW_TOKEN" ]; then
        echo "Please enter the new Cloudflare tunnel token:"
        read -s NEW_TOKEN
        echo
    fi
    
    # Validate token
    if ! validate_token "$NEW_TOKEN"; then
        exit 1
    fi
    
    # Backup current token
    backup_current_token
    
    # Update the secret
    if ! update_secret "$NEW_TOKEN"; then
        exit 1
    fi
    
    # Restart service if requested
    if [ "$RESTART_SERVICE" = true ]; then
        if restart_ecs_service; then
            # Give the service a moment to start
            sleep 30
            
            # Verify health
            verify_tunnel_health || print_warning "Please check CloudWatch logs for any issues"
        fi
    else
        print_warning "Service not restarted. Use -r flag to restart the ECS service."
        print_info "You will need to manually restart the service for the new token to take effect."
    fi
    
    echo
    print_success "Token rotation completed successfully!"
    
    if [ "$RESTART_SERVICE" = false ]; then
        echo
        echo "Next steps:"
        echo "1. Restart the ECS service: aws ecs update-service --cluster n8n-${ENVIRONMENT} --service n8n-${ENVIRONMENT} --force-new-deployment"
        echo "2. Monitor CloudWatch logs for any connection issues"
        echo "3. Verify tunnel health in Cloudflare dashboard"
    fi
}

# Run main function
main