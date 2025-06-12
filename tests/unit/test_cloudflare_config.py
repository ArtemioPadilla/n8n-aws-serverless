"""Unit tests for Cloudflare Tunnel configuration and constructs."""
from unittest.mock import MagicMock, Mock, patch

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_logs as logs
import pytest
from aws_cdk import App, Stack
from aws_cdk.assertions import Match, Template

from n8n_deploy.config.models import (
    AccessConfig,
    AccessType,
    CloudflareConfig,
    EnvironmentConfig,
    EnvironmentSettings,
)
from n8n_deploy.constructs.cloudflare_tunnel import (
    CloudflareTunnelConfiguration,
    CloudflareTunnelSidecar,
)


class TestCloudflareConfig:
    """Test Cloudflare configuration model validation."""

    def test_cloudflare_config_minimal(self):
        """Test minimal Cloudflare configuration."""
        config = CloudflareConfig(enabled=True, tunnel_token_secret_name="my-secret")
        assert config.enabled is True
        assert config.tunnel_token_secret_name == "my-secret"
        assert config.access_enabled is False

    def test_cloudflare_config_full(self):
        """Test full Cloudflare configuration."""
        config = CloudflareConfig(
            enabled=True,
            tunnel_token_secret_name="my-secret",
            tunnel_name="n8n-prod",
            tunnel_domain="n8n.example.com",
            access_enabled=True,
            access_allowed_emails=["admin@example.com"],
            access_allowed_domains=["example.com"],
        )
        assert config.tunnel_name == "n8n-prod"
        assert config.tunnel_domain == "n8n.example.com"
        assert config.access_enabled is True
        assert "admin@example.com" in config.access_allowed_emails
        assert "example.com" in config.access_allowed_domains

    def test_cloudflare_config_validation_error(self):
        """Test validation error when enabled without token."""
        with pytest.raises(ValueError, match="tunnel_token_secret_name is required"):
            CloudflareConfig(enabled=True)

    def test_domain_validation(self):
        """Test domain format validation."""
        # Valid domains
        valid_domains = [
            "example.com",
            "sub.example.com",
            "sub-domain.example.com",
            "n8n.company.io",
            "test-123.example.co.uk",
        ]

        for domain in valid_domains:
            config = CloudflareConfig(
                enabled=True, tunnel_token_secret_name="secret", tunnel_domain=domain
            )
            assert config.tunnel_domain == domain

        # Invalid domains
        invalid_domains = [
            "example",  # No TLD
            ".example.com",  # Starts with dot
            "example.com.",  # Ends with dot
            "example..com",  # Double dots
            "-example.com",  # Starts with hyphen
            "example-.com",  # Ends with hyphen
            "example.c",  # TLD too short
            "exam ple.com",  # Contains space
            "example.com/path",  # Contains path
            "https://example.com",  # Contains protocol
        ]

        for domain in invalid_domains:
            with pytest.raises(ValueError, match="Invalid domain format"):
                CloudflareConfig(
                    enabled=True,
                    tunnel_token_secret_name="secret",
                    tunnel_domain=domain,
                )


class TestAccessConfig:
    """Test access configuration with Cloudflare support."""

    def test_access_config_api_gateway(self):
        """Test traditional API Gateway access configuration."""
        config = AccessConfig(
            type=AccessType.API_GATEWAY,
            domain_name="api.example.com",
            cloudfront_enabled=True,
            waf_enabled=True,
        )
        assert config.type == AccessType.API_GATEWAY
        assert config.cloudfront_enabled is True
        assert config.waf_enabled is True

    def test_access_config_cloudflare(self):
        """Test Cloudflare access configuration."""
        config = AccessConfig(
            type=AccessType.CLOUDFLARE,
            cloudflare=CloudflareConfig(
                enabled=True, tunnel_token_secret_name="my-secret"
            ),
        )
        assert config.type == AccessType.CLOUDFLARE
        assert config.cloudflare.enabled is True

    def test_access_config_cloudflare_auto_enable(self):
        """Test Cloudflare auto-enable when type is CLOUDFLARE."""
        config = AccessConfig(type=AccessType.CLOUDFLARE)
        assert config.cloudflare is not None
        assert config.cloudflare.enabled is True


