"""Unit tests for network stack."""
import pytest
from unittest.mock import MagicMock, patch
from aws_cdk import App
from aws_cdk.assertions import Template, Match

from n8n_aws_serverless.stacks.network_stack import NetworkStack
from n8n_aws_serverless.config.models import NetworkingConfig


class TestNetworkStack:
    """Test network stack functionality."""
    
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.Vpc')
    def test_create_new_vpc(self, mock_vpc_class, mock_app, test_config):
        """Test creating a new VPC."""
        # Configure test
        test_config.environments["test"].settings.networking = NetworkingConfig(
            use_existing_vpc=False,
            vpc_cidr="10.0.0.0/16",
            nat_gateways=0
        )
        
        # Create mock VPC
        mock_vpc = MagicMock()
        mock_vpc.vpc_id = "vpc-new123"
        mock_vpc.public_subnets = [
            MagicMock(subnet_id="subnet-pub1"),
            MagicMock(subnet_id="subnet-pub2")
        ]
        mock_vpc.private_subnets = []
        mock_vpc_class.return_value = mock_vpc
        
        # Create stack
        stack = NetworkStack(
            mock_app,
            "network-stack",
            config=test_config,
            environment="test"
        )
        
        # Verify VPC was created with correct parameters
        mock_vpc_class.assert_called_once()
        call_kwargs = mock_vpc_class.call_args[1]
        assert call_kwargs['vpc_name'] == "test-n8n-test-vpc"
        assert call_kwargs['nat_gateways'] == 0
        assert call_kwargs['enable_dns_hostnames'] is True
        assert call_kwargs['enable_dns_support'] is True
    
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.Vpc.from_lookup')
    def test_import_existing_vpc(self, mock_vpc_lookup, mock_app, test_config):
        """Test importing an existing VPC."""
        # Configure test
        test_config.environments["test"].settings.networking = NetworkingConfig(
            use_existing_vpc=True,
            vpc_id="vpc-existing123",
            subnet_ids=["subnet-1", "subnet-2"]
        )
        
        # Create mock VPC
        mock_vpc = MagicMock()
        mock_vpc.vpc_id = "vpc-existing123"
        mock_vpc_lookup.return_value = mock_vpc
        
        # Create stack
        stack = NetworkStack(
            mock_app,
            "network-stack",
            config=test_config,
            environment="test"
        )
        
        # Verify VPC was imported
        mock_vpc_lookup.assert_called_once_with(
            stack,
            "ImportedVpc",
            vpc_id="vpc-existing123"
        )
        assert stack.vpc == mock_vpc
    
    def test_vpc_id_required_for_import(self, mock_app, test_config):
        """Test that vpc_id is required when importing VPC."""
        # Configure test without vpc_id
        test_config.environments["test"].settings.networking = NetworkingConfig(
            use_existing_vpc=True,
            vpc_id=None
        )
        
        # Should raise error
        with pytest.raises(ValueError, match="vpc_id is required"):
            NetworkStack(
                mock_app,
                "network-stack",
                config=test_config,
                environment="test"
            )
    
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.SecurityGroup')
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.Vpc')
    def test_security_group_creation(self, mock_vpc_class, mock_sg_class, mock_app, test_config):
        """Test security group creation."""
        # Setup mocks
        mock_vpc = MagicMock()
        mock_vpc.public_subnets = [MagicMock()]
        mock_vpc_class.return_value = mock_vpc
        
        mock_n8n_sg = MagicMock()
        mock_efs_sg = MagicMock()
        mock_sg_class.side_effect = [mock_n8n_sg, mock_efs_sg]
        
        # Create stack
        stack = NetworkStack(
            mock_app,
            "network-stack",
            config=test_config,
            environment="test"
        )
        
        # Verify security groups were created
        assert mock_sg_class.call_count == 2
        
        # Check n8n security group
        n8n_sg_call = mock_sg_class.call_args_list[0]
        assert n8n_sg_call[1]['security_group_name'] == "test-n8n-test-sg-n8n"
        assert n8n_sg_call[1]['description'] == "Security group for n8n Fargate tasks"
        assert n8n_sg_call[1]['allow_all_outbound'] is True
        
        # Check EFS security group
        efs_sg_call = mock_sg_class.call_args_list[1]
        assert efs_sg_call[1]['security_group_name'] == "test-n8n-test-sg-efs"
        assert efs_sg_call[1]['description'] == "Security group for EFS mount targets"
        assert efs_sg_call[1]['allow_all_outbound'] is False
    
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.Vpc')
    def test_max_azs_based_on_environment(self, mock_vpc_class, mock_app, test_config):
        """Test that max AZs is set based on environment."""
        # Test production environment
        test_config.environments["production"] = test_config.environments["test"]
        
        stack_prod = NetworkStack(
            mock_app,
            "network-stack-prod",
            config=test_config,
            environment="production"
        )
        
        prod_vpc_call = mock_vpc_class.call_args_list[-1]
        assert prod_vpc_call[1]['max_azs'] == 3
        
        # Test staging environment
        test_config.environments["staging"] = test_config.environments["test"]
        
        stack_staging = NetworkStack(
            mock_app,
            "network-stack-staging",
            config=test_config,
            environment="staging"
        )
        
        staging_vpc_call = mock_vpc_class.call_args_list[-1]
        assert staging_vpc_call[1]['max_azs'] == 2
        
        # Test dev environment
        test_config.environments["dev"] = test_config.environments["test"]
        
        stack_dev = NetworkStack(
            mock_app,
            "network-stack-dev",
            config=test_config,
            environment="dev"
        )
        
        dev_vpc_call = mock_vpc_class.call_args_list[-1]
        assert dev_vpc_call[1]['max_azs'] == 1
    
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.Vpc')
    def test_nat_gateway_configuration(self, mock_vpc_class, mock_app, test_config):
        """Test NAT gateway configuration."""
        # Test with NAT gateways
        test_config.environments["test"].settings.networking.nat_gateways = 2
        
        stack = NetworkStack(
            mock_app,
            "network-stack",
            config=test_config,
            environment="test"
        )
        
        vpc_call = mock_vpc_class.call_args_list[-1]
        assert vpc_call[1]['nat_gateways'] == 2
        
        # Verify subnet configuration includes private subnets
        subnet_config = vpc_call[1]['subnet_configuration']
        assert len(subnet_config) == 2  # Public and Private
        assert any(sc['name'] == 'Private' for sc in subnet_config)
    
    @patch('n8n_aws_serverless.stacks.network_stack.CfnOutput')
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.SecurityGroup')
    @patch('n8n_aws_serverless.stacks.network_stack.ec2.Vpc')
    def test_stack_outputs(self, mock_vpc_class, mock_sg_class, mock_output_class, mock_app, test_config):
        """Test that stack outputs are created correctly."""
        # Setup mocks
        mock_vpc = MagicMock()
        mock_vpc.vpc_id = "vpc-123"
        mock_vpc.public_subnets = [
            MagicMock(subnet_id="subnet-1", availability_zone="us-east-1a"),
            MagicMock(subnet_id="subnet-2", availability_zone="us-east-1b")
        ]
        mock_vpc_class.return_value = mock_vpc
        
        mock_sg = MagicMock()
        mock_sg.security_group_id = "sg-123"
        mock_sg_class.return_value = mock_sg
        
        # Create stack
        stack = NetworkStack(
            mock_app,
            "network-stack",
            config=test_config,
            environment="test"
        )
        
        # Verify outputs were created
        output_calls = mock_output_class.call_args_list
        output_names = [call[1]['value'] for call in output_calls if 'value' in call[1]]
        
        # Check VPC output
        assert any("vpc-123" in str(val) for val in output_names)
        # Check security group outputs
        assert any("sg-123" in str(val) for val in output_names)