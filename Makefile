.PHONY: help install test lint format clean deploy local-up local-down docker-build docs

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
CDK := cdk
DOCKER_COMPOSE := docker-compose
PYTEST := pytest
BLACK := black
FLAKE8 := flake8
ISORT := isort

# Detect OS for script execution
ifeq ($(OS),Windows_NT)
    SCRIPT_EXT := .bat
    ACTIVATE := .venv\Scripts\activate
else
    SCRIPT_EXT := .sh
    ACTIVATE := source .venv/bin/activate
endif

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "n8n AWS Serverless - Available Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# Setup and Installation
install: venv ## Install all dependencies
	$(ACTIVATE) && $(PIP) install -r requirements.txt -r requirements-dev.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

venv: ## Create virtual environment
	@if [ ! -d ".venv" ]; then \
		$(PYTHON) -m venv .venv; \
		echo "$(GREEN)✓ Virtual environment created$(NC)"; \
	else \
		echo "$(YELLOW)Virtual environment already exists$(NC)"; \
	fi

update: ## Update dependencies
	$(ACTIVATE) && $(PIP) install --upgrade pip
	$(ACTIVATE) && $(PIP) install --upgrade -r requirements.txt -r requirements-dev.txt
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

# Development
lint: ## Run linting checks
	@echo "$(YELLOW)Running linting checks...$(NC)"
	$(ACTIVATE) && $(BLACK) --check n8n_aws_serverless tests
	$(ACTIVATE) && $(FLAKE8) n8n_aws_serverless tests
	$(ACTIVATE) && $(ISORT) --check-only n8n_aws_serverless tests
	@echo "$(GREEN)✓ Linting passed$(NC)"

format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(ACTIVATE) && $(BLACK) n8n_aws_serverless tests
	$(ACTIVATE) && $(ISORT) n8n_aws_serverless tests
	@echo "$(GREEN)✓ Code formatted$(NC)"

test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	$(ACTIVATE) && $(PYTEST)

test-cov: ## Run tests with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(ACTIVATE) && $(PYTEST) --cov=n8n_aws_serverless --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	$(ACTIVATE) && $(PYTEST) -f

# AWS CDK Commands
synth: ## Synthesize CDK stacks
	@echo "$(YELLOW)Synthesizing CDK stacks...$(NC)"
	$(CDK) synth -c environment=dev

diff: ## Show CDK diff
	$(CDK) diff -c environment=dev

deploy-dev: ## Deploy to development environment
	@echo "$(YELLOW)Deploying to development...$(NC)"
	$(CDK) deploy -c environment=dev --all

deploy-staging: ## Deploy to staging environment
	@echo "$(YELLOW)Deploying to staging...$(NC)"
	$(CDK) deploy -c environment=staging --all

deploy-prod: ## Deploy to production environment
	@echo "$(RED)Deploying to PRODUCTION...$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(CDK) deploy -c environment=production --all; \
	else \
		echo "$(YELLOW)Deployment cancelled$(NC)"; \
	fi

destroy-dev: ## Destroy development environment
	@echo "$(RED)Destroying development environment...$(NC)"
	$(CDK) destroy -c environment=dev --all

