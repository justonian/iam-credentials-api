#!/usr/bin/env python3
import os

import aws_cdk as cdk

from iam_credentials_api.iam_credentials_api_stack import IamCredentialsApiStack


app = cdk.App()
env = app.node.try_get_context('env')
if not env:
    raise Exception("Env not defined. Please include env variable using the following syntax. --context=env=Dev Default env is Dev, but should be updated for production")
IamCredentialsApiStack(app, "IamApi" + env,
    # If you don't specify 'env', this stack will be environment-agnostic.
    # Account/Region-dependent features and context lookups will not work,
    # but a single synthesized template can be deployed anywhere.

    # Uncomment the next line to specialize this stack for the AWS Account
    # and Region that are implied by the current CLI configuration.

    #env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),

    # Uncomment the next line if you know exactly what Account and Region you
    # want to deploy the stack to. */

    #env=cdk.Environment(account='123456789012', region='us-east-1'),

    # For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
    )

app.synth()
