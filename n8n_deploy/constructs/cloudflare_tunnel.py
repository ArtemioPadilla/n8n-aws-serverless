"""Cloudflare Tunnel construct for zero-trust access to n8n."""

from typing import Any, Dict, Optional

from aws_cdk import Duration, Stack
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct


class CloudflareTunnelConfiguration(Construct):
    """Configuration for Cloudflare Tunnel including secrets and access policies."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        tunnel_name: str,
        tunnel_domain: str,
        service_url: str,
        environment: str,
        tunnel_secret_name: Optional[str] = None,
        access_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize Cloudflare Tunnel configuration.

        Args:
            scope: Parent construct
            id: Construct ID
            tunnel_name: Name of the Cloudflare tunnel
            tunnel_domain: Domain for accessing the service
            service_url: Internal service URL (e.g., http://localhost:5678)
            environment: Environment name
            tunnel_secret_name: Name of the secret containing tunnel token
            access_config: Cloudflare Access configuration
        """
        super().__init__(scope, id)

        self.tunnel_name = tunnel_name
        self.tunnel_domain = tunnel_domain
        self.service_url = service_url
        self.environment = environment
        self.access_config = access_config or {}

        # Create or reference the tunnel token secret
        if tunnel_secret_name:
            # Reference existing secret
            self.tunnel_secret = secretsmanager.Secret.from_secret_name_v2(
                self, "TunnelTokenSecret", tunnel_secret_name
            )
        else:
            # Create new secret placeholder
            self.tunnel_secret = secretsmanager.Secret(
                self,
                "TunnelTokenSecret",
                description=f"Cloudflare Tunnel token for {tunnel_name}",
                secret_name=f"n8n/{environment}/cloudflare-tunnel-token",
            )

            # Add output for manual token configuration
            from aws_cdk import CfnOutput

            stack = Stack.of(self)
            CfnOutput(
                stack,
                f"{id}TunnelTokenSecretArn",
                value=self.tunnel_secret.secret_arn,
                description="ARN of the secret where Cloudflare tunnel token should be stored",
            )

        # Store configuration for tunnel
        self.tunnel_config = {
            "tunnel": tunnel_name,
            "credentials-file": "/etc/cloudflared/creds.json",
            "metrics": "0.0.0.0:2000",
            "no-autoupdate": True,
            "ingress": [
                {
                    "hostname": tunnel_domain,
                    "service": service_url,
                    "originRequest": {
                        "noTLSVerify": True,  # Since we're connecting to localhost
                        "connectTimeout": "30s",
                        "tcpKeepAlive": "30s",
                        "keepAliveConnections": 100,
                        "keepAliveTimeout": "90s",
                        "httpHostHeader": tunnel_domain,
                        "originServerName": tunnel_domain,
                    },
                },
                # Catch-all rule
                {"service": "http_status:404"},
            ],
        }

        # Add access policies if enabled
        if self.access_config.get("enabled"):
            self._add_access_policies()

    def _add_access_policies(self) -> None:
        """Add Cloudflare Access policies to the tunnel configuration."""
        access_rules = []

        # Email-based access
        if self.access_config.get("allowed_emails"):
            for email in self.access_config["allowed_emails"]:
                access_rules.append({"type": "email", "email": {"email": email}})

        # Domain-based access
        if self.access_config.get("allowed_domains"):
            for domain in self.access_config["allowed_domains"]:
                access_rules.append({"type": "email_domain", "email_domain": {"domain": domain}})

        # Add access configuration to the tunnel
        if access_rules:
            self.tunnel_config["ingress"][0]["originRequest"]["access"] = {
                "required": True,
                "teamName": self.environment,
                "policies": access_rules,
            }


class CloudflareTunnelSidecar(Construct):
    """ECS sidecar container for Cloudflare Tunnel."""

    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        task_definition: ecs.TaskDefinition,
        tunnel_secret: secretsmanager.ISecret,
        tunnel_config: Dict[str, Any],
        log_group: logs.LogGroup,
        environment: str,
        container_cpu: int = 256,
        container_memory: int = 512,
    ) -> None:
        """
        Initialize Cloudflare Tunnel sidecar container.

        Args:
            scope: Parent construct
            id: Construct ID
            task_definition: ECS task definition to add the sidecar to
            tunnel_secret: Secret containing the tunnel token
            tunnel_config: Tunnel configuration dict
            log_group: CloudWatch log group for container logs
            environment: Environment name
            container_cpu: CPU units for the container (default: 256)
            container_memory: Memory in MB for the container (default: 512)
        """
        super().__init__(scope, id)

        self.task_definition = task_definition
        self.tunnel_secret = tunnel_secret
        self.tunnel_config = tunnel_config
        self.environment = environment

        # Create log stream for Cloudflare
        self.log_stream = logs.LogStream(
            self,
            "CloudflareLogStream",
            log_group=log_group,
            log_stream_name=f"cloudflare-tunnel-{environment}",
        )

        # Add Cloudflare container to task definition
        self.container = task_definition.add_container(
            "cloudflare-tunnel",
            image=ecs.ContainerImage.from_registry("cloudflare/cloudflared:latest"),
            cpu=container_cpu,
            memory_limit_mib=container_memory,
            essential=True,  # If tunnel fails, the whole task should restart
            command=["tunnel", "--no-autoupdate", "--metrics", "0.0.0.0:2000", "run"],
            environment={
                "TUNNEL_METRICS": "0.0.0.0:2000",
                "TUNNEL_LOGLEVEL": "info",
                "TUNNEL_TRANSPORT_PROTOCOL": "quic",
            },
            secrets={"TUNNEL_TOKEN": ecs.Secret.from_secrets_manager(tunnel_secret)},
            logging=ecs.LogDriver.aws_logs(stream_prefix="cloudflare", log_group=log_group),
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "wget -q -O /dev/null http://localhost:2000/ready || exit 1",
                ],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(10),
            ),
        )

        # Add port mapping for metrics
        self.container.add_port_mappings(ecs.PortMapping(container_port=2000, protocol=ecs.Protocol.TCP))

        # Grant read access to the tunnel secret
        tunnel_secret.grant_read(task_definition.task_role)

        # Add CloudWatch Logs permissions
        task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                resources=[log_group.log_group_arn],
            )
        )

        # Add container dependency - ensure n8n starts before tunnel
        # The n8n container should be added before this sidecar
        # We'll rely on the fact that the n8n container is essential
        # and let ECS handle the startup order
