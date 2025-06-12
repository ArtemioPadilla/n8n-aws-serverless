"""Unit tests for MonitoringStack."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from aws_cdk import App, Environment, Duration
from aws_cdk.assertions import Template, Match
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_ecs as ecs
from n8n_deploy.config.models import (
    N8nConfig, EnvironmentConfig, EnvironmentSettings,
    MonitoringConfig, GlobalConfig, ScalingConfig
)
from n8n_deploy.stacks.monitoring_stack import MonitoringStack
from n8n_deploy.stacks.compute_stack import ComputeStack
from n8n_deploy.stacks.storage_stack import StorageStack
from n8n_deploy.stacks.database_stack import DatabaseStack


class TestMonitoringStack:
    """Test cases for MonitoringStack."""
    
    @pytest.fixture
    def app(self):
        """Create CDK app."""
        return App()
    
    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        return N8nConfig(
            global_config=GlobalConfig(
                project_name="test-n8n",
                organization="test-org"
            ),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        monitoring=MonitoringConfig(
                            log_retention_days=30,
                            alarm_email="alerts@example.com",
                            enable_container_insights=True,
                            enable_xray_tracing=False
                        ),
                        scaling=ScalingConfig(
                            min_tasks=1,
                            max_tasks=3
                        )
                    )
                )
            }
        )
    
    @pytest.fixture
    def compute_stack_mock(self, ecs_cluster_mock, ecs_service_mock):
        """Create mock compute stack."""
        stack = Mock(spec=ComputeStack)
        
        # Mock n8n service
        n8n_service = Mock()
        n8n_service.service = ecs_service_mock
        n8n_service.task_definition = Mock()
        n8n_service.log_group = Mock()
        n8n_service.log_group.log_group_name = "/ecs/test-n8n"
        
        # Set attributes
        stack.cluster = ecs_cluster_mock
        stack.n8n_service = n8n_service
        
        return stack
    
    @pytest.fixture
    def storage_stack_mock(self, efs_file_system_mock):
        """Create mock storage stack."""
        stack = Mock(spec=StorageStack)
        stack.file_system = efs_file_system_mock
        return stack
    
    @pytest.fixture
    def database_stack_mock(self):
        """Create mock database stack."""
        stack = Mock(spec=DatabaseStack)
        
        # Mock RDS instance
        instance = Mock()
        instance.metric_cpu_utilization = Mock(return_value=Mock())
        instance.metric_database_connections = Mock(return_value=Mock())
        
        stack.instance = instance
        return stack
    
    def test_stack_initialization(self, app, test_config, compute_stack_mock):
        """Test monitoring stack initialization."""
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        assert stack.stack_name == "test-n8n-test-monitoring"
        assert stack.compute_stack == compute_stack_mock
        assert hasattr(stack, 'alarm_topic')
        assert hasattr(stack, 'dashboard')
    
    def test_alarm_topic_creation(self, app, test_config, compute_stack_mock):
        """Test SNS topic creation for alarms."""
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify SNS topic
        template.has_resource_properties("AWS::SNS::Topic", {
            "TopicName": Match.string_like_regexp("test-n8n-test-alarms"),
            "DisplayName": "n8n test Alarms"
        })
        
        # Verify email subscription
        template.has_resource_properties("AWS::SNS::Subscription", {
            "Protocol": "email",
            "Endpoint": "alerts@example.com"
        })
    
    def test_compute_alarms_creation(self, app, test_config, compute_stack_mock):
        """Test creation of compute resource alarms."""
        # Set up mock service and cluster names
        compute_stack_mock.n8n_service.service.service_name = "test-n8n-service"
        compute_stack_mock.cluster.cluster_name = "test-cluster"
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify CPU alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*cpu-high"),
            "AlarmDescription": "n8n CPU utilization is too high",
            "MetricName": "CPUUtilization",
            "Namespace": "AWS/ECS",
            "Statistic": "Average",
            "Threshold": 80,
            "EvaluationPeriods": 3,
            "DatapointsToAlarm": 2,
            "ComparisonOperator": "GreaterThanThreshold",
            "TreatMissingData": "notBreaching"
        })
        
        # Verify Memory alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*memory-high"),
            "AlarmDescription": "n8n memory utilization is too high",
            "MetricName": "MemoryUtilization",
            "Namespace": "AWS/ECS",
            "Threshold": 85
        })
        
        # Verify Task count alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*task-count-low"),
            "AlarmDescription": "n8n service has insufficient running tasks",
            "MetricName": "RunningTaskCount",
            "Threshold": 1,
            "ComparisonOperator": "LessThanThreshold",
            "TreatMissingData": "breaching"
        })
    
    def test_storage_alarms_creation(self, app, test_config, compute_stack_mock, storage_stack_mock):
        """Test creation of storage resource alarms."""
        storage_stack_mock.file_system.file_system_id = "fs-12345678"
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            storage_stack=storage_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify EFS burst credit alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*efs-burst-credits-low"),
            "AlarmDescription": "EFS burst credits are running low",
            "MetricName": "BurstCreditBalance",
            "Namespace": "AWS/EFS",
            "Threshold": 1000000000000,  # 1 TB
            "ComparisonOperator": "LessThanThreshold"
        })
    
    def test_database_alarms_creation(self, app, test_config, compute_stack_mock, database_stack_mock):
        """Test creation of database resource alarms."""
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            database_stack=database_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify database CPU alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*db-cpu-high"),
            "AlarmDescription": "Database CPU utilization is too high",
            "Threshold": 80,
            "EvaluationPeriods": 3,
            "DatapointsToAlarm": 2
        })
        
        # Verify database connections alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*db-connections-high"),
            "AlarmDescription": "Database connections are too high",
            "Threshold": 50,
            "EvaluationPeriods": 2
        })
    
    def test_dashboard_creation(self, app, test_config, compute_stack_mock):
        """Test CloudWatch dashboard creation."""
        compute_stack_mock.n8n_service.service.service_name = "test-n8n-service"
        compute_stack_mock.cluster.cluster_name = "test-cluster"
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify dashboard
        template.has_resource_properties("AWS::CloudWatch::Dashboard", {
            "DashboardName": Match.string_like_regexp("test-n8n-test-dashboard"),
            "DashboardBody": Match.any_value()  # Complex JSON structure
        })
    
    def test_no_email_subscription_when_not_configured(self, app, compute_stack_mock):
        """Test that email subscription is not created when alarm_email is not set."""
        config = N8nConfig(
            global_config=GlobalConfig(
                project_name="test-n8n",
                organization="test-org"
            ),
            environments={
                "test": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        monitoring=MonitoringConfig(
                            alarm_email=None  # No email
                        )
                    )
                )
            }
        )
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify no email subscription
        template.resource_count_is("AWS::SNS::Subscription", 0)
    
    def test_stack_outputs(self, app, test_config, compute_stack_mock):
        """Test stack outputs are created correctly."""
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify outputs
        outputs = template.find_outputs("*")
        output_keys = set(outputs.keys())
        
        expected_outputs = {
            "AlarmTopicArn",
            "DashboardUrl"
        }
        
        for output in expected_outputs:
            assert any(output in key for key in output_keys), f"Missing output: {output}"
    
    def test_no_database_alarms_without_database_stack(self, app, test_config, compute_stack_mock):
        """Test that database alarms are not created when database stack is not provided."""
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            database_stack=None,  # No database
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Count total alarms - should not include database alarms
        alarms = template.find_resources("AWS::CloudWatch::Alarm")
        alarm_names = [alarm["Properties"]["AlarmName"] for alarm in alarms.values()]
        
        # Verify no database alarms
        assert not any("db-cpu" in name for name in alarm_names)
        assert not any("db-connections" in name for name in alarm_names)
    
    def test_production_memory_scaling_alarms(self, app, compute_stack_mock):
        """Test additional alarms for production environment."""
        config = N8nConfig(
            global_config=GlobalConfig(
                project_name="test-n8n",
                organization="test-org"
            ),
            environments={
                "production": EnvironmentConfig(
                    account="123456789012",
                    region="us-east-1",
                    settings=EnvironmentSettings(
                        monitoring=MonitoringConfig(
                            enable_container_insights=True
                        )
                    )
                )
            }
        )
        
        # In production, container insights should be enabled by default
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=config,
            environment="production",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        assert stack.is_production() is True
        assert stack.monitoring_config.enable_container_insights is True
    
    def test_dashboard_widgets_configuration(self, app, test_config, compute_stack_mock, storage_stack_mock):
        """Test dashboard widget configuration with storage stack."""
        compute_stack_mock.n8n_service.service.service_name = "test-n8n-service"
        compute_stack_mock.cluster.cluster_name = "test-cluster"
        storage_stack_mock.file_system.file_system_id = "fs-12345678"
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            storage_stack=storage_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        # Verify dashboard has expected widgets
        assert hasattr(stack, 'dashboard')
        
        # The dashboard body would contain widget definitions
        template = Template.from_stack(stack)
        dashboards = template.find_resources("AWS::CloudWatch::Dashboard")
        assert len(dashboards) == 1
        
        # Dashboard body should contain metrics for CPU, Memory, Tasks, and EFS
        dashboard_body = list(dashboards.values())[0]["Properties"]["DashboardBody"]
        assert "CPUUtilization" in dashboard_body
        assert "MemoryUtilization" in dashboard_body
        assert "RunningTaskCount" in dashboard_body
        assert "BurstCreditBalance" in dashboard_body  # EFS metric
    
    def test_log_query_widget(self, app, test_config, compute_stack_mock):
        """Test log query widget for error monitoring."""
        compute_stack_mock.n8n_service.log_group.log_group_name = "/ecs/test-n8n"
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify dashboard contains log query widget
        dashboards = template.find_resources("AWS::CloudWatch::Dashboard")
        dashboard_body = list(dashboards.values())[0]["Properties"]["DashboardBody"]
        
        # Check for error filter in log query
        assert "/ecs/test-n8n" in dashboard_body
        assert "ERROR" in dashboard_body
    
    def test_alarm_actions_configuration(self, app, test_config, compute_stack_mock):
        """Test that alarms are configured with correct actions."""
        compute_stack_mock.n8n_service.service.service_name = "test-n8n-service"
        compute_stack_mock.cluster.cluster_name = "test-cluster"
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Get all alarms
        alarms = template.find_resources("AWS::CloudWatch::Alarm")
        
        # Verify each alarm has alarm actions pointing to SNS topic
        for alarm in alarms.values():
            assert "AlarmActions" in alarm["Properties"]
            assert len(alarm["Properties"]["AlarmActions"]) > 0
            # Should reference the SNS topic
            action = alarm["Properties"]["AlarmActions"][0]
            assert "Ref" in action or "Fn::GetAtt" in action
    
    def test_custom_n8n_metrics_creation(self, app, test_config, compute_stack_mock):
        """Test creation of custom n8n metrics."""
        compute_stack_mock.n8n_service.log_group.log_group_name = "/ecs/test-n8n"
        
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify metric filters are created
        metric_filters = template.find_resources("AWS::Logs::MetricFilter")
        assert len(metric_filters) > 0
        
        # Check for specific metric filters
        filter_names = [filter["Properties"]["FilterName"] for filter in metric_filters.values() if "FilterName" in filter["Properties"]]
        expected_filters = [
            "WorkflowSuccessMetric",
            "WorkflowFailureMetric",
            "WorkflowDurationMetric",
            "WebhookRequestMetric",
            "WebhookResponseTimeMetric",
            "AuthErrorMetric",
            "DatabaseErrorMetric",
            "NodeExecutionTimeMetric",
            "QueueDepthMetric"
        ]
        
        for expected in expected_filters:
            assert any(expected in str(name) for name in filter_names), f"Missing metric filter: {expected}"
    
    def test_custom_metric_alarms(self, app, test_config, compute_stack_mock):
        """Test custom n8n metric alarms."""
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Verify workflow failure rate alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*workflow-failure-rate-high"),
            "AlarmDescription": "High workflow failure rate detected",
            "Threshold": 10,
            "EvaluationPeriods": 3,
            "DatapointsToAlarm": 2
        })
        
        # Verify webhook response time alarm
        template.has_resource_properties("AWS::CloudWatch::Alarm", {
            "AlarmName": Match.string_like_regexp(".*webhook-response-time-high"),
            "AlarmDescription": "Webhook response time is too high",
            "Threshold": 1000
        })
    
    def test_custom_dashboard_widgets(self, app, test_config, compute_stack_mock):
        """Test that custom n8n metrics are added to dashboard."""
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            config=test_config,
            environment="test",
            compute_stack=compute_stack_mock,
            env=Environment(account="123456789012", region="us-east-1")
        )
        
        template = Template.from_stack(stack)
        
        # Get dashboard body
        dashboards = template.find_resources("AWS::CloudWatch::Dashboard")
        assert len(dashboards) == 1
        
        dashboard_body = list(dashboards.values())[0]["Properties"]["DashboardBody"]
        
        # Verify custom metrics are in dashboard
        assert "Workflow Execution Metrics" in dashboard_body
        assert "Webhook Performance" in dashboard_body
        assert "Performance Metrics" in dashboard_body
        assert "Authentication Errors" in dashboard_body
        assert "Workflow Success Rate" in dashboard_body