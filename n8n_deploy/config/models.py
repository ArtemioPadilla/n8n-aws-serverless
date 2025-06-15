"""Pydantic models for configuration validation."""

import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator, validator


class DatabaseType(str, Enum):
    """Supported database types."""

    SQLITE = "sqlite"
    POSTGRES = "postgres"


class AuthProvider(str, Enum):
    """OAuth providers."""

    GOOGLE = "google"
    GITHUB = "github"
    OKTA = "okta"
    AZURE_AD = "azure_ad"


class StackType(str, Enum):
    """Predefined stack configurations."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"


class FargateConfig(BaseModel):
    """Fargate task configuration."""

    cpu: int = Field(256, ge=256, le=16384)
    memory: int = Field(512, ge=512, le=122880)
    spot_percentage: int = Field(80, ge=0, le=100)
    n8n_version: str = Field("1.94.1", description="n8n Docker image version")

    @validator("memory")
    def validate_cpu_memory_combination(cls, memory, values):
        """Validate Fargate CPU/memory combinations."""
        cpu = values.get("cpu", 256)
        valid_combinations = {
            256: [512, 1024, 2048],
            512: [1024, 2048, 3072, 4096],
            1024: list(range(2048, 8193, 1024)),
            2048: list(range(4096, 16385, 1024)),
            4096: list(range(8192, 30721, 1024)),
            8192: list(range(16384, 61441, 4096)),
            16384: list(range(32768, 122881, 8192)),
        }

        if cpu in valid_combinations and memory not in valid_combinations[cpu]:
            raise ValueError(f"Invalid CPU/memory combination: {cpu}/{memory}")
        return memory


class ScalingConfig(BaseModel):
    """Auto-scaling configuration."""

    min_tasks: int = Field(1, ge=1)
    max_tasks: int = Field(1, ge=1)
    target_cpu_utilization: int = Field(70, ge=10, le=90)
    scale_in_cooldown: int = Field(300, ge=60)
    scale_out_cooldown: int = Field(60, ge=60)

    @validator("max_tasks")
    def validate_max_tasks(cls, max_tasks, values):
        """Ensure max_tasks >= min_tasks."""
        min_tasks = values.get("min_tasks", 1)
        if max_tasks < min_tasks:
            raise ValueError(f"max_tasks ({max_tasks}) must be >= min_tasks ({min_tasks})")
        return max_tasks


class NetworkingConfig(BaseModel):
    """Network configuration."""

    use_existing_vpc: bool = False
    vpc_id: Optional[str] = None
    vpc_cidr: str = "10.0.0.0/16"
    subnet_ids: Optional[List[str]] = None
    availability_zones: Optional[List[str]] = None
    nat_gateways: int = Field(0, ge=0, le=3)

    @validator("vpc_id")
    def validate_vpc_id(cls, vpc_id, values):
        """Validate VPC ID when using existing VPC."""
        if values.get("use_existing_vpc") and not vpc_id:
            raise ValueError("vpc_id required when use_existing_vpc is True")
        return vpc_id


class DatabaseConfig(BaseModel):
    """Database configuration."""

    type: DatabaseType = DatabaseType.SQLITE
    use_existing: bool = False
    connection_secret_arn: Optional[str] = None
    instance_class: Optional[str] = None
    multi_az: bool = False
    aurora_serverless: Optional[Dict[str, float]] = None
    backup_retention_days: int = Field(7, ge=1, le=35)


class AccessType(str, Enum):
    """Access method for n8n."""

    API_GATEWAY = "api_gateway"
    CLOUDFLARE = "cloudflare"


class CloudflareConfig(BaseModel):
    """Cloudflare Tunnel configuration."""

    enabled: bool = False
    tunnel_token_secret_name: Optional[str] = None
    tunnel_name: Optional[str] = None
    tunnel_domain: Optional[str] = None
    access_enabled: bool = False
    access_allowed_emails: Optional[List[str]] = None
    access_allowed_domains: Optional[List[str]] = None

    @model_validator(mode="after")
    def validate_tunnel_token(self):
        """Ensure tunnel token is provided when Cloudflare is enabled."""
        if self.enabled and not self.tunnel_token_secret_name:
            raise ValueError("tunnel_token_secret_name is required when Cloudflare is enabled")
        return self

    @field_validator("tunnel_domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate tunnel domain format."""
        if v:
            # More strict domain validation
            # - Must start with alphanumeric
            # - Can contain alphanumeric, hyphens, and dots
            # - Cannot have consecutive dots
            # - Cannot end with hyphen
            # - Must have valid TLD
            pattern = (
                r"^[a-zA-Z0-9]([a-zA-Z0-9-_]*[a-zA-Z0-9])?"
                r"(\.[a-zA-Z0-9]([a-zA-Z0-9-_]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
            )
            if not re.match(pattern, v):
                raise ValueError(f"Invalid domain format: {v}. Must be a valid domain name.")
        return v


class AccessConfig(BaseModel):
    """API access configuration."""

    type: AccessType = AccessType.API_GATEWAY
    domain_name: Optional[str] = None
    cloudfront_enabled: bool = True
    waf_enabled: bool = False
    api_gateway_throttle: int = Field(1000, ge=1)
    cors_origins: List[str] = ["*"]
    ip_whitelist: Optional[List[str]] = None
    cloudflare: Optional[CloudflareConfig] = None

    @model_validator(mode="after")
    def validate_cloudflare(self):
        """Validate Cloudflare config when type is CLOUDFLARE."""
        if self.type == AccessType.CLOUDFLARE:
            if not self.cloudflare:
                # Create a default cloudflare config without full validation
                # The actual validation will happen when the config is used
                self.cloudflare = CloudflareConfig.model_construct(enabled=True)
            else:
                self.cloudflare.enabled = True
        return self


