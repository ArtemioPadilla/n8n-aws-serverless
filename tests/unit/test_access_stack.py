"""Unit tests for AccessStack."""

from unittest.mock import Mock, patch

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template

from n8n_deploy.config.models import (
    AccessConfig,
    EnvironmentConfig,
    EnvironmentSettings,
    GlobalConfig,
    N8nConfig,
)
from n8n_deploy.stacks.access_stack import AccessStack
from n8n_deploy.stacks.compute_stack import ComputeStack
from n8n_deploy.stacks.network_stack import NetworkStack


@pytest.mark.skip(reason="Unit tests require CDK synthesis which needs valid AWS environment")
class TestAccessStack:
    """Test cases for AccessStack."""

    @pytest.fixture
    def app(self):
        """Create CDK app."""
        return App()

    @pytest.fixture
    def test_config_basic(self):
        """Create basic test configuration."""
        return N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        access=AccessConfig(
                            cloudfront_enabled=False,
                            api_gateway_throttle=100,
                            cors_origins=["http://localhost:3000"],
                        )
                    ),
                )
            },
        )

    @pytest.fixture
    def test_config_cloudfront(self):
        """Create test configuration with CloudFront enabled."""
        return N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        access=AccessConfig(
                            cloudfront_enabled=True,
                            waf_enabled=False,
                            api_gateway_throttle=1000,
                            domain_name="n8n.example.com",
                        )
                    ),
                )
            },
        )

    @pytest.fixture
    def test_config_waf(self):
        """Create test configuration with WAF enabled."""
        return N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        access=AccessConfig(
                            cloudfront_enabled=True,
                            waf_enabled=True,
                            ip_whitelist=["1.2.3.4/32", "5.6.7.8/32"],
                        )
                    ),
                )
            },
        )

    @pytest.fixture
    def compute_stack_mock(self, mock_vpc, mock_security_group):
        """Create mock compute stack."""
        stack = Mock(spec=ComputeStack)

        # Mock network stack
        network_stack = Mock(spec=NetworkStack)
        network_stack.vpc = mock_vpc
        network_stack.subnets = [Mock() for _ in range(2)]
        network_stack.n8n_security_group = mock_security_group

        # Mock service
        service = Mock()
        cloud_map_service = Mock()
        cloud_map_service.service_name = "n8n.local"
        service.cloud_map_service = cloud_map_service

        # Mock n8n service
        n8n_service = Mock()
        n8n_service.service = service

        # Set up compute stack attributes
        stack.network_stack = network_stack
        stack.n8n_service = n8n_service
        stack.service_security_group = mock_security_group

        return stack

    @patch.object(AccessStack, "_create_vpc_link")
    @patch.object(AccessStack, "_create_api_gateway")
    @patch.object(AccessStack, "_add_outputs")
    def test_stack_initialization_basic(
        self,
        mock_add_outputs,
        mock_create_api,
        mock_create_vpc_link,
        app,
        test_config_basic,
        compute_stack_mock,
    ):
        """Test access stack initialization with basic configuration."""
        # Mock the VPC link creation
        mock_vpc_link = Mock()
        mock_create_vpc_link.return_value = mock_vpc_link

        # Mock the API gateway creation
        mock_api = Mock()
        mock_create_api.return_value = mock_api

        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_basic,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        assert stack.stack_name == "test-n8n-test-access"
        assert stack.compute_stack == compute_stack_mock
        assert mock_create_vpc_link.called
        assert mock_create_api.called
        assert hasattr(stack, "vpc_link")
        assert hasattr(stack, "api")
        assert not hasattr(stack, "distribution")  # CloudFront disabled

    def test_vpc_link_creation(self, app, test_config_basic, compute_stack_mock):
        """Test VPC link creation for API Gateway."""
        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_basic,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify VPC link
        template.has_resource_properties(
            "AWS::ApiGatewayV2::VpcLink",
            {
                "Name": Match.string_like_regexp("test-n8n-test-vpc-link"),
                "SubnetIds": Match.any_value(),
                "SecurityGroupIds": Match.any_value(),
            },
        )

    def test_api_gateway_creation(self, app, test_config_basic, compute_stack_mock):
        """Test HTTP API Gateway creation."""
        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_basic,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify HTTP API
        template.has_resource_properties(
            "AWS::ApiGatewayV2::Api",
            {
                "Name": Match.string_like_regexp("test-n8n-test-api"),
                "Description": "n8n API for test",
                "ProtocolType": "HTTP",
                "CorsConfiguration": {
                    "AllowOrigins": ["http://localhost:3000"],
                    "AllowMethods": ["*"],
                    "AllowHeaders": ["*"],
                    "MaxAge": 86400,
                },
            },
        )

        # Verify routes
        template.has_resource_properties("AWS::ApiGatewayV2::Route", {"RouteKey": "ANY /{proxy+}"})

        template.has_resource_properties("AWS::ApiGatewayV2::Route", {"RouteKey": "ANY /"})

    def test_security_group_ingress_rule(self, app, test_config_basic, compute_stack_mock):
        """Test that API Gateway can access the compute service."""
        # Create a real security group mock with add_ingress_rule method
        sg_mock = Mock()
        sg_mock.add_ingress_rule = Mock()
        compute_stack_mock.service_security_group = sg_mock

        AccessStack(
            app,
            "TestAccessStack",
            config=test_config_basic,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        # Verify ingress rule was added
        sg_mock.add_ingress_rule.assert_called_once()
        call_args = sg_mock.add_ingress_rule.call_args
        assert call_args[1]["connection"].from_port == 5678
        assert call_args[1]["description"] == "Allow API Gateway to access n8n"

    def test_cloudfront_distribution_creation(self, app, test_config_cloudfront, compute_stack_mock):
        """Test CloudFront distribution creation when enabled."""
        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_cloudfront,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify CloudFront distribution
        template.has_resource_properties(
            "AWS::CloudFront::Distribution",
            {
                "DistributionConfig": {
                    "Enabled": True,
                    "HttpVersion": "http2and3",
                    "IPV6Enabled": True,
                    "PriceClass": "PriceClass_100",  # Development environment
                    "Comment": "n8n distribution for test",
                    "DefaultRootObject": Match.absent(),  # API, not static site
                    "Origins": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "DomainName": Match.string_like_regexp(".*execute-api.*amazonaws.com"),
                                    "CustomOriginConfig": {"OriginProtocolPolicy": "https-only"},
                                }
                            )
                        ]
                    ),
                }
            },
        )

    def test_cloudfront_cache_behaviors(self, app, test_config_cloudfront, compute_stack_mock):
        """Test CloudFront cache behaviors for specific paths."""
        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_cloudfront,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify cache behaviors for webhooks and REST API
        dist_config = template.find_resources("AWS::CloudFront::Distribution")
        assert len(dist_config) == 1

        # Check that there are cache behaviors for /webhook/* and /rest/*
        dist_props = list(dist_config.values())[0]["Properties"]["DistributionConfig"]
        assert "CacheBehaviors" in dist_props

        paths = [behavior["PathPattern"] for behavior in dist_props["CacheBehaviors"]]
        assert "/webhook/*" in paths
        assert "/rest/*" in paths

    def test_waf_web_acl_creation(self, app, test_config_waf, compute_stack_mock):
        """Test WAF web ACL creation when enabled."""
        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_waf,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify IP set for whitelist
        template.has_resource_properties(
            "AWS::WAFv2::IPSet",
            {
                "Name": Match.string_like_regexp("test-n8n-test-ip-whitelist"),
                "Scope": "CLOUDFRONT",
                "IPAddressVersion": "IPV4",
                "Addresses": ["1.2.3.4/32", "5.6.7.8/32"],
            },
        )

        # Verify Web ACL
        template.has_resource_properties(
            "AWS::WAFv2::WebACL",
            {
                "Name": Match.string_like_regexp("test-n8n-test-waf"),
                "Scope": "CLOUDFRONT",
                "DefaultAction": {"Block": {}},  # Block by default with IP whitelist
                "Rules": Match.array_with(
                    [
                        Match.object_like({"Name": "AWSManagedRulesCommonRuleSet", "Priority": 10}),
                        Match.object_like(
                            {
                                "Name": "RateLimitRule",
                                "Priority": 20,
                                "Statement": {
                                    "RateBasedStatement": {
                                        "Limit": 2000,
                                        "AggregateKeyType": "IP",
                                    }
                                },
                            }
                        ),
                    ]
                ),
            },
        )

    def test_custom_domain_setup(self, app, test_config_cloudfront, compute_stack_mock):
        """Test custom domain setup with Route53."""
        # Mock shared resources
        with patch.object(AccessStack, "get_shared_resource") as mock_shared:
            mock_shared.side_effect = lambda category, key: {
                ("security", "certificate_arn"): None,
                ("networking", "route53_zone_id"): "Z1234567890ABC",
            }.get((category, key))

            stack = AccessStack(
                app,
                "TestAccessStack",
                config=test_config_cloudfront,
                environment="test",
                compute_stack=compute_stack_mock,
                env=Environment(account="123456789012", region="us-east-1"),
            )

            template = Template.from_stack(stack)

            # Verify Route53 record
            template.has_resource_properties(
                "AWS::Route53::RecordSet",
                {
                    "Name": "n8n.example.com.",
                    "Type": "A",
                    "AliasTarget": Match.object_like(
                        {
                            "DNSName": Match.any_value(),
                            "HostedZoneId": Match.any_value(),
                        }
                    ),
                },
            )

    def test_stack_outputs(self, app, test_config_cloudfront, compute_stack_mock):
        """Test stack outputs are created correctly."""
        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_cloudfront,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify outputs
        outputs = template.find_outputs("*")
        output_keys = set(outputs.keys())

        expected_outputs = {
            "ApiUrl",
            "ApiId",
            "DistributionUrl",
            "DistributionId",
            "CustomDomainUrl",
        }

        for output in expected_outputs:
            assert any(output in key for key in output_keys), f"Missing output: {output}"

    def test_no_cloudfront_when_disabled(self, app, test_config_basic, compute_stack_mock):
        """Test that CloudFront is not created when disabled."""
        stack = AccessStack(
            app,
            "TestAccessStack",
            config=test_config_basic,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify no CloudFront resources
        template.resource_count_is("AWS::CloudFront::Distribution", 0)
        template.resource_count_is("AWS::WAFv2::WebACL", 0)

    def test_production_cloudfront_settings(self, app, compute_stack_mock):
        """Test production-specific CloudFront settings."""
        config = N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "production": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        access=AccessConfig(cloudfront_enabled=True, api_gateway_throttle=10000)
                    ),
                )
            },
        )

        stack = AccessStack(
            app,
            "TestAccessStack",
            config=config,
            environment="production",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify production price class
        template.has_resource_properties(
            "AWS::CloudFront::Distribution",
            {"DistributionConfig": {"PriceClass": "PriceClass_All"}},  # All edge locations for production
        )

    def test_cors_configuration(self, app, compute_stack_mock):
        """Test CORS configuration options."""
        config = N8nConfig(
            global_config=GlobalConfig(project_name="test-n8n", organization="test-org"),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        access=AccessConfig(
                            cors_origins=[
                                "https://app.example.com",
                                "https://dashboard.example.com",
                            ]
                        )
                    ),
                )
            },
        )

        stack = AccessStack(
            app,
            "TestAccessStack",
            config=config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1"),
        )

        template = Template.from_stack(stack)

        # Verify CORS configuration
        template.has_resource_properties(
            "AWS::ApiGatewayV2::Api",
            {
                "CorsConfiguration": {
                    "AllowOrigins": [
                        "https://app.example.com",
                        "https://dashboard.example.com",
                    ]
                }
            },
        )

    def test_certificate_import(self, app, test_config_cloudfront, compute_stack_mock):
        """Test certificate import from shared resources."""
        with patch.object(AccessStack, "get_shared_resource") as mock_shared:
            mock_shared.return_value = (
                "arn:aws:acm:us-east-1:123456789012:certificate/" "12345678-1234-1234-1234-123456789012"
            )

            with patch("n8n_deploy.stacks.access_stack.acm.Certificate.from_certificate_arn") as mock_cert:
                mock_cert_instance = Mock()
                mock_cert.return_value = mock_cert_instance

                stack = AccessStack(
                    app,
                    "TestAccessStack",
                    config=test_config_cloudfront,
                    environment="test",
                    compute_stack=compute_stack_mock,
                    env=Environment(account="123456789012", region="us-east-1"),
                )

                # Verify certificate was imported
                mock_cert.assert_called_once()
                assert stack._get_or_create_certificate() is not None
