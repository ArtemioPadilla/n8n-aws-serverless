import aws_cdk as core
import aws_cdk.assertions as assertions

from n8n_deploy.n8n_deploy_stack import N8NAwsServerlessStack


# example tests. To run these tests, uncomment this file along with the example
# resource in n8n_deploy/n8n_deploy_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = N8NAwsServerlessStack(app, "n8n-aws-serverless")
    template = assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
