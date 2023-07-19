import json
import uuid
import os
import boto3

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

    # Generate session token and construct response
    session_token = str(uuid.uuid4())
    print(event)
    print(context)
    # domainName and path from requestContext contain the path all the way to sessions/ complete
    # the path with sessionId/cluster/clusterId/project/projectId
    api_gateway_endpoint = event['requestContext']['domainName'] + event['requestContext']['path']  # Replace with your API Gateway endpoint
    response = {
        'credentialsAwsApiEndpoint': f"https://{api_gateway_endpoint}/{session_id}/cluster/{cluster_name}/project/{project_id}",
        'credentialsLocalApiEndpoint': f"http://localhost:9999/sessions/{session_id}/cluster/{cluster_name}/project/{project_id}",
        'authorizationToken': session_token
    }
    # Check if sessionId already exists
    session_response = table.query(
        KeyConditionExpression='sessionId = :id',
        ExpressionAttributeValues={
            ':id': session_id
        }
    )
    session_list = session_response['Items']

    if len(session_list) > 0:
        return {
            'statusCode': 400,
            'body': json.dumps({"message": "sessionId already exists"})
        }
    # Write session token to DynamoDB table
    table.put_item(
        Item={
            'sessionId': session_id,
            'projectId': project_id,
            'clusterName': cluster_name,
            'clusterUser': cluster_user,
            'sessionToken': session_token,
            'status': 'ACTIVE'
        }
    )

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
