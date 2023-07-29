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
    
    # the sessionId is not unique, it must be combined with clusterName
    response = table.query(
        KeyConditionExpression='sessionId = :id',
        ExpressionAttributeValues={
            ':id': event["pathParameters"]["sessionId"]
        }
    )
    items = response['Items']

    if len(items) != 1:
        return {
            'statusCode': 404,
            'body': json.dumps({"message": "sessionId invalid"})
        }
    # /sessions/{id}/cluster/{id}/project/{id}/clusterNode/{id}
    session = items[0]
    # TODO Validate status
    if session['status'] not in ["COMPLETED", "ACTIVE"]:
        return {
            'statusCode': 400,
            'body': json.dumps({"message": "Status can only be updated to ACTIVE or COMPLETED"})
        }
    session['status'] = body['status']

    # Write session token to DynamoDB table
    table.put_item(
        Item=session
    )
    del session['sessionToken']
    return {
        'statusCode': 200,
        'body': json.dumps(session)
    }
