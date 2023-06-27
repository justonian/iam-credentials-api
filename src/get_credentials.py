import boto3
import json
import os

dynamodb = boto3.resource('dynamodb')
sessions_table_name = os.environ['SESSIONS_TABLE_NAME']
sessions_table = dynamodb.Table(sessions_table_name)
iam_role_mapping_table_name = os.environ['IAM_ROLE_MAPPING_TABLE_NAME']
iam_role_mapping_table = dynamodb.Table(iam_role_mapping_table_name)

def handler(event, context):
    # Lookup Role ARN for project associated with job session
    response = sessions_table.query(
        KeyConditionExpression='sessionId = :id',
        ExpressionAttributeValues={
            ':id': event["pathParameters"]["sessionId"]
        }
    )
    items = response['Items']

    if len(items) != 1:
        raise Exception("Session does not exist")
    # /sessions/{id}/cluster/{id}/project/{id}/clusterNode/{id}
    item = items[0]
    response = iam_role_mapping_table.query(
        KeyConditionExpression='projectId = :id',
        ExpressionAttributeValues={
            ':id': item["projectId"]
        }
    )
    items = response['Items']
    if len(items) != 1:
        raise Exception("Role Mapping does not exists")
    out = assume_iam_role(items[0]["roleArn"], event["pathParameters"]["clusterNodeId"])
    return {
        'statusCode': 200,
        'body': json.dumps(out)
    }

def assume_iam_role(role_arn, session_name):
    # Create a STS client
    sts_client = boto3.client('sts')

    # Assume the IAM role
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )
    print(response)
    # datetime not serializable
    response['Credentials']['Expiration'] = str(response['Credentials']['Expiration'].utcnow())
    return response
    # # Extract the temporary credentials
    # credentials = response['Credentials']
    # access_key = credentials['AccessKeyId']
    # secret_key = credentials['SecretAccessKey']
    # session_token = credentials['SessionToken']
