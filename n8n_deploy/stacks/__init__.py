"""Stack definitions for n8n AWS Serverless CDK."""
from .access_stack import AccessStack
from .base_stack import N8nBaseStack
from .compute_stack import ComputeStack
from .database_stack import DatabaseStack
from .monitoring_stack import MonitoringStack
from .network_stack import NetworkStack
from .storage_stack import StorageStack

__all__ = [
    "N8nBaseStack",
    "NetworkStack",
    "StorageStack",
    "ComputeStack",
    "DatabaseStack",
    "AccessStack",
    "MonitoringStack",
]
