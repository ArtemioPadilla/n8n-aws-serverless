import re

# List of files and their fixes
test_fixes = {
    "tests/performance/test_load_benchmarks.py": {
        "remove_imports": ["concurrent.futures.ThreadPoolExecutor", "concurrent.futures.as_completed"],
        "unused_vars": [("e", "Exception")]
    },
    "tests/security/test_iam_policies.py": {
        "remove_imports": ["json", "unittest.mock.Mock", "aws_cdk.assertions.Match"]
    },
    "tests/security/test_secrets_scanning.py": {
        "remove_imports": ["json", "os"]
    },
    "tests/unit/conftest.py": {
        "remove_imports": ["unittest.mock.patch", "aws_cdk.Stack"]
    },
    "tests/unit/test_access_stack.py": {
        "remove_imports": ["unittest.mock.MagicMock", "unittest.mock.PropertyMock", "aws_cdk.Duration", "aws_cdk.aws_apigatewayv2 as apigatewayv2", "aws_cdk.aws_cloudfront as cloudfront"]
    },
    "tests/unit/test_base_stack.py": {
        "remove_imports": ["pytest", "aws_cdk.App", "aws_cdk.Stack", "aws_cdk.Tags"]
    },
    "tests/unit/test_cloudflare_config.py": {
        "remove_imports": ["unittest.mock.MagicMock", "unittest.mock.Mock", "unittest.mock.patch", "n8n_deploy.config.models.EnvironmentConfig", "n8n_deploy.config.models.EnvironmentSettings"]
    },
    "tests/unit/test_compute_stack.py": {
        "remove_imports": ["unittest.mock.MagicMock", "unittest.mock.PropertyMock", "n8n_deploy.config.models.BackupConfig"]
    }
}

for file_path, fixes in test_fixes.items():
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Remove unused imports
        if "remove_imports" in fixes:
            for imp in fixes["remove_imports"]:
                # Handle different import patterns
                if " as " in imp:
                    pattern = f"import {re.escape(imp)}\n"
                    content = re.sub(pattern, "", content)
                    pattern = f"from .* import {re.escape(imp)}\n"
                    content = re.sub(pattern, "", content)
                else:
                    # Try various patterns
                    patterns = [
                        f"import {re.escape(imp)}\n",
                        f"from {re.escape(imp)} import .*\n",
                        f"from .* import .*{re.escape(imp)}.*\n"
                    ]
                    for pattern in patterns:
                        if imp in content:
                            # Be more careful about what we remove
                            lines = content.split('\n')
                            new_lines = []
                            for line in lines:
                                if f"import {imp}" in line or f"from {imp}" in line:
                                    # Check if it's the exact import we want to remove
                                    if imp == line.split()[-1] or f"import {imp}" in line:
                                        continue  # Skip this line
                                new_lines.append(line)
                            content = '\n'.join(new_lines)
        
        # Clean up multiple blank lines
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        with open(file_path, 'w') as f:
            f.write(content)
            
        print(f"Fixed {file_path}")
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")

print("Done fixing test imports")
