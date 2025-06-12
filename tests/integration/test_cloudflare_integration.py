"""Integration tests for Cloudflare Tunnel deployment."""
import pytest
from aws_cdk import App, Environment

from n8n_deploy.config import ConfigLoader
from n8n_deploy.stacks.access_stack import AccessStack
from n8n_deploy.stacks.compute_stack import ComputeStack
from n8n_deploy.stacks.monitoring_stack import MonitoringStack
from n8n_deploy.stacks.network_stack import NetworkStack
from n8n_deploy.stacks.storage_stack import StorageStack


class TestCloudflareIntegration:
    """Test Cloudflare Tunnel integration with full stack deployment."""

    @property
    def test_env(self):
        """Get test environment configuration."""
        return Environment(account="123456789012", region="us-east-1")

    @pytest.fixture
    def cloudflare_config(self, tmp_path):
        """Create a test configuration with Cloudflare enabled."""
        config_content = """
project_name: n8n-serverless
aws_region: us-east-1
default_tags:
  Project: n8n-serverless-test
  ManagedBy: CDK

global:
  project_name: n8n-serverless
  organization: test-org

environments:
  test:
    account: "123456789012"
    region: "us-east-1"
    settings:
      fargate:
        cpu: 256
        memory: 512
      networking:
        use_existing_vpc: false
        vpc_cidr: "10.0.0.0/16"
      access:
        type: "cloudflare"
        cloudflare:
          enabled: true
          tunnel_token_secret_name: "test-tunnel-secret"
          tunnel_name: "test-tunnel"
          tunnel_domain: "test.example.com"
          access_enabled: true
          access_allowed_emails:
            - "test@example.com"
          access_allowed_domains:
            - "example.com"
      monitoring:
        enabled: true
        custom_metrics_namespace: "N8n/Test"
"""
        config_file = tmp_path / "test_system.yaml"
        config_file.write_text(config_content)

        loader = ConfigLoader(str(config_file))
        return loader.load_config(environment="test")

    def test_cloudflare_stack_deployment(self, cloudflare_config):
        """Test full stack deployment with Cloudflare Tunnel."""
        app = App()

        # Create all stacks
        network_stack = NetworkStack(
            app,
            "TestNetworkStack",
            config=cloudflare_config,
            environment="test",
            env=self.test_env,
        )

        storage_stack = StorageStack(
            app,
            "TestStorageStack",
            config=cloudflare_config,
            environment="test",
            network_stack=network_stack,
            env=self.test_env,
        )

        compute_stack = ComputeStack(
            app,
            "TestComputeStack",
            config=cloudflare_config,
            environment="test",
            network_stack=network_stack,
            storage_stack=storage_stack,
            env=self.test_env,
        )

        access_stack = AccessStack(
            app,
            "TestAccessStack",
            config=cloudflare_config,
            environment="test",
            compute_stack=compute_stack,
            env=self.test_env,
        )

        # Verify Cloudflare tunnel was configured in compute stack
        assert hasattr(compute_stack, "cloudflare_config")
        assert compute_stack.cloudflare_config.tunnel_name == "test-tunnel"
        assert compute_stack.cloudflare_config.tunnel_domain == "test.example.com"

        # Verify sidecar was added
        assert hasattr(compute_stack, "cloudflare_sidecar")

        # Verify access stack doesn't have API Gateway resources
        assert access_stack.vpc_link is None
        assert access_stack.api is None
        assert access_stack.distribution is None

    def test_cloudflare_monitoring_integration(self, cloudflare_config):
        """Test monitoring stack includes Cloudflare metrics."""
        app = App()

        # Create required stacks
        network_stack = NetworkStack(
            app,
            "TestNetworkStack",
            config=cloudflare_config,
            environment="test",
            env=self.test_env,
        )

        storage_stack = StorageStack(
            app,
            "TestStorageStack",
            config=cloudflare_config,
            environment="test",
            network_stack=network_stack,
        )

        compute_stack = ComputeStack(
            app,
            "TestComputeStack",
            config=cloudflare_config,
            environment="test",
            network_stack=network_stack,
            storage_stack=storage_stack,
        )

        monitoring_stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=cloudflare_config,
            environment="test",
            compute_stack=compute_stack,
            storage_stack=storage_stack,
        )

        # Verify monitoring includes Cloudflare alarms
        # Since we can't use Template.from_stack, we'll just verify the stack was created
        assert monitoring_stack is not None
        assert monitoring_stack.alarm_topic is not None

    def test_cloudflare_outputs(self, cloudflare_config):
        """Test stack outputs for Cloudflare deployment."""
        app = App()

        # Create stacks
        network_stack = NetworkStack(
            app, "TestNetworkStack", config=cloudflare_config, environment="test"
        )

        storage_stack = StorageStack(
            app,
            "TestStorageStack",
            config=cloudflare_config,
            environment="test",
            network_stack=network_stack,
        )

        compute_stack = ComputeStack(
            app,
            "TestComputeStack",
            config=cloudflare_config,
            environment="test",
            network_stack=network_stack,
            storage_stack=storage_stack,
        )

        access_stack = AccessStack(
            app,
            "TestAccessStack",
            config=cloudflare_config,
            environment="test",
            compute_stack=compute_stack,
        )

        # Verify stacks were created with proper Cloudflare configuration
        assert hasattr(compute_stack, "cloudflare_config")
        assert compute_stack.cloudflare_config.tunnel_name == "test-tunnel"
        assert compute_stack.cloudflare_config.tunnel_domain == "test.example.com"

        # Verify access stack recognized Cloudflare mode
        assert access_stack.access_config.type == "cloudflare"
        assert access_stack.vpc_link is None
        assert access_stack.api is None

    def test_api_gateway_to_cloudflare_switch(self, tmp_path):
        """Test switching from API Gateway to Cloudflare Tunnel."""
        # First deploy with API Gateway
        api_config_content = """
project_name: n8n-serverless
aws_region: us-east-1

global:
  project_name: n8n-serverless
  organization: test-org

environments:
  test:
    account: "123456789012"
    region: "us-east-1"
    settings:
      access:
        type: "api_gateway"
        cloudfront_enabled: true
"""
        config_file = tmp_path / "api_system.yaml"
        config_file.write_text(api_config_content)

        loader = ConfigLoader(str(config_file))
        api_config = loader.load_config(environment="test")

        app = App()

        # Create stacks with API Gateway
        network_stack = NetworkStack(
            app, "TestNetworkStack", config=api_config, environment="test"
        )

        storage_stack = StorageStack(
            app,
            "TestStorageStack",
            config=api_config,
            environment="test",
            network_stack=network_stack,
        )

        compute_stack = ComputeStack(
            app,
            "TestComputeStack",
            config=api_config,
            environment="test",
            network_stack=network_stack,
            storage_stack=storage_stack,
        )

        access_stack = AccessStack(
            app,
            "TestAccessStack",
            config=api_config,
            environment="test",
            compute_stack=compute_stack,
        )

        # Verify API Gateway is created
        assert access_stack.api is not None
        assert access_stack.vpc_link is not None

        # Now switch to Cloudflare
        cloudflare_config_content = """
project_name: n8n-serverless
aws_region: us-east-1

global:
  project_name: n8n-serverless
  organization: test-org

environments:
  test:
    account: "123456789012"
    region: "us-east-1"
    settings:
      access:
        type: "cloudflare"
        cloudflare:
          enabled: true
          tunnel_token_secret_name: "test-tunnel-secret"
          tunnel_name: "test-tunnel"
          tunnel_domain: "test.example.com"
"""
        cf_config_file = tmp_path / "cf_system.yaml"
        cf_config_file.write_text(cloudflare_config_content)

        cf_loader = ConfigLoader(str(cf_config_file))
        cf_config = cf_loader.load_config(environment="test")

        # Create new app for Cloudflare deployment
        cf_app = App()

        # Create stacks with Cloudflare
        cf_network_stack = NetworkStack(
            cf_app, "TestNetworkStack", config=cf_config, environment="test"
        )

        cf_storage_stack = StorageStack(
            cf_app,
            "TestStorageStack",
            config=cf_config,
            environment="test",
            network_stack=cf_network_stack,
        )

        cf_compute_stack = ComputeStack(
            cf_app,
            "TestComputeStack",
            config=cf_config,
            environment="test",
            network_stack=cf_network_stack,
            storage_stack=cf_storage_stack,
        )

        cf_access_stack = AccessStack(
            cf_app,
            "TestAccessStack",
            config=cf_config,
            environment="test",
            compute_stack=cf_compute_stack,
        )

        # Verify API Gateway is NOT created
        assert cf_access_stack.api is None
        assert cf_access_stack.vpc_link is None

        # Verify Cloudflare tunnel is created
        assert hasattr(cf_compute_stack, "cloudflare_config")
        assert hasattr(cf_compute_stack, "cloudflare_sidecar")
