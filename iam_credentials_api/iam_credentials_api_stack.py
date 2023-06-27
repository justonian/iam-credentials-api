from constructs import Construct

from aws_cdk import (
    aws_lambda as lambd,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_iam as iam,
)

import aws_cdk as core


class IamCredentialsApiStack(core.Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        sessions_dynamo_table = dynamodb.Table(self, "SessionsTable",
            partition_key=dynamodb.Attribute(
                name="sessionId",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=core.RemovalPolicy.DESTROY
        )

        def create_authorizer():
            authorizer_lambda = lambd.Function(self, "AuthorizerLambda",
                runtime=lambd.Runtime.PYTHON_3_8,
                handler="authorizer.handler",
                code=lambd.Code.from_asset("authorizer")
            )

            authorizer = apigateway.TokenAuthorizer(self, "Authorizer",
                handler=authorizer_lambda,
                identity_source=apigateway.IdentitySource.header("Authorization"),
            )

            authorizer_lambda.add_to_role_policy(iam.PolicyStatement(
                actions=["dynamodb:Query"],
                effect=iam.Effect.ALLOW,
                resources=[sessions_dynamo_table.table_arn]
            ))

            return authorizer

        
        # Lambda functions
        create_session_lambda = lambd.Function(self, "CreateSession",
            runtime=lambd.Runtime.PYTHON_3_8,
            handler="create_session.handler",
            code=lambd.Code.from_asset("src"),
            environment={
                "SESSIONS_TABLE_NAME": sessions_dynamo_table.table_name
            }
        )

        get_credentials_lambda = lambd.Function(self, "GetCredentials",
            runtime=lambd.Runtime.PYTHON_3_8,
            handler="get_credentials.handler",
            code=lambd.Code.from_asset("src"),
            environment={
                "SESSIONS_TABLE_NAME": sessions_dynamo_table.table_name
            }
        )

        update_session_lambda = lambd.Function(self, "UpdateSession",
            runtime=lambd.Runtime.PYTHON_3_8,
            handler="update_session.handler",
            code=lambd.Code.from_asset("src"),
            environment={
                "SESSIONS_TABLE_NAME": sessions_dynamo_table.table_name
            }
        )

        sessions_dynamo_table.grant_read_write_data(create_session_lambda)
        sessions_dynamo_table.grant_read_data(get_credentials_lambda)
        sessions_dynamo_table.grant_read_write_data(update_session_lambda)

        # API Gateway
        api = apigateway.RestApi(self, "CredentialsApi",
            rest_api_name="Credentials API",
            description="Dynamic IAM Credentials Gateway",
            # default_method_options=apigateway.MethodOptions(
            #     authorization_type=apigateway.AuthorizationType.CUSTOM,
            #     # authorizer=apigateway.TokenAuthorizerConfig(
            #     #     authorizer_id=create_authorizer().authorizer_id
            #     # ),
            # )
        )
        auth = create_authorizer()

        session_resource = api.root.add_resource("sessions")

        # API Gateway Resources and Methods
        session_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(create_session_lambda),
        )
        session_resource_child = session_resource.add_resource("{sessionId}")
        session_resource_child.add_resource(
            "cluster").add_resource(
            "{clusterId}").add_resource(
            "project").add_resource(
            "{projectId}").add_resource(
            "clusterNode").add_resource(
            "{clusterNodeId}").add_method(
            "GET",
            apigateway.LambdaIntegration(get_credentials_lambda),
            authorizer=auth,
        )

        session_resource_child.add_method(
            "PUT",
            apigateway.LambdaIntegration(update_session_lambda),
            authorizer=auth,
        )

    


app = core.App()
IamCredentialsApiStack(app, 'IamCredentialsApiStackInstance')
app.synth()