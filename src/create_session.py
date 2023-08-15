import json
import uuid
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['SESSIONS_TABLE_NAME']
table = dynamodb.Table(table_name)

def handler(event, context):
    try:
        body = json.loads(event['body'])
    except KeyError:
        return {
            'statusCode': 400,
            'body': 'Missing request body'
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': 'Invalid JSON format'
        }
    # Extract request parameters
    session_id = body['sessionId']
    project_id = body['projectId']
    cluster_name = body['clusterName']
    cluster_user = body['clusterUser']
    submitted_time_string = body['submittedTime']
    submitted_time_number = int(datetime.strptime(submitted_time_string, "%Y-%m-%dT%H:%M:%S").timestamp())

    # Generate session token and construct response
    session_token = str(uuid.uuid4())
    print(event)
    print(context)
    # domainName and path from requestContext contain the path all the way to sessions/ complete
    # the path with sessionId/cluster/clusterId/project/projectId
    api_gateway_endpoint = event['requestContext']['domainName'] + event['requestContext']['path']  # Replace with your API Gateway endpoint
    api_gateway_endpoint_path = api_gateway_endpoint.split('/', 1)[1]
    response = {
        'APIGATEWAY_AWS_CONTAINER_CREDENTIALS_FULL_URI': f"https://{api_gateway_endpoint}/{session_id}/cluster/{cluster_name}/project/{project_id}",
        'LOCALHOST_AWS_CONTAINER_CREDENTIALS_FULL_URI': f"http://localhost:9999/{api_gateway_endpoint_path}/{session_id}/cluster/{cluster_name}/project/{project_id}",
        'AWS_CONTAINER_AUTHORIZATION_TOKEN': session_token
    }
    # Check if sessionId already exists
    session_response = table.query(
        KeyConditionExpression='ClusterNameSessionId = :clusterNameSessionId AND SubmittedTime = :submittedTimeId',
        ExpressionAttributeValues={
            ':clusterNameSessionId': cluster_name + "-" + session_id,
            ':submittedTimeId': submitted_time_number
        }
    )
    session_list = session_response['Items']

    if len(session_list) > 0:
        return {
            'statusCode': 400,
            'body': json.dumps({"message": "Cluster Name, Session ID, and Submitted Time already exist."})
        }
    # Write session token to DynamoDB table
    table.put_item(
        Item={
            'ClusterNameSessionId': cluster_name + "-" + session_id,
            'SessionId': session_id,
            'ProjectId': project_id,
            'ClusterName': cluster_name,
            'ClusterUser': cluster_user,
            'SessionToken': session_token,
            'Status': 'ACTIVE',
            'SubmittedTime': submitted_time_number
        },
        ConditionExpression='attribute_not_exists(sessionId)'
    )

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
