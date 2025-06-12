"""Pytest configuration and fixtures for unit tests."""
import pytest
from aws_cdk import App, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_secretsmanager as secretsmanager
from unittest.mock import MagicMock, patch

from n8n_deploy.config.models import (
    N8nConfig,
    GlobalConfig,
    EnvironmentConfig,
    EnvironmentSettings,
    FargateConfig,
    NetworkingConfig,
    ScalingConfig,
    AccessConfig,
    AuthConfig,
    MonitoringConfig,
    BackupConfig,
)


@pytest.fixture
def mock_app():
    """Create a mock CDK app."""
    return App()


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return N8nConfig(
        global_config=GlobalConfig(
            project_name="test-n8n",
            organization="testorg",
            tags={"Environment": "test", "Project": "n8n"},
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
                    ),
                    scaling=ScalingConfig(
                        min_tasks=1,
                        max_tasks=3,
                        target_cpu_utilization=70,
                    ),
                    networking=NetworkingConfig(
                        use_existing_vpc=False,
                        vpc_cidr="10.0.0.0/16",
                    ),
                    access=AccessConfig(
                        domain_name="n8n.test.com",
                        cloudfront_enabled=True,
                        api_gateway_throttle=1000,
                    ),
                    auth=AuthConfig(
                        basic_auth_enabled=True,
                        oauth_enabled=False,
                    ),
                    monitoring=MonitoringConfig(
                        log_retention_days=30,
                        alarm_email="test@example.com",
                        enable_container_insights=True,
                    ),
                    backup=BackupConfig(
                        enabled=True,
                        retention_days=7,
                    ),
                ),
            )
        },
    )


@pytest.fixture
def mock_vpc():
    """Create a mock VPC."""
    vpc = MagicMock(spec=ec2.Vpc)
    vpc.vpc_id = "vpc-12345"
    vpc.vpc_cidr_block = "10.0.0.0/16"
    vpc.public_subnets = [
        MagicMock(subnet_id="subnet-1", availability_zone="us-east-1a"),
        MagicMock(subnet_id="subnet-2", availability_zone="us-east-1b"),
    ]
    vpc.private_subnets = []
    return vpc


@pytest.fixture
def mock_security_group():
    """Create a mock security group."""
    sg = MagicMock(spec=ec2.SecurityGroup)
    sg.security_group_id = "sg-12345"
    return sg


@pytest.fixture
def mock_file_system():
    """Create a mock EFS file system."""
    fs = MagicMock(spec=efs.FileSystem)
    fs.file_system_id = "fs-12345"
    fs.file_system_arn = "arn:aws:efs:us-east-1:123456789012:file-system/fs-12345"
    return fs


@pytest.fixture
def mock_access_point():
    """Create a mock EFS access point."""
    ap = MagicMock(spec=efs.AccessPoint)
    ap.access_point_id = "fsap-12345"
    ap.access_point_arn = "arn:aws:efs:us-east-1:123456789012:access-point/fsap-12345"
    return ap


@pytest.fixture
def mock_cluster():
    """Create a mock ECS cluster."""
    cluster = MagicMock(spec=ecs.Cluster)
    cluster.cluster_name = "test-cluster"
    cluster.cluster_arn = "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster"
    return cluster


@pytest.fixture
def mock_service():
    """Create a mock ECS service."""
    service = MagicMock(spec=ecs.FargateService)
    service.service_name = "test-service"
    service.service_arn = "arn:aws:ecs:us-east-1:123456789012:service/test-service"
    service.cloud_map_service = MagicMock()
    service.cloud_map_service.service_name = "n8n"
    return service


@pytest.fixture
def mock_secret():
    """Create a mock Secrets Manager secret."""
    secret = MagicMock(spec=secretsmanager.Secret)
    secret.secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret"
    return secret


@pytest.fixture
def mock_network_stack(mock_vpc, mock_security_group):
    """Create a mock network stack."""
    stack = MagicMock()
    stack.vpc = mock_vpc
    stack.subnets = mock_vpc.public_subnets
    stack.n8n_security_group = mock_security_group
    stack.efs_security_group = mock_security_group
    return stack


@pytest.fixture
def mock_storage_stack(mock_file_system, mock_access_point):
    """Create a mock storage stack."""
    stack = MagicMock()
    stack.file_system = mock_file_system
    stack.n8n_access_point = mock_access_point
    return stack


@pytest.fixture
def mock_compute_stack(mock_cluster, mock_service, mock_security_group):
    """Create a mock compute stack."""
    stack = MagicMock()
    stack.cluster = mock_cluster
    stack.n8n_service = MagicMock()
    stack.n8n_service.service = mock_service
    stack.n8n_service.log_group = MagicMock()
    stack.n8n_service.log_group.log_group_name = "/ecs/n8n/test"
    stack.service = mock_service
    stack.service_security_group = mock_security_group
    stack.network_stack = MagicMock()
    stack.network_stack.vpc = MagicMock()
    stack.network_stack.vpc.vpc_cidr_block = "10.0.0.0/16"
    return stack


@pytest.fixture
def mock_database_stack(mock_secret):
    """Create a mock database stack."""
    stack = MagicMock()
    stack.secret = mock_secret
    stack.endpoint = "test-db.cluster-12345.us-east-1.rds.amazonaws.com:5432"
    stack.instance = MagicMock()
    stack.instance.db_instance_endpoint_address = "test-db.12345.us-east-1.rds.amazonaws.com"
    stack.instance.db_instance_endpoint_port = "5432"
    return stack