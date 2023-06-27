import aws_cdk as core
import aws_cdk.assertions as assertions

from iam_credentials_api.iam_credentials_api_stack import IamCredentialsApiStack

# example tests. To run these tests, uncomment this file along with the example
# resource in iam_credentials_api/iam_credentials_api_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = IamCredentialsApiStack(app, "iam-credentials-api")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
