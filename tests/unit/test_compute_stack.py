"""Unit tests for ComputeStack."""
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import pytest
from aws_cdk import App, Duration, Environment
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_ecs as ecs
from aws_cdk.assertions import Match, Template

from n8n_deploy.config.models import (
    BackupConfig,
    EnvironmentConfig,
    EnvironmentSettings,
    FargateConfig,
    GlobalConfig,
    MonitoringConfig,
    N8nConfig,
    ScalingConfig,
)
from n8n_deploy.stacks.compute_stack import ComputeStack
from n8n_deploy.stacks.network_stack import NetworkStack
from n8n_deploy.stacks.storage_stack import StorageStack


class TestComputeStack:
    """Test cases for ComputeStack."""

    @pytest.fixture
    def app(self):
        """Create CDK app."""
        return App()

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return N8nConfig(
            global_config=GlobalConfig(
                project_name="test-n8n", organization="test-org"
            ),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        fargate=FargateConfig(
                            cpu=256,
                            memory=512,
                            spot_percentage=80,
                            n8n_version="1.94.1",
                        ),
                        scaling=ScalingConfig(
                            min_tasks=1,
                            max_tasks=3,
                            target_cpu_utilization=70,
                            scale_in_cooldown=300,
                            scale_out_cooldown=60,
                        ),
                        monitoring=MonitoringConfig(enable_container_insights=True),
                    ),
                )
            },
        )

    @pytest.fixture
    def network_stack_mock(self, vpc_mock, security_group_mock):
        """Create mock network stack."""
        stack = Mock(spec=NetworkStack)
        stack.vpc = vpc_mock
        stack.subnets = [Mock() for _ in range(2)]
        stack.n8n_security_group = security_group_mock
        return stack

    @pytest.fixture
    def storage_stack_mock(self, efs_file_system_mock, efs_access_point_mock):
        """Create mock storage stack."""
        stack = Mock(spec=StorageStack)
        stack.file_system = efs_file_system_mock
        stack.n8n_access_point = efs_access_point_mock
        return stack

    def test_stack_initialization(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test compute stack initialization."""
        stack = ComputeStack(
            app,
            "TestComputeStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            storage_stack=storage_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.stack_name == "test-n8n-test-compute"
        assert stack.network_stack == network_stack_mock
        assert stack.storage_stack == storage_stack_mock
        assert hasattr(stack, "cluster")
        assert hasattr(stack, "n8n_service")

    def test_ecs_cluster_creation(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test ECS cluster creation with correct properties."""
        stack = ComputeStack(
            app,
            "TestComputeStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            storage_stack=storage_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify ECS cluster
        template.has_resource_properties(
            "AWS::ECS::Cluster",
            {
                "ClusterName": Match.string_like_regexp("test-n8n-test-ecs-cluster"),
                "ClusterSettings": [{"Name": "containerInsights", "Value": "enabled"}],
            },
        )

    def test_container_insights_disabled(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test container insights can be disabled."""
        test_config.environments[
            "test"
        ].settings.monitoring.enable_container_insights = False

        stack = ComputeStack(
            app,
            "TestComputeStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            storage_stack=storage_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify container insights disabled
        template.has_resource_properties(
            "AWS::ECS::Cluster",
            {"ClusterSettings": [{"Name": "containerInsights", "Value": "disabled"}]},
        )

    @patch("n8n_deploy.stacks.compute_stack.N8nFargateService")
    def test_fargate_service_creation(
        self,
        mock_fargate_service,
        app,
        test_config,
        network_stack_mock,
        storage_stack_mock,
    ):
        """Test Fargate service is created with correct parameters."""
        mock_service_instance = Mock()
        mock_fargate_service.return_value = mock_service_instance

        stack = ComputeStack(
            app,
            "TestComputeStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            storage_stack=storage_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Verify Fargate service was created with correct parameters
        mock_fargate_service.assert_called_once()
        call_args = mock_fargate_service.call_args

        assert call_args[1]["cluster"] == stack.cluster
        assert call_args[1]["vpc"] == network_stack_mock.vpc
        assert call_args[1]["subnets"] == network_stack_mock.subnets
        assert call_args[1]["security_group"] == network_stack_mock.n8n_security_group
        assert call_args[1]["file_system"] == storage_stack_mock.file_system
        assert call_args[1]["access_point"] == storage_stack_mock.n8n_access_point
        assert call_args[1]["environment"] == "test"

    def test_auto_scaling_setup(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test auto-scaling is set up when max_tasks > min_tasks."""
        # Ensure auto-scaling is configured
        test_config.environments["test"].settings.scaling.min_tasks = 1
        test_config.environments["test"].settings.scaling.max_tasks = 5

        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            # Set up mock service with auto-scaling capabilities
            mock_service = Mock()
            mock_scalable_target = Mock()
            mock_service.service.auto_scale_task_count.return_value = (
                mock_scalable_target
            )
            mock_fargate.return_value = mock_service

            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=test_config,
                environment="test",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            # Verify auto-scaling was set up
            mock_service.service.auto_scale_task_count.assert_called_once_with(
                min_capacity=1, max_capacity=5
            )

            # Verify CPU scaling was configured
            mock_scalable_target.scale_on_cpu_utilization.assert_called_once()
            cpu_scaling_args = mock_scalable_target.scale_on_cpu_utilization.call_args[
                1
            ]
            assert cpu_scaling_args["target_utilization_percent"] == 70

    def test_no_auto_scaling_when_disabled(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test auto-scaling is not set up when min_tasks equals max_tasks."""
        # Disable auto-scaling
        test_config.environments["test"].settings.scaling.min_tasks = 1
        test_config.environments["test"].settings.scaling.max_tasks = 1

        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            mock_service = Mock()
            mock_fargate.return_value = mock_service

            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=test_config,
                environment="test",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            # Verify auto-scaling was not called
            mock_service.service.auto_scale_task_count.assert_not_called()

    def test_production_memory_scaling(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test memory-based scaling is added for production environments."""
        # Set up production environment
        test_config.environments["production"] = EnvironmentConfig(
            account="123456789012",
            region="us-east-1",
            settings=EnvironmentSettings(
                fargate=FargateConfig(cpu=1024, memory=2048),
                scaling=ScalingConfig(min_tasks=2, max_tasks=10),
                monitoring=MonitoringConfig(enable_container_insights=True),
            ),
        )

        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            mock_service = Mock()
            mock_scalable_target = Mock()
            mock_service.service.auto_scale_task_count.return_value = (
                mock_scalable_target
            )
            mock_service.service.service_name = "test-service"
            mock_fargate.return_value = mock_service

            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=test_config,
                environment="production",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            # Verify memory scaling was configured for production
            mock_scalable_target.scale_on_metric.assert_called_once()
            memory_scaling_args = mock_scalable_target.scale_on_metric.call_args
            assert memory_scaling_args[0][0] == "MemoryScaling"

    def test_database_integration(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test compute stack with database integration."""
        mock_secret = Mock()

        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=test_config,
                environment="test",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                database_endpoint="test-db.cluster-xxx.us-east-1.rds.amazonaws.com",
                database_secret=mock_secret,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            # Verify database parameters were passed
            call_args = mock_fargate.call_args[1]
            assert (
                call_args["database_endpoint"]
                == "test-db.cluster-xxx.us-east-1.rds.amazonaws.com"
            )
            assert call_args["database_secret"] == mock_secret

    def test_stack_outputs(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test stack outputs are created correctly."""
        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            # Set up mock service
            mock_service = Mock()
            mock_service.service.service_name = "test-n8n-service"
            mock_service.service.service_arn = (
                "arn:aws:ecs:us-east-1:123456789012:service/test"
            )
            mock_service.service.cloud_map_service = Mock(service_name="n8n.local")
            mock_service.task_definition.task_definition_arn = (
                "arn:aws:ecs:us-east-1:123456789012:task-definition/test"
            )
            mock_service.log_group.log_group_name = "/ecs/test-n8n"
            mock_fargate.return_value = mock_service

            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=test_config,
                environment="test",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            template = Template.from_stack(stack)

            # Verify outputs
            outputs = template.find_outputs("*")
            output_keys = set(outputs.keys())

            expected_outputs = {
                "ClusterName",
                "ClusterArn",
                "ServiceName",
                "ServiceArn",
                "TaskDefinitionArn",
                "ServiceDiscoveryName",
                "LogGroupName",
            }

            for output in expected_outputs:
                assert any(
                    output in key for key in output_keys
                ), f"Missing output: {output}"

    def test_spot_percentage_configuration(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test spot percentage is correctly passed from configuration."""
        # Set spot percentage
        test_config.environments["test"].settings.fargate.spot_percentage = 100

        stack = ComputeStack(
            app,
            "TestComputeStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            storage_stack=storage_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Verify spot configuration
        assert stack.is_spot_enabled is True
        assert stack.env_config.settings.fargate.spot_percentage == 100

    def test_service_property_accessors(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test property accessors for service and security group."""
        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            mock_service = Mock()
            mock_fargate_service = Mock()
            mock_service.service = mock_fargate_service
            mock_fargate.return_value = mock_service

            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=test_config,
                environment="test",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            # Test service property
            assert stack.service == mock_fargate_service

            # Test security group property
            assert stack.service_security_group == network_stack_mock.n8n_security_group

    def test_scaling_cooldown_periods(
        self, app, test_config, network_stack_mock, storage_stack_mock
    ):
        """Test scaling cooldown periods are correctly configured."""
        # Set custom cooldown periods
        test_config.environments["test"].settings.scaling.scale_in_cooldown = 600
        test_config.environments["test"].settings.scaling.scale_out_cooldown = 120

        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            mock_service = Mock()
            mock_scalable_target = Mock()
            mock_service.service.auto_scale_task_count.return_value = (
                mock_scalable_target
            )
            mock_fargate.return_value = mock_service

            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=test_config,
                environment="test",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            # Verify cooldown periods
            cpu_scaling_call = mock_scalable_target.scale_on_cpu_utilization.call_args[
                1
            ]
            assert cpu_scaling_call["scale_in_cooldown"].to_seconds() == 600
            assert cpu_scaling_call["scale_out_cooldown"].to_seconds() == 120

    def test_no_scaling_config(self, app, network_stack_mock, storage_stack_mock):
        """Test stack creation without scaling configuration."""
        # Create config without scaling
        config = N8nConfig(
            global_config=GlobalConfig(
                project_name="test-n8n", organization="test-org"
            ),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(),  # No scaling config
                )
            },
        )

        with patch("n8n_deploy.stacks.compute_stack.N8nFargateService") as mock_fargate:
            mock_service = Mock()
            mock_fargate.return_value = mock_service

            stack = ComputeStack(
                app,
                "TestComputeStack",
                config=config,
                environment="test",
                network_stack=network_stack_mock,
                storage_stack=storage_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            # Verify no auto-scaling setup was attempted
            mock_service.service.auto_scale_task_count.assert_not_called()
