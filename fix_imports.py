import re

# List of files and their unused imports
fixes = {
    "n8n_deploy/stacks/access_stack.py": ["typing.List", "aws_cdk.CfnOutput", "aws_cdk.RemovalPolicy", "aws_cdk.aws_iam as iam"],
    "n8n_deploy/stacks/base_stack.py": ["typing.Any", "aws_cdk.Aws", "..config.models.EnvironmentConfig"],
    "n8n_deploy/stacks/compute_stack.py": ["aws_cdk.CfnOutput"],
    "n8n_deploy/stacks/database_stack.py": ["typing.Optional", "aws_cdk.CfnOutput", "aws_cdk.RemovalPolicy"],
    "n8n_deploy/stacks/monitoring_stack.py": ["typing.List", "aws_cdk.CfnOutput"],
    "n8n_deploy/stacks/network_stack.py": ["typing.Optional", "aws_cdk.CfnOutput"],
    "n8n_deploy/stacks/storage_stack.py": ["typing.List", "typing.Optional", "aws_cdk.RemovalPolicy"],
    "tests/integration/test_cloudflare_integration.py": ["aws_cdk.assertions.Match", "aws_cdk.assertions.Template"],
    "tests/integration/test_config_validation.py": ["tempfile", "pathlib.Path"],
    "tests/integration/test_local_deployment.py": ["unittest.mock.Mock", "unittest.mock.patch"],
    "tests/integration/test_stack_deployment.py": ["os"],
    "tests/unit/test_compute_stack.py": ["aws_cdk.Duration", "aws_cdk.aws_autoscaling as autoscaling", "aws_cdk.aws_ecs as ecs", "n8n_deploy.config.models.BackupConfig"],
    "tests/unit/test_config_loader.py": ["tempfile", "pathlib.Path"],
    "tests/unit/test_database_stack.py": ["unittest.mock.MagicMock", "unittest.mock.patch", "aws_cdk.Duration", "aws_cdk.aws_ec2 as ec2", "aws_cdk.aws_rds as rds"],
    "tests/unit/test_monitoring_stack.py": ["unittest.mock.MagicMock", "unittest.mock.patch"],
}

for file_path, imports in fixes.items():
    with open(file_path, 'r') as f:
        content = f.read()
    
    for imp in imports:
        # Handle different import patterns
        if " as " in imp:
            # Handle 'from x import y as z'
            pattern = f"from .* import {re.escape(imp)}\n"
            content = re.sub(pattern, "", content)
            # Handle 'import x as y'
            pattern = f"import {re.escape(imp)}\n"
            content = re.sub(pattern, "", content)
        elif imp.startswith(".."):
            # Handle relative imports
            pattern = f"from {re.escape(imp)} import .*\n"
            content = re.sub(pattern, "", content)
        else:
            # Handle regular imports
            if "." in imp:
                # Module.Class pattern
                parts = imp.rsplit(".", 1)
                if len(parts) == 2:
                    module, cls = parts
                    # Try both patterns
                    pattern1 = f"from {re.escape(module)} import .*{re.escape(cls)}.*\n"
                    pattern2 = f"import {re.escape(imp)}\n"
                    content = re.sub(pattern1, lambda m: m.group(0) if cls not in m.group(0) else "", content)
                    content = re.sub(pattern2, "", content)
            else:
                # Simple import
                pattern = f"from .* import .*{re.escape(imp)}.*\n"
                content = re.sub(pattern, lambda m: m.group(0) if imp not in m.group(0) else "", content)
                pattern = f"import {re.escape(imp)}\n"
                content = re.sub(pattern, "", content)
    
    # Clean up multiple blank lines
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    with open(file_path, 'w') as f:
        f.write(content)

print("Fixed imports in all files")