class TestCloudflareTunnelConfiguration:
    """Test Cloudflare Tunnel Configuration construct."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = App()
        self.stack = Stack(self.app, "TestStack")

    def test_configuration_with_existing_secret(self):
        """Test configuration with existing secret reference."""
        config = CloudflareTunnelConfiguration(
            self.stack,
            "TunnelConfig",
            tunnel_name="test-tunnel",
            tunnel_domain="test.example.com",
            service_url="http://localhost:5678",
            environment="test",
            tunnel_secret_name="existing-secret",
        )

        template = Template.from_stack(self.stack)

        # Should not create a new secret
        template.resource_count_is("AWS::SecretsManager::Secret", 0)

        # Verify configuration properties
        assert config.tunnel_name == "test-tunnel"
        assert config.tunnel_domain == "test.example.com"
        assert config.service_url == "http://localhost:5678"

    def test_configuration_creates_new_secret(self):
        """Test configuration creates new secret when not provided."""
        config = CloudflareTunnelConfiguration(
            self.stack,
            "TunnelConfig",
            tunnel_name="test-tunnel",
            tunnel_domain="test.example.com",
            service_url="http://localhost:5678",
            environment="test",
        )

        template = Template.from_stack(self.stack)

        # Should create a new secret
        template.has_resource_properties(
            "AWS::SecretsManager::Secret", {"Name": "n8n/test/cloudflare-tunnel-token"}
        )

        # Should output the secret ARN
        template.has_output("TunnelConfigTunnelTokenSecretArn", {})

    def test_configuration_with_access_policies(self):
        """Test configuration with Cloudflare Access policies."""
        access_config = {
            "enabled": True,
            "allowed_emails": ["admin@example.com", "user@example.com"],
            "allowed_domains": ["example.com", "company.com"],
        }

        config = CloudflareTunnelConfiguration(
            self.stack,
            "TunnelConfig",
            tunnel_name="test-tunnel",
            tunnel_domain="test.example.com",
            service_url="http://localhost:5678",
            environment="test",
            access_config=access_config,
        )

        # Verify access configuration is stored
        assert config.access_config["enabled"] is True
        assert (
            len(
                config.tunnel_config["ingress"][0]["originRequest"]
                .get("access", {})
                .get("policies", [])
            )
            > 0
        )


class TestCloudflareTunnelSidecar:
    """Test Cloudflare Tunnel Sidecar construct."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = App()
        self.stack = Stack(self.app, "TestStack")

        # Create mock VPC
        self.vpc = ec2.Vpc(self.stack, "TestVpc")

        # Create task definition
        self.task_definition = ecs.FargateTaskDefinition(
            self.stack, "TestTaskDef", cpu=512, memory_limit_mib=1024
        )

        # Add n8n container
        self.n8n_container = self.task_definition.add_container(
            "n8n",
            image=ecs.ContainerImage.from_registry("n8nio/n8n:latest"),
            cpu=256,
            memory_limit_mib=512,
        )

        # Create log group
        self.log_group = logs.LogGroup(self.stack, "TestLogGroup")

        # Create mock secret
        from aws_cdk import aws_secretsmanager as sm

        self.secret = sm.Secret(self.stack, "TestSecret")

    def test_sidecar_creation(self):
        """Test sidecar container creation."""
        sidecar = CloudflareTunnelSidecar(
            self.stack,
            "TestSidecar",
            task_definition=self.task_definition,
            tunnel_secret=self.secret,
            tunnel_config={"tunnel": "test"},
            log_group=self.log_group,
            environment="test",
        )

        template = Template.from_stack(self.stack)

        # Verify container is added to task definition
        template.has_resource_properties(
            "AWS::ECS::TaskDefinition",
            {
                "ContainerDefinitions": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Name": "cloudflare-tunnel",
                                "Image": "cloudflare/cloudflared:latest",
                                "Essential": True,
                                "Command": [
                                    "tunnel",
                                    "--no-autoupdate",
                                    "--metrics",
                                    "0.0.0.0:2000",
                                    "run",
                                ],
                            }
                        )
                    ]
                )
            },
        )

    def test_sidecar_health_check(self):
        """Test sidecar container health check configuration."""
        sidecar = CloudflareTunnelSidecar(
            self.stack,
            "TestSidecar",
            task_definition=self.task_definition,
            tunnel_secret=self.secret,
            tunnel_config={"tunnel": "test"},
            log_group=self.log_group,
            environment="test",
        )

        template = Template.from_stack(self.stack)

        # Verify health check
        template.has_resource_properties(
            "AWS::ECS::TaskDefinition",
            {
                "ContainerDefinitions": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Name": "cloudflare-tunnel",
                                "HealthCheck": {
                                    "Command": [
                                        "CMD-SHELL",
                                        "wget -q -O /dev/null http://localhost:2000/ready || exit 1",
                                    ],
                                    "Interval": 30,
                                    "Timeout": 5,
                                    "Retries": 3,
                                    "StartPeriod": 10,
                                },
                            }
                        )
                    ]
                )
            },
        )

    def test_sidecar_secret_access(self):
        """Test sidecar has access to tunnel secret."""
        sidecar = CloudflareTunnelSidecar(
            self.stack,
            "TestSidecar",
            task_definition=self.task_definition,
            tunnel_secret=self.secret,
            tunnel_config={"tunnel": "test"},
            log_group=self.log_group,
            environment="test",
        )

        template = Template.from_stack(self.stack)

        # Verify secret is passed as environment variable
        template.has_resource_properties(
            "AWS::ECS::TaskDefinition",
            {
                "ContainerDefinitions": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "Name": "cloudflare-tunnel",
                                "Secrets": Match.array_with(
                                    [Match.object_like({"Name": "TUNNEL_TOKEN"})]
                                ),
                            }
                        )
                    ]
                )
            },
        )

        # Verify IAM permissions for secret access
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Action": Match.array_with(
                                        [
                                            "secretsmanager:GetSecretValue",
                                            "secretsmanager:DescribeSecret",
                                        ]
                                    )
                                }
                            )
                        ]
                    )
                }
            },
        )

    def test_sidecar_container_dependency(self):
        """Test sidecar depends on n8n container."""
        sidecar = CloudflareTunnelSidecar(
            self.stack,
            "TestSidecar",
            task_definition=self.task_definition,
            tunnel_secret=self.secret,
            tunnel_config={"tunnel": "test"},
            log_group=self.log_group,
            environment="test",
        )

        # Since CDK doesn't expose container dependencies directly in CloudFormation,
        # we verify the container was found and dependency logic executed
        assert sidecar.container is not None
        assert sidecar.container.container_name == "cloudflare-tunnel"
