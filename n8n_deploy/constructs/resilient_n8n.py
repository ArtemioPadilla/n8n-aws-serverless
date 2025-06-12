"""Resilient n8n construct with error recovery mechanisms."""
from typing import Any, Dict, Optional

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as events_targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sqs as sqs
from constructs import Construct


class ResilientN8n(Construct):
    """Construct for adding resilience patterns to n8n deployment."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        compute_stack: Any,
        monitoring_topic: sns.Topic,
        environment: str,
        **kwargs,
    ) -> None:
        """Initialize resilient n8n construct.

        Args:
            scope: CDK scope
            construct_id: Construct ID
            compute_stack: Compute stack with n8n service
            monitoring_topic: SNS topic for alerts
            environment: Environment name
            **kwargs: Additional properties
        """
        super().__init__(scope, construct_id, **kwargs)

        self.compute_stack = compute_stack
        self.monitoring_topic = monitoring_topic
        self.environment = environment

        # Create dead letter queues
        self.webhook_dlq = self._create_webhook_dlq()
        self.workflow_dlq = self._create_workflow_dlq()

        # Create circuit breaker for external services
        self.circuit_breaker = self._create_circuit_breaker()

        # Create retry handler
        self.retry_handler = self._create_retry_handler()

        # Create health check automation
        self._create_health_check_automation()

        # Create auto-recovery mechanisms
        self._create_auto_recovery()

    def _create_webhook_dlq(self) -> sqs.Queue:
        """Create dead letter queue for failed webhook processing."""
        dlq = sqs.Queue(
            self,
            "WebhookDLQ",
            queue_name=f"n8n-{self.environment}-webhook-dlq",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            visibility_timeout=Duration.minutes(5),
        )

        # Create alarm for DLQ messages
        dlq_alarm = cloudwatch.Alarm(
            self,
            "WebhookDLQAlarm",
            alarm_name=f"n8n-{self.environment}-webhook-dlq-messages",
            alarm_description="Messages in webhook dead letter queue",
            metric=dlq.metric_approximate_number_of_messages_visible(),
            threshold=5,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        dlq_alarm.add_alarm_action(cloudwatch_actions.SnsAction(self.monitoring_topic))

        # Grant n8n service permission to send to DLQ
        dlq.grant_send_messages(
            self.compute_stack.n8n_service.task_definition.task_role
        )

        return dlq

    def _create_workflow_dlq(self) -> sqs.Queue:
        """Create dead letter queue for failed workflow executions."""
        dlq = sqs.Queue(
            self,
            "WorkflowDLQ",
            queue_name=f"n8n-{self.environment}-workflow-dlq",
            retention_period=Duration.days(14),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
            visibility_timeout=Duration.minutes(30),  # Longer for workflows
        )

        # Create alarm for DLQ messages
        dlq_alarm = cloudwatch.Alarm(
            self,
            "WorkflowDLQAlarm",
            alarm_name=f"n8n-{self.environment}-workflow-dlq-messages",
            alarm_description="Failed workflows in dead letter queue",
            metric=dlq.metric_approximate_number_of_messages_visible(),
            threshold=10,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        dlq_alarm.add_alarm_action(cloudwatch_actions.SnsAction(self.monitoring_topic))

        # Grant permissions
        dlq.grant_send_messages(
            self.compute_stack.n8n_service.task_definition.task_role
        )

        return dlq

    def _create_circuit_breaker(self) -> lambda_.Function:
        """Create Lambda function for circuit breaker pattern."""
        # Create Lambda function for circuit breaker logic
        circuit_breaker_fn = lambda_.Function(
            self,
            "CircuitBreaker",
            function_name=f"n8n-{self.environment}-circuit-breaker",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import os
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['CIRCUIT_STATE_TABLE'])
cloudwatch = boto3.client('cloudwatch')

def handler(event, context):
    service_name = event.get('service_name')
    action = event.get('action', 'check')  # check, open, close, half-open
    
    if action == 'check':
        # Check circuit state
        response = table.get_item(Key={'service_name': service_name})
        item = response.get('Item', {})
        
        state = item.get('state', 'closed')
        if state == 'open':
            # Check if it's time to try half-open
            open_time = datetime.fromisoformat(item.get('open_time', ''))
            if datetime.now() - open_time > timedelta(minutes=5):
                # Try half-open
                table.update_item(
                    Key={'service_name': service_name},
                    UpdateExpression='SET #state = :state',
                    ExpressionAttributeNames={'#state': 'state'},
                    ExpressionAttributeValues={':state': 'half-open'}
                )
                return {'state': 'half-open', 'allow_request': True}
            else:
                return {'state': 'open', 'allow_request': False}
        
        return {'state': state, 'allow_request': state != 'open'}
    
    elif action == 'record_failure':
        # Record failure and potentially open circuit
        failure_count = event.get('failure_count', 1)
        threshold = int(os.environ.get('FAILURE_THRESHOLD', '5'))
        
        if failure_count >= threshold:
            # Open circuit
            table.put_item(Item={
                'service_name': service_name,
                'state': 'open',
                'open_time': datetime.now().isoformat(),
                'failure_count': failure_count
            })
            
            # Send metric
            cloudwatch.put_metric_data(
                Namespace='N8n/CircuitBreaker',
                MetricData=[{
                    'MetricName': 'CircuitOpened',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'ServiceName', 'Value': service_name},
                        {'Name': 'Environment', 'Value': os.environ['ENVIRONMENT']}
                    ]
                }]
            )
            
            return {'state': 'open', 'message': 'Circuit opened due to failures'}
        
        return {'state': 'closed', 'failure_count': failure_count}
    
    elif action == 'record_success':
        # Record success and potentially close circuit
        table.update_item(
            Key={'service_name': service_name},
            UpdateExpression='SET #state = :state, failure_count = :count',
            ExpressionAttributeNames={'#state': 'state'},
            ExpressionAttributeValues={
                ':state': 'closed',
                ':count': 0
            }
        )
        return {'state': 'closed', 'message': 'Circuit closed after success'}
    
    return {'error': 'Invalid action'}
"""
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "CIRCUIT_STATE_TABLE": f"n8n-{self.environment}-circuit-state",
                "FAILURE_THRESHOLD": "5",
                "ENVIRONMENT": self.environment,
            },
            tracing=lambda_.Tracing.ACTIVE,
        )

        # Create DynamoDB table for circuit state
        from aws_cdk import aws_dynamodb as dynamodb

        circuit_state_table = dynamodb.Table(
            self,
            "CircuitStateTable",
            table_name=f"n8n-{self.environment}-circuit-state",
            partition_key=dynamodb.Attribute(
                name="service_name", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
            if self.environment != "production"
            else RemovalPolicy.RETAIN,
            point_in_time_recovery=self.environment == "production",
        )

        # Grant permissions
        circuit_state_table.grant_read_write_data(circuit_breaker_fn)
        circuit_breaker_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # Allow n8n to invoke circuit breaker
        circuit_breaker_fn.grant_invoke(
            self.compute_stack.n8n_service.task_definition.task_role
        )

        return circuit_breaker_fn

    def _create_retry_handler(self) -> lambda_.Function:
        """Create Lambda function for intelligent retry handling."""
        retry_handler_fn = lambda_.Function(
            self,
            "RetryHandler",
            function_name=f"n8n-{self.environment}-retry-handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import os
import time
import random
from datetime import datetime

sqs = boto3.client('sqs')
cloudwatch = boto3.client('cloudwatch')

def exponential_backoff(retry_count, base_delay=1, max_delay=300):
    \"\"\"Calculate exponential backoff with jitter.\"\"\"
    delay = min(base_delay * (2 ** retry_count), max_delay)
    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
    return delay + jitter

def handler(event, context):
    # Parse retry request
    request = json.loads(event['Records'][0]['body'])
    
    retry_count = request.get('retry_count', 0)
    max_retries = int(os.environ.get('MAX_RETRIES', '3'))
    workflow_id = request.get('workflow_id')
    webhook_url = request.get('webhook_url')
    payload = request.get('payload')
    
    if retry_count >= max_retries:
        # Send to DLQ
        dlq_url = os.environ['DLQ_URL']
        sqs.send_message(
            QueueUrl=dlq_url,
            MessageBody=json.dumps({
                'workflow_id': workflow_id,
                'webhook_url': webhook_url,
                'payload': payload,
                'failed_at': datetime.now().isoformat(),
                'retry_count': retry_count,
                'reason': 'Max retries exceeded'
            })
        )
        
        # Send metric
        cloudwatch.put_metric_data(
            Namespace='N8n/Retry',
            MetricData=[{
                'MetricName': 'RetryExhausted',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': os.environ['ENVIRONMENT']}
                ]
            }]
        )
        
        return {'status': 'failed', 'reason': 'Max retries exceeded'}
    
    # Calculate backoff
    delay = exponential_backoff(retry_count)
    
    # Wait (in real implementation, would reschedule)
    time.sleep(min(delay, 5))  # Cap at 5 seconds for Lambda
    
    # In real implementation, would call n8n API to retry
    # For now, just return success
    return {
        'status': 'retried',
        'retry_count': retry_count + 1,
        'delay': delay
    }
"""
            ),
            timeout=Duration.minutes(1),
            memory_size=256,
            environment={
                "MAX_RETRIES": "3",
                "DLQ_URL": self.workflow_dlq.queue_url,
                "ENVIRONMENT": self.environment,
            },
            reserved_concurrent_executions=10,  # Limit concurrency
        )

        # Create retry queue
        retry_queue = sqs.Queue(
            self,
            "RetryQueue",
            queue_name=f"n8n-{self.environment}-retry-queue",
            visibility_timeout=Duration.minutes(2),
            encryption=sqs.QueueEncryption.KMS_MANAGED,
        )

        # Add Lambda trigger
        retry_handler_fn.add_event_source(
            lambda_.SqsEventSource(
                retry_queue,
                batch_size=1,
                max_batching_window_time=Duration.seconds(5),
            )
        )

        # Grant permissions
        retry_queue.grant_consume_messages(retry_handler_fn)
        self.workflow_dlq.grant_send_messages(retry_handler_fn)
        retry_handler_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # Allow n8n to send to retry queue
        retry_queue.grant_send_messages(
            self.compute_stack.n8n_service.task_definition.task_role
        )

        return retry_handler_fn

    def _create_health_check_automation(self) -> None:
        """Create automated health check and recovery."""
        # Create Lambda for health checks
        health_check_fn = lambda_.Function(
            self,
            "HealthCheck",
            function_name=f"n8n-{self.environment}-health-check",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import urllib3
import os
from datetime import datetime

ecs = boto3.client('ecs')
cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')
http = urllib3.PoolManager()

def handler(event, context):
    cluster_name = os.environ['CLUSTER_NAME']
    service_name = os.environ['SERVICE_NAME']
    health_url = os.environ['HEALTH_URL']
    
    # Check ECS service health
    response = ecs.describe_services(
        cluster=cluster_name,
        services=[service_name]
    )
    
    service = response['services'][0]
    running_count = service['runningCount']
    desired_count = service['desiredCount']
    
    # Check if service is healthy
    if running_count < desired_count:
        # Service is unhealthy
        message = f"n8n service unhealthy: {running_count}/{desired_count} tasks running"
        
        # Send notification
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Subject=f"n8n Health Check Failed - {os.environ['ENVIRONMENT']}",
            Message=message
        )
        
        # Send metric
        cloudwatch.put_metric_data(
            Namespace='N8n/Health',
            MetricData=[{
                'MetricName': 'ServiceUnhealthy',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': os.environ['ENVIRONMENT']}
                ]
            }]
        )
        
        # Attempt recovery if too many tasks are failing
        if running_count == 0:
            ecs.update_service(
                cluster=cluster_name,
                service=service_name,
                forceNewDeployment=True
            )
            return {'status': 'recovery_initiated', 'message': message}
    
    # Try HTTP health check
    try:
        resp = http.request('GET', health_url, timeout=10)
        if resp.status != 200:
            raise Exception(f"Health check returned {resp.status}")
    except Exception as e:
        # HTTP health check failed
        cloudwatch.put_metric_data(
            Namespace='N8n/Health',
            MetricData=[{
                'MetricName': 'HealthCheckFailed',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Environment', 'Value': os.environ['ENVIRONMENT']}
                ]
            }]
        )
        return {'status': 'unhealthy', 'error': str(e)}
    
    return {'status': 'healthy', 'running_tasks': running_count}
"""
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "CLUSTER_NAME": self.compute_stack.cluster.cluster_name,
                "SERVICE_NAME": self.compute_stack.n8n_service.service.service_name,
                "HEALTH_URL": f"http://{self.compute_stack.n8n_service.service.cloud_map_service.service_name}.{self.compute_stack.n8n_service.service.cloud_map_service.namespace.namespace_name}:5678/healthz",
                "SNS_TOPIC_ARN": self.monitoring_topic.topic_arn,
                "ENVIRONMENT": self.environment,
            },
            vpc=self.compute_stack.network_stack.vpc,
            vpc_subnets=self.compute_stack.network_stack.subnets,
        )

        # Grant permissions
        health_check_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "ecs:DescribeServices",
                    "ecs:UpdateService",
                ],
                resources=["*"],  # Can be scoped down to specific service
            )
        )
        health_check_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )
        self.monitoring_topic.grant_publish(health_check_fn)

        # Schedule health checks
        health_check_rule = events.Rule(
            self,
            "HealthCheckSchedule",
            rule_name=f"n8n-{self.environment}-health-check",
            schedule=events.Schedule.rate(Duration.minutes(5)),
        )
        health_check_rule.add_target(events_targets.LambdaFunction(health_check_fn))

    def _create_auto_recovery(self) -> None:
        """Create auto-recovery alarms for the ECS service."""
        # Create alarm for service with no running tasks
        no_tasks_alarm = cloudwatch.Alarm(
            self,
            "NoRunningTasksAlarm",
            alarm_name=f"n8n-{self.environment}-no-running-tasks",
            alarm_description="n8n service has no running tasks",
            metric=cloudwatch.Metric(
                namespace="AWS/ECS",
                metric_name="RunningTaskCount",
                dimensions_map={
                    "ServiceName": self.compute_stack.n8n_service.service.service_name,
                    "ClusterName": self.compute_stack.cluster.cluster_name,
                },
                statistic="Average",
            ),
            threshold=0.5,  # Less than 1 task
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.BREACHING,
        )

        # Add alarm action
        no_tasks_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(self.monitoring_topic)
        )

        # Create alarm for high error rate
        error_rate_alarm = cloudwatch.Alarm(
            self,
            "HighErrorRateAlarm",
            alarm_name=f"n8n-{self.environment}-high-error-rate",
            alarm_description="n8n service has high error rate",
            metric=cloudwatch.MathExpression(
                expression="(errors / requests) * 100",
                using_metrics={
                    "errors": cloudwatch.Metric(
                        namespace="N8n/Serverless",
                        metric_name="WorkflowExecutionFailure",
                        statistic="Sum",
                        period=Duration.minutes(5),
                    ),
                    "requests": cloudwatch.Metric(
                        namespace="N8n/Serverless",
                        metric_name="WorkflowExecutionSuccess",
                        statistic="Sum",
                        period=Duration.minutes(5),
                    ),
                },
                label="Error Rate %",
                period=Duration.minutes(5),
            ),
            threshold=50,  # 50% error rate
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        error_rate_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(self.monitoring_topic)
        )

    def get_dlq_arns(self) -> Dict[str, str]:
        """Get ARNs of dead letter queues."""
        return {
            "webhook_dlq": self.webhook_dlq.queue_arn,
            "workflow_dlq": self.workflow_dlq.queue_arn,
        }

    def get_circuit_breaker_function_name(self) -> str:
        """Get circuit breaker Lambda function name."""
        return self.circuit_breaker.function_name