# Local Development
local-setup: ## Setup local development environment
	@echo "$(YELLOW)Setting up local environment...$(NC)"
	chmod +x scripts/*$(SCRIPT_EXT)
	./scripts/local-setup$(SCRIPT_EXT)

local-up: ## Start local n8n
	@echo "$(YELLOW)Starting local n8n...$(NC)"
	./scripts/local-deploy$(SCRIPT_EXT)

local-down: ## Stop local n8n
	@echo "$(YELLOW)Stopping local n8n...$(NC)"
	./scripts/local-deploy$(SCRIPT_EXT) -d

local-logs: ## Show local n8n logs
	./scripts/local-deploy$(SCRIPT_EXT) -l

local-test: ## Test local n8n
	@echo "$(YELLOW)Testing local n8n...$(NC)"
	./scripts/local-test$(SCRIPT_EXT)

# Docker Commands
docker-build: ## Build Docker images
	@echo "$(YELLOW)Building Docker images...$(NC)"
	cd docker && $(DOCKER_COMPOSE) build

docker-pull: ## Pull latest Docker images
	@echo "$(YELLOW)Pulling latest images...$(NC)"
	cd docker && $(DOCKER_COMPOSE) pull

# Documentation
docs-serve: ## Serve documentation locally
	@echo "$(YELLOW)Serving documentation...$(NC)"
	cd docs && python -m http.server 8000

# Utility Commands
clean: ## Clean up temporary files
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".tox" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov coverage.xml .coverage cdk.out || true
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

check: lint test ## Run all checks (lint + test)
	@echo "$(GREEN)✓ All checks passed$(NC)"

pre-commit: format lint test ## Run pre-commit checks
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

# Configuration
show-config: ## Show current configuration
	@echo "$(YELLOW)Current configuration:$(NC)"
	@if [ -f "system.yaml" ]; then \
		$(PYTHON) -c "import yaml; print(yaml.dump(yaml.safe_load(open('system.yaml')), default_flow_style=False))"; \
	else \
		echo "$(RED)system.yaml not found$(NC)"; \
	fi

validate-config: ## Validate configuration
	@echo "$(YELLOW)Validating configuration...$(NC)"
	$(ACTIVATE) && $(PYTHON) -c "from n8n_aws_serverless.config import ConfigLoader; ConfigLoader().validate_config_file()"
	@echo "$(GREEN)✓ Configuration valid$(NC)"

# AWS Commands
aws-costs: ## Show AWS costs for n8n resources
	@echo "$(YELLOW)Fetching AWS costs...$(NC)"
	aws ce get-cost-and-usage \
		--time-period Start=$$(date -d "30 days ago" +%Y-%m-%d),End=$$(date +%Y-%m-%d) \
		--granularity MONTHLY \
		--metrics "UnblendedCost" \
		--filter file://cost-filter.json 2>/dev/null || echo "$(RED)Error fetching costs. Ensure cost-filter.json exists$(NC)"

aws-status: ## Show status of deployed resources
	@echo "$(YELLOW)Checking resource status...$(NC)"
	@ENV=$${ENVIRONMENT:-dev}; \
	aws cloudformation describe-stacks \
		--stack-name n8n-serverless-$$ENV-compute \
		--query 'Stacks[0].StackStatus' \
		--output text 2>/dev/null || echo "Stack not found"

# Combined Commands
all: install lint test ## Install dependencies and run all checks

dev: local-up ## Start local development environment

prod-check: ## Pre-production deployment checks
	@echo "$(YELLOW)Running production checks...$(NC)"
	$(MAKE) lint
	$(MAKE) test-cov
	$(MAKE) validate-config
	@echo "$(GREEN)✓ Ready for production deployment$(NC)"

# Version Information
version: ## Show version information
	@echo "n8n AWS Serverless"
	@echo "=================="
	@echo "Python: $$($(PYTHON) --version)"
	@echo "CDK: $$($(CDK) --version)"
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$($(DOCKER_COMPOSE) --version)"

.PHONY: install-cdk
install-cdk: ## Install AWS CDK
	npm install -g aws-cdk
	@echo "$(GREEN)✓ AWS CDK installed$(NC)"

.PHONY: bootstrap
bootstrap: ## Bootstrap CDK in AWS account
	@echo "$(YELLOW)Bootstrapping CDK...$(NC)"
	$(CDK) bootstrap
	@echo "$(GREEN)✓ CDK bootstrapped$(NC)"

# Quick Commands
.PHONY: up down restart
up: local-up ## Alias for local-up
down: local-down ## Alias for local-down
restart: down up ## Restart local environment