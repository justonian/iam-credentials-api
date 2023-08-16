import json
import uuid
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['SESSIONS_TABLE_NAME']
table = dynamodb.Table(table_name)

def handler(event, context):
    # Validate body is present and proper JSON
    try:
        body = json.loads(event['body'])
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps({"message": "Missing request body"})
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({"message": "Invalid JSON format"})
        }

    # Validate all session creation properties are present and valid
    required_properties = ['sessionId', 'projectId', 'clusterName', 'clusterUser', 'submittedTime']
    for property in required_properties:
        if property not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({"message": "Missing property " + property + " in JSON body"})
            }
    
    # Extract request parameters
    session_id = body['sessionId']
    project_id = body['projectId']
    cluster_name = body['clusterName']
    cluster_user = body['clusterUser']
    submitted_time_string = body['submittedTime']
    try:
        submitted_time_number = int(datetime.strptime(submitted_time_string, "%Y-%m-%dT%H:%M:%S").timestamp())
    except:
        return {
                'statusCode': 400,
                'body': json.dumps({"message": "submittedTime not in ISO 8601 format"})
            }

    # Generate session token and construct response
    session_token = str(uuid.uuid4())
    # domainName and path from requestContext contain the path all the way to sessions/ complete
    # the path with sessionId/cluster/clusterId/project/projectId
    api_gateway_endpoint = event['requestContext']['domainName'] + event['requestContext']['path']  # Replace with your API Gateway endpoint
    api_gateway_endpoint_path = api_gateway_endpoint.split('/', 1)[1]
    response = {
        'APIGATEWAY_AWS_CONTAINER_CREDENTIALS_FULL_URI': f"https://{api_gateway_endpoint}/{session_id}/cluster/{cluster_name}/project/{project_id}",
        'LOCALHOST_AWS_CONTAINER_CREDENTIALS_FULL_URI': f"http://localhost:9999/{api_gateway_endpoint_path}/{session_id}/cluster/{cluster_name}/project/{project_id}",
        'AWS_CONTAINER_AUTHORIZATION_TOKEN': session_token
    }
    
    # TODO: Add logic to handle previuos sessions with same clusterId and sessionId. One option is to update those previous sessions to "Completed" here

    # Write new session details to DynamoDB table
    try:
        table.put_item(
            Item={
                'ClusterNameSessionId': cluster_name + "-" + session_id,
                'SessionId': session_id,
                'ProjectId': project_id,
                'ClusterName': cluster_name,
                'ClusterUser': cluster_user,
                'SessionToken': session_token,
                'Status': 'ACTIVE',
                'SubmittedTime': submitted_time_number,
                'LastUpdatedTime': submitted_time_number
            },
            ConditionExpression='attribute_not_exists(SessionId)'
        )
        return {
            'statusCode': 200,
            'body': json.dumps(response)
            }
    except:
        return {
            'statusCode': 400,
            'body': json.dumps({"message": "Cluster Name, Session ID, and Submitted Time already exist."})
        }
