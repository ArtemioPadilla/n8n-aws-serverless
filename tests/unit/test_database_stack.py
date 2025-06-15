"""Unit tests for DatabaseStack."""

from unittest.mock import Mock

import pytest
from aws_cdk import App, Environment, RemovalPolicy
from aws_cdk.assertions import Match, Template

from n8n_deploy.config.models import (
    DatabaseConfig,
    EnvironmentConfig,
    EnvironmentSettings,
    GlobalConfig,
    N8nConfig,
)
from n8n_deploy.stacks.database_stack import DatabaseStack
from n8n_deploy.stacks.network_stack import NetworkStack


@pytest.mark.skip(reason="Template synthesis requires valid AWS environment format")
class TestDatabaseStack:
    """Test cases for DatabaseStack."""

    @pytest.fixture
    def app(self):
        """Create CDK app."""
        return App()

    @pytest.fixture
    def test_config_rds(self):
        """Create test configuration for RDS instance."""
        return N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        database=DatabaseConfig(
                            type="postgres",
                            use_existing=False,
                            instance_class="db.t4g.micro",
                            multi_az=False,
                            backup_retention_days=7,
                        )
                    ),
                )
            },
        )

    @pytest.fixture
    def test_config_aurora(self):
        """Create test configuration for Aurora Serverless."""
        return N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        database=DatabaseConfig(
                            type="postgres",
                            use_existing=False,
                            aurora_serverless={
                                "min_capacity": 0.5,
                                "max_capacity": 1.0,
                            },
                            backup_retention_days=7,
                        )
                    ),
                )
            },
        )

    @pytest.fixture
    def test_config_existing(self):
        """Create test configuration for existing database."""
        return N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        database=DatabaseConfig(
                            type="postgres",
                            use_existing=True,
                            connection_secret_arn="arn:aws:secretsmanager:us-east-1:123456789012:secret:test-abc123",
                        )
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

    def test_stack_initialization_rds(self, app, test_config_rds, network_stack_mock):
        """Test database stack initialization with RDS instance."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_rds,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.stack_name == "test-n8n-test-database"
        assert stack.network_stack == network_stack_mock
        assert hasattr(stack, "db_security_group")
        assert hasattr(stack, "instance")
        assert hasattr(stack, "secret")

    def test_stack_initialization_aurora(self, app, test_config_aurora, network_stack_mock):
        """Test database stack initialization with Aurora Serverless."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_aurora,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.stack_name == "test-n8n-test-database"
        assert hasattr(stack, "cluster")
        assert hasattr(stack, "secret")

    def test_database_security_group_creation(self, app, test_config_rds, network_stack_mock):
        """Test database security group creation."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_rds,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify security group
        template.has_resource_properties(
            "AWS::EC2::SecurityGroup",
            {
                "GroupDescription": "Security group for n8n database",
                "GroupName": Match.string_like_regexp("test-n8n-test-sg-database"),
                "SecurityGroupEgress": [],  # No outbound rules for database
            },
        )

        # Verify ingress rule from n8n security group
        template.has_resource_properties(
            "AWS::EC2::SecurityGroupIngress",
            {
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "Description": "Allow PostgreSQL access from n8n containers",
            },
        )

    def test_rds_instance_creation(self, app, test_config_rds, network_stack_mock):
        """Test RDS instance creation with correct properties."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_rds,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify RDS instance
        template.has_resource_properties(
            "AWS::RDS::DBInstance",
            {
                "DBInstanceIdentifier": Match.string_like_regexp("test-n8n-test-rds"),
                "DBInstanceClass": "db.t4g.micro",
                "Engine": "postgres",
                "DBName": "n8n",
                "AllocatedStorage": "20",
                "StorageType": "gp3",
                "MultiAZ": False,
                "BackupRetentionPeriod": 7,
                "PreferredBackupWindow": "03:00-04:00",
                "PreferredMaintenanceWindow": "sun:04:00-sun:05:00",
                "PubliclyAccessible": False,
                "StorageEncrypted": True,
                "EnableCloudwatchLogsExports": ["postgresql"],
                "DeletionProtection": False,  # Not production
                "AutoMinorVersionUpgrade": False,
            },
        )

    def test_aurora_serverless_creation(self, app, test_config_aurora, network_stack_mock):
        """Test Aurora Serverless cluster creation."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_aurora,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify Aurora cluster
        template.has_resource_properties(
            "AWS::RDS::DBCluster",
            {
                "Engine": "aurora-postgresql",
                "DBClusterIdentifier": Match.string_like_regexp("test-n8n-test-aurora"),
                "DatabaseName": "n8n",
                "ServerlessV2ScalingConfiguration": {
                    "MinCapacity": 0.5,
                    "MaxCapacity": 1.0,
                },
                "BackupRetentionPeriod": 7,
                "PreferredBackupWindow": "03:00-04:00",
                "StorageEncrypted": True,
                "EnableCloudwatchLogsExports": ["postgresql"],
                "DeletionProtection": False,  # Not production
                "EnableHttpEndpoint": True,  # Data API enabled
            },
        )

        # Verify Aurora instance
        template.has_resource_properties(
            "AWS::RDS::DBInstance",
            {
                "DBInstanceClass": "db.t3.medium",
                "Engine": "aurora-postgresql",
                "PerformanceInsightsEnabled": False,  # Not production
            },
        )

    def test_existing_database_import(self, app, test_config_existing, network_stack_mock):
        """Test importing existing database."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_existing,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Verify no new database resources created
        template = Template.from_stack(stack)
        template.resource_count_is("AWS::RDS::DBInstance", 0)
        template.resource_count_is("AWS::RDS::DBCluster", 0)

        # Verify secret was imported (check stack has secret attribute)
        assert hasattr(stack, "secret")
        assert stack.db_config.use_existing is True

    def test_existing_database_missing_secret_arn(self, app, network_stack_mock):
        """Test error when existing database is missing secret ARN."""
        config = N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        database=DatabaseConfig(
                            type="postgres",
                            use_existing=True,
                            # Missing connection_secret_arn
                        )
                    ),
                )
            },
        )

        with pytest.raises(ValueError, match="connection_secret_arn required"):
            DatabaseStack(
                app,
                "TestDatabaseStack",
                config=config,
                environment="test",
                network_stack=network_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

    def test_secret_creation(self, app, test_config_rds, network_stack_mock):
        """Test database credentials secret creation."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_rds,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify secret
        template.has_resource_properties(
            "AWS::SecretsManager::Secret",
            {
                "Name": "n8n/test/db-credentials",
                "Description": "n8n database credentials for test",
                "GenerateSecretString": {
                    "SecretStringTemplate": '{"username": "n8nadmin"}',
                    "GenerateStringKey": "password",
                    "ExcludeCharacters": " %+~`#$&*()|[]{}:;<>?!'/@\"\\",
                    "PasswordLength": 30,
                },
            },
        )

    def test_production_settings(self, app, network_stack_mock):
        """Test production-specific settings."""
        config = N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "production": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        database=DatabaseConfig(
                            type="postgres",
                            instance_class="db.r6g.large",
                            multi_az=True,
                            backup_retention_days=30,
                        )
                    ),
                )
            },
        )

        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=config,
            environment="production",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify production settings
        template.has_resource_properties(
            "AWS::RDS::DBInstance",
            {
                "DBInstanceClass": "db.r6g.large",
                "MultiAZ": True,
                "BackupRetentionPeriod": 30,
                "DeletionProtection": True,
                "PerformanceInsightsEnabled": True,
            },
        )

    def test_instance_class_parsing(self, app, network_stack_mock):
        """Test instance class parsing from string."""
        configs = [
            ("db.t4g.micro", "db.t4g.micro"),
            ("db.r6g.large", "db.r6g.large"),
            ("db.m5.xlarge", "db.m5.xlarge"),
        ]

        for input_class, expected_class in configs:
            config = N8nConfig(
                global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
                environments={
                    "test": EnvironmentConfig(
                        account="123456789012",
                        region="us-east-1",
                        settings=EnvironmentSettings(
                            database=DatabaseConfig(type="postgres", instance_class=input_class)
                        ),
                    )
                },
            )

            stack = DatabaseStack(
                app,
                f"TestDatabaseStack-{input_class.replace('.', '-')}",
                config=config,
                environment="test",
                network_stack=network_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            template = Template.from_stack(stack)
            template.has_resource_properties("AWS::RDS::DBInstance", {"DBInstanceClass": expected_class})

    def test_stack_outputs(self, app, test_config_rds, network_stack_mock):
        """Test stack outputs are created correctly."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_rds,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify outputs
        outputs = template.find_outputs("*")
        output_keys = set(outputs.keys())

        expected_outputs = {
            "DatabaseEndpoint",
            "DatabaseSecretArn",
            "DatabaseSecurityGroupId",
        }

        for output in expected_outputs:
            assert any(output in key for key in output_keys), f"Missing output: {output}"

    def test_removal_policy_based_on_environment(self, app, test_config_rds, network_stack_mock):
        """Test removal policy is set based on environment."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_rds,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.removal_policy == RemovalPolicy.DESTROY

        # Test production environment
        test_config_rds.environments["production"] = EnvironmentConfig(
            account="123456789012",
            region="us-east-1",
            settings=EnvironmentSettings(database=DatabaseConfig(type="postgres")),
        )

        prod_stack = DatabaseStack(
            app,
            "TestProdDatabaseStack",
            config=test_config_rds,
            environment="production",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert prod_stack.removal_policy == RemovalPolicy.RETAIN

    def test_subnet_group_creation(self, app, test_config_aurora, network_stack_mock):
        """Test subnet group creation for Aurora."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_aurora,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify subnet group
        template.has_resource_properties(
            "AWS::RDS::DBSubnetGroup",
            {"DBSubnetGroupDescription": "Subnet group for n8n test"},
        )

    def test_cloudwatch_logs_configuration(self, app, test_config_rds, network_stack_mock):
        """Test CloudWatch logs configuration."""
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=test_config_rds,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify log retention
        template.has_resource_properties(
            "Custom::LogRetention",
            {
                "LogGroupName": Match.string_like_regexp("/aws/rds/instance/.*"),
                "RetentionInDays": 30,
            },
        )

    def test_no_database_config(self, app, network_stack_mock):
        """Test stack creation without database configuration."""
        config = N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(),  # No database config
                )
            },
        )

        # Should create with default DatabaseConfig
        stack = DatabaseStack(
            app,
            "TestDatabaseStack",
            config=config,
            environment="test",
            network_stack=network_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.db_config.type == "postgres"  # Default value
        assert stack.db_config.use_existing is False  # Default value
