"""Integration tests for configuration validation and loading."""
import os

import pytest
import yaml

from n8n_deploy.config import ConfigLoader
from n8n_deploy.config.models import N8nConfig


@pytest.mark.integration
class TestConfigValidation:
    """Integration tests for configuration validation."""

    @pytest.fixture
    def valid_config(self):
        """Create a valid configuration dictionary."""
        return {
            "global": {
                "project_name": "test-n8n",
                "organization": "test-org",
                "tags": {"Project": "n8n", "ManagedBy": "CDK"},
            },
            "defaults": {
                "fargate": {
                    "cpu": 256,
                    "memory": 512,
                    "spot_percentage": 80,
                    "n8n_version": "1.94.1",
                },
                "efs": {"lifecycle_days": 30, "backup_retention_days": 7},
                "monitoring": {
                    "log_retention_days": 30,
                    "alarm_email": "ops@example.com",
                    "enable_container_insights": True,
                },
                "backup": {
                    "enabled": True,
                    "retention_days": 7,
                    "cross_region_backup": False,
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
                    "account": "123456789012",
                    "region": "us-west-2",
                    "settings": {
                        "fargate": {"cpu": 1024, "memory": 2048, "spot_percentage": 50},
                        "scaling": {
                            "min_tasks": 2,
                            "max_tasks": 10,
                            "target_cpu_utilization": 70,
                        },
                        "networking": {
                            "use_existing_vpc": False,
                            "vpc_cidr": "10.1.0.0/16",
                        },
                        "access": {
                            "domain_name": "n8n.example.com",
                            "cloudfront_enabled": True,
                            "waf_enabled": True,
                            "api_gateway_throttle": 10000,
                        },
                        "database": {
                            "type": "postgres",
                            "use_existing": False,
                            "instance_class": "db.t4g.micro",
                            "multi_az": True,
                            "backup_retention_days": 30,
                        },
                        "auth": {
                            "basic_auth_enabled": False,
                            "oauth_enabled": True,
                            "oauth_provider": "okta",
                            "mfa_required": True,
                        },
                        "monitoring": {
                            "log_retention_days": 90,
                            "alarm_email": "prod-ops@example.com",
                            "enable_container_insights": True,
                            "enable_xray_tracing": True,
                        },
                        "backup": {
                            "enabled": True,
                            "retention_days": 30,
                            "cross_region_backup": True,
                            "backup_regions": ["us-east-1"],
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
                "enterprise": {
                    "description": "Full enterprise setup",
                    "components": [
                        "fargate",
                        "rds_postgres",
                        "api_gateway",
                        "cloudfront",
                        "waf",
                        "monitoring",
                        "backup",
                    ],
                    "settings": {"fargate": {"cpu": 2048, "memory": 4096}},
                },
            },
        }

    def test_load_valid_config_file(self, valid_config, tmp_path):
        """Test loading a valid configuration file."""
        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        loader = ConfigLoader(str(config_file))
        config = loader.load_config("dev")

        assert isinstance(config, N8nConfig)
        assert config.global_config.project_name == "test-n8n"
        assert len(config.environments) == 1
        assert "dev" in config.environments

    def test_environment_inheritance(self, valid_config, tmp_path):
        """Test that environment settings inherit from defaults."""
        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        loader = ConfigLoader(str(config_file))

        # Test dev environment
        dev_config = loader.load_config("dev")
        dev_fargate = dev_config.environments["dev"].settings.fargate
        assert dev_fargate.n8n_version == "1.94.1"

        # Test production environment overrides
        prod_config = loader.load_config("production")
        prod_fargate = prod_config.environments["production"].settings.fargate
        assert prod_fargate.cpu == 1024
        assert prod_fargate.memory == 2048

    def test_invalid_cpu_memory_combination(self, valid_config, tmp_path):
        """Test validation of invalid Fargate CPU/memory combinations."""
        # Set invalid memory for CPU 256
        valid_config["environments"]["dev"]["settings"]["fargate"]["memory"] = 4096

        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        loader = ConfigLoader(str(config_file))
        with pytest.raises(ValueError, match="Invalid CPU/memory combination"):
            loader.load_config("dev")

    def test_missing_required_fields(self, tmp_path):
        """Test validation with missing required fields."""
        invalid_config = {
            "global": {
                # Missing project_name
                "organization": "test-org"
            },
            "environments": {
                "dev": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {},
                }
            },
        }

        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(invalid_config, f)

        loader = ConfigLoader(str(config_file))
        with pytest.raises(ValueError):
            loader.load_config("dev")

    def test_oauth_validation(self, valid_config, tmp_path):
        """Test OAuth configuration validation."""
        # Enable OAuth without provider
        valid_config["environments"]["dev"]["settings"]["auth"]["oauth_enabled"] = True
        valid_config["environments"]["dev"]["settings"]["auth"]["oauth_provider"] = None

        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        loader = ConfigLoader(str(config_file))
        with pytest.raises(ValueError, match="oauth_provider required"):
            loader.load_config("dev")

    def test_scaling_validation(self, valid_config, tmp_path):
        """Test auto-scaling configuration validation."""
        # Set max_tasks less than min_tasks
        valid_config["environments"]["dev"]["settings"]["scaling"]["min_tasks"] = 5
        valid_config["environments"]["dev"]["settings"]["scaling"]["max_tasks"] = 3

        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        loader = ConfigLoader(str(config_file))
        with pytest.raises(ValueError, match="max_tasks.*must be.*min_tasks"):
            loader.load_config("dev")

    def test_environment_variables_override(self, valid_config, tmp_path):
        """Test that environment variables can override configuration."""
        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        # Set environment variable to override
        os.environ["N8N_ENVIRONMENT"] = "production"

        try:
            loader = ConfigLoader(str(config_file))
            config = loader.load_config("production")

            assert isinstance(config, N8nConfig)
        finally:
            # Clean up
            del os.environ["N8N_ENVIRONMENT"]

    def test_stack_type_validation(self, valid_config, tmp_path):
        """Test stack type configuration validation."""
        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        loader = ConfigLoader(str(config_file))
        config = loader.load_config("dev")

        assert "minimal" in config.stacks
        assert "enterprise" in config.stacks
        assert config.stacks["minimal"].description == "Minimal setup for personal use"
        assert "fargate" in config.stacks["minimal"].components

    def test_cross_region_backup_validation(self, valid_config, tmp_path):
        """Test cross-region backup configuration validation."""
        # Enable cross-region backup without regions
        valid_config["environments"]["production"]["settings"]["backup"][
            "backup_regions"
        ] = []

        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        loader = ConfigLoader(str(config_file))
        config = loader.load_config("production")

        # Should still be valid but with empty regions
        prod_backup = config.environments["production"].settings.backup
        assert prod_backup.cross_region_backup is True
        assert len(prod_backup.backup_regions) == 0

    def test_multi_file_configuration(self, tmp_path):
        """Test loading configuration from multiple files."""
        # Create base config
        base_config = {
            "global": {"project_name": "test-n8n", "organization": "test-org"},
            "defaults": {
                "fargate": {"cpu": 256, "memory": 512, "n8n_version": "1.94.1"}
            },
        }

        # Create environment-specific config
        env_config = {
            "environments": {
                "dev": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {"fargate": {"cpu": 512, "memory": 1024}},
                }
            }
        }

        base_file = tmp_path / "base.yaml"
        env_file = tmp_path / "environments.yaml"

        with open(base_file, "w") as f:
            yaml.dump(base_config, f)

        with open(env_file, "w") as f:
            yaml.dump(env_config, f)

        # Merge configs
        merged_config = {**base_config, **env_config}
        merged_file = tmp_path / "system.yaml"

        with open(merged_file, "w") as f:
            yaml.dump(merged_config, f)

        loader = ConfigLoader(str(merged_file))
        config = loader.load_config("dev")

        assert config.global_config.project_name == "test-n8n"
        assert config.environments["dev"].settings.fargate.cpu == 512

    def test_config_file_not_found(self):
        """Test handling of missing configuration file."""
        loader = ConfigLoader("/non/existent/path/nonexistent-config.yaml")
        with pytest.raises(FileNotFoundError):
            loader.load_config("dev")

    def test_invalid_yaml_syntax(self, tmp_path):
        """Test handling of invalid YAML syntax."""
        config_file = tmp_path / "system.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: syntax: ][")

        loader = ConfigLoader(str(config_file))
        with pytest.raises(yaml.YAMLError):
            loader.load_config("dev")
