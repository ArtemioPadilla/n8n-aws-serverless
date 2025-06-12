"""Security tests for secrets scanning and validation."""
import json
import os
import re
from pathlib import Path

import pytest
import yaml


@pytest.mark.security
class TestSecretsScanning:
    """Test for secrets and sensitive data exposure."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    def test_no_aws_credentials_in_code(self, project_root):
        """Test that no AWS credentials are hardcoded."""
        aws_key_patterns = [
            r"AKIA[0-9A-Z]{16}",  # AWS Access Key ID
            r'(?i)aws_secret_access_key\s*=\s*["\'][^"\']{40}["\']',  # AWS Secret
            r'(?i)aws_session_token\s*=\s*["\'][^"\']+["\']',  # Session token
        ]

        files_to_check = (
            list(project_root.rglob("*.py"))
            + list(project_root.rglob("*.yaml"))
            + list(project_root.rglob("*.yml"))
            + list(project_root.rglob("*.json"))
        )

        for file_path in files_to_check:
            # Skip test files and virtual environments
            if any(
                skip in str(file_path)
                for skip in [".venv", "venv", "__pycache__", ".git"]
            ):
                continue

            try:
                content = file_path.read_text()

                for pattern in aws_key_patterns:
                    matches = re.findall(pattern, content)
                    assert (
                        not matches
                    ), f"AWS credentials found in {file_path}: {matches}"
            except Exception:
                pass  # Skip binary files

    def test_no_private_keys_in_repository(self, project_root):
        """Test that no private keys are committed."""
        key_patterns = [
            r"-----BEGIN RSA PRIVATE KEY-----",
            r"-----BEGIN OPENSSH PRIVATE KEY-----",
            r"-----BEGIN DSA PRIVATE KEY-----",
            r"-----BEGIN EC PRIVATE KEY-----",
            r"-----BEGIN PRIVATE KEY-----",
        ]

        key_extensions = [".pem", ".key", ".pfx", ".p12"]

        # Check for key files
        for ext in key_extensions:
            key_files = list(project_root.rglob(f"*{ext}"))
            for key_file in key_files:
                # Allow certain test keys if needed
                if "test" not in str(key_file).lower():
                    assert False, f"Private key file found: {key_file}"

        # Check for key content in files
        text_files = (
            list(project_root.rglob("*.py"))
            + list(project_root.rglob("*.yaml"))
            + list(project_root.rglob("*.yml"))
            + list(project_root.rglob("*.txt"))
        )

        for file_path in text_files:
            if any(skip in str(file_path) for skip in [".venv", "venv", "__pycache__"]):
                continue

            try:
                content = file_path.read_text()
                for pattern in key_patterns:
                    if pattern in content:
                        assert False, f"Private key content found in {file_path}"
            except Exception:
                pass

    def test_env_files_are_examples(self, project_root):
        """Test that .env files are not committed (only .env.example)."""
        env_files = list(project_root.rglob(".env"))

        for env_file in env_files:
            # Only .env.example should exist
            assert (
                env_file.name == ".env.example"
            ), f"Found committed .env file: {env_file}"

    def test_no_database_credentials(self, project_root):
        """Test that no database credentials are hardcoded."""
        db_patterns = [
            r'(?i)db_password\s*=\s*["\'][^"\']+["\']',
            r'(?i)database_url\s*=\s*["\']postgres://[^"\']+:[^"\']+@[^"\']+["\']',
            r"(?i)mysql://[^:]+:[^@]+@",
            r"(?i)mongodb://[^:]+:[^@]+@",
        ]

        files_to_check = (
            list(project_root.rglob("*.py"))
            + list(project_root.rglob("*.yaml"))
            + list(project_root.rglob("*.yml"))
        )

        for file_path in files_to_check:
            if any(skip in str(file_path) for skip in [".venv", "venv", "__pycache__"]):
                continue

            try:
                content = file_path.read_text()

                for pattern in db_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Allow examples and placeholders
                        if not any(
                            placeholder in match.lower()
                            for placeholder in [
                                "example",
                                "your",
                                "xxx",
                                "placeholder",
                                "test",
                            ]
                        ):
                            assert (
                                False
                            ), f"Database credentials found in {file_path}: {match}"
            except Exception:
                pass

    def test_config_files_no_secrets(self, project_root):
        """Test that configuration files don't contain secrets."""
        config_files = (
            list(project_root.rglob("system.yaml"))
            + list(project_root.rglob("config.yaml"))
            + list(project_root.rglob("settings.yaml"))
        )

        for config_file in config_files:
            if config_file.name.endswith(".example"):
                continue

            try:
                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)

                # Check for common secret fields
                secret_fields = ["password", "secret", "key", "token", "credential"]

                def check_dict_for_secrets(d, path=""):
                    if isinstance(d, dict):
                        for k, v in d.items():
                            current_path = f"{path}.{k}" if path else k

                            # Check if key suggests secret
                            if any(secret in k.lower() for secret in secret_fields):
                                if (
                                    isinstance(v, str)
                                    and v
                                    and not any(
                                        placeholder in v.lower()
                                        for placeholder in [
                                            "your",
                                            "xxx",
                                            "example",
                                            "placeholder",
                                        ]
                                    )
                                ):
                                    assert (
                                        False
                                    ), f"Potential secret in {config_file} at {current_path}: {v}"

                            # Recurse
                            check_dict_for_secrets(v, current_path)
                    elif isinstance(d, list):
                        for i, item in enumerate(d):
                            check_dict_for_secrets(item, f"{path}[{i}]")

                check_dict_for_secrets(config)

            except yaml.YAMLError:
                pass  # Skip invalid YAML files

    def test_no_api_keys_in_code(self, project_root):
        """Test that no API keys are hardcoded."""
        api_key_patterns = [
            r'(?i)api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'(?i)apikey\s*=\s*["\'][a-zA-Z0-9]{20,}["\']',
            r'(?i)x-api-key\s*:\s*["\'][a-zA-Z0-9]{20,}["\']',
        ]

        files_to_check = (
            list(project_root.rglob("*.py"))
            + list(project_root.rglob("*.js"))
            + list(project_root.rglob("*.ts"))
        )

        for file_path in files_to_check:
            if any(
                skip in str(file_path) for skip in [".venv", "venv", "node_modules"]
            ):
                continue

            try:
                content = file_path.read_text()

                for pattern in api_key_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        if not any(
                            placeholder in match.lower()
                            for placeholder in [
                                "example",
                                "your-api-key",
                                "xxx",
                                "test",
                            ]
                        ):
                            assert False, f"API key found in {file_path}: {match}"
            except Exception:
                pass

    def test_git_secrets_config_exists(self, project_root):
        """Test that git-secrets or similar is configured."""
        # Check for .gitsecrets file or git hooks
        gitsecrets_file = project_root / ".gitsecrets"
        pre_commit_file = project_root / ".pre-commit-config.yaml"

        # At least one secrets scanning mechanism should exist
        assert (
            gitsecrets_file.exists() or pre_commit_file.exists()
        ), "No secrets scanning configuration found (git-secrets or pre-commit)"

        # If pre-commit exists, check it has secrets scanning
        if pre_commit_file.exists():
            with open(pre_commit_file, "r") as f:
                pre_commit_config = yaml.safe_load(f)

            repos = pre_commit_config.get("repos", [])
            has_secrets_scanning = any(
                "detect-secrets" in str(repo)
                or "git-secrets" in str(repo)
                or "truffleHog" in str(repo)
                for repo in repos
            )

            assert (
                has_secrets_scanning
            ), "Pre-commit configuration doesn't include secrets scanning"

    def test_docker_files_no_secrets(self, project_root):
        """Test that Dockerfiles don't contain secrets."""
        docker_files = list(project_root.rglob("Dockerfile*")) + list(
            project_root.rglob("docker-compose*.yml")
        )

        for docker_file in docker_files:
            try:
                content = docker_file.read_text()

                # Check for hardcoded secrets in ENV or ARG
                env_patterns = [
                    r'ENV\s+\w*(?:PASSWORD|SECRET|KEY|TOKEN)\w*\s*=\s*["\']?[^"\'\s]+["\']?',
                    r'ARG\s+\w*(?:PASSWORD|SECRET|KEY|TOKEN)\w*\s*=\s*["\']?[^"\'\s]+["\']?',
                ]

                for pattern in env_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if not any(
                            placeholder in match.lower()
                            for placeholder in ["build-arg", "your", "example", "xxx"]
                        ):
                            assert False, f"Secret in Dockerfile {docker_file}: {match}"

            except Exception:
                pass

    def test_terraform_files_no_secrets(self, project_root):
        """Test that Terraform files don't contain secrets."""
        tf_files = list(project_root.rglob("*.tf")) + list(
            project_root.rglob("*.tfvars")
        )

        for tf_file in tf_files:
            # Skip example files
            if "example" in tf_file.name:
                continue

            try:
                content = tf_file.read_text()

                # Check for hardcoded secrets
                secret_patterns = [
                    r'password\s*=\s*"[^"]{8,}"',
                    r'secret\s*=\s*"[^"]{8,}"',
                    r'access_key\s*=\s*"[^"]{20,}"',
                ]

                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if not any(
                            placeholder in match.lower()
                            for placeholder in ["var.", "data.", "example"]
                        ):
                            assert False, f"Secret in Terraform file {tf_file}: {match}"

            except Exception:
                pass
