#!/bin/bash
# Performance testing script for n8n AWS Serverless

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=${ENVIRONMENT:-dev}
N8N_URL=""
TEST_TYPE="baseline"
DURATION=300  # 5 minutes
CONCURRENT_USERS=10
REQUESTS_PER_SECOND=10

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

print_header() {
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
}

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Performance testing script for n8n AWS Serverless deployment.

OPTIONS:
    -e, --environment ENV       Environment to test (default: dev)
    -u, --url URL              n8n URL to test (required)
    -t, --type TYPE            Test type: baseline, load, stress, spike (default: baseline)
    -d, --duration SECONDS     Test duration in seconds (default: 300)
    -c, --concurrent USERS     Number of concurrent users (default: 10)
    -r, --rps RPS             Requests per second (default: 10)
    -h, --help                Show this help message

EXAMPLES:
    # Run baseline performance test
    $0 -u https://n8n.example.com -t baseline

    # Run load test for 10 minutes with 50 concurrent users
    $0 -u https://n8n.example.com -t load -d 600 -c 50

    # Run stress test
    $0 -u https://n8n.example.com -t stress -c 200 -r 100

EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -u|--url)
            N8N_URL="$2"
            shift 2
            ;;
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -d|--duration)
            DURATION="$2"
            shift 2
            ;;
        -c|--concurrent)
            CONCURRENT_USERS="$2"
            shift 2
            ;;
        -r|--rps)
            REQUESTS_PER_SECOND="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$N8N_URL" ]; then
    print_error "n8n URL is required"
    usage
fi

# Check dependencies
check_dependencies() {
    print_info "Checking dependencies..."

    local deps=("python3" "pip" "aws")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing[*]}"
        echo "Please install the missing dependencies and try again."
        exit 1
    fi

    # Check Python packages
    if ! python3 -c "import pytest" &> /dev/null; then
        print_error "pytest not installed. Run: pip install pytest pytest-asyncio aiohttp"
        exit 1
    fi

    print_success "All dependencies installed"
}

# Setup test environment
setup_test_env() {
    print_info "Setting up test environment..."

    # Create results directory
    RESULTS_DIR="$PROJECT_ROOT/performance-results"
    mkdir -p "$RESULTS_DIR"

    # Export environment variables for tests
    export N8N_TEST_URL="$N8N_URL"
    export N8N_TEST_ENVIRONMENT="$ENVIRONMENT"
    export N8N_TEST_DURATION="$DURATION"
    export N8N_TEST_CONCURRENT="$CONCURRENT_USERS"
    export N8N_TEST_RPS="$REQUESTS_PER_SECOND"

    print_success "Test environment configured"
}

# Run baseline test
run_baseline_test() {
    print_header "Running Baseline Performance Test"

    print_info "Configuration:"
    echo "  - URL: $N8N_URL"
    echo "  - Duration: ${DURATION}s"
    echo "  - Concurrent Users: $CONCURRENT_USERS"
    echo "  - Target RPS: $REQUESTS_PER_SECOND"
    echo

    # Run pytest with baseline test
    python3 -m pytest "$PROJECT_ROOT/tests/performance/test_load_benchmarks.py::TestLoadBenchmarks::test_webhook_performance_baseline" \
        -v \
        --tb=short \
        --junit-xml="$RESULTS_DIR/baseline-$(date +%Y%m%d-%H%M%S).xml"
}

# Run load test
run_load_test() {
    print_header "Running Load Performance Test"

    print_info "Configuration:"
    echo "  - URL: $N8N_URL"
    echo "  - Duration: ${DURATION}s"
    echo "  - Concurrent Users: $CONCURRENT_USERS"
    echo "  - Target RPS: $REQUESTS_PER_SECOND"
    echo

    # Run pytest with load test
    python3 -m pytest "$PROJECT_ROOT/tests/performance/test_load_benchmarks.py::TestLoadBenchmarks::test_webhook_performance_under_load" \
        -v \
        --tb=short \
        --junit-xml="$RESULTS_DIR/load-$(date +%Y%m%d-%H%M%S).xml"
}

