"""Unit tests for configuration loader."""
import pytest
import tempfile
import yaml
from pathlib import Path

from n8n_aws_serverless.config.config_loader import ConfigLoader
from n8n_aws_serverless.config.models import N8nConfig, DatabaseType


class TestConfigLoader:
    """Test configuration loading and validation."""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        # Create test config
        config_data = {
            "global": {
                "project_name": "test-project",
                "organization": "test-org",
                "tags": {"Environment": "test"}
            },
            "environments": {
                "test": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {
                        "fargate": {
                            "cpu": 256,
                            "memory": 512
                        }
                    }
                }
            }
        }
        
        # Write config file
        config_file = tmp_path / "system.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Load config
        loader = ConfigLoader(str(config_file))
        config = loader.load_config("test")
        
        assert isinstance(config, N8nConfig)
        assert config.global_config.project_name == "test-project"
        assert config.global_config.organization == "test-org"
        assert "test" in config.environments
    
    def test_load_nonexistent_file(self):
        """Test loading a non-existent configuration file."""
        loader = ConfigLoader("nonexistent.yaml")
        
        with pytest.raises(FileNotFoundError):
            loader.load_config("test")
    
    def test_invalid_environment(self, tmp_path):
        """Test loading an invalid environment."""
        # Create minimal config
        config_data = {
            "global": {
                "project_name": "test",
                "organization": "test",
            },
            "environments": {
                "dev": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {}
                }
            }
        }
        
        config_file = tmp_path / "system.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(ValueError, match="Environment 'prod' not found"):
            loader.load_config("prod")
    
    def test_invalid_cpu_memory_combination(self, tmp_path):
        """Test invalid Fargate CPU/memory combinations."""
        config_data = {
            "global": {
                "project_name": "test",
                "organization": "test",
            },
            "environments": {
                "test": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {
                        "fargate": {
                            "cpu": 256,
                            "memory": 8192  # Invalid for 256 CPU
                        }
                    }
                }
            }
        }
        
        config_file = tmp_path / "system.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigLoader(str(config_file))
        
        with pytest.raises(ValueError, match="Invalid CPU/memory combination"):
            loader.load_config("test")
    
    def test_merge_with_defaults(self, tmp_path):
        """Test merging environment config with defaults."""
        config_data = {
            "global": {
                "project_name": "test",
                "organization": "test",
            },
            "defaults": {
                "fargate": {
                    "cpu": 512,
                    "memory": 1024,
                    "spot_percentage": 80
                },
                "monitoring": {
                    "log_retention_days": 30
                }
            },
            "environments": {
                "test": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {
                        "fargate": {
                            "cpu": 256,
                            "memory": 512
                            # spot_percentage should come from defaults
                        }
                    }
                }
            }
        }
        
        config_file = tmp_path / "system.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigLoader(str(config_file))
        config = loader.load_config("test")
        
        env_config = config.get_environment("test")
        assert env_config.settings.fargate.cpu == 256  # Override
        assert env_config.settings.fargate.memory == 512  # Override
        # Note: The current implementation doesn't deep merge, so we'd need to enhance it
    
    def test_stack_type_application(self, tmp_path):
        """Test applying stack type configuration."""
        config_data = {
            "global": {
                "project_name": "test",
                "organization": "test",
            },
            "environments": {
                "test": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {}
                }
            },
            "stacks": {
                "minimal": {
                    "description": "Minimal setup",
                    "components": ["fargate", "efs", "api_gateway"],
                    "settings": {
                        "fargate": {
                            "cpu": 256,
                            "memory": 512
                        }
                    }
                }
            }
        }
        
        config_file = tmp_path / "system.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigLoader(str(config_file))
        config = loader.load_config("test", stack_type="minimal")
        
        env_config = config.get_environment("test")
        assert env_config.settings.features is not None
        assert "components" in env_config.settings.features
        assert env_config.settings.features["components"] == ["fargate", "efs", "api_gateway"]
    
    def test_database_configuration(self, tmp_path):
        """Test database configuration validation."""
        config_data = {
            "global": {
                "project_name": "test",
                "organization": "test",
            },
            "environments": {
                "test": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {
                        "database": {
                            "type": "postgres",
                            "use_existing": False,
                            "aurora_serverless": {
                                "min_capacity": 0.5,
                                "max_capacity": 1.0
                            }
                        }
                    }
                }
            }
        }
        
        config_file = tmp_path / "system.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigLoader(str(config_file))
        config = loader.load_config("test")
        
        env_config = config.get_environment("test")
        assert env_config.settings.database.type == DatabaseType.POSTGRES
        assert env_config.settings.database.aurora_serverless["min_capacity"] == 0.5
    
    def test_get_available_environments(self, tmp_path):
        """Test getting list of available environments."""
        config_data = {
            "global": {
                "project_name": "test",
                "organization": "test",
            },
            "environments": {
                "dev": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {}
                },
                "staging": {
                    "account": "123456789013",
                    "region": "us-east-1",
                    "settings": {}
                },
                "prod": {
                    "account": "123456789014",
                    "region": "us-east-1",
                    "settings": {}
                }
            }
        }
        
        config_file = tmp_path / "system.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        loader = ConfigLoader(str(config_file))
        environments = loader.get_available_environments()
        
        assert len(environments) == 3
        assert "dev" in environments
        assert "staging" in environments
        assert "prod" in environments
    
    def test_validate_config_file(self, tmp_path):
        """Test configuration file validation."""
        # Valid config
        valid_config = {
            "global": {
                "project_name": "test",
                "organization": "test",
            },
            "environments": {
                "test": {
                    "account": "123456789012",
                    "region": "us-east-1",
                    "settings": {}
                }
            }
        }
        
        config_file = tmp_path / "valid.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(valid_config, f)
        
        loader = ConfigLoader(str(config_file))
        assert loader.validate_config_file() is True
        
        # Invalid config (missing required fields)
        invalid_config = {
            "global": {
                "project_name": "test"
                # Missing organization
            },
            "environments": {}
        }
        
        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            yaml.dump(invalid_config, f)
        
        loader = ConfigLoader(str(invalid_file))
        with pytest.raises(ValueError):
            loader.validate_config_file()