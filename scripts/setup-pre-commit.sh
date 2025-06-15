#!/usr/bin/env bash
#
# Setup pre-commit hooks for n8n AWS Serverless
#
# This script installs and configures pre-commit hooks to ensure
# code quality before commits and pushes.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up pre-commit hooks for n8n AWS Serverless...${NC}"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
# shellcheck source=/dev/null
source .venv/bin/activate

# Install pre-commit if not already installed
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install
pre-commit install --hook-type pre-push

# Run pre-commit on all files to check current state
echo -e "\n${YELLOW}Running pre-commit on all files to check current state...${NC}"
pre-commit run --all-files || true

echo -e "\n${GREEN}Pre-commit hooks installed successfully!${NC}"
echo -e "\nThe following hooks will run:"
echo -e "  ${YELLOW}On every commit:${NC}"
echo -e "    - Code formatting (black, isort)"
echo -e "    - Linting (flake8, bandit)"
echo -e "    - Security checks (detect-secrets)"
echo -e "    - make lint"
echo -e "    - Quick unit tests"
echo -e "\n  ${YELLOW}On git push:${NC}"
echo -e "    - Full test suite (make test)"
echo -e "\n${GREEN}Tips:${NC}"
echo -e "  - To run all hooks manually: ${YELLOW}pre-commit run --all-files${NC}"
echo -e "  - To skip hooks temporarily: ${YELLOW}git commit --no-verify${NC}"
echo -e "  - To update hook versions: ${YELLOW}pre-commit autoupdate${NC}"
