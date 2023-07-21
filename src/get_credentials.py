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
        return {
            'statusCode': 404,
            'body': json.dumps({"message": "sessionId does not exists"})
        }
    # /sessions/{id}/cluster/{id}/project/{id}
    session = items[0]
    response = iam_role_mapping_table.query(
        KeyConditionExpression='projectId = :id',
        ExpressionAttributeValues={
            ':id': session["projectId"]
        }
    )
    if "status" not in session:
        return {
            'statusCode': 500,
            'body': json.dumps({"message": "All sessions must have a status"})
        }
    if session["clusterName"] != event["pathParameters"]["clusterId"]:
        return {
            'statusCode': 400,
            'body': '{"message": "clusterId does not match session clusterId"}'
        }
    if session["projectId"] != event["pathParameters"]["projectId"]:
        return {
            'statusCode': 400,
            'body': '{"message": "projectId does not match session projectId"}'
        }
    if session["status"] not in ["ACTIVE"]:
        return {
            'statusCode': 403,
            'body': '{"message": "session is not ACTIVE"}'
        }
    items = response['Items']
    if len(items) != 1:
        return {
            'statusCode': 404,
            'body': json.dumps({"message": "There is no role mapping for given projectId"})
        }
    role_mapping = items[0]
    assume_role_args = {
       "RoleArn": role_mapping["roleArn"]
    }
    
    if event["queryStringParameters"] and "clusterNodeId" in event["queryStringParameters"]:
        assume_role_args["RoleSessionName"] = event["queryStringParameters"]["clusterNodeId"]
    else:
        return {
            'statusCode': 400,
            'body': '{"message": "Missing clusterNodeId queryParameter"}'
        }
    out = assume_iam_role(assume_role_args)
    return {
        'statusCode': 200,
        'body': json.dumps(out)
    }

def assume_iam_role(assume_role_args):
    # Create a STS client
    sts_client = boto3.client('sts')

    # Assume the IAM role
    response = sts_client.assume_role(**assume_role_args)
    # datetime not serializable
    creds = response['Credentials']
    return {
        "AccessKeyId": creds["AccessKeyId"],
        "Expiration": str(creds['Expiration']),
        "RoleArn": assume_role_args["RoleArn"],
        "SecretAccessKey": creds["SecretAccessKey"],
        "Token": creds["SessionToken"],
    }
