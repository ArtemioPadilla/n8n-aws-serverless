from aws_cdk import Stack  # Duration,; aws_sqs as sqs,
from constructs import Construct


class N8NAwsServerlessStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "N8NAwsServerlessQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )
