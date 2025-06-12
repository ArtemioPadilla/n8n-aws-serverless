"""Configuration loader for system.yaml."""
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import ValidationError

from .models import EnvironmentConfig, N8nConfig


class ConfigLoader:
    """Load and validate configuration from system.yaml."""

    def __init__(self, config_file: str = "system.yaml"):
        """Initialize config loader.

        Args:
            config_file: Path to configuration file (default: system.yaml)
        """
        self.config_file = Path(config_file)
        self._config: Optional[N8nConfig] = None
        self._raw_config: Optional[Dict[str, Any]] = None

    def load_config(
        self,
        environment: str,
        stack_type: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> N8nConfig:
        """Load configuration for a specific environment.

        Args:
            environment: Environment name (dev, staging, production)
            stack_type: Optional stack type (minimal, standard, enterprise)
            overrides: Optional configuration overrides

        Returns:
            Validated N8nConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If environment not found or validation fails
        """
        # Load raw configuration
        if not self._raw_config:
            self._load_raw_config()

        # Validate base configuration
        if not self._config:
            self._validate_config()

        # Get environment configuration
        env_config = self._config.get_environment(environment)
        if not env_config:
            raise ValueError(f"Environment '{environment}' not found in configuration")

        # Apply stack type overrides if specified
        if stack_type:
            env_config = self._apply_stack_type(env_config, stack_type)

        # Merge with defaults
        env_config = self._config.merge_with_defaults(env_config)

        # Apply runtime overrides
        if overrides:
            env_config = self._apply_overrides(env_config, overrides)

        # Create a new config with only the selected environment
        selected_config = N8nConfig(
            global_config=self._config.global_config,
            defaults=self._config.defaults,
            environments={environment: env_config},
            stacks=self._config.stacks,
            shared_resources=self._config.shared_resources,
        )

        return selected_config

    def _load_raw_config(self) -> None:
        """Load raw YAML configuration."""
        if not self.config_file.exists():
            # Try to find config file in parent directories
            current = Path.cwd()
            while current != current.parent:
                potential_config = current / self.config_file.name
                if potential_config.exists():
                    self.config_file = potential_config
                    break
                current = current.parent
            else:
                raise FileNotFoundError(
                    f"Configuration file '{self.config_file}' not found"
                )

        with open(self.config_file, "r") as f:
            self._raw_config = yaml.safe_load(f)

    def _validate_config(self) -> None:
        """Validate configuration against Pydantic models."""
        try:
            self._config = N8nConfig(**self._raw_config)
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")

    def _apply_stack_type(
        self, env_config: EnvironmentConfig, stack_type: str
    ) -> EnvironmentConfig:
        """Apply stack type configuration to environment.

        Args:
            env_config: Base environment configuration
            stack_type: Stack type to apply

        Returns:
            Modified environment configuration
        """
        stack_config = self._config.get_stack_config(stack_type)
        if not stack_config:
            raise ValueError(f"Stack type '{stack_type}' not found in configuration")

        # Create a copy to avoid modifying original
        modified_config = env_config.copy(deep=True)

        # Apply stack settings
        if stack_config.settings:
            # Update components list if specified
            if "components" in stack_config.settings:
                # This would be used by the CDK app to determine which stacks to create
                modified_config.settings.features = (
                    modified_config.settings.features or {}
                )
                modified_config.settings.features["components"] = stack_config.settings[
                    "components"
                ]

            # Apply other settings
            for key, value in stack_config.settings.items():
                if key != "components" and hasattr(modified_config.settings, key):
                    setattr(modified_config.settings, key, value)

        return modified_config

    def _apply_overrides(
        self, env_config: EnvironmentConfig, overrides: Dict[str, Any]
    ) -> EnvironmentConfig:
        """Apply runtime overrides to configuration.

        Args:
            env_config: Base environment configuration
            overrides: Dictionary of overrides

        Returns:
            Modified environment configuration
        """
        # Create a copy to avoid modifying original
        modified_config = env_config.copy(deep=True)

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(modified_config.settings, key):
                setattr(modified_config.settings, key, value)

        return modified_config

    def get_available_environments(self) -> list[str]:
        """Get list of available environments."""
        if not self._config:
            self._load_raw_config()
            self._validate_config()

        return list(self._config.environments.keys())

    def get_available_stack_types(self) -> list[str]:
        """Get list of available stack types."""
        if not self._config:
            self._load_raw_config()
            self._validate_config()

        return list(self._config.stacks.keys()) if self._config.stacks else []

    def validate_config_file(self) -> bool:
        """Validate the configuration file without loading specific environment.

        Returns:
            True if valid, raises exception otherwise
        """
        try:
            self._load_raw_config()
            self._validate_config()
            return True
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}")

    @staticmethod
    def generate_example_config(output_path: str = "system.yaml.example") -> None:
        """Generate an example configuration file.

        Args:
            output_path: Path to write example configuration
        """
        example_config = {
            "global": {
                "project_name": "n8n-serverless",
                "organization": "mycompany",
                "tags": {
                    "Project": "n8n",
                    "ManagedBy": "CDK",
                    "Environment": "{{ environment }}",
                },
            },
            "defaults": {
                "fargate": {"cpu": 256, "memory": 512, "spot_percentage": 80},
                "monitoring": {
                    "log_retention_days": 30,
                    "enable_container_insights": True,
                },
            },
            "environments": {
                "dev": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {
                        "fargate": {"cpu": 256, "memory": 512},
                        "scaling": {"min_tasks": 1, "max_tasks": 1},
                        "networking": {
                            "use_existing_vpc": False,
                            "vpc_cidr": "10.0.0.0/16",
                        },
                        "access": {
                            "cloudfront_enabled": False,
                            "api_gateway_throttle": 100,
                        },
                        "auth": {"basic_auth_enabled": True, "oauth_enabled": False},
                    },
                },
                "production": {
                    "account": "123456789013",
                    "region": "us-west-2",
                    "settings": {
                        "fargate": {"cpu": 1024, "memory": 2048, "spot_percentage": 50},
                        "scaling": {
                            "min_tasks": 2,
                            "max_tasks": 10,
                            "target_cpu_utilization": 70,
                        },
                        "networking": {
                            "use_existing_vpc": True,
                            "vpc_id": "vpc-prod12345",
                            "subnet_ids": ["subnet-1", "subnet-2"],
                        },
                        "access": {
                            "domain_name": "n8n.example.com",
                            "cloudfront_enabled": True,
                            "waf_enabled": True,
                            "api_gateway_throttle": 10000,
                        },
                        "database": {"type": "postgres", "use_existing": False},
                        "auth": {
                            "basic_auth_enabled": False,
                            "oauth_enabled": True,
                            "oauth_provider": "okta",
                        },
                    },
                },
            },
            "stacks": {
                "minimal": {
                    "description": "Minimal setup for personal use",
                    "components": ["fargate", "efs", "api_gateway"],
                    "settings": {"fargate": {"cpu": 256, "memory": 512}},
                },
                "standard": {
                    "description": "Standard setup with monitoring",
                    "components": [
                        "fargate",
                        "efs",
                        "api_gateway",
                        "cloudfront",
                        "monitoring",
                    ],
                    "inherit_from": "defaults",
                },
            },
        }

        with open(output_path, "w") as f:
            yaml.dump(example_config, f, default_flow_style=False, sort_keys=False)


# Helper function for CLI usage
def get_config(environment: str, stack_type: Optional[str] = None) -> N8nConfig:
    """Helper function to quickly load configuration.

    Args:
        environment: Environment name
        stack_type: Optional stack type

    Returns:
        Loaded and validated configuration
    """
    loader = ConfigLoader()
    return loader.load_config(environment, stack_type)
