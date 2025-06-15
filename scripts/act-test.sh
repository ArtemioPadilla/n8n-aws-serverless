#!/bin/bash
# Script to run GitHub Actions locally with act
# This addresses common issues like missing Node.js in containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running GitHub Actions locally with act...${NC}"

# Check if act is installed
if ! command -v act &> /dev/null; then
    echo -e "${RED}Error: act is not installed${NC}"
    echo "Install with: brew install act (macOS) or see https://github.com/nektos/act"
    exit 1
fi

# Check if .env.act exists
if [ ! -f .env.act ]; then
    echo -e "${YELLOW}Warning: .env.act not found. Creating from template...${NC}"
    echo "Please edit .env.act with your tokens if needed"
fi

# Parse command line arguments
WORKFLOW=""
JOB=""
EVENT="push"

while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--workflow)
            WORKFLOW="$2"
            shift 2
            ;;
        -j|--job)
            JOB="$2"
            shift 2
            ;;
        -e|--event)
            EVENT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -w, --workflow <name>  Specific workflow to run (e.g., test.yml)"
            echo "  -j, --job <name>       Specific job to run"
            echo "  -e, --event <type>     Event type (default: push)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run all workflows"
            echo "  $0 -w test.yml        # Run test workflow"
            echo "  $0 -j lint            # Run lint job"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Build act command
ACT_CMD="act $EVENT"

# Add workflow filter if specified
if [ -n "$WORKFLOW" ]; then
    ACT_CMD="$ACT_CMD -W .github/workflows/$WORKFLOW"
fi

# Add job filter if specified
if [ -n "$JOB" ]; then
    ACT_CMD="$ACT_CMD -j $JOB"
fi

# Add common flags
ACT_CMD="$ACT_CMD --container-architecture linux/amd64"

# Show what we're running
echo -e "${YELLOW}Running: $ACT_CMD${NC}"

# Run act with error handling
if $ACT_CMD; then
    echo -e "${GREEN}✅ Act run completed successfully${NC}"
else
    echo -e "${RED}❌ Act run failed${NC}"
    echo -e "${YELLOW}Common issues:${NC}"
    echo "1. If you see 'node not found' errors, make sure .actrc uses 'full' images"
    echo "2. If you see token errors, add GITHUB_TOKEN to .env.act"
    echo "3. For 'docker not found' errors, add: -P ubuntu-latest=catthehacker/ubuntu:full-latest"
    exit 1
fi
