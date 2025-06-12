"""Construct for n8n Fargate service with all required configurations."""
from typing import Dict, List, Optional

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_efs as efs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_servicediscovery as servicediscovery
from constructs import Construct

from ..config.models import DatabaseConfig, DatabaseType, EnvironmentConfig, FargateConfig


class N8nFargateService(Construct):
    """Construct for n8n Fargate service."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cluster: ecs.Cluster,
        vpc: ec2.IVpc,
        subnets: List[ec2.ISubnet],
        security_group: ec2.SecurityGroup,
        file_system: efs.FileSystem,
        access_point: efs.AccessPoint,
        env_config: EnvironmentConfig,
        environment: str,
        database_endpoint: Optional[str] = None,
        database_secret: Optional[secretsmanager.ISecret] = None,
        **kwargs,
    ) -> None:
        """Initialize n8n Fargate service.

        Args:
            scope: CDK scope
            construct_id: Construct ID
            cluster: ECS cluster
            vpc: VPC for the service
            subnets: Subnets for the service
            security_group: Security group for the service
            file_system: EFS file system
            access_point: EFS access point
            env_config: Environment configuration
            environment: Environment name
            database_endpoint: Optional RDS endpoint
            database_secret: Optional database credentials secret
            **kwargs: Additional properties
        """
        super().__init__(scope, construct_id, **kwargs)

        self.cluster = cluster
        self.vpc = vpc
        self.subnets = subnets
        self.security_group = security_group
        self.file_system = file_system
        self.access_point = access_point
        self.env_config = env_config
        self.environment = environment

        # Get configurations
        self.fargate_config = env_config.settings.fargate or FargateConfig()
        self.database_config = env_config.settings.database or DatabaseConfig()

        # Create log group
        self.log_group = self._create_log_group()

        # Create task definition
        self.task_definition = self._create_task_definition()

        # Add container
        self.container = self._add_n8n_container(database_endpoint, database_secret)

        # Create service
        self.service = self._create_fargate_service()

        # Enable service discovery
        self._setup_service_discovery()

    def _create_log_group(self) -> logs.LogGroup:
        """Create CloudWatch log group for n8n."""
        # Map numeric days to RetentionDays enum
        retention_map = {
            1: logs.RetentionDays.ONE_DAY,
            3: logs.RetentionDays.THREE_DAYS,
            5: logs.RetentionDays.FIVE_DAYS,
            7: logs.RetentionDays.ONE_WEEK,
            14: logs.RetentionDays.TWO_WEEKS,
            30: logs.RetentionDays.ONE_MONTH,
            60: logs.RetentionDays.TWO_MONTHS,
            90: logs.RetentionDays.THREE_MONTHS,
            120: logs.RetentionDays.FOUR_MONTHS,
            150: logs.RetentionDays.FIVE_MONTHS,
            180: logs.RetentionDays.SIX_MONTHS,
            365: logs.RetentionDays.ONE_YEAR,
            400: logs.RetentionDays.THIRTEEN_MONTHS,
            545: logs.RetentionDays.EIGHTEEN_MONTHS,
            731: logs.RetentionDays.TWO_YEARS,
            1096: logs.RetentionDays.THREE_YEARS,
            1827: logs.RetentionDays.FIVE_YEARS,
        }

        retention_days = logs.RetentionDays.ONE_MONTH  # Default
        if (
            self.env_config.settings.monitoring
            and self.env_config.settings.monitoring.log_retention_days
        ):
            requested_days = self.env_config.settings.monitoring.log_retention_days
            # Find the closest matching retention period
            closest_days = min(
                retention_map.keys(), key=lambda x: abs(x - requested_days)
            )
            retention_days = retention_map[closest_days]

        return logs.LogGroup(
            self,
            "LogGroup",
            log_group_name=f"/ecs/n8n/{self.environment}",
            retention=retention_days,
            removal_policy=RemovalPolicy.DESTROY
            if self.environment == "dev"
            else RemovalPolicy.RETAIN,
        )

    def _create_task_definition(self) -> ecs.FargateTaskDefinition:
        """Create Fargate task definition."""
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            cpu=self.fargate_config.cpu,
            memory_limit_mib=self.fargate_config.memory,
            family=f"n8n-{self.environment}",
        )

        # Add EFS volume
        task_definition.add_volume(
            name="n8n-data",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=self.file_system.file_system_id,
                transit_encryption="ENABLED",
                authorization_config=ecs.AuthorizationConfig(
                    access_point_id=self.access_point.access_point_id, iam="ENABLED"
                ),
            ),
        )

        # Grant EFS permissions
        self.file_system.grant_read_write(task_definition.task_role)

        # Add required permissions for n8n
        self._add_n8n_permissions(task_definition.task_role)

        return task_definition

    def _add_n8n_container(
        self,
        database_endpoint: Optional[str],
        database_secret: Optional[secretsmanager.ISecret],
    ) -> ecs.ContainerDefinition:
        """Add n8n container to task definition."""
        # Get or create encryption key secret
        encryption_key = self._get_or_create_encryption_key()

        # Build environment variables
        environment = self._build_environment_variables(database_endpoint)

        # Build secrets
        secrets = self._build_secrets(encryption_key, database_secret)

        # Get n8n version from config, default to 1.94.1
        n8n_version = "1.94.1"
        if self.env_config.settings and self.env_config.settings.fargate:
            n8n_version = self.env_config.settings.fargate.n8n_version or "1.94.1"

        # Add container
        container = self.task_definition.add_container(
            "n8n",
            image=ecs.ContainerImage.from_registry(f"n8nio/n8n:{n8n_version}"),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="n8n",
                log_group=self.log_group,
            ),
            environment=environment,
            secrets=secrets,
            port_mappings=[
                ecs.PortMapping(
                    container_port=5678,
                    protocol=ecs.Protocol.TCP,
                )
            ],
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "wget --no-verbose --tries=1 --spider http://localhost:5678/healthz || exit 1",
                ],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60),
            ),
            memory_reservation_mib=int(
                self.fargate_config.memory * 0.8
            ),  # 80% soft limit
        )

        # Mount EFS volume
        container.add_mount_points(
            ecs.MountPoint(
                source_volume="n8n-data",
                container_path="/home/node/.n8n",
                read_only=False,
            )
        )

        return container

    def _build_environment_variables(
        self, database_endpoint: Optional[str]
    ) -> Dict[str, str]:
        """Build environment variables for n8n container."""
        env_vars = {
            # Basic configuration
            "N8N_HOST": "0.0.0.0",
            "N8N_PORT": "5678",
            "N8N_PROTOCOL": "https",
            "NODE_ENV": "production",
            # Paths
            "N8N_USER_FOLDER": "/home/node/.n8n",
            # Security
            "N8N_SECURE_COOKIE": "true",
            # Execution settings
            "EXECUTIONS_MODE": "regular",
            "EXECUTIONS_PROCESS": "main",
            # Timezone
            "TZ": "UTC",
            "GENERIC_TIMEZONE": "UTC",
        }

        # Database configuration
        if self.database_config.type == DatabaseType.POSTGRES and database_endpoint:
            env_vars.update(
                {
                    "DB_TYPE": "postgresdb",
                    "DB_POSTGRESDB_HOST": database_endpoint.split(":")[0],
                    "DB_POSTGRESDB_PORT": database_endpoint.split(":")[1]
                    if ":" in database_endpoint
                    else "5432",
                    "DB_POSTGRESDB_DATABASE": "n8n",
                    "DB_POSTGRESDB_SCHEMA": "public",
                }
            )
        else:
            env_vars.update(
                {
                    "DB_TYPE": "sqlite",
                    "DB_SQLITE_DATABASE": "/home/node/.n8n/database.sqlite",
                }
            )

        # Auth configuration
        if self.env_config.settings.auth:
            if self.env_config.settings.auth.basic_auth_enabled:
                env_vars["N8N_BASIC_AUTH_ACTIVE"] = "true"

        # Webhook configuration
        if self.env_config.settings.features and self.env_config.settings.features.get(
            "webhooks_enabled"
        ):
            env_vars["WEBHOOK_URL"] = (
                f"https://{self.env_config.settings.access.domain_name}/webhook"
                if self.env_config.settings.access
                and self.env_config.settings.access.domain_name
                else ""
            )

        # Metrics
        env_vars["N8N_METRICS"] = "true"
        env_vars["N8N_METRICS_PREFIX"] = "n8n_"

        return env_vars

    def _build_secrets(
        self,
        encryption_key: secretsmanager.ISecret,
        database_secret: Optional[secretsmanager.ISecret],
    ) -> Dict[str, ecs.Secret]:
        """Build secrets for n8n container."""
        secrets = {
            "N8N_ENCRYPTION_KEY": ecs.Secret.from_secrets_manager(encryption_key),
        }

        # Database credentials
        if database_secret and self.database_config.type == DatabaseType.POSTGRES:
            secrets.update(
                {
                    "DB_POSTGRESDB_USER": ecs.Secret.from_secrets_manager(
                        database_secret, "username"
                    ),
                    "DB_POSTGRESDB_PASSWORD": ecs.Secret.from_secrets_manager(
                        database_secret, "password"
                    ),
                }
            )

        # Basic auth credentials
        if (
            self.env_config.settings.auth
            and self.env_config.settings.auth.basic_auth_enabled
        ):
            basic_auth_secret = self._get_or_create_basic_auth_secret()
            secrets.update(
                {
                    "N8N_BASIC_AUTH_USER": ecs.Secret.from_secrets_manager(
                        basic_auth_secret, "username"
                    ),
                    "N8N_BASIC_AUTH_PASSWORD": ecs.Secret.from_secrets_manager(
                        basic_auth_secret, "password"
                    ),
                }
            )

        return secrets

    def _get_or_create_encryption_key(self) -> secretsmanager.ISecret:
        """Get or create n8n encryption key secret."""
        return secretsmanager.Secret(
            self,
            "EncryptionKey",
            secret_name=f"n8n/{self.environment}/encryption-key",
            description=f"n8n encryption key for {self.environment}",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\",
                password_length=32,
            ),
        )

    def _get_or_create_basic_auth_secret(self) -> secretsmanager.ISecret:
        """Get or create basic auth credentials secret."""
        return secretsmanager.Secret(
            self,
            "BasicAuthSecret",
            secret_name=f"n8n/{self.environment}/basic-auth",
            description=f"n8n basic auth credentials for {self.environment}",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "admin"}',
                generate_string_key="password",
                exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\",
                password_length=20,
            ),
        )

    def _create_fargate_service(self) -> ecs.FargateService:
        """Create Fargate service."""
        # Determine capacity provider strategy
        capacity_provider_strategies = []

        if self.fargate_config.spot_percentage > 0:
            # Use spot instances
            capacity_provider_strategies.append(
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT",
                    weight=self.fargate_config.spot_percentage,
                )
            )

            if self.fargate_config.spot_percentage < 100:
                # Use on-demand for remaining capacity
                capacity_provider_strategies.append(
                    ecs.CapacityProviderStrategy(
                        capacity_provider="FARGATE",
                        weight=100 - self.fargate_config.spot_percentage,
                    )
                )
        else:
            # Use only on-demand
            capacity_provider_strategies.append(
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE",
                    weight=100,
                )
            )

        # Create service
        service = ecs.FargateService(
            self,
            "Service",
            cluster=self.cluster,
            task_definition=self.task_definition,
            service_name=f"n8n-{self.environment}",
            vpc_subnets=ec2.SubnetSelection(subnets=self.subnets),
            security_groups=[self.security_group],
            desired_count=self.env_config.settings.scaling.min_tasks
            if self.env_config.settings.scaling
            else 1,
            capacity_provider_strategies=capacity_provider_strategies,
            enable_execute_command=True,  # Enable ECS Exec for debugging
            health_check_grace_period=Duration.seconds(120),
            platform_version=ecs.FargatePlatformVersion.LATEST,
        )

        return service

    def _setup_service_discovery(self) -> None:
        """Set up service discovery for internal communication."""
        # Check if namespace already exists on the cluster
        namespace = None
        if hasattr(self.cluster, "default_cloud_map_namespace"):
            namespace = self.cluster.default_cloud_map_namespace
        else:
            # Create new namespace
            namespace = self.cluster.add_default_cloud_map_namespace(
                name=f"n8n-{self.environment}.local",
                type=servicediscovery.NamespaceType.DNS_PRIVATE,
                vpc=self.vpc,
            )

        # Associate service with service discovery if namespace exists
        if namespace:
            self.service.enable_cloud_map(
                name="n8n",
                dns_record_type=servicediscovery.DnsRecordType.A,
                dns_ttl=Duration.seconds(10),
            )

    def _add_n8n_permissions(self, role: iam.IRole) -> None:
        """Add required IAM permissions for n8n."""
        # S3 permissions for workflow storage/import/export
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                ],
                resources=[
                    f"arn:aws:s3:::n8n-{self.environment}-*/*",
                    f"arn:aws:s3:::n8n-{self.environment}-*",
                ],
            )
        )

        # SES permissions for email sending (if needed)
        if self.env_config.settings.features and self.env_config.settings.features.get(
            "email_enabled"
        ):
            role.add_to_policy(
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ses:SendEmail",
                        "ses:SendRawEmail",
                    ],
                    resources=["*"],
                )
            )

        # SSM Parameter Store (for dynamic configuration)
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                ],
                resources=[
                    f"arn:aws:ssm:{Stack.of(self).region}:{Stack.of(self).account}:parameter/n8n/{self.environment}/*",
                ],
            )
        )
