"""Stack definitions for n8n AWS Serverless CDK."""
from .base_stack import N8nBaseStack
from .network_stack import NetworkStack
from .storage_stack import StorageStack
from .compute_stack import ComputeStack
from .database_stack import DatabaseStack
from .access_stack import AccessStack
from .monitoring_stack import MonitoringStack

__all__ = [
    "N8nBaseStack",
    "NetworkStack", 
    "StorageStack",
    "ComputeStack",
    "DatabaseStack",
    "AccessStack",
    "MonitoringStack",
]