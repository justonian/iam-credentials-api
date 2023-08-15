from constructs import Construct

from aws_cdk import (
    aws_lambda as lambd,
    aws_dynamodb as dynamodb,
    aws_apigateway as apigateway,
    aws_iam as iam,
    CfnOutput,
    aws_secretsmanager as secretsmanager
)

import aws_cdk as core

class IamCredentialsApiStack(core.Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        env = self.node.try_get_context('env')
        if not env:
            raise Exception("env is not defined")

        head_node_secret = secretsmanager.Secret(self, "HeadNodeSecret", secret_name="IamApi" + env + "-HeadNodeSecret");

        sessions_dynamo_table = dynamodb.Table(self, "SessionsTable",
            partition_key=dynamodb.Attribute(
                name="ClusterNameSessionId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SubmittedTime",
                type=dynamodb.AttributeType.NUMBER
            ),
            removal_policy=core.RemovalPolicy.DESTROY
        )

        iam_role_mapping_dynamo_table = dynamodb.Table(self, "IamRoleMappingTable",
            partition_key=dynamodb.Attribute(
                name="ProjectId",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=core.RemovalPolicy.DESTROY
        )

        # Global Secondary Index
        session_token_gsi = sessions_dynamo_table.add_global_secondary_index(
            index_name="SessionTokenGSI",
            partition_key=dynamodb.Attribute(
                name="SessionToken",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        def create_authorizer():
            authorizer_lambda = lambd.Function(self, "AuthorizerLambda",
                runtime=lambd.Runtime.PYTHON_3_8,
                handler="authorizer.handler",
                code=lambd.Code.from_asset("authorizer"),
                environment={
                    "SESSIONS_TABLE_NAME": sessions_dynamo_table.table_name,
                    "HEAD_NODE_SECRET": head_node_secret.secret_name,
                }
            )
            sessions_dynamo_table.grant_read_data(authorizer_lambda)

            authorizer = apigateway.TokenAuthorizer(self, "Authorizer",
                handler=authorizer_lambda,
                identity_source=apigateway.IdentitySource.header("Authorization"),
            )
            authorizer_lambda.add_to_role_policy(iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                effect=iam.Effect.ALLOW,
                resources=[head_node_secret.secret_arn]
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
                "SESSIONS_TABLE_NAME": sessions_dynamo_table.table_name,
                "IAM_ROLE_MAPPING_TABLE_NAME": iam_role_mapping_dynamo_table.table_name,
            }
        )

        get_credentials_inline_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sts:AssumeRole"],
            resources=["*"]
        )

        # Add inline policy to Lambda function's role
        get_credentials_lambda.role.add_to_policy(get_credentials_inline_policy)

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
        iam_role_mapping_dynamo_table.grant_read_data(get_credentials_lambda)

        # API Gateway
        api = apigateway.RestApi(self, "CredentialsApi",
            deploy_options=apigateway.StageOptions(
                tracing_enabled=True
            ),
            endpoint_types=[
                apigateway.EndpointType.REGIONAL
            ],
            rest_api_name="IamApi"+env,
            description="IAM Credentials API" + " " + env,
        )
        auth = create_authorizer()

        session_resource = api.root.add_resource("sessions")

        # API Gateway Resources and Methods
        session_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(create_session_lambda),
            authorizer=auth,
        )
        session_resource_child = session_resource.add_resource("{sessionId}").add_resource("cluster").add_resource("{clusterId}")
        session_resource_child.add_method(
            "PUT",
            apigateway.LambdaIntegration(update_session_lambda),
            authorizer=auth,
        )

        session_resource_child.add_resource(
            "project").add_resource(
            "{projectId}").add_method(
            "GET",
            apigateway.LambdaIntegration(get_credentials_lambda),
            authorizer=auth,
        )

        CfnOutput(self, 'RoleTableName', value=iam_role_mapping_dynamo_table.table_name)
        CfnOutput(self, 'SessionseTableName', value=sessions_dynamo_table.table_name)
        CfnOutput(self, 'GetCredentialsLambdaRoleArn', value=get_credentials_lambda.role.role_arn)
        CfnOutput(self, 'HeadNodeSecretArn', value=head_node_secret.secret_arn)
