"""Integration tests for stack deployment and dependencies."""
import os
from unittest.mock import Mock, patch

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Template

from n8n_deploy.config import ConfigLoader
from n8n_deploy.stacks.access_stack import AccessStack
from n8n_deploy.stacks.compute_stack import ComputeStack
from n8n_deploy.stacks.database_stack import DatabaseStack
from n8n_deploy.stacks.monitoring_stack import MonitoringStack
from n8n_deploy.stacks.network_stack import NetworkStack
from n8n_deploy.stacks.storage_stack import StorageStack


@pytest.mark.integration
class TestStackDeployment:
    """Integration tests for full stack deployment."""

    @pytest.fixture
    def config_loader(self):
        """Create config loader with test configuration."""
        # Use a test configuration file or mock
        with patch.object(ConfigLoader, "_load_config_file") as mock_load:
            mock_load.return_value = {
                "global": {"project_name": "test-n8n", "organization": "test-org"},
                "defaults": {
                    "fargate": {
                        "cpu": 256,
                        "memory": 512,
                        "spot_percentage": 80,
                        "n8n_version": "1.94.1",
                    },
                    "efs": {"lifecycle_days": 30},
                    "monitoring": {"log_retention_days": 30},
                },
                "environments": {
                    "test": {
                        "account": "123456789012",
                        "region": "us-east-1",
                        "settings": {
                            "fargate": {"cpu": 256, "memory": 512},
                            "scaling": {"min_tasks": 1, "max_tasks": 3},
                            "networking": {
                                "use_existing_vpc": False,
                                "vpc_cidr": "10.0.0.0/16",
                            },
                            "access": {
                                "cloudfront_enabled": True,
                                "api_gateway_throttle": 100,
                            },
                            "monitoring": {
                                "alarm_email": "test@example.com",
                                "enable_container_insights": True,
                            },
                        },
                    }
                },
            }
            loader = ConfigLoader()
            return loader

    def test_minimal_stack_deployment(self, config_loader):
        """Test deployment of minimal stack configuration."""
        app = App()
        environment = "test"
        config = config_loader.get_config()
        env = Environment(
            account=config.environments[environment].account,
            region=config.environments[environment].region,
        )

        # Deploy network stack
        network_stack = NetworkStack(
            app,
            f"{config.global_config.project_name}-{environment}-network",
            config=config,
            environment=environment,
            env=env,
        )

        # Deploy storage stack
        storage_stack = StorageStack(
            app,
            f"{config.global_config.project_name}-{environment}-storage",
            config=config,
            environment=environment,
            network_stack=network_stack,
            env=env,
        )

        # Deploy compute stack
        compute_stack = ComputeStack(
            app,
            f"{config.global_config.project_name}-{environment}-compute",
            config=config,
            environment=environment,
            network_stack=network_stack,
            storage_stack=storage_stack,
            env=env,
        )

        # Verify stack dependencies
        assert compute_stack.dependencies
        assert network_stack in compute_stack.dependencies
        assert storage_stack in compute_stack.dependencies

        # Synthesize and verify templates
        network_template = Template.from_stack(network_stack)
        storage_template = Template.from_stack(storage_stack)
        compute_template = Template.from_stack(compute_stack)

        # Verify resources are created
        network_template.resource_count_is("AWS::EC2::VPC", 1)
        storage_template.resource_count_is("AWS::EFS::FileSystem", 1)
        compute_template.resource_count_is("AWS::ECS::Cluster", 1)

    def test_full_stack_deployment(self, config_loader):
        """Test deployment of all stacks with dependencies."""
        app = App()
        environment = "test"
        config = config_loader.get_config()

        # Add database configuration
        config.environments[environment].settings.database = {
            "type": "postgres",
            "use_existing": False,
            "instance_class": "db.t4g.micro",
        }

        env = Environment(
            account=config.environments[environment].account,
            region=config.environments[environment].region,
        )

        # Deploy all stacks in order
        network_stack = NetworkStack(
            app, f"test-network", config=config, environment=environment, env=env
        )

        storage_stack = StorageStack(
            app,
            f"test-storage",
            config=config,
            environment=environment,
            network_stack=network_stack,
            env=env,
        )

        database_stack = DatabaseStack(
            app,
            f"test-database",
            config=config,
            environment=environment,
            network_stack=network_stack,
            env=env,
        )

        compute_stack = ComputeStack(
            app,
            f"test-compute",
            config=config,
            environment=environment,
            network_stack=network_stack,
            storage_stack=storage_stack,
            database_endpoint=database_stack.endpoint
            if hasattr(database_stack, "endpoint")
            else None,
            database_secret=database_stack.secret
            if hasattr(database_stack, "secret")
            else None,
            env=env,
        )

        access_stack = AccessStack(
            app,
            f"test-access",
            config=config,
            environment=environment,
            compute_stack=compute_stack,
            env=env,
        )

        monitoring_stack = MonitoringStack(
            app,
            f"test-monitoring",
            config=config,
            environment=environment,
            compute_stack=compute_stack,
            storage_stack=storage_stack,
            database_stack=database_stack,
            env=env,
        )

        # Verify all stacks are created
        assert network_stack
        assert storage_stack
        assert database_stack
        assert compute_stack
        assert access_stack
        assert monitoring_stack

        # Verify cross-stack references
        assert hasattr(compute_stack, "network_stack")
        assert hasattr(compute_stack, "storage_stack")
        assert hasattr(access_stack, "compute_stack")
        assert hasattr(monitoring_stack, "compute_stack")

    def test_stack_outputs_cross_references(self, config_loader):
        """Test that stack outputs are properly referenced across stacks."""
        app = App()
        environment = "test"
        config = config_loader.get_config()
        env = Environment(
            account=config.environments[environment].account,
            region=config.environments[environment].region,
        )

        # Deploy network and storage stacks
        network_stack = NetworkStack(
            app, f"test-network", config=config, environment=environment, env=env
        )

        storage_stack = StorageStack(
            app,
            f"test-storage",
            config=config,
            environment=environment,
            network_stack=network_stack,
            env=env,
        )

        # Get templates
        network_template = Template.from_stack(network_stack)
        storage_template = Template.from_stack(storage_stack)

        # Verify network stack outputs
        network_outputs = network_template.find_outputs("*")
        assert "VpcId" in str(network_outputs)
        assert "PrivateSubnetIds" in str(network_outputs)

        # Verify storage stack uses network resources
        storage_resources = storage_template.find_resources("AWS::EFS::FileSystem")
        assert len(storage_resources) > 0

    def test_environment_specific_configuration(self, config_loader):
        """Test that environment-specific settings are applied correctly."""
        app = App()
        config = config_loader.get_config()

        # Add production environment configuration
        config.environments["production"] = config.environments["test"].copy()
        config.environments["production"].settings.fargate.cpu = 1024
        config.environments["production"].settings.fargate.memory = 2048
        config.environments["production"].settings.scaling.min_tasks = 2
        config.environments["production"].settings.scaling.max_tasks = 10

        # Deploy stacks for different environments
        environments = ["test", "production"]

        for environment in environments:
            env = Environment(
                account=config.environments[environment].account,
                region=config.environments[environment].region,
            )

            network_stack = NetworkStack(
                app,
                f"{environment}-network",
                config=config,
                environment=environment,
                env=env,
            )

            storage_stack = StorageStack(
                app,
                f"{environment}-storage",
                config=config,
                environment=environment,
                network_stack=network_stack,
                env=env,
            )

            compute_stack = ComputeStack(
                app,
                f"{environment}-compute",
                config=config,
                environment=environment,
                network_stack=network_stack,
                storage_stack=storage_stack,
                env=env,
            )

            # Verify environment-specific settings
            if environment == "production":
                assert compute_stack.env_config.settings.fargate.cpu == 1024
                assert compute_stack.env_config.settings.fargate.memory == 2048
                assert compute_stack.is_production() is True
            else:
                assert compute_stack.env_config.settings.fargate.cpu == 256
                assert compute_stack.env_config.settings.fargate.memory == 512
                assert compute_stack.is_production() is False

    def test_existing_vpc_integration(self, config_loader):
        """Test integration with existing VPC."""
        app = App()
        environment = "test"
        config = config_loader.get_config()

        # Configure to use existing VPC
        config.environments[environment].settings.networking.use_existing_vpc = True
        config.environments[environment].settings.networking.vpc_id = "vpc-12345678"
        config.environments[environment].settings.networking.subnet_ids = [
            "subnet-12345678",
            "subnet-87654321",
        ]

        env = Environment(
            account=config.environments[environment].account,
            region=config.environments[environment].region,
        )

        # Deploy network stack with existing VPC
        network_stack = NetworkStack(
            app, f"test-network", config=config, environment=environment, env=env
        )

        # Verify VPC was imported, not created
        template = Template.from_stack(network_stack)
        template.resource_count_is("AWS::EC2::VPC", 0)  # No new VPC created

    @pytest.mark.slow
    def test_cdk_snapshot_consistency(self, config_loader, tmp_path):
        """Test that CDK synthesis produces consistent snapshots."""
        app = App(outdir=str(tmp_path / "cdk.out"))
        environment = "test"
        config = config_loader.get_config()
        env = Environment(
            account=config.environments[environment].account,
            region=config.environments[environment].region,
        )

        # Deploy minimal stack
        network_stack = NetworkStack(
            app, f"test-network", config=config, environment=environment, env=env
        )

        storage_stack = StorageStack(
            app,
            f"test-storage",
            config=config,
            environment=environment,
            network_stack=network_stack,
            env=env,
        )

        # Synthesize twice
        assembly1 = app.synth()
        assembly2 = app.synth()

        # Verify synthesis is deterministic
        assert assembly1.directory == assembly2.directory

        # Verify CloudFormation templates exist
        assert (tmp_path / "cdk.out" / "test-network.template.json").exists()
        assert (tmp_path / "cdk.out" / "test-storage.template.json").exists()

    def test_cross_region_deployment(self, config_loader):
        """Test deployment across multiple regions."""
        app = App()
        config = config_loader.get_config()

        # Configure multiple regions
        regions = ["us-east-1", "us-west-2", "eu-west-1"]

        for region in regions:
            environment = f"test-{region}"
            config.environments[environment] = config.environments["test"].copy()
            config.environments[environment].region = region

            env = Environment(
                account=config.environments[environment].account, region=region
            )

            # Deploy network stack in each region
            network_stack = NetworkStack(
                app,
                f"network-{region}",
                config=config,
                environment=environment,
                env=env,
            )

            # Verify region-specific configuration
            assert network_stack.region == region

            template = Template.from_stack(network_stack)
            template.resource_count_is("AWS::EC2::VPC", 1)

    def test_stack_tagging(self, config_loader):
        """Test that all resources are properly tagged."""
        app = App()
        environment = "test"
        config = config_loader.get_config()

        # Add custom tags
        config.global_config.tags = {
            "Project": "n8n",
            "ManagedBy": "CDK",
            "CostCenter": "Engineering",
        }

        env = Environment(
            account=config.environments[environment].account,
            region=config.environments[environment].region,
        )

        network_stack = NetworkStack(
            app, f"test-network", config=config, environment=environment, env=env
        )

        # Verify tags are applied
        template = Template.from_stack(network_stack)

        # Check VPC has tags
        vpc_resources = template.find_resources("AWS::EC2::VPC")
        for vpc in vpc_resources.values():
            tags = vpc["Properties"]["Tags"]
            tag_dict = {tag["Key"]: tag["Value"] for tag in tags}
            assert "Project" in tag_dict
            assert "Environment" in tag_dict
            assert tag_dict["Project"] == "n8n"
            assert tag_dict["Environment"] == environment
