"""Storage stack for EFS and backup resources."""
from typing import List, Optional
from aws_cdk import (
    RemovalPolicy,
    Duration,
    Fn,
)
from aws_cdk import aws_efs as efs
from aws_cdk import aws_backup as backup
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_events as events
from constructs import Construct
from .base_stack import N8nBaseStack
from .network_stack import NetworkStack
from ..config.models import N8nConfig


class StorageStack(N8nBaseStack):
    """Stack for storage resources (EFS, backups)."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        config: N8nConfig,
        environment: str,
        network_stack: NetworkStack,
        **kwargs
    ) -> None:
        """Initialize storage stack.
        
        Args:
            scope: CDK scope
            construct_id: Stack ID
            config: N8n configuration
            environment: Environment name
            network_stack: Network stack with VPC and security groups
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, config, environment, **kwargs)
        
        self.network_stack = network_stack
        
        # Create EFS file system
        self.file_system = self._create_efs_file_system()
        
        # Create EFS access point for n8n
        self.n8n_access_point = self._create_n8n_access_point()
        
        # Set up backups if enabled
        if self.env_config.settings.backup and self.env_config.settings.backup.enabled:
            self._setup_backups()
        
        # Add outputs
        self._add_outputs()
    
    def _create_efs_file_system(self) -> efs.FileSystem:
        """Create EFS file system for n8n data."""
        # Get EFS configuration from defaults
        efs_config = self.config.defaults.efs if self.config.defaults and self.config.defaults.efs else {}
        lifecycle_days = efs_config.get("lifecycle_days", 30)
        
        # Map lifecycle days to available policies
        lifecycle_policy_map = {
            1: efs.LifecyclePolicy.AFTER_1_DAY,
            7: efs.LifecyclePolicy.AFTER_7_DAYS,
            14: efs.LifecyclePolicy.AFTER_14_DAYS,
            30: efs.LifecyclePolicy.AFTER_30_DAYS,
            60: efs.LifecyclePolicy.AFTER_60_DAYS,
            90: efs.LifecyclePolicy.AFTER_90_DAYS,
            180: efs.LifecyclePolicy.AFTER_180_DAYS,
            270: efs.LifecyclePolicy.AFTER_270_DAYS,
            365: efs.LifecyclePolicy.AFTER_365_DAYS,
        }
        
        # Find the closest matching policy
        closest_days = min(lifecycle_policy_map.keys(), 
                          key=lambda x: abs(x - lifecycle_days))
        lifecycle_policy = lifecycle_policy_map[closest_days]
        
        # Create file system
        file_system = efs.FileSystem(
            self,
            "N8nFileSystem",
            file_system_name=self.get_resource_name("efs", "n8n"),
            vpc=self.network_stack.vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=self.network_stack.subnets),
            security_group=self.network_stack.efs_security_group,
            encrypted=True,
            enable_automatic_backups=self.is_production(),
            lifecycle_policy=lifecycle_policy,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            throughput_mode=efs.ThroughputMode.BURSTING,
            removal_policy=self.removal_policy,
        )
        
        # Add production-specific settings
        if self.is_production():
            # Enable replication to another region if cross-region backup is enabled
            if (self.env_config.settings.backup and 
                self.env_config.settings.backup.cross_region_backup and
                self.env_config.settings.backup.backup_regions):
                
                # Note: EFS replication would need to be set up separately
                # as CDK doesn't directly support it yet
                pass
        
        return file_system
    
    def _create_n8n_access_point(self) -> efs.AccessPoint:
        """Create EFS access point for n8n container."""
        access_point = efs.AccessPoint(
            self,
            "N8nAccessPoint",
            file_system=self.file_system,
            path="/n8n-data",
            create_acl=efs.Acl(
                owner_uid="1000",  # n8n user
                owner_gid="1000",  # n8n group
                permissions="755"
            ),
            posix_user=efs.PosixUser(
                uid="1000",
                gid="1000"
            )
        )
        
        return access_point
    
    def _setup_backups(self) -> None:
        """Set up AWS Backup for EFS."""
        backup_config = self.env_config.settings.backup
        
        # Create backup vault
        backup_vault = backup.BackupVault(
            self,
            "BackupVault",
            backup_vault_name=self.get_resource_name("backup-vault"),
            encryption_key=None,  # Use default AWS managed key
            removal_policy=self.removal_policy,
        )
        
        # Create backup plan
        backup_plan = backup.BackupPlan(
            self,
            "BackupPlan",
            backup_plan_name=self.get_resource_name("backup-plan"),
            backup_vault=backup_vault,
        )
        
        # Add backup rule
        backup_plan.add_rule(
            backup.BackupPlanRule(
                backup_vault=backup_vault,
                rule_name="DailyBackup",
                schedule_expression=events.Schedule.cron(
                    hour="3",
                    minute="0"
                ),
                delete_after=Duration.days(backup_config.retention_days),
                enable_continuous_backup=self.is_production(),
                start_window=Duration.hours(1),
                completion_window=Duration.hours(2),
            )
        )
        
        # Add EFS to backup plan
        backup_plan.add_selection(
            "EfsBackupSelection",
            resources=[backup.BackupResource.from_efs_file_system(self.file_system)],
            allow_restores=True,
        )
        
        # Cross-region backup (if enabled)
        if backup_config.cross_region_backup and backup_config.backup_regions:
            for region in backup_config.backup_regions:
                # Note: Cross-region backup copying would need additional setup
                # This is a placeholder for the cross-region backup logic
                pass
    
    def _add_outputs(self) -> None:
        """Add stack outputs."""
        # EFS outputs
        self.add_output(
            "FileSystemId",
            value=self.file_system.file_system_id,
            description="EFS file system ID"
        )
        
        self.add_output(
            "FileSystemArn",
            value=self.file_system.file_system_arn,
            description="EFS file system ARN"
        )
        
        self.add_output(
            "AccessPointId",
            value=self.n8n_access_point.access_point_id,
            description="EFS access point ID for n8n"
        )
        
        self.add_output(
            "AccessPointArn",
            value=self.n8n_access_point.access_point_arn,
            description="EFS access point ARN for n8n"
        )
        
        # Mount target info
        mount_targets = []
        for subnet in self.network_stack.subnets:
            mount_targets.append(f"{self.file_system.file_system_id}.efs.{self.region}.amazonaws.com")
        
        self.add_output(
            "MountTargets",
            value=Fn.join(",", mount_targets),
            description="EFS mount targets"
        )
    
    def get_efs_volume_configuration(self) -> dict:
        """Get EFS volume configuration for Fargate task definition.
        
        Returns:
            Dictionary with EFS volume configuration
        """
        return {
            "name": "n8n-data",
            "efs_volume_configuration": {
                "file_system_id": self.file_system.file_system_id,
                "transit_encryption": "ENABLED",
                "authorization_config": {
                    "access_point_id": self.n8n_access_point.access_point_id,
                    "iam": "ENABLED"
                }
            }
        }
    
    def grant_read_write(self, grantee: iam.IGrantable) -> None:
        """Grant read/write permissions to EFS.
        
        Args:
            grantee: IAM grantable (role, user, etc.)
        """
        self.file_system.grant_read_write(grantee)