# Run stress test
run_stress_test() {
    print_header "Running Stress Test"

    print_info "Configuration:"
    echo "  - URL: $N8N_URL"
    echo "  - Duration: ${DURATION}s"
    echo "  - Concurrent Users: $CONCURRENT_USERS"
    echo "  - Target RPS: $REQUESTS_PER_SECOND"
    echo

    # Run pytest with stress test
    python3 -m pytest "$PROJECT_ROOT/tests/performance/test_load_benchmarks.py::TestLoadBenchmarks::test_webhook_performance_stress" \
        -v \
        --tb=short \
        --junit-xml="$RESULTS_DIR/stress-$(date +%Y%m%d-%H%M%S).xml"
}

# Run spike test
run_spike_test() {
    print_header "Running Spike Test"

    print_info "Configuration:"
    echo "  - URL: $N8N_URL"
    echo "  - Normal Load: 10 RPS"
    echo "  - Spike Load: $REQUESTS_PER_SECOND RPS"
    echo "  - Spike Duration: 60s"
    echo

    # For spike test, we'll use a custom script
    python3 << EOF
import asyncio
import time
from tests.performance.test_load_benchmarks import TestLoadBenchmarks

async def spike_test():
    test = TestLoadBenchmarks()

    # Normal load
    print("Starting normal load phase...")
    normal_results = await test._run_webhook_load_test("$N8N_URL/webhook/test", 100, 10)
    print(f"Normal load results: {normal_results}")

    # Spike
    print("\nStarting spike phase...")
    spike_results = await test._run_webhook_load_test("$N8N_URL/webhook/test", 1000, $CONCURRENT_USERS)
    print(f"Spike results: {spike_results}")

    # Return to normal
    print("\nReturning to normal load...")
    recovery_results = await test._run_webhook_load_test("$N8N_URL/webhook/test", 100, 10)
    print(f"Recovery results: {recovery_results}")

asyncio.run(spike_test())
EOF
}

# Monitor resources during test
monitor_resources() {
    print_info "Monitoring AWS resources during test..."

    # Get ECS service metrics
    aws cloudwatch get-metric-statistics \
        --namespace AWS/ECS \
        --metric-name CPUUtilization \
        --dimensions Name=ServiceName,Value=n8n-"$ENVIRONMENT" \
        --start-time "$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S)" \
        --end-time "$(date -u +%Y-%m-%dT%H:%M:%S)" \
        --period 60 \
        --statistics Average,Maximum \
        --output table
}

# Generate report
generate_report() {
    print_header "Generating Performance Report"

    REPORT_FILE="$RESULTS_DIR/performance-report-$(date +%Y%m%d-%H%M%S).md"

    cat > "$REPORT_FILE" << EOF
# n8n Performance Test Report

**Date**: $(date)
**Environment**: $ENVIRONMENT
**URL**: $N8N_URL
**Test Type**: $TEST_TYPE

## Test Configuration
- Duration: ${DURATION}s
- Concurrent Users: $CONCURRENT_USERS
- Target RPS: $REQUESTS_PER_SECOND

## Results Summary
$(find "$RESULTS_DIR" -name "*.xml" -mtime -1 -exec echo "- {}" \;)

## Resource Utilization
\`\`\`
$(monitor_resources)
\`\`\`

## Recommendations
- Monitor CPU and memory usage during peak loads
- Consider scaling policies based on test results
- Review error logs for any failures during testing

EOF

    print_success "Report generated: $REPORT_FILE"
}

# Main execution
main() {
    print_header "n8n AWS Serverless Performance Testing"

    check_dependencies
    setup_test_env

    case $TEST_TYPE in
        baseline)
            run_baseline_test
            ;;
        load)
            run_load_test
            ;;
        stress)
            run_stress_test
            ;;
        spike)
            run_spike_test
            ;;
        *)
            print_error "Invalid test type: $TEST_TYPE"
            usage
            ;;
    esac

    # Monitor resources
    monitor_resources

    # Generate report
    generate_report

    print_success "Performance testing completed!"
    echo
    echo "Results saved to: $RESULTS_DIR"
}

# Run main function
main
