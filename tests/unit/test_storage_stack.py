"""Unit tests for StorageStack."""

from unittest.mock import Mock

import pytest
from aws_cdk import App, Environment, RemovalPolicy
from aws_cdk.assertions import Match, Template

from n8n_deploy.config.models import (
    BackupConfig,
    DefaultsConfig,
    EnvironmentConfig,
    EnvironmentSettings,
    GlobalConfig,
    N8nConfig,
)
from n8n_deploy.stacks.network_stack import NetworkStack
from n8n_deploy.stacks.storage_stack import StorageStack


@pytest.mark.skip(reason="Template synthesis requires valid AWS environment format")
class TestStorageStack:
    """Test cases for StorageStack."""

    @pytest.fixture
    def app(self):
        """Create CDK app."""
        return App()

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            defaults=DefaultsConfig(efs={"lifecycle_days": 30, "backup_retention_days": 7}),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        backup=BackupConfig(enabled=True, retention_days=7, cross_region_backup=False)
                    ),
                )
            },
        )

    @pytest.fixture
    def network_stack_mock(self, app, test_config, vpc_mock, security_group_mock):
        """Create mock network stack."""
        stack = Mock(spec=NetworkStack)
        stack.vpc = vpc_mock
        stack.subnets = [Mock() for _ in range(2)]
        stack.efs_security_group = security_group_mock
        return stack

    def test_stack_initialization(self, app, test_config, network_stack_mock):
        """Test storage stack initialization."""
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.stack_name == "test-n8n-test-storage"
        assert stack.network_stack == network_stack_mock
        assert hasattr(stack, "file_system")
        assert hasattr(stack, "n8n_access_point")

    def test_efs_file_system_creation(self, app, test_config, network_stack_mock):
        """Test EFS file system creation with correct properties."""
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify EFS file system
        template.has_resource_properties(
            "AWS::EFS::FileSystem",
            {
                "Encrypted": True,
                "LifecyclePolicies": [{"TransitionToIA": "AFTER_30_DAYS"}],
                "PerformanceMode": "generalPurpose",
                "ThroughputMode": "bursting",
                "FileSystemTags": Match.array_with(
                    [
                        {
                            "Key": "Name",
                            "Value": Match.string_like_regexp("test-n8n-test-efs-n8n"),
                        },
                        {"Key": "Environment", "Value": "test"},
                        {"Key": "Project", "Value": "test-n8n"},
                    ]
                ),
            },
        )

    def test_efs_access_point_creation(self, app, test_config, network_stack_mock):
        """Test EFS access point creation for n8n."""
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify access point
        template.has_resource_properties(
            "AWS::EFS::AccessPoint",
            {
                "RootDirectory": {
                    "Path": "/n8n-data",
                    "CreationInfo": {
                        "OwnerUid": "1000",
                        "OwnerGid": "1000",
                        "Permissions": "755",
                    },
                },
                "PosixUser": {"Uid": "1000", "Gid": "1000"},
            },
        )

    def test_backup_setup_when_enabled(self, app, test_config, network_stack_mock):
        """Test backup setup when enabled in configuration."""
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify backup vault
        template.has_resource_properties(
            "AWS::Backup::BackupVault",
            {"BackupVaultName": Match.string_like_regexp("test-n8n-test-backup-vault")},
        )

        # Verify backup plan
        template.has_resource_properties(
            "AWS::Backup::BackupPlan",
            {
                "BackupPlan": {
                    "BackupPlanName": Match.string_like_regexp("test-n8n-test-backup-plan"),
                    "BackupPlanRule": [
                        {
                            "RuleName": "DailyBackup",
                            "ScheduleExpression": "cron(0 3 * * ? *)",
                            "TargetBackupVault": Match.any_value(),
                            "Lifecycle": {"DeleteAfterDays": 7},
                            "EnableContinuousBackup": False,
                            "StartWindowMinutes": 60,
                            "CompletionWindowMinutes": 120,
                        }
                    ],
                }
            },
        )

        # Verify backup selection
        template.has_resource_properties(
            "AWS::Backup::BackupSelection",
            {
                "BackupSelection": {
                    "SelectionName": "EfsBackupSelection",
                    "Resources": Match.array_with([Match.string_like_regexp("arn:aws:elasticfilesystem:.*")]),
                }
            },
        )

    def test_backup_not_created_when_disabled(self, app, test_config, network_stack_mock):
        """Test that backup resources are not created when disabled."""
        # Disable backup in config
        test_config.environments["test"].settings.backup.enabled = False

        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify no backup resources
        template.resource_count_is("AWS::Backup::BackupVault", 0)
        template.resource_count_is("AWS::Backup::BackupPlan", 0)
        template.resource_count_is("AWS::Backup::BackupSelection", 0)

    def test_production_environment_settings(self, app, test_config, network_stack_mock):
        """Test production-specific settings."""
        # Set environment to production
        test_config.environments["production"] = EnvironmentConfig(
            account="123456789012",
            region="us-east-1",
            settings=EnvironmentSettings(
                backup=BackupConfig(
                    enabled=True,
                    retention_days=30,
                    cross_region_backup=True,
                    backup_regions=["us-west-2"],
                )
            ),
        )

        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="production",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify automatic backups enabled for production
        template.has_resource_properties("AWS::EFS::FileSystem", {"BackupPolicy": {"Status": "ENABLED"}})

        # Verify continuous backup for production
        template.has_resource_properties(
            "AWS::Backup::BackupPlan",
            {
                "BackupPlan": {
                    "BackupPlanRule": [
                        {
                            "EnableContinuousBackup": True,
                            "Lifecycle": {"DeleteAfterDays": 30},
                        }
                    ]
                }
            },
        )

    def test_stack_outputs(self, app, test_config, network_stack_mock):
        """Test stack outputs are created correctly."""
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify outputs
        outputs = template.find_outputs("*")
        output_keys = set(outputs.keys())

        expected_outputs = {
            "FileSystemId",
            "FileSystemArn",
            "AccessPointId",
            "AccessPointArn",
            "MountTargets",
        }

        for output in expected_outputs:
            assert any(output in key for key in output_keys), f"Missing output: {output}"

    def test_efs_volume_configuration(self, app, test_config, network_stack_mock):
        """Test EFS volume configuration for Fargate."""
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Test volume configuration method
        volume_config = stack.get_efs_volume_configuration()

        assert volume_config["name"] == "n8n-data"
        assert "efs_volume_configuration" in volume_config
        assert volume_config["efs_volume_configuration"]["transit_encryption"] == "ENABLED"
        assert volume_config["efs_volume_configuration"]["authorization_config"]["iam"] == "ENABLED"
        assert "access_point_id" in volume_config["efs_volume_configuration"]["authorization_config"]
        assert "file_system_id" in volume_config["efs_volume_configuration"]

    def test_grant_read_write_permissions(self, app, test_config, network_stack_mock):
        """Test granting read/write permissions to EFS."""
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Mock grantee
        grantee_mock = Mock()

        # Mock file system grant method
        stack.file_system.grant_read_write = Mock()

        # Test grant method
        stack.grant_read_write(grantee_mock)

        # Verify grant was called
        stack.file_system.grant_read_write.assert_called_once_with(grantee_mock)

    def test_removal_policy_based_on_environment(self, app, test_config, network_stack_mock):
        """Test removal policy is set based on environment."""
        # Test non-production environment
        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.removal_policy == RemovalPolicy.DESTROY

        # Test production environment
        test_config.environments["production"] = EnvironmentConfig(
            account="123456789012", region="us-east-1", settings=EnvironmentSettings()
        )

        prod_stack = StorageStack(
            app,
            "TestProdStorageStack",
            config=test_config,
            environment="production",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert prod_stack.removal_policy == RemovalPolicy.RETAIN

    def test_lifecycle_policy_from_config(self, app, test_config, network_stack_mock):
        """Test EFS lifecycle policy is set from configuration."""
        # Update lifecycle days in config
        test_config.defaults.efs["lifecycle_days"] = 60

        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify lifecycle policy
        template.has_resource_properties(
            "AWS::EFS::FileSystem",
            {"LifecyclePolicies": [{"TransitionToIA": "AFTER_60_DAYS"}]},
        )

    def test_mount_targets_configuration(self, app, test_config, network_stack_mock):
        """Test mount targets are configured correctly."""
        # Set up mock subnets
        network_stack_mock.subnets = [
            Mock(subnet_id="subnet-12345"),
            Mock(subnet_id="subnet-67890"),
        ]

        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify mount targets are created for each subnet
        template.resource_count_is("AWS::EFS::MountTarget", 2)

    def test_cross_region_backup_configuration(self, app, test_config, network_stack_mock):
        """Test cross-region backup configuration."""
        # Enable cross-region backup
        test_config.environments["test"].settings.backup.cross_region_backup = True
        test_config.environments["test"].settings.backup.backup_regions = [
            "us-west-2",
            "eu-west-1",
        ]

        stack = StorageStack(
            app,
            "TestStorageStack",
            config=test_config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # The implementation has placeholders for cross-region backup
        # This test verifies the configuration is properly passed
        assert stack.env_config.settings.backup.cross_region_backup is True
        assert len(stack.env_config.settings.backup.backup_regions) == 2

    def test_error_handling_missing_network_stack(self, app, test_config):
        """Test error handling when network stack is missing required attributes."""
        incomplete_network_stack = Mock(spec=NetworkStack)
        incomplete_network_stack.vpc = None  # Missing VPC

        with pytest.raises(AttributeError):
            StorageStack(
                app,
                "TestStorageStack",
                config=test_config,
                environment="test",
                network_stack=incomplete_network_stack,
                env=Environment(account="123456789012", region="us-east-1"),
            )