class AuthConfig(BaseModel):
    """Authentication configuration."""

    basic_auth_enabled: bool = True
    oauth_enabled: bool = False
    oauth_provider: Optional[AuthProvider] = None
    mfa_required: bool = False
    allowed_email_domains: Optional[List[str]] = None

    @validator("oauth_provider")
    def validate_oauth_provider(cls, oauth_provider, values):
        """Validate OAuth provider when OAuth is enabled."""
        if values.get("oauth_enabled") and not oauth_provider:
            raise ValueError("oauth_provider required when oauth_enabled is True")
        return oauth_provider


class MonitoringConfig(BaseModel):
    """Monitoring and logging configuration."""

    log_retention_days: int = Field(30, ge=1, le=365)
    alarm_email: Optional[str] = None
    enable_container_insights: bool = True
    enable_xray_tracing: bool = False
    custom_metrics_namespace: str = "N8n/Serverless"


class BackupConfig(BaseModel):
    """Backup configuration."""

    enabled: bool = True
    retention_days: int = Field(7, ge=1, le=365)
    cross_region_backup: bool = False
    backup_regions: Optional[List[str]] = None


class HighAvailabilityConfig(BaseModel):
    """High availability configuration."""

    multi_az: bool = False
    auto_scaling_enabled: bool = True
    health_check_interval: int = Field(30, ge=10, le=300)
    unhealthy_threshold: int = Field(2, ge=2, le=10)


class DockerConfig(BaseModel):
    """Docker deployment configuration for local development."""

    compose_file: str = "docker/docker-compose.yml"
    image: str = "n8nio/n8n:1.94.1"
    port: int = 5678
    profiles: Optional[List[str]] = None


class EnvironmentSettings(BaseModel):
    """Environment-specific settings."""

    deployment_type: Optional[str] = "aws"  # "aws" or "docker"
    docker: Optional[DockerConfig] = None
    fargate: Optional[FargateConfig] = None
    scaling: Optional[ScalingConfig] = None
    networking: Optional[NetworkingConfig] = None
    access: Optional[AccessConfig] = None
    database: Optional[DatabaseConfig] = None
    auth: Optional[AuthConfig] = None
    monitoring: Optional[MonitoringConfig] = None
    backup: Optional[BackupConfig] = None
    high_availability: Optional[HighAvailabilityConfig] = None
    features: Optional[Dict[str, Any]] = None


class MultiRegionConfig(BaseModel):
    """Multi-region deployment configuration."""

    enabled: bool = False
    regions: Optional[List[Dict[str, Any]]] = None


class EnvironmentConfig(BaseModel):
    """Complete environment configuration."""

    account: str
    region: str
    multi_region: Optional[MultiRegionConfig] = None
    settings: EnvironmentSettings
    tags: Optional[Dict[str, str]] = None


class StackConfig(BaseModel):
    """Stack type configuration."""

    description: str
    components: List[str]
    settings: Optional[Dict[str, Any]] = None
    inherit_from: Optional[str] = None


class SharedResources(BaseModel):
    """Shared resources across environments."""

    security: Optional[Dict[str, str]] = None
    networking: Optional[Dict[str, str]] = None
    storage: Optional[Dict[str, str]] = None


class GlobalConfig(BaseModel):
    """Global project configuration."""

    project_name: str
    organization: str
    tags: Optional[Dict[str, str]] = None
    cost_allocation_tags: Optional[List[str]] = None


class DefaultsConfig(BaseModel):
    """Default configurations."""

    fargate: Optional[FargateConfig] = None
    efs: Optional[Dict[str, Any]] = None
    monitoring: Optional[MonitoringConfig] = None
    backup: Optional[BackupConfig] = None


class N8nConfig(BaseModel):
    """Root configuration model."""

    global_config: GlobalConfig = Field(..., alias="global")
    defaults: Optional[DefaultsConfig] = None
    environments: Dict[str, EnvironmentConfig]
    stacks: Optional[Dict[str, StackConfig]] = None
    shared_resources: Optional[SharedResources] = None

    class Config:
        populate_by_name = True

    def get_environment(self, env_name: str) -> Optional[EnvironmentConfig]:
        """Get configuration for a specific environment."""
        return self.environments.get(env_name)

    def get_stack_config(self, stack_type: str) -> Optional[StackConfig]:
        """Get configuration for a specific stack type."""
        return self.stacks.get(stack_type) if self.stacks else None

    def merge_with_defaults(self, env_config: EnvironmentConfig) -> EnvironmentConfig:
        """Merge environment config with defaults."""
        if not self.defaults:
            return env_config

        # Deep merge logic here
        merged = env_config.copy(deep=True)

        # Merge each configuration section with defaults
        if self.defaults.fargate and not merged.settings.fargate:
            merged.settings.fargate = self.defaults.fargate

        if self.defaults.monitoring and not merged.settings.monitoring:
            merged.settings.monitoring = self.defaults.monitoring

        if self.defaults.backup and not merged.settings.backup:
            merged.settings.backup = self.defaults.backup

        return merged
