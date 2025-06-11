# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AWS CDK (Cloud Development Kit) Python project for deploying n8n workflow automation tool in a serverless architecture on AWS. The project aims to provide a cost-effective serverless deployment solution for n8n.

## Development Commands

### Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # MacOS/Linux
.venv\Scripts\activate.bat  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### CDK Commands
```bash
cdk ls        # List all stacks in the app
cdk synth     # Synthesize CloudFormation template
cdk deploy    # Deploy stack to AWS
cdk diff      # Compare deployed stack with current state
cdk destroy   # Remove stack from AWS
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_n8n_aws_serverless_stack.py

# Run with verbose output
pytest -v
```

## Project Architecture

### Core Structure
- **app.py**: CDK application entry point that instantiates the stack
- **n8n_aws_serverless/n8n_aws_serverless_stack.py**: Main stack definition where all AWS resources for n8n serverless deployment should be defined
- **cdk.json**: CDK configuration with security-focused feature flags and app settings

### Stack Implementation
The `N8NAwsServerlessStack` class in `n8n_aws_serverless_stack.py` is where all AWS infrastructure should be defined. Currently empty, it will need to include:
- Container/Lambda definitions for running n8n
- API Gateway or ALB for HTTP access
- Database resources (DynamoDB/RDS)
- S3 buckets for workflow storage
- IAM roles and policies
- Secrets management for n8n configuration

### Testing Approach
Tests use pytest with AWS CDK assertions library. Unit tests should verify:
- Stack synthesis without errors
- Presence of expected resources
- Correct resource configurations
- IAM policy validations

The test structure follows CDK best practices with separate unit test directories